from dense_graph import DenseGraph, DereferenceEdge, OperationEdge
from ssa_objects import Variable, Constant
from type_definitions import UNKNOWN, StructType
from loguru import logger


class StructReconstructor:

    def __init__(self, graph: DenseGraph):
        self.graph = graph

    def reconstruct_for_variable(self, base_var_name: str) -> StructType:
        start_node_id = self.graph.find_node_by_name(base_var_name)
        if not start_node_id:
            return None

        paths = self.graph.get_all_paths_from(start_node_id)

        if not paths:
            return None

        fields = {}

        for i, path in enumerate(paths):
            if len(path) == 1:
                source, edge, target = path[0]
                if source == start_node_id and isinstance(edge, DereferenceEdge):
                    val_type = self.graph.get_node(target).type
                    fields[0] = fields.get(0, UNKNOWN).join(val_type)

            if len(path) >= 2:
                step1_source, step1_edge, step1_target = path[0]
                step2_source, step2_edge, step2_target = path[1]

                if (step1_source == start_node_id and
                        isinstance(step1_edge, OperationEdge) and step1_edge.op_name == "IntAdd" and
                        step1_target == step2_source and
                        isinstance(step2_edge, DereferenceEdge)):

                    if len(step1_edge.operands) > 0 and isinstance(step1_edge.operands[0], Constant):
                        offset = step1_edge.operands[0].value
                        val_type = self.graph.get_node(step2_target).type
                        fields[offset] = fields.get(offset, UNKNOWN).join(val_type)

        if not fields:
            return None

        struct_name = f"struct_{base_var_name}"
        final_struct = StructType(struct_name, fields)
        return final_struct