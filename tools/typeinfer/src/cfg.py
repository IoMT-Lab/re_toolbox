from collections import defaultdict
from loguru import logger
from scc import SCC

class BasicBlock:
    """Represents a Basic Block in the CFG."""

    def __init__(self, start_id):
        self.id = start_id
        self.instructions = []
        self.predecessors = set()
        self.successors = set()

    @property
    def start_id(self):
        return self.instructions[0].id if self.instructions else self.id

    @property
    def end_id(self):
        return self.instructions[-1].id if self.instructions else self.id

    def __iter__(self):
        return iter(self.instructions)

    def __len__(self):
        return len(self.instructions)

    def __repr__(self):
        return f"BB@{self.id}"


class ControlFlowGraph:
    """Represents the Control Flow Graph and runs various analyses."""

    def __init__(self):
        self.blocks = {}
        self.entry_node_id = None
        self.exit_node_ids = []

        # Analysis results
        self.dominators = {}
        self.immediate_dominators = {}
        self.dominator_frontiers = {}
        self.critical_edges = []
        self.sccs = []

    def _get_target_id(self, arg):
        if hasattr(arg, 'name') and arg.name == 'ILA' and arg.args:
            return arg.args[0]

        if isinstance(arg, (int, str)):
            return arg

        logger.warning(f"cannot infer {arg} (type: {type(arg)}) branch target id")
        return None

    def build(self, instructions):
        if not instructions:
            return

        logger.info("building (CFG)...")
        inst_map = {inst.id: inst for inst in instructions}
        leaders = {instructions[0].id}
        terminator_ops = {
            "Branch", "Cbranch", "Return", "FunctionEnd",
            "CallWithFallthrough", "CallWithNoFallthrough",
            "CallWithFallthroughIndirect", "CallWithNoFallthroughIndirect"
        }

        for i, inst in enumerate(instructions):
            if inst.operation in terminator_ops:
                if i + 1 < len(instructions):
                    leaders.add(instructions[i + 1].id)

                if inst.operation in ("Branch", "Cbranch"):
                    target_id = self._get_target_id(inst.args[0])
                    if target_id and target_id in inst_map:
                        leaders.add(target_id)

        sorted_leaders = sorted(list(leaders))

        for i, leader_id in enumerate(sorted_leaders):
            start_idx = instructions.index(inst_map[leader_id])

            end_idx = len(instructions)
            if i + 1 < len(sorted_leaders):
                next_leader_id = sorted_leaders[i + 1]
                end_idx = instructions.index(inst_map[next_leader_id])

            block_instructions = instructions[start_idx:end_idx]

            if not block_instructions:
                logger.warning(f"find empty block leader at{leader_id} and skip it.")
                continue

            bb = BasicBlock(leader_id)
            bb.instructions = block_instructions
            self.blocks[leader_id] = bb

        if not self.blocks:
            logger.error("CFG failed, not enough basic blocks.")
            return

        self.entry_node_id = instructions[0].id

        id_to_block_map = {inst.id: bb for bb_id, bb in self.blocks.items() for inst in bb.instructions}

        for bb_id, bb in self.blocks.items():
            last_inst = bb.instructions[-1]
            op = last_inst.operation

            if op in ("Branch", "Cbranch"):
                target_id = self._get_target_id(last_inst.args[0])
                if target_id and target_id in id_to_block_map:
                    target_bb = id_to_block_map[target_id]
                    bb.successors.add(target_bb.id)
                    target_bb.predecessors.add(bb.id)

            non_fallthrough_ops = {
                "Branch", "Return", "FunctionEnd",
                "CallWithNoFallthrough", "CallWithNoFallthroughIndirect"
            }
            if op not in non_fallthrough_ops:
                current_inst_index = instructions.index(last_inst)
                if current_inst_index + 1 < len(instructions):
                    next_inst = instructions[current_inst_index + 1]
                    if next_inst.id in id_to_block_map:
                        fallthrough_bb = id_to_block_map[next_inst.id]
                        bb.successors.add(fallthrough_bb.id)
                        fallthrough_bb.predecessors.add(bb.id)

            if op in {"Return", "FunctionEnd"}:
                self.exit_node_ids.append(bb_id)

        logger.success("CFG done")

    def compute_dominators(self):
        if not self.blocks: return
        logger.info("Computing Dominators...")
        all_nodes = set(self.blocks.keys())
        dom = {n: all_nodes.copy() for n in all_nodes}
        dom[self.entry_node_id] = {self.entry_node_id}
        changed = True
        while changed:
            changed = False
            for n_id in sorted(list(all_nodes - {self.entry_node_id})):
                node = self.blocks[n_id]
                if not node.predecessors: continue
                pred_doms = [dom[p_id] for p_id in node.predecessors]
                new_dom = set.intersection(*pred_doms) | {n_id}
                if new_dom != dom[n_id]:
                    dom[n_id] = new_dom
                    changed = True
        self.dominators = dom
        for n_id in all_nodes:
            sdoms = self.dominators[n_id] - {n_id}
            idom = None
            for sdom_id in sdoms:
                if all(other_id in self.dominators[sdom_id] for other_id in sdoms - {sdom_id}):
                    idom = sdom_id
                    break
            if idom: self.immediate_dominators[n_id] = idom
        logger.success("Dominator analysis complete.")

    def compute_dominator_frontiers(self):
        if not self.dominators: self.compute_dominators()
        logger.info("Computing Dominator Frontiers...")
        df = {n_id: set() for n_id in self.blocks}
        for b_id in self.blocks:
            b = self.blocks[b_id]
            if len(b.predecessors) >= 2:
                for p_id in b.predecessors:
                    runner_id = p_id
                    while runner_id and runner_id != self.immediate_dominators.get(b_id):
                        df[runner_id].add(b_id)
                        runner_id = self.immediate_dominators.get(runner_id)
        self.dominator_frontiers = df
        logger.success("Dominator Frontier analysis complete.")

    def compute_critical_edges(self):
        if not self.blocks: return
        logger.info("Computing Critical Edges...")
        self.critical_edges = []
        for u_id, u_block in self.blocks.items():
            if len(u_block.successors) > 1:
                for v_id in u_block.successors:
                    v_block = self.blocks[v_id]
                    if len(v_block.predecessors) > 1:
                        self.critical_edges.append((u_id, v_id))
        logger.success("Critical Edge analysis complete.")

    def compute_sccs(self):
        if not self.blocks:
            return
        if self.sccs:
            return

        logger.info("computing (SCC)...")

        self.sccs = []
        visited = set()
        stack = []
        on_stack = {n_id: False for n_id in self.blocks}
        disc = {n_id: -1 for n_id in self.blocks}
        low = {n_id: -1 for n_id in self.blocks}
        time = 0

        def _tarjan_dfs(u_id):
            nonlocal time
            visited.add(u_id)
            disc[u_id] = low[u_id] = time
            time += 1
            stack.append(u_id)
            on_stack[u_id] = True

            for v_id in self.blocks[u_id].successors:
                if v_id not in visited:
                    _tarjan_dfs(v_id)
                    low[u_id] = min(low[u_id], low[v_id])
                elif on_stack[v_id]:
                    low[u_id] = min(low[u_id], disc[v_id])

            if low[u_id] == disc[u_id]:
                component_ids = []
                while True:
                    node_id = stack.pop()
                    on_stack[node_id] = False
                    component_ids.append(node_id)
                    if node_id == u_id:
                        break
                self.sccs.append(SCC(component_ids, self))

        for n_id in self.blocks:
            if n_id not in visited:
                _tarjan_dfs(n_id)

        logger.success("SCC done")

    def generate_dot(self, filename="cfg.dot"):

        logger.info(f"Generating high-readability DOT graph file: {filename}...")

        if not self.dominators: self.compute_dominators()
        if not self.dominator_frontiers: self.compute_dominator_frontiers()
        if not self.sccs: self.compute_sccs()
        if not self.critical_edges: self.compute_critical_edges()

        scc_color_map = {}
        if self.sccs:
            colors = ["#FFDDC1", "#D1E8FF", "#D4F0D4", "#FFFACD", "#FFECB3", "#E6E0F8"]
            for i, scc in enumerate(self.sccs):
                if scc.is_loop:
                    color = colors[i % len(colors)]
                    for node_id in scc.block_ids:
                        scc_color_map[node_id] = color

        with open(filename, 'w', encoding='utf-8') as f:
            f.write("digraph CFG {\n")
            f.write('  graph [rankdir=TD, splines=ortho, dpi=150];\n')
            f.write('  node [shape=record, fontname="Courier New", fontsize=12, style="rounded,filled"];\n')
            f.write('  edge [fontname="Courier New", fontsize=10];\n\n')

            for bb_id, bb in self.blocks.items():
                inst_texts = [f"{inst.id}: {inst}" for inst in bb.instructions]
                inst_label = "".join([s.replace('\\', '\\\\').replace('"', '\\"').replace('{', '\\{').replace('}',
                                                                                                              '\\}').replace(
                    '|', '\\|').replace('<', '\\<').replace('>', '\\>') + "\\l" for s in inst_texts])

                analysis_label_parts = []
                if self.dominator_frontiers.get(bb_id):
                    df_set_str = ', '.join(map(str, sorted(list(self.dominator_frontiers[bb_id]))))
                    analysis_label_parts.append(f"DF: \\{{ {df_set_str} \\}}")

                analysis_label = "| " + "\\l".join(analysis_label_parts) + "\\l" if analysis_label_parts else ""
                final_label = f'{{ BB@{bb_id} {analysis_label} | {inst_label} }}'

                attrs = [f'label="{final_label}"']
                attrs.append('fillcolor=white')
                if bb_id == self.entry_node_id: attrs.append(
                    'color=blue, style="filled,bold,rounded", fillcolor="#D1E8FF"')
                if bb_id in self.exit_node_ids: attrs.append(
                    'color=red, style="filled,bold,rounded", fillcolor="#FFDDC1"')
                if bb_id in scc_color_map: attrs.append(f'fillcolor="{scc_color_map[bb_id]}"')

                f.write(f'  BB_{bb_id} [{", ".join(attrs)}];\n')

            f.write("\n  // CFG Edges\n")
            critical_edges_set = set(self.critical_edges)
            for bb_id, bb in self.blocks.items():
                for succ_id in sorted(list(bb.successors)):
                    edge_attrs = []
                    if (bb_id, succ_id) in critical_edges_set:
                        edge_attrs.append('color="red", penwidth=2.0, label="critical"')
                    f.write(f'  BB_{bb_id} -> BB_{succ_id} [{", ".join(edge_attrs)}];\n')

            f.write("\n  // Dominator Tree Edges\n")
            if self.immediate_dominators:
                for node_id, idom_id in self.immediate_dominators.items():
                    f.write(f'  BB_{idom_id} -> BB_{node_id} [style=dashed, color=blue, constraint=false];\n')

            f.write("}\n")

        logger.success(f"Successfully wrote high-readability DOT file to {filename}.")
        logger.info(
            f"To render a large, readable image, run: dot -Tpng {filename} -o {filename.replace('.dot', '.png')}")

    #
    def print_cfg(self):
        print("\n--- Control Flow Graph (CFG) ---")
        for bb_id in sorted(self.blocks.keys()):
            bb = self.blocks[bb_id]
            print(f"  {repr(bb)} (instructions: {bb.start_id}-{bb.end_id})")
            print(f"    Predecessors: {{ {', '.join(map(str, sorted(list(bb.predecessors))))} }}")
            print(f"    Successors:   {{ {', '.join(map(str, sorted(list(bb.successors))))} }}")

    def print_analysis_results(self):
        if self.dominators:
            print("\n--- Dominator Sets ---")
            for n_id in sorted(self.dominators.keys()):
                dom_set_str = ', '.join(map(str, sorted(list(self.dominators[n_id]))))
                idom_str = f"(idom: {self.immediate_dominators.get(n_id, 'None')})"
                print(f"  Dom({n_id}): {{ {dom_set_str} }} {idom_str}")

        if self.dominator_frontiers:
            print("\n--- Dominator Frontiers ---")
            for n_id in sorted(self.dominator_frontiers.keys()):
                if self.dominator_frontiers[n_id]:
                    df_set_str = ', '.join(map(str, sorted(list(self.dominator_frontiers[n_id]))))
                    print(f"  DF({n_id}): {{ {df_set_str} }}")

        if self.critical_edges:
            print("\n--- Critical Edges ---")
            for u, v in self.critical_edges:
                print(f"  {u} -> {v}")

        if self.sccs:
            print("\n--- Strongly Connected Components (Loops) ---")
            for i, scc in enumerate(self.sccs):
                if scc.is_loop:
                    scc_str = ', '.join(map(str, scc.block_ids))
                    print(f"  Loop {i + 1}: {{ {scc_str} }}")

    def get_sccs(self):
        if not self.sccs:
            self.compute_sccs()
        return self.sccs

    def get_sccs_topological(self):
        if not self.sccs:
            self.compute_sccs()

        logger.info(" SCC ordering... ")

        node_to_scc_map = {}
        for scc_obj in self.sccs:
            for node_id in scc_obj.block_ids:
                node_to_scc_map[node_id] = scc_obj

        scc_adj = defaultdict(set)
        scc_in_degree = defaultdict(int)
        for u_id, u_block in self.blocks.items():
            scc_u = node_to_scc_map[u_id]
            for v_id in u_block.successors:
                scc_v = node_to_scc_map[v_id]

                if scc_u is not scc_v:
                    if scc_v not in scc_adj[scc_u]:
                        scc_adj[scc_u].add(scc_v)
                        scc_in_degree[scc_v] += 1

        queue = [scc for scc in self.sccs if scc_in_degree[scc] == 0]

        sorted_sccs = []
        while queue:
            queue.sort(key=lambda s: s.block_ids[0])
            u_scc = queue.pop(0)
            sorted_sccs.append(u_scc)

            sorted_successors = sorted(list(scc_adj[u_scc]), key=lambda s: s.block_ids[0])
            for v_scc in sorted_successors:
                scc_in_degree[v_scc] -= 1
                if scc_in_degree[v_scc] == 0:
                    queue.append(v_scc)


        if len(sorted_sccs) != len(self.sccs):
            logger.error("find a cycle ")
            return self.sccs

        logger.success("SCC done")
        return sorted_sccs

    def get_branch_info(self, cbranch_instruction_id):
        inst_to_block_map = {inst.id: bb for bb in self.blocks.values() for inst in bb}
        block_to_scc_map = {block_id: scc for scc in self.get_sccs() for block_id in scc.block_ids}

        if cbranch_instruction_id not in inst_to_block_map:
            logger.error(f"cannot find instruction ID: {cbranch_instruction_id}")
            return None

        source_block = inst_to_block_map[cbranch_instruction_id]
        instruction = source_block.instructions[-1]

        if instruction.operation != "Cbranch":
            logger.error(f"instructino {cbranch_instruction_id} is not cbranch but {instruction.operation}。")
            return None

        if len(source_block.successors) != 2:
            logger.warning(f"Cbranch block {source_block.id} successors number is not 2.")
            return None

        true_target_id = self._get_target_id(instruction.args[0])
        if not true_target_id:
            logger.error(f"cannot infer target branch from {instruction}")
            return None

        true_branch_block_id = inst_to_block_map[true_target_id].id

        false_branch_block_id = next(iter(source_block.successors - {true_branch_block_id}))

        true_block = self.blocks[true_branch_block_id]
        false_block = self.blocks[false_branch_block_id]

        true_scc = block_to_scc_map.get(true_block.id)
        false_scc = block_to_scc_map.get(false_block.id)

        return {
            "source_instruction": instruction,
            "source_block": source_block,
            "true_branch": {
                "block": true_block,
                "scc": true_scc
            },
            "false_branch": {
                "block": false_block,
                "scc": false_scc
            }
        }