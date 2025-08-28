from collections import deque
from loguru import logger

from abstract_types import StructFieldType, ABS_UNKNOWN
from dense_graph import DenseGraph, OperationEdge, DereferenceEdge, AddressOfEdge, GetFieldOffsetEdge, \
    GetArrayElementEdge
from ssa_objects import Constant, Variable
from type_definitions import UNKNOWN, IntType, FloatType, PointerType, BaseType, UnionType, UnknownType, StructType, \
    RecursiveType, ArrayType, BoolType


class TypePropagator:
    def __init__(self, graph: DenseGraph):
        self.graph = graph
        self.worklist = deque()
        self.struct_definitions = {}

    def get_graph(self):
        return self.graph

    def _reset_all_types(self):
        for node in self.graph.nodes.values():
            node.type = UNKNOWN

    def _update_getelementoffset_edge(self):

        #self.graph.generate_dot("graph_before_transformation.dot")
        edges_to_transform = []
        edges_to_transform_array = []

        for source_a, target_b, edge_ab in self.graph.iter_edges():

            if isinstance(edge_ab, OperationEdge) and edge_ab.op_name == "IntAdd":
                if len(edge_ab.operands) > 0 and isinstance(edge_ab.operands[0], Constant):
                    offset = edge_ab.operands[0].value

                    is_dereferenced = any(
                        isinstance(edge, DereferenceEdge)
                        for edge_list in self.graph.edges.get(target_b, {}).values()
                        for edge in edge_list
                    )

                    node_a = self.graph.get_node(source_a)
                    node_b = self.graph.get_node(target_b)
                    if is_dereferenced or isinstance(node_b.type, PointerType) or isinstance(node_a.type, PointerType):
                        edges_to_transform.append((source_a, target_b, edge_ab, offset))


                elif len(edge_ab.operands) > 0 and isinstance(source_a,
                                                              Constant) and source_a.value != 0 and isinstance(
                        edge_ab.operands[0], Variable):
                    offset = source_a.value

                    is_dereferenced = any(
                        isinstance(edge, DereferenceEdge)
                        for edge_list in self.graph.edges.get(target_b, {}).values()
                        for edge in edge_list
                    )

                    if is_dereferenced:
                        edges_to_transform.append((edge_ab.operands[0], target_b, edge_ab, offset))

                    pass
                elif len(edge_ab.operands) > 0 and isinstance(edge_ab.operands[0], Variable) and isinstance(source_a,
                                                                                                            Variable) and isinstance(
                        target_b, Variable):
                    edges_to_transform_array.append((source_a, target_b, edge_ab, edge_ab.operands[0]))

        if not edges_to_transform and not edges_to_transform_array:
            return False

        for source_id, target_id, old_edge, offset in edges_to_transform:
            self.graph.remove_edge(source_id, target_id, old_edge)

            new_edge = GetFieldOffsetEdge(offset)
            self.graph.add_edge(source_id, target_id, new_edge)


        for source_id, target_id, old_edge, var in edges_to_transform_array:
            self.graph.remove_edge(source_id, target_id, old_edge)

            new_edge = GetArrayElementEdge(var)
            self.graph.add_edge(source_id, target_id, new_edge)


        #self.graph.generate_dot("graph_after_transformation.dot")

        return True


    def _type_contains(self, haystack: 'Type', needle: 'Type') -> bool:
        if haystack == needle: return True
        if isinstance(haystack, PointerType): return self._type_contains(haystack.points_to, needle)
        if isinstance(haystack, UnionType): return any(self._type_contains(t, needle) for t in haystack.types)
        return False

    def _update_node_type(self, node_id, new_type) -> bool:
        node = self.graph.get_node(node_id)
        if not node: return False
        current_type = node.type

        if self._type_contains(new_type, current_type) and not isinstance(current_type, (UnknownType, BaseType)):
            #rec_name = f"rec_{node_id.name}" if hasattr(node_id, 'name') else "rec_unknown"
            #final_type = PointerType(RecursiveType(rec_name))
            final_type = new_type
        else:
            final_type = new_type.join(current_type)

        if final_type and final_type != current_type:
            node.type = final_type
            if node_id not in self.worklist: self.worklist.append(node_id)
            for pred_id in self.graph.reverse_edges.get(node_id, {}):
                if pred_id not in self.worklist: self.worklist.append(pred_id)
            for succ_id in self.graph.edges.get(node_id, {}):
                if succ_id not in self.worklist: self.worklist.append(succ_id)
            return True
        return False

    def _get_or_create_struct_def(self, name: str) -> StructType:
        if name not in self.struct_definitions:
            self.struct_definitions[name] = StructType(name, {0: UNKNOWN}) #ensure structures must have at least one field
        return self.struct_definitions[name]

    def _update_struct_field(self, ptr_id, offset: int, field_type: 'Type'):
        ptr_node = self.graph.get_node(ptr_id)
        if not (ptr_node and isinstance(ptr_node.type, PointerType)): return False
        base_struct_type = ptr_node.type.points_to
        struct_name = f"struct_{ptr_id.name}" if isinstance(ptr_id, Variable) else "struct_const"
        if isinstance(base_struct_type, StructType): struct_name = base_struct_type.name
        canonical_def = self._get_or_create_struct_def(struct_name)
        new_info = StructType(struct_name, {offset: field_type})
        updated_def = canonical_def.join(new_info)
        if updated_def != canonical_def or not isinstance(base_struct_type, StructType):
            self.struct_definitions[struct_name] = updated_def
            return self._update_node_type(ptr_id, PointerType(updated_def))
        return False

    def _get_node_type(self, var_name: str):
        node_id = self.graph.find_node_by_name(var_name)
        if not node_id:
            return UNKNOWN

        node = self.graph.get_node(node_id)
        if not node:
            return UNKNOWN

        raw_type = node.type

        simplified_type = self._simplify_type(raw_type, set())

        return simplified_type

    def _update_abstract_type(self, node_id, new_abs_type) -> bool:
        node = self.graph.get_node(node_id)
        if not node: return False

        current_abs_type = node.abstract_type

        if new_abs_type != current_abs_type:
            node.abstract_type = new_abs_type

            if node_id not in self.worklist: self.worklist.append(node_id)
            for pred_id in self.graph.reverse_edges.get(node_id, {}):
                if pred_id not in self.worklist: self.worklist.append(pred_id)
            for succ_id in self.graph.edges.get(node_id, {}):
                if succ_id not in self.worklist: self.worklist.append(succ_id)
            return True
        return False

    def _update_struct_array_member(self, ptr_id, array_type: 'ArrayType'):
        ptr_node = self.graph.get_node(ptr_id)
        if not (ptr_node and isinstance(ptr_node.type, PointerType)): return False

        base_struct_type = ptr_node.type.points_to
        if not isinstance(base_struct_type, StructType): return False

        new_struct_def = base_struct_type.join(StructType(base_struct_type.name, {}, array_type))

        if new_struct_def != base_struct_type:
            self.struct_definitions[new_struct_def.name] = new_struct_def
            return self._update_node_type(ptr_id, PointerType(new_struct_def))
        return False

    def _apply_rules_for_node(self, node_id):
        node = self.graph.get_node(node_id)
        if not node: return False

        changed = False
        transofrmed_edge = []
        for pred_id, edge_list in self.graph.reverse_edges.get(node_id, {}).items():
            pred_node = self.graph.get_node(pred_id)
            if not pred_node: continue
            for edge in edge_list:
                current_node_type = node.type
                current_pred_type = pred_node.type

                if isinstance(edge, GetFieldOffsetEdge):
                    if not isinstance(pred_node.type, PointerType) and isinstance(node.type, PointerType):
                        self._update_node_type(pred_id, PointerType(node.type.points_to))
                    if isinstance(pred_node.type, PointerType) and not isinstance(pred_node.type.points_to,
                                                                                  StructType) and isinstance(pred_id,
                                                                                                             Variable):
                        prev_pred_node_type = pred_node.type.points_to
                        self._update_node_type(pred_id, PointerType(StructType(f"struct_{pred_id.name}", {})))
                        self._update_struct_field(pred_id, 0, prev_pred_node_type)
                        changed = (current_pred_type != pred_node.type)

                    # if not isinstance(node.type, PointerType) and self._update_node_type(node_id, PointerType(node.type)):
                    #     changed = (current_node_type != node.type)

                    if isinstance(pred_node.type, PointerType) and isinstance(node.type, PointerType):
                        field_type = node.type.points_to
                        for val_id, out_edges in self.graph.edges.get(node_id, {}).items():
                            if any(isinstance(e, DereferenceEdge) for e in out_edges):
                                if val_node := self.graph.get_node(val_id):
                                    field_type = field_type.join(val_node.type)

                        if isinstance(field_type, StructType) and field_type.name == pred_node.type.points_to.name:
                            type_name = field_type.name
                            field_type = RecursiveType(type_name)

                        if self._update_struct_field(pred_id, edge.offset, field_type):
                            changed = (current_pred_type != pred_node.type)

                    elif isinstance(pred_node.type, PointerType):
                        field_type = node.type
                        for val_id, out_edges in self.graph.edges.get(node_id, {}).items():
                            if any(isinstance(e, DereferenceEdge) for e in out_edges):
                                if val_node := self.graph.get_node(val_id):
                                    field_type = field_type.join(val_node.type)
                        if self._update_struct_field(pred_id, edge.offset, field_type):
                            changed = (current_pred_type != pred_node.type)

                elif isinstance(edge, GetArrayElementEdge):
                    element_type = UNKNOWN
                    if isinstance(node.type, PointerType):
                        element_type = node.type.points_to

                    self._update_node_type(pred_id, ArrayType(element_type))

                    if isinstance(pred_node.type, PointerType) and isinstance(pred_node.type.points_to, ArrayType):
                        elem_ptr_type = PointerType(pred_node.type.points_to.element_type)
                        self._update_node_type(node_id, elem_ptr_type)
                        self._update_struct_array_member(pred_id, pred_node.type.points_to)

                elif isinstance(edge, DereferenceEdge):

                    if pred_id == node_id:
                        if isinstance(node.type, PointerType) and isinstance(node.type.points_to, StructType):

                            struct_name = f"struct_{node_id.name}" if isinstance(node_id,
                                                                                 Variable) else "struct_recursive"

                            struct_def = self._get_or_create_struct_def(struct_name)

                            recursive_pointer_type = PointerType(RecursiveType(struct_name))

                            self._update_struct_field(node_id, 0, recursive_pointer_type)

                            self._update_node_type(node_id, recursive_pointer_type)
                            self._update_node_type(pred_id, recursive_pointer_type)
                        pass

                    elif not isinstance(pred_node.type, PointerType) and self._update_node_type(pred_id,
                                                                                                PointerType(node.type)):
                        changed = (current_pred_type != pred_node.type)
                    elif isinstance(pred_node.type, PointerType) and node.type != pred_node.type.points_to:
                        if self._update_node_type(pred_id, PointerType(node.type)):
                            changed = (current_pred_type != pred_node.type)

                elif isinstance(edge, AddressOfEdge):
                    # print(f"Store: {pred_id} {pred_node.type} \n-> {node_id} {node.type}\n")
                    if not isinstance(pred_node, Constant) and node.type != PointerType(
                            pred_node.type) and self._update_node_type(node_id, PointerType(pred_node.type)):
                        changed = (current_node_type != node.type)
                        # store 0 -> var
                    elif isinstance(pred_node, Constant) and not isinstance(node.type,
                                                                            PointerType) and self._update_node_type(
                            node_id, PointerType(IntType())):
                        changed = (current_node_type != node.type)

                elif isinstance(edge, OperationEdge):
                    if edge.op_name == "IntAdd":
                        if isinstance(pred_node.type, PointerType) and isinstance(edge.operands[0], Constant):
                            # self.graph.remove_edge(pred_id, node_id, edge)
                            offset = edge.operands[0].value
                            new_edge = GetFieldOffsetEdge(offset)
                            # self.graph.add_edge(pred_id, node_id, new_edge)
                            transofrmed_edge.append((pred_id, node_id, edge, new_edge))
                            changed = True
                        elif pred_node.type != PointerType(node.type) and self._update_node_type(node_id, IntType()):
                            changed = (current_node_type != node.type)

                    elif edge.op_name == "IntZext":
                        if not isinstance(pred_node.type, IntType) and self._update_node_type(node_id, IntType()):
                            changed = (current_node_type != node.type)
                    elif edge.op_name == "IntEqual":
                        if not isinstance(pred_node.type, IntType) and self._update_node_type(pred_id, IntType()):
                            changed = (current_pred_type != pred_node.type)
                    elif edge.op_name == "IntSLess":
                        if self._update_node_type(node_id, BoolType()):
                            changed = (current_node_type != node.type)
                    elif edge.op_name == "Popcount":
                        if self._update_node_type(node_id, IntType()):
                            changed = (current_node_type != node.type)

        # if len(transofrmed_edge) > 0:
        #     for pred_id, node_id, edge, new_edge in transofrmed_edge:
        #         self.graph.remove_edge(node_id, node_id, edge)
        #         self.graph.add_edge(pred_id, node_id, new_edge)
        #     changed = True

        return changed

    def run(self):
        #self._reset_all_types()
        self._update_getelementoffset_edge()
        self.worklist.extend(self.graph.nodes.keys())

        iteration = 0

        # file_name = "iter_" + str(iteration) + ".dot"
        # self.get_graph().generate_dot(file_name)

        max_iterations = len(self.graph.nodes) * 50
        while self.worklist and iteration < max_iterations:
            iteration += 1
            node_id = self.worklist.popleft()

            changed = self._apply_rules_for_node(node_id)
            # file_name = "iter_" + str(iteration) + ".dot"
            # self.get_graph().generate_dot(file_name)


        if iteration >= max_iterations:
            logger.warning(f"reaching max {max_iterations}，")
        else:
            logger.success(f"reached fixed point")

    def get_final_simplified_types(self) -> dict:
        final_types = {}
        for node_id, node in self.graph.nodes.items():
            if isinstance(node_id, Variable):
                final_types[node_id] = node.type

        simplified_types = {}
        for var, var_type in final_types.items():
            simplified_types[var] = self._simplify_type(var_type, {})

        return simplified_types

    def _simplify_type(self, t: 'Type', simplified_cache: dict) -> 'Type':
        if id(t) in simplified_cache:
            return simplified_cache[id(t)]

        simplified_cache[id(t)] = t

        result = t
        if isinstance(t, PointerType):
            simplified_points_to = self._simplify_type(t.points_to, simplified_cache)
            result = PointerType(simplified_points_to)
        elif isinstance(t, StructType):
            simplified_fields = {
                offset: self._simplify_type(ft, simplified_cache)
                for offset, ft in t.fields
            }
            result = StructType(t.name, simplified_fields)
        elif isinstance(t, UnionType):
            simplified_members = {self._simplify_type(sub_type, simplified_cache) for sub_type in t.types}
            struct_types = {m for m in simplified_members if isinstance(m, StructType)}
            base_types = {m for m in simplified_members if isinstance(m, BaseType) and m.name.startswith('rec_')}
            if struct_types and base_types:
                survivors = set(simplified_members)
                for st in struct_types:
                    rec_name_to_find = "rec_" + st.name.replace("struct_", "")
                    if any(bt.name == rec_name_to_find for bt in base_types):
                        survivors = {s for s in survivors if
                                     not (isinstance(s, BaseType) and s.name == rec_name_to_find)}
                result = UnionType(list(survivors))
            else:
                result = UnionType(list(simplified_members))

        if isinstance(result, PointerType) and isinstance(result.points_to, StructType):
            struct_def = result.points_to
            if len(struct_def.fields) == 1:
                offset, field_type = next(iter(struct_def.fields))
                if offset == 0: result = PointerType(field_type)

        if isinstance(result, UnionType) and len(result.types) == 1:
            result = next(iter(result.types))

        simplified_cache[id(t)] = result
        return result

    def print_struct_definitions(self):
        print("\n\n" + "#" * 40)
        print("###" + " " * 10 + "structure type " + " " * 10 + "###")
        print("#" * 40)

        if not self.struct_definitions:
            print("\ncannot find any structure type definition.")
            return

        simplified_defs = {}
        for name, struct_def in self.struct_definitions.items():
            simplified_defs[name] = self._simplify_type(struct_def, {})

        structs_to_print = {
            name: s_def for name, s_def in simplified_defs.items()
            if isinstance(s_def, StructType) and (
                        len(s_def.fields) > 1 or (len(s_def.fields) == 1 and next(iter(s_def.fields))[0] != 0))
        }

        if not structs_to_print:
            print("\nall structures are empty or only have one field at offset 0.")
            return

        sorted_struct_names = sorted(structs_to_print.keys())
        for name in sorted_struct_names:
            struct_def = structs_to_print[name]
            print(f"\nstruct {name} {{")
            sorted_fields = sorted(list(struct_def.fields), key=lambda item: item[0])
            for offset, field_type in sorted_fields:
                field_name = f"field_{hex(offset)}"
                print(f"  /* offset {hex(offset)} */  {repr(field_type)} {field_name};")
            print("};")

    def _resolve_and_simplify_type(self, t: 'Type', cache: dict):
        if id(t) in cache:
            return cache[id(t)]

        cache[id(t)] = BaseType(f"resolving_{id(t)}")

        simplified_t = t
        if isinstance(t, PointerType):
            simplified_points_to = self._resolve_and_simplify_type(t.points_to, cache)
            simplified_t = PointerType(simplified_points_to)
        elif isinstance(t, StructType):
            simplified_fields = {
                offset: self._resolve_and_simplify_type(ft, cache)
                for offset, ft in t.fields
            }
            simplified_t = StructType(t.name, simplified_fields)
        elif isinstance(t, UnionType):
            simplified_members = {self._resolve_and_simplify_type(m, cache) for m in t.types}
            simplified_t = UnionType(list(simplified_members))

        if isinstance(simplified_t, PointerType) and isinstance(simplified_t.points_to,
                                                                BaseType) and simplified_t.points_to.name.startswith(
                'rec_'):
            rec_name = simplified_t.points_to.name
            struct_name = rec_name.replace('rec_', 'struct_')
            if struct_name in self.struct_definitions:
                final_struct_def = self._resolve_and_simplify_type(self.struct_definitions[struct_name], cache)
                simplified_t = PointerType(final_struct_def)

        if isinstance(simplified_t, UnionType) and len(simplified_t.types) == 1:
            simplified_t = next(iter(simplified_t.types))

        cache[id(t)] = simplified_t
        return simplified_t

    def get_final_report(self) -> (dict, dict):
        raw_types = {node_id: node.type for node_id, node in self.graph.nodes.items() if isinstance(node_id, Variable)}

        final_types = {var: self._resolve_and_simplify_type(t, {}) for var, t in raw_types.items()}
        final_structs = {name: self._resolve_and_simplify_type(s, {}) for name, s in self.struct_definitions.items()}

        return final_types, final_structs

    def print_final_report(self):
        final_types, final_structs = self.get_final_report()


        print("\n\n" + "#" * 40);
        print("###" + " " * 9 + "final type" + " " * 10 + "###");
        print("#" * 40)
        sorted_vars = sorted(final_types.items(),
                             key=lambda i: (int(i[0].name[1:]) if i[0].name[1:].isdigit() else 9999, i[0].name))
        for var, var_type in sorted_vars:
            if var_type != UNKNOWN: print(f"  - {var.name}: {var_type!r}")

        print("\n\n" + "#" * 40);
        print("###" + " " * 10 + "structure type" + " " * 11 + "###");
        print("#" * 40)
        if not final_structs: print("\ncannot find any structure definition。"); return
        for name, struct_def in sorted(final_structs.items()):
            print(f"\nstruct {name} {{")
            if not struct_def.fields:
                print("  // empty struct")
            else:
                for offset, field_type in sorted(list(struct_def.fields)):
                    print(f"  /* offset {hex(offset)} */  {repr(field_type)} field_{hex(offset)};")
            print("};")

    def _print_variable_types_report(self, final_types: dict):
        print("\n\n" + "#" * 40)
        print("###" + " " * 9 + "var type" + " " * 10 + "###")
        print("#" * 40)

        if not final_types:
            return

        sorted_vars = sorted(
            final_types.items(),
            key=lambda item: (
                int(item[0].name[1:]) if item[0].name.startswith('v') and item[0].name[1:].isdigit() else 9999,
                item[0].name
            )
        )

        for var, var_type in sorted_vars:
            if var_type != UNKNOWN:
                print(f"  - {var.name}: {var_type!r}")

    def _print_struct_definitions_report(self):

        print("\n\n" + "#" * 40)
        print("###" + " " * 10 + " struct" + " " * 10 + "###")
        print("#" * 40)

        if not self.struct_definitions:
            print("\nfailed to find any struct definitions.")
            return

        simplified_defs = {}
        for name, struct_def in self.struct_definitions.items():
            simplified_defs[name] = self._simplify_type(struct_def, {})

        structs_to_print = {
            name: s_def for name, s_def in simplified_defs.items()
            if isinstance(s_def, StructType) and (
                    len(s_def.fields) > 1 or (len(s_def.fields) == 1 and next(iter(s_def.fields))[0] != 0))
        }

        if not structs_to_print:
            print("\nall structures are empty or only have one field at offset 0.")
            return

        sorted_struct_names = sorted(structs_to_print.keys())
        for name in sorted_struct_names:
            struct_def = structs_to_print[name]
            print(f"\nstruct {name} {{")
            sorted_fields = sorted(list(struct_def.fields), key=lambda item: item[0])
            for offset, field_type in sorted_fields:
                field_name = f"field_{hex(offset)}"
                print(f"  /* offset {hex(offset)} */  {repr(field_type)} {field_name};")
            print("};")

    def get_variable_type(self, var_name: str) -> 'Type':
        if isinstance(var_name, Variable):
            target_var = var_name.name
        else:
            target_var = var_name
        target_node = self.graph.find_node_by_name(target_var)
        if target_node is not None and isinstance(target_node, Constant):
            return IntType()
        final_types, _ = self.get_final_report()


        var_type = final_types.get(target_node)

        if var_type is not None:
            logger.success(f"succ: var: '{var_name}' type: {var_type!r}")
            return var_type
        else:
            logger.warning(f"failed: cannot find '{var_name}' type info")
            return UNKNOWN