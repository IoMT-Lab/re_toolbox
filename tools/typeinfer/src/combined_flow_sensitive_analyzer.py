from collections import defaultdict, deque
from dense_graph import Variable, DereferenceEdge, OperationEdge, AddressOfEdge, DenseGraph
from type_definitions import UNKNOWN, PointerType, IntType, BaseType, BoolType, UnionType, FloatType
from utils import is_negative, get_signed_value

from visitor import Visitor, AnalysisContext
from ssa_objects import Variable, Constant, Instruction
from loguru import logger


class CombinedFlowSensitiveAnalyzer(Visitor):
    def __init__(self, cfg):
        super().__init__(cfg)
        self.graph = DenseGraph()
        self._value_to_node_map = {}

    def _get_or_create_node(self, value):
        if value not in self._value_to_node_map:
            node_id = value
            self._value_to_node_map[value] = node_id
            self.graph.add_node(node_id, initial_type=UNKNOWN)
            self.graph.add_value_to_node(node_id, value)
        return self._value_to_node_map[value]

    def _update_node_type(self, node_id, new_type):
        node = self.graph.get_node(node_id)
        if not node: return

        current_type = node.type
        joined_type = current_type.join(new_type)
        if joined_type != current_type:
            logger.debug(f"type updated: node {node_id!r} type: {current_type!r} -> {joined_type!r}")
            node.type = joined_type

    def _refine_pointer_type(self, node_id):
        node = self.graph.get_node(node_id)
        if not node or not isinstance(node.type, UnionType):
            return

        current_type = node.type
        pointer_types = {t for t in current_type.types if isinstance(t, PointerType)}

        if not pointer_types:
            return

        refined_type = UnionType(pointer_types) if len(pointer_types) > 1 else pointer_types.pop()

        if refined_type != current_type:
            logger.info(f"update {node_id!r} type from {current_type!r} -> {refined_type!r}")
            node.type = refined_type

    def visit_instruction(self, instruction: Instruction, context: AnalysisContext):

        inst = instruction
        op, output, args = inst.operation, inst.output, inst.args

        integer_ops = {"IntAdd", "IntSub", "IntMult", "IntDiv", "IntXor", "IntAnd", "IntOr", "IntShl", "IntLShr",}
        float_ops = {"FloatAdd", "FloatSub", "FloatMult", "FloatDiv"}
        boolean_ops = {"IntEqual", "IntNotEqual", "IntLess", "IntSLess", "IntLessEqual", "IntSLessEqual", "BoolNegate"}
        integer_conversion_ops = {"IntZext", "IntSext", "IntTrunc", "Popcount"}

        if op in integer_ops and len(args) == 2 and output:
            output_node = self._get_or_create_node(output)
            source_node = self._get_or_create_node(args[0])
            op2_node = self._get_or_create_node(args[1])
            op2 = args[1]

            final_op_name = op
            final_op_val = op2
            if isinstance(args[0], Constant) and not isinstance(args[1], Constant):
                source_node = self._get_or_create_node(args[1])
                op2_node = self._get_or_create_node(args[0])
                op2 = args[0]


            if op == "IntAdd" and isinstance(op2, Constant) and is_negative(op2):
                logger.debug(f"find IntAdd: to be replaced by IntSub:  {inst}")
                final_op_name = "IntSub"
                positive_sub_val = -get_signed_value(op2)
                final_op_val = Constant(str(positive_sub_val))
                self._get_or_create_node(final_op_val)

            edge = OperationEdge(final_op_name, final_op_val)
            self.graph.add_edge(source_node, output_node, edge)

            int_type = IntType(64)
            self._update_node_type(output_node, int_type)
            self._update_node_type(source_node, int_type)
            self._update_node_type(op2_node, int_type)

        elif op in float_ops and len(args) == 2 and output:
            output_node = self._get_or_create_node(output)
            source_node = self._get_or_create_node(args[0])
            op2_node = self._get_or_create_node(args[1])
            edge = OperationEdge(op, args[1])
            self.graph.add_edge(source_node, output_node, edge)
            float_type = FloatType(64)
            self._update_node_type(output_node, float_type)
            self._update_node_type(source_node, float_type)
            self._update_node_type(op2_node, float_type)

        elif op in boolean_ops and output and args:
            output_node = self._get_or_create_node(output)
            self._update_node_type(output_node, BoolType())
            if op.startswith("Int"):
                for arg in args: self._update_node_type(self._get_or_create_node(arg), IntType(64))
            elif op.startswith("Bool"):
                for arg in args: self._update_node_type(self._get_or_create_node(arg), BoolType())
            input_node = self._get_or_create_node(args[0])
            edge = OperationEdge(op, *args[1:])
            self.graph.add_edge(input_node, output_node, edge)

        elif op in integer_conversion_ops and len(args) == 1 and output:
            output_node = self._get_or_create_node(output)
            input_node = self._get_or_create_node(args[0])
            edge = OperationEdge(op)
            self.graph.add_edge(input_node, output_node, edge)
            int_type = IntType(64)
            self._update_node_type(output_node, int_type)
            self._update_node_type(input_node, int_type)

        elif op.startswith("Load") and len(args) == 1 and output:
            output_node = self._get_or_create_node(output)
            ptr_node = self._get_or_create_node(args[0])
            self.graph.add_edge(ptr_node, output_node, DereferenceEdge())
            output_node_obj = self.graph.get_node(output_node)
            if output_node_obj:
                self._update_node_type(ptr_node, PointerType(output_node_obj.type))
            self._refine_pointer_type(ptr_node)
            ptr_node_obj = self.graph.get_node(ptr_node)
            if ptr_node_obj and isinstance(ptr_node_obj.type, PointerType):
                self._update_node_type(output_node, ptr_node_obj.type.points_to)

        elif op.startswith("Store") and len(args) == 2:
            ptr_node = self._get_or_create_node(args[0])
            val_node = self._get_or_create_node(args[1])
            self.graph.add_edge(val_node, ptr_node, AddressOfEdge())
            val_node_obj = self.graph.get_node(val_node)
            if val_node_obj:
                self._update_node_type(ptr_node, PointerType(val_node_obj.type))
            self._refine_pointer_type(ptr_node)

        elif op == "Assign" and len(args) == 1 and output:
            output_node = self._get_or_create_node(output)
            input_node = self._get_or_create_node(args[0])
            self.graph.add_edge(input_node, output_node, OperationEdge("Assign"))
            input_node_obj = self.graph.get_node(input_node)
            output_node_obj = self.graph.get_node(output_node)
            if input_node_obj and output_node_obj:
                self._update_node_type(output_node, input_node_obj.type)
                self._update_node_type(input_node, output_node_obj.type)

        elif op == "Phi" and output and args:
            output_node = self._get_or_create_node(output)

            arg_nodes = [self._get_or_create_node(arg) for arg in args if isinstance(arg, (Variable, Constant))]

            for input_node in arg_nodes:
                self.graph.add_edge(input_node, output_node, OperationEdge("Assign"))

            joined_type = UNKNOWN
            for arg_node_id in arg_nodes:
                arg_node_obj = self.graph.get_node(arg_node_id)
                if arg_node_obj:
                    joined_type = joined_type.join(arg_node_obj.type)

            self._update_node_type(output_node, joined_type)
            for arg_node_id in arg_nodes:
                self._update_node_type(arg_node_id, joined_type)

        else:
            logger.warning(f"skip '{op}' {inst}")

    def run_gvn_simplification(self):
        logger.info("--- GVN ---")

        iteration = 1
        while True:
            changed_in_pass = False
            logger.info(f"GVN iter #{iteration}...")

            all_node_ids = list(self.graph.nodes.keys())

            for node_id in all_node_ids:
                if node_id not in self.graph.nodes:
                    continue

                edge_to_dests = defaultdict(list)

                if node_id in self.graph.edges:
                    for dest_id, edge_list in self.graph.edges[node_id].items():
                        for edge in edge_list:
                            edge_to_dests[edge].append(dest_id)


                for edge, dests in edge_to_dests.items():
                    if len(dests) > 1:
                        sorted_dests = sorted(dests, key=repr)
                        target_dest = sorted_dests[0]

                        logger.info(
                            f"GVN Found at Node {node_id!r}: Edge '{edge!r}' points to multiple destinations {sorted_dests}.")

                        for source_dest in sorted_dests[1:]:
                            if target_dest != source_dest and source_dest in self.graph.nodes:
                                logger.info(f"  -> Merging {source_dest!r} into {target_dest!r}")
                                self.graph.merge_nodes(target_dest, source_dest)
                                changed_in_pass = True

            if not changed_in_pass:
                logger.success("GVN done")
                break

            iteration += 1

    def generate_dot(self, filename="combined_alias_flow_graph.dot"):
        self.graph.generate_dot(filename)

    def get_graph(self):
        return self.graph


    def get_subgraph_reachable_from(self, start_value: [Variable, Constant]):
        start_node_id = self._value_to_node_map.get(start_value)
        if not start_node_id:
            return None

        reachable_node_ids = set()
        queue = deque([start_node_id])
        visited = {start_node_id}
        while queue:
            current_id = queue.popleft()
            reachable_node_ids.add(current_id)
            for neighbor_id in self.graph.edges.get(current_id, {}).keys():
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append(neighbor_id)

        subgraph = DenseGraph()
        for node_id in reachable_node_ids:
            original_node = self.graph.nodes[node_id]
            subgraph.add_node(node_id, initial_type=original_node.type)
            subgraph.nodes[node_id].values.update(original_node.values)
        for source_id in reachable_node_ids:
            if source_id in self.graph.edges:
                for target_id, edge_list in self.graph.edges[source_id].items():
                    if target_id in reachable_node_ids:
                        for edge in edge_list:
                            subgraph.add_edge(source_id, target_id, edge)
        return subgraph

    def get_subgraph_reaching_to(self, target_value: [Variable, Constant]):
        target_node_id = self._value_to_node_map.get(target_value)
        if not target_node_id:
            return None

        reaching_node_ids = set()
        queue = deque([target_node_id])
        visited = {target_node_id}
        while queue:
            current_id = queue.popleft()
            reaching_node_ids.add(current_id)
            for predecessor_id in self.graph.reverse_edges.get(current_id, {}).keys():
                if predecessor_id not in visited:
                    visited.add(predecessor_id)
                    queue.append(predecessor_id)

        subgraph = DenseGraph()
        for node_id in reaching_node_ids:
            original_node = self.graph.nodes[node_id]
            subgraph.add_node(node_id, initial_type=original_node.type)
            subgraph.nodes[node_id].values.update(original_node.values)
        for source_id in reaching_node_ids:
            if source_id in self.graph.edges:
                for target_id, edge_list in self.graph.edges[source_id].items():
                    if target_id in reaching_node_ids:
                        for edge in edge_list:
                            subgraph.add_edge(source_id, target_id, edge)
        return subgraph