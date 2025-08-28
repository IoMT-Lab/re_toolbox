import copy

from loguru import logger
from ssa_objects import Condition


class AnalysisContext:

    def __init__(self, path_history=None, path_condition=None, visited_edges=None, equal_map=None):
        self.path_history = path_history or []
        self.path_condition = path_condition or frozenset()
        self.visited_edges = visited_edges or frozenset()
        self.equal_map = equal_map or {}

    def branch(self, from_block_id, to_block_id, new_condition=None):
        new_visited_edges = self.visited_edges.union({(from_block_id, to_block_id)})

        return AnalysisContext(
            path_history=self.path_history + [to_block_id],
            path_condition=self.path_condition.union({new_condition}) if new_condition else self.path_condition,
            visited_edges=new_visited_edges,
            equal_map=copy.deepcopy(self.equal_map)
        )

    def __repr__(self):
        cond_str = "{" + ", ".join(map(str, sorted(list(self.path_condition), key=repr))) + "}" if self.path_condition else "{}"
        return f"Context(Path={self.path_history}, Cond={cond_str}, MapSize={len(self.equal_map)})"


class Visitor:

    def __init__(self, cfg):
        self.cfg = cfg
        if not self.cfg.dominators: self.cfg.compute_dominators()
        self.completed_paths = []

    def visit_program_flow_insensitive(self) -> AnalysisContext:
        shared_context = AnalysisContext()

        for block_id in sorted(self.cfg.blocks.keys()):
            block = self.cfg.blocks[block_id]

            self.on_enter_block(block, shared_context)

            for instruction in block:
                self.visit_instruction(instruction, shared_context)

            self.on_exit_block(block, shared_context)

        return shared_context

    def visit_program(self):
        self.completed_paths = []
        if not self.cfg.entry_node_id:
            return

        initial_context = AnalysisContext(path_history=[self.cfg.entry_node_id])
        stack = [(self.cfg.entry_node_id, initial_context)]

        while stack:
            block_id, context = stack.pop()
            block = self.cfg.blocks[block_id]

            self.on_enter_block(block, context)
            for instruction in block:
                self.visit_instruction(instruction, context)
            self.on_exit_block(block, context)

            if not block.successors:
                self.completed_paths.append(context)
                continue

            successors_to_visit = []
            last_inst = block.instructions[-1]

            if last_inst.operation == "Cbranch":
                cond_var = last_inst.args[1]
                true_target_id = self.cfg._get_target_id(last_inst.args[0])
                false_target_id = next(iter(block.successors - {true_target_id}), None)
                if false_target_id: successors_to_visit.append((false_target_id, Condition(cond_var, False)))
                if true_target_id: successors_to_visit.append((true_target_id, Condition(cond_var, True)))
            else:
                for succ_id in sorted(list(block.successors), reverse=True):
                    successors_to_visit.append((succ_id, None))

            for succ_id, new_condition in successors_to_visit:
                edge_tuple = (block_id, succ_id)
                if edge_tuple in context.visited_edges:
                    continue

                new_context = context.branch(block_id, succ_id, new_condition)
                stack.append((succ_id, new_context))

    def _visit_path_recursive(self, block_id, context):

        block = self.cfg.blocks[block_id]

        self.on_enter_block(block, context)
        for instruction in block:
            self.visit_instruction(instruction, context)
        self.on_exit_block(block, context)

        if not block.successors:
            self.completed_paths.append(context)
            return

        last_inst = block.instructions[-1]

        if last_inst.operation == "Cbranch":
            true_target_id = self.cfg._get_target_id(last_inst.args[0])

            false_target_id_set = block.successors - {true_target_id}
            false_target_id = false_target_id_set.pop() if false_target_id_set else None

            cond_var = last_inst.args[1]

            if true_target_id:
                true_cond = Condition(cond_var, is_true=True)
                self._traverse_to_next(block_id, true_target_id, context, new_condition=true_cond)


            if false_target_id:
                false_cond = Condition(cond_var, is_true=False)
                self._traverse_to_next(block_id, false_target_id, context, new_condition=false_cond)

        else:
            for succ_id in sorted(list(block.successors)):
                self._traverse_to_next(block_id, succ_id, context)

    def _traverse_to_next(self, from_id, to_id, context, new_condition=None):

        is_back_edge = to_id in self.cfg.dominators.get(from_id, set())
        back_edge_tuple = (from_id, to_id) if is_back_edge else None

        if is_back_edge and back_edge_tuple in context.taken_back_edges:
            return

        loop_increment = 1 if is_back_edge else 0


        new_context = context.branch(
            new_block_id=to_id,
            new_condition=new_condition,
            loop_increment=loop_increment,
            back_edge_to_add=back_edge_tuple
        )
        self._visit_path_recursive(to_id, new_context)

    def on_enter_block(self, block, context):
        indent = "  " * (len(context.path_history) - 1)
        logger.debug(f"{indent}-> Entering {block} | {context}")
        pass


    def visit_instruction(self, instruction, context):
        pass

    def on_exit_block(self, block, context):
        pass