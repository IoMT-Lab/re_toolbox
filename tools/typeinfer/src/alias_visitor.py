from loguru import logger
from visitor import Visitor
from dense_graph import DenseGraph, OperationEdge
from ssa_objects import Variable, Constant
from type_definitions import UNKNOWN, IntType, FloatType


class AliasVisitor(Visitor):

    def __init__(self, cfg):
        super().__init__(cfg)
        self.path_graphs = []

    def _process_instruction(self, graph, value_to_node_map, instruction):
        op = instruction.operation
        output = instruction.output
        args = instruction.args

        def _get_or_create_node(value, init_type=UNKNOWN):
            if value not in value_to_node_map:
                node_id = value
                value_to_node_map[value] = node_id
                graph.add_node(node_id, initial_type=init_type)
                graph.add_value_to_node(node_id, value)
            return value_to_node_map[value]

        if isinstance(output, (Variable, Constant)):
            output_node = _get_or_create_node(output)

        if op.startswith("Int") or op.startswith("Float"):
            current_type = UNKNOWN
            if op.startswith("Int"):
                current_type = IntType()
            elif op.startswith("Float"):
                current_type = FloatType()

            if len(args) == 2:
                op1, op2 = args[0], args[1]
                op1_node = _get_or_create_node(op1, current_type)
                op2_node = _get_or_create_node(op2, current_type)
                _get_or_create_node(output, current_type)

                graph.add_edge(op1_node, output_node, OperationEdge(op, op2))
                graph.add_edge(op2_node, output_node, OperationEdge(op, op1))

        elif op.startswith("Store"):
            if len(args) == 2:
                ptr, val = args[0], args[1]
                ptr_node = _get_or_create_node(ptr)
                val_node = _get_or_create_node(val)
                graph.add_edge(val_node, ptr_node, OperationEdge(op))

        elif op.startswith("Load"):
            if len(args) == 1:
                ptr = args[0]
                ptr_node = _get_or_create_node(ptr)
                graph.add_edge(ptr_node, output_node, OperationEdge(op))

        elif op == "Assign":
            if len(args) == 1:
                input_var = args[0]
                input_node = _get_or_create_node(input_var)
                graph.add_edge(input_node, output_node, OperationEdge("Copy"))

        elif op == "Phi":
            for arg in args:
                if isinstance(arg, (Variable, Constant)):
                    arg_node = _get_or_create_node(arg)
                    graph.add_edge(arg_node, output_node, OperationEdge("Phi"))

    def build_graphs_for_all_paths(self):
        if not self.completed_paths:
            self.visit_program()

        logger.info(f"in CFG find {len(self.completed_paths)} paths")

        for i, context in enumerate(self.completed_paths):
            logger.info(f"--- building #{i + 1} ---")
            path_graph = DenseGraph()
            value_to_node_map = {}
            for bb_id in context.path_history:
                block = self.cfg.blocks[bb_id]
                for instruction in block:
                    self._process_instruction(path_graph, value_to_node_map, instruction)

            self.path_graphs.append((context, path_graph))

        return self.path_graphs
