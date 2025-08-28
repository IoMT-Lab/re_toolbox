from collections import deque
from loguru import logger
from dense_graph import DenseGraph, OperationEdge
from ssa_objects import Variable, Constant
from type_definitions import PointerType, StructType
from abstract_types import ABS_UNKNOWN, BaseAbstractType, StructFieldType


class AbstractTypePropagator:
    def __init__(self, graph: DenseGraph):
        self.graph = graph
        self.worklist = deque()

    def _initialize_abstract_types(self):
        for node_id, node in self.graph.nodes.items():
            if isinstance(node_id, Variable):
                node.abstract_type = BaseAbstractType(node_id.name)

    def _update_abstract_type(self, node, new_abs_type) -> bool:
        if node.abstract_type != new_abs_type:
            node.abstract_type = new_abs_type
            if node.id not in self.worklist:
                self.worklist.append(node.id)
            return True
        return False

    def _apply_rules_for_node(self, node_id):
        node = self.graph.get_node(node_id)
        if not node: return

        for pred_id, edge_list in self.graph.reverse_edges.get(node_id, {}).items():
            pred_node = self.graph.get_node(pred_id)
            if not pred_node: continue
            for edge in edge_list:
                if isinstance(edge, OperationEdge) and edge.op_name == "IntAdd":
                    if len(edge.operands) > 0 and isinstance(edge.operands[0], Constant):
                        offset = edge.operands[0].value
                        base_concrete_type = pred_node.type

                        if isinstance(base_concrete_type, PointerType) and isinstance(base_concrete_type.points_to,
                                                                                      StructType):
                            parent_struct_obj = base_concrete_type.points_to


                            new_abs_type = StructFieldType(parent_struct_obj, offset)

                            self._update_abstract_type(node, new_abs_type)

                elif isinstance(edge, OperationEdge) and edge.op_name == "Assign":
                    if not isinstance(node.abstract_type, StructFieldType):
                        self._update_abstract_type(node, pred_node.abstract_type)

    def run(self):
        logger.info(f"starting {self.__class__.__name__} for abstract type propagation...")
        self._initialize_abstract_types()
        self.worklist.extend(self.graph.nodes.keys())
        while self.worklist:
            node_id = self.worklist.popleft()
            self._apply_rules_for_node(node_id)
        logger.success("abstract type propagation done")