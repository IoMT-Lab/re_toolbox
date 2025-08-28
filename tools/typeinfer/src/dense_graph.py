from collections import defaultdict, deque
from loguru import logger
import sys

from abstract_types import ABS_UNKNOWN
from ssa_objects import Variable, Constant
from type_definitions import UNKNOWN, IntType, PointerType, FloatType, StructType, Type, UnionType





class Edge:
    def __repr__(self): return self.__class__.__name__

    def __eq__(self, other): return isinstance(other, self.__class__)

    def __hash__(self): return hash(self.__class__.__name__)


class DereferenceEdge(Edge):
    def __repr__(self): return "*"


class AddressOfEdge(Edge):
    def __repr__(self): return "&"


class EqualsEdge(Edge):
    def __repr__(self): return "="


class OffsetEdge(Edge):
    def __init__(self, offset):
        if not isinstance(offset, int): raise TypeError("offset should be an integer.")
        self.offset = offset
        self.offset = offset

    def __repr__(self): return f"offset_{self.offset}"

    def __eq__(self, other): return isinstance(other, OffsetEdge) and self.offset == other.offset

    def __hash__(self): return hash(("OffsetEdge", self.offset))


class OperationEdge(Edge):
    def __init__(self, op_name: str, *operands):
        if not isinstance(op_name, str): raise TypeError("op should be a string.")
        self.op_name = op_name
        self.operands = operands
        self.op_name = op_name
        self.operands = operands
    def __repr__(self):
        if self.operands:
            operands_str = ", ".join(map(repr, self.operands))
            return f"{self.op_name}({operands_str})"
        return self.op_name
    def __eq__(self, other): return isinstance(other, OperationEdge) and self.op_name == other.op_name and self.operands == other.operands
    def __hash__(self): return hash(("OperationEdge", self.op_name, self.operands))

class FieldAccessEdge(Edge):
    def __init__(self, offset):
        self.offset = offset

    def __repr__(self): return f"field_access({self.offset})"

    def __eq__(self, other): return isinstance(other, FieldAccessEdge) and self.offset == other.offset

    def __hash__(self): return hash(("FieldAccessEdge", self.offset))


class GetFieldOffsetEdge(Edge):
    def __init__(self, offset):
        if not isinstance(offset, int): raise TypeError("Offset must be an integer.")
        self.offset = offset

    def __repr__(self):
        return f"GetFieldOffset({hex(self.offset)})"

    def __eq__(self, other):
        return isinstance(other, GetFieldOffsetEdge) and self.offset == other.offset

    def __hash__(self):
        return hash(("GetFieldOffsetEdge", self.offset))


class GetArrayElementEdge(Edge):
    def __init__(self, index_variable: Variable):
        if not isinstance(index_variable, Variable):
            raise TypeError("index_variable must be a Variable object.")
        self.index_variable = index_variable

    def __repr__(self):
        return f"GetArrayElement({self.index_variable!r})"

    def __eq__(self, other):
        return isinstance(other, GetArrayElementEdge) and self.index_variable == other.index_variable

    def __hash__(self):
        return hash(("GetArrayElementEdge", self.index_variable))

class Var:
    def __init__(self, name): self.name = name

    def __repr__(self): return f"Var({self.name})"


class EdgePattern:
    def __init__(self, edge_type, *args):
        self.edge_type = edge_type
        self.args = args

    def match(self, edge, bindings):
        if not isinstance(edge, self.edge_type): return None
        new_bindings = bindings.copy()
        edge_attrs = []
        if hasattr(edge, 'offset'): edge_attrs.append(edge.offset)
        if hasattr(edge, 'op_name'): edge_attrs.append(edge.op_name)
        if hasattr(edge, 'operands'): edge_attrs.extend(edge.operands)
        if len(self.args) != len(edge_attrs): return None
        for pattern_arg, edge_attr in zip(self.args, edge_attrs):
            if isinstance(pattern_arg, Var):
                var_name = pattern_arg.name
                if var_name in new_bindings and new_bindings[var_name] != edge_attr: return None
                new_bindings[var_name] = edge_attr
            elif callable(pattern_arg):
                try:
                    if pattern_arg(new_bindings) != edge_attr: return None
                except (KeyError, IndexError):
                    return None
            elif pattern_arg != edge_attr:
                return None
        return new_bindings


class CFLRule:
    def __init__(self, patterns, result_factory, condition=None):
        self.patterns = patterns
        self.result_factory = result_factory
        self.condition = condition



class GraphNode:
    def __init__(self, node_id, initial_type=UNKNOWN):
        if not isinstance(node_id, (str, int, Constant, Variable)):
            raise TypeError("wrong id")
        self.id = node_id
        self.values = set()
        self.type = initial_type
        self.abstract_type = ABS_UNKNOWN
        self.in_edges = defaultdict(list)
        self.out_edges = defaultdict(list)

    def add_value(self, value):
        if not isinstance(value, (Variable, Constant)):
            raise TypeError("type error")
        self.values.add(value)

    def __repr__(self):
        return f"Node({self.id!r})"


class DenseGraph:
    def __init__(self):
        self.nodes = {}
        self.edges = defaultdict(lambda: defaultdict(list))
        self.reverse_edges = defaultdict(lambda: defaultdict(list))
        self.variable_map = {}
        self._value_to_node_map = {}

    def iter_edges(self):
        for source_id, targets_map in self.edges.items():
            for target_id, edge_list in targets_map.items():
                for edge in edge_list:
                    yield (source_id, target_id, edge)

    def add_node(self, node_id, initial_type=UNKNOWN):
        if node_id not in self.nodes:
            self.nodes[node_id] = GraphNode(node_id, initial_type)
        return self.nodes[node_id]

    def get_node(self, node_id):
        return self.nodes.get(node_id)

    def get_node_for_var(self, var: Variable):
        return self.variable_map.get(var)

    def add_edge(self, source_id, target_id, edge: Edge):
        if not isinstance(edge, Edge):
            raise TypeError("wrong edge type")
        source_node = self.add_node(source_id)
        target_node = self.add_node(target_id)
        if edge not in self.edges[source_id].get(target_id, []):
            self.edges[source_id][target_id].append(edge)
            self.reverse_edges[target_id][source_id].append(edge)
            source_node.out_edges[target_id].append(edge)
            target_node.in_edges[source_id].append(edge)
            return True
        return False

    def add_value_to_node(self, node_id, value, initial_type=UNKNOWN):
        node = self.add_node(node_id, initial_type)
        node.add_value(value)
        if isinstance(value, Variable):
            self.variable_map[value] = node

    def __iter__(self):
        return iter(self.nodes.values())

    def __len__(self):
        return len(self.nodes)

    def remove_edge(self, source_id, target_id, edge):
        try:
            self.edges[source_id][target_id].remove(edge)
            if not self.edges[source_id][target_id]: del self.edges[source_id][target_id]
            if not self.edges[source_id]: del self.edges[source_id]

            self.reverse_edges[target_id][source_id].remove(edge)
            if not self.reverse_edges[target_id][source_id]: del self.reverse_edges[target_id][source_id]
            if not self.reverse_edges[target_id]: del self.reverse_edges[target_id]

            source_node, target_node = self.nodes.get(source_id), self.nodes.get(target_id)
            if source_node and hasattr(source_node, 'out_edges'):
                if edge in source_node.out_edges.get(target_id, []):
                    source_node.out_edges[target_id].remove(edge)
                    if not source_node.out_edges[target_id]: del source_node.out_edges[target_id]
            if target_node and hasattr(target_node, 'in_edges'):
                if edge in target_node.in_edges.get(source_id, []):
                    target_node.in_edges[source_id].remove(edge)
                    if not target_node.in_edges[source_id]: del target_node.in_edges[source_id]

            return True
        except (KeyError, ValueError):
            return False

    def merge_nodes(self, target_id, source_id):
        if target_id not in self.nodes or source_id not in self.nodes: return []
        if target_id == source_id: return []

        target_node, source_node = self.nodes[target_id], self.nodes[source_id]

        if hasattr(target_node, 'type'): target_node.type = target_node.type.join(source_node.type)
        target_node.values.update(source_node.values)
        for val in source_node.values:
            if isinstance(val, Variable): self.variable_map[val] = target_node

        newly_affected_edges = []

        for dest_id, edge_list in list(self.edges.get(source_id, {}).items()):
            for edge in list(edge_list):
                self.remove_edge(source_id, dest_id, edge)
                if self.add_edge(target_id, dest_id, edge):
                    newly_affected_edges.append((target_id, dest_id, edge))

        for prev_id, edge_list in list(self.reverse_edges.get(source_id, {}).items()):
            for edge in list(edge_list):
                self.remove_edge(prev_id, source_id, edge)
                if self.add_edge(prev_id, target_id, edge):
                    newly_affected_edges.append((prev_id, target_id, edge))


        if source_id in self.nodes: del self.nodes[source_id]
        return newly_affected_edges

    def generate_dot(self, filename="dense_graph.dot"):

        safe_node_ids = {original_id: f"Node_{i}" for i, original_id in enumerate(self.nodes.keys())}
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("digraph DenseGraph {\n")
            f.write('  graph [rankdir=TD, splines=ortho];\n')
            f.write('  node [fontname="Courier New", fontsize=10, style="rounded,filled"];\n')
            f.write('  edge [fontname="Courier New", fontsize=9];\n\n')
            for node_id, node in self.nodes.items():
                dot_id = safe_node_ids[node_id]
                if isinstance(node.id, Constant):
                    label = str(node.id).replace('"', '\\"')
                    f.write(f'  {dot_id} [label="{label}", shape=ellipse, fillcolor=gold];\n')
                else:
                    values_str = ", ".join(sorted([str(v) for v in node.values], key=str))
                    safe_id_str = str(node.id).replace('"', '\\"')
                    safe_values_str = values_str.replace('{', '\\{').replace('}', '\\}')
                    type_str = f"Type: {getattr(node, 'type', 'N/A')!r}"
                    label = f'{{ {safe_id_str} | {type_str} | Values: \\{{ {safe_values_str} \\}} }}'
                    f.write(f'  {dot_id} [label="{label}", shape=record, fillcolor=lightblue];\n')
            f.write("\n  // Edges\n")
            for source_id, targets in self.edges.items():
                if source_id not in safe_node_ids: continue
                dot_source_id = safe_node_ids[source_id]
                for target_id, edge_list in targets.items():
                    if target_id not in safe_node_ids: continue
                    dot_target_id = safe_node_ids[target_id]
                    for edge in edge_list:
                        label = str(edge).replace('"', '\\"')
                        f.write(f'  {dot_source_id} -> {dot_target_id} [label="{label}"];\n')
            f.write("}\n")

    def run_cfl_solver(self, grammar):
        solver = CFLSolver(self, grammar)
        solver.solve()

    def run_type_propagation(self):
        solver = TypePropagationSolver(self)
        solver.solve()

    def print_summary(self):

        logger.info("--- Graph Content Summary ---")
        logger.info(f"Total nodes in memory: {len(self.nodes)}")

        edge_count = sum(len(el) for targets in self.edges.values() for el in targets.values())
        logger.info(f"Total edges in memory: {edge_count}")

        store_edge_found = False
        for source_id, targets in self.edges.items():
            for target_id, edge_list in targets.items():
                for edge in edge_list:
                    if isinstance(edge, OperationEdge) and edge.op_name.startswith("Store"):
                        logger.info(f"  [STORE EDGE FOUND IN MEMORY] From {source_id!r} To {target_id!r}")
                        store_edge_found = True

        if not store_edge_found:
            logger.warning("  [VALIDATION] No 'Store' edges were found in the graph's internal dictionary.")
        logger.info("--- End of Summary ---")

    def find_node_by_name(self, name: str):

        var_obj = Variable(name)
        if var_obj in self.variable_map:
            return self.variable_map[var_obj].id

        for node_id, node in self.nodes.items():
            for value in node.values:
                if str(value) == name:
                    return node_id  

        return None

    def get_reachable_subgraph(self, start_node_id: any):
        if start_node_id not in self.nodes:
            return None

        reachable_node_ids = set()
        queue = deque([start_node_id])
        visited = {start_node_id}
        while queue:
            current_id = queue.popleft()
            reachable_node_ids.add(current_id)
            for neighbor_id in self.edges.get(current_id, {}).keys():
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append(neighbor_id)

        return self._create_subgraph_from_ids(reachable_node_ids)

    def get_reaching_subgraph(self, target_node_id: any):
        if target_node_id not in self.nodes:
            return None

        reaching_node_ids = set()
        queue = deque([target_node_id])
        visited = {target_node_id}
        while queue:
            current_id = queue.popleft()
            reaching_node_ids.add(current_id)
            for predecessor_id in self.reverse_edges.get(current_id, {}).keys():
                if predecessor_id not in visited:
                    visited.add(predecessor_id)
                    queue.append(predecessor_id)

        return self._create_subgraph_from_ids(reaching_node_ids)

    def _create_subgraph_from_ids(self, node_ids: set) -> 'DenseGraph':

        subgraph = DenseGraph()
        if not node_ids:
            return subgraph

        for node_id in node_ids:
            original_node = self.nodes[node_id]
            subgraph.add_node(node_id, initial_type=original_node.type)
            subgraph.nodes[node_id].values.update(original_node.values)
            for value in original_node.values:
                if value in self._value_to_node_map:
                    subgraph._value_to_node_map[value] = node_id

        for source_id in node_ids:
            if source_id in self.edges:
                for target_id, edge_list in self.edges[source_id].items():
                    if target_id in node_ids:
                        for edge in edge_list:
                            subgraph.add_edge(source_id, target_id, edge)

        return subgraph

    def get_all_paths_from(self, start_node_id: any) -> list[list[tuple]]:

        if start_node_id not in self.nodes:
            return []

        all_paths = []
        stack = [(start_node_id, [])]

        while stack:
            current_id, path = stack.pop()
            successors = self.edges.get(current_id, {})

            has_valid_successor = False
            for neighbor_id, edge_list in successors.items():
                for edge in edge_list:
                    if (current_id, edge, neighbor_id) not in path:
                        has_valid_successor = True
                        break
                if has_valid_successor:
                    break

            if not has_valid_successor:
                if path: all_paths.append(path)
                continue

            for neighbor_id, edge_list in successors.items():
                for edge in edge_list:
                    edge_tuple = (current_id, edge, neighbor_id)
                    if edge_tuple in path:
                        continue

                    new_path = path + [edge_tuple]
                    stack.append((neighbor_id, new_path))

        return all_paths

    def get_all_paths_to(self, end_node_id: any) -> list[list[tuple]]:

        if end_node_id not in self.nodes:
            return []

        all_paths = []
        stack = [(end_node_id, [])]

        while stack:
            current_id, back_path = stack.pop()
            predecessors = self.reverse_edges.get(current_id, {})

            has_valid_predecessor = False
            for pred_id, edge_list in predecessors.items():
                for edge in edge_list:
                    if (pred_id, edge, current_id) not in back_path:
                        has_valid_predecessor = True
                        break
                if has_valid_predecessor:
                    break

            if not has_valid_predecessor:
                if back_path:
                    all_paths.append(list(reversed(back_path)))
                continue

            for pred_id, edge_list in predecessors.items():
                for edge in edge_list:
                    edge_tuple = (pred_id, edge, current_id)
                    if edge_tuple in back_path:
                        continue
                    new_back_path = back_path + [edge_tuple]
                    stack.append((pred_id, new_back_path))

        return all_paths

    def find_canonical_node_for_var(self, var: Variable):
        current_node = self.variable_map.get(var)
        if not current_node:
            return None

        current_id = current_node.id

        path = [current_id]
        while current_id in self.merged_into:
            current_id = self.merged_into[current_id]
            path.append(current_id)

        canonical_id = current_id
        canonical_node = self.nodes.get(canonical_id)

        if canonical_node:
            for node_id in path:
                if isinstance(node_id, Variable):
                    self.variable_map[node_id] = canonical_node
                self.merged_into[node_id] = canonical_id

        return canonical_node

class CFLSolver:
    def __init__(self, graph: DenseGraph, grammar: list):
        self.graph = graph
        self.grammar = grammar

    def _apply_path_rules(self, n1, n2, n3, edge1, edge2, worklist):
        for rule in self.grammar:
            if len(rule.patterns) != 2: continue
            if (bindings := rule.patterns[0].match(edge1, {})) is None: continue
            if (final_bindings := rule.patterns[1].match(edge2, bindings)) is None: continue
            if rule.condition and not rule.condition(final_bindings): continue
            result = rule.result_factory(final_bindings)
            if isinstance(result, EqualsEdge):
                target_id, source_id = (n1, n3) if repr(n1) < repr(n3) else (n3, n1)
                affected_edges = self.graph.merge_nodes(target_id, source_id)
                for edge_tuple in affected_edges:
                    if edge_tuple not in worklist: worklist.append(edge_tuple)
            elif isinstance(result, Edge):
                if self.graph.add_edge(n1, n3, result):
                    worklist.append((n1, n3, result))

    def solve(self):
        iteration = 1
        while True:
            assign_edges_to_process = [
                (u, v, edge)
                for u, targets in list(self.graph.edges.items())
                for v, edge_list in list(targets.items())
                for edge in edge_list
                if isinstance(edge, OperationEdge) and edge.op_name == 'Assign'
            ]

            if not assign_edges_to_process:
                break

            for u, v, edge in assign_edges_to_process:
                if u in self.graph.nodes and v in self.graph.nodes:
                    self.graph.remove_edge(u, v, edge)
                    target_id, source_id = (u, v) if repr(u) < repr(v) else (v, u)
                    self.graph.merge_nodes(target_id, source_id)
            iteration += 1

        worklist = [(u, v, e) for u, targets in list(self.graph.edges.items()) for v, e_list in list(targets.items())
                    for e in e_list]

        processed_idx = 0
        while processed_idx < len(worklist):
            u, v, edge = worklist[processed_idx];
            processed_idx += 1
            if u not in self.graph.nodes or v not in self.graph.nodes: continue
            if u in self.graph.reverse_edges:
                for t, prev_edge_list in list(self.graph.reverse_edges[u].items()):
                    for e_prev in prev_edge_list: self._apply_path_rules(t, u, v, e_prev, edge, worklist)
            if v in self.graph.edges:
                for w, next_edge_list in list(self.graph.edges[v].items()):
                    for e_next in next_edge_list: self._apply_path_rules(u, v, w, edge, e_next, worklist)




class TypePropagationSolver:
    def __init__(self, graph: DenseGraph):
        self.graph = graph
        self.worklist = deque()

    def _update_node_type(self, node_id, new_type):
        node = self.graph.get_node(node_id)
        if not node: return False
        current_type = node.type
        joined_type = current_type.join(new_type)
        if joined_type != current_type:
            node.type = joined_type
            if node_id not in self.worklist:
                self.worklist.append(node_id)
            return True
        return False

    def solve(self):
        self.worklist.extend(node.id for node in self.graph)
        while self.worklist:
            node_id = self.worklist.popleft()
            node = self.graph.get_node(node_id)
            if not node: continue
            self._apply_rules_for_node(node)

    def _apply_rules_for_node(self, node: GraphNode):
        for target_id, edge_list in list(node.out_edges.items()):
            for edge in edge_list:
                if isinstance(edge, OperationEdge):
                    if edge.op_name.startswith("Load"):
                        self._handle_load(ptr_id=node.id, val_id=target_id)
                    elif edge.op_name.startswith("Store"):
                        self._handle_store(val_id=node.id, ptr_id=target_id)
        for pred_id, edge_list in list(node.in_edges.items()):
            for edge in edge_list:
                if isinstance(edge, OperationEdge):
                    op_name = edge.op_name
                    if op_name in ("IntAdd", "IntSub"):
                        all_ops = [pred_id] + list(edge.operands)
                        self._handle_int_arith(all_ops, node.id)
                    elif op_name in ("FloatAdd", "FloatSub"):
                        all_ops = [pred_id] + list(edge.operands)
                        self._handle_float_arith(all_ops, node.id)

    def _handle_int_arith(self, operand_ids, dest_id):
        dest_node = self.graph.get_node(dest_id)
        if not dest_node: return
        op_nodes = [self.graph.get_node(op_id) for op_id in operand_ids if self.graph.get_node(op_id)]
        ptr_op_node = next((n for n in op_nodes if isinstance(n.type, PointerType)), None)
        const_op_node = next((n for n in op_nodes if isinstance(n.id, Constant)), None)
        if ptr_op_node and const_op_node:
            offset = const_op_node.id.value
            self._update_node_type(dest_id, PointerType(UNKNOWN))
            field_type = UNKNOWN
            if isinstance(dest_node.type, PointerType): field_type = dest_node.type.points_to
            self._update_node_type(ptr_op_node.id, PointerType(StructType({offset: field_type})))
            return
        self._update_node_type(dest_id, IntType(64))
        for op_node in op_nodes:
            self._update_node_type(op_node.id, IntType(64))

    def _handle_float_arith(self, operand_ids, dest_id):
        self._update_node_type(dest_id, FloatType(64))
        for op_id in operand_ids: self._update_node_type(op_id, FloatType(64))

    def _handle_store(self, val_id, ptr_id):
        val_node = self.graph.get_node(val_id)
        ptr_node = self.graph.get_node(ptr_id)
        if not (val_node and ptr_node): return
        self._update_node_type(ptr_id, PointerType(val_node.type))

    def _handle_load(self, ptr_id, val_id):
        ptr_node = self.graph.get_node(ptr_id)
        val_node = self.graph.get_node(val_id)
        if not (ptr_node and val_node): return
        if isinstance(ptr_node.type, PointerType):
            self._update_node_type(val_id, ptr_node.type.points_to)
        self._update_node_type(ptr_id, PointerType(val_node.type))


def run_struct_recovery_test():
    graph = DenseGraph()
    v_struct_ptr, v_field1_ptr, v_field2_ptr, v_int, v_float = Variable("v_struct_ptr"), Variable(
        "v_field1_ptr"), Variable("v_field2_ptr"), Variable("v_int"), Variable("v_float")
    offset_8, offset_16 = Constant("$0x8"), Constant("$0x10")
    graph.add_value_to_node("node_struct_ptr", v_struct_ptr);
    graph.add_value_to_node("node_field1_ptr", v_field1_ptr);
    graph.add_value_to_node("node_field2_ptr", v_field2_ptr);
    graph.add_value_to_node("node_int", v_int);
    graph.add_value_to_node("node_float", v_float)
    graph.add_node(offset_8);
    graph.add_node(offset_16)
    graph.add_edge("dummy_int_op", "node_int", OperationEdge("IntAdd"));
    graph.add_edge("dummy_float_op", "node_float", OperationEdge("FloatAdd"))
    graph.add_edge("node_struct_ptr", "node_field1_ptr", OperationEdge("IntAdd", offset_8));
    graph.add_edge(offset_8, "node_field1_ptr", OperationEdge("IntAdd"))
    graph.add_edge("node_struct_ptr", "node_field2_ptr", OperationEdge("IntAdd", offset_16));
    graph.add_edge(offset_16, "node_field2_ptr", OperationEdge("IntAdd"))
    graph.add_edge("node_int", "node_field1_ptr", OperationEdge("Store"));
    graph.add_edge("node_float", "node_field2_ptr", OperationEdge("Store"))
    graph.generate_dot("graph_struct_before.dot")
    graph.run_type_propagation()
    graph.generate_dot("graph_struct_after.dot")

