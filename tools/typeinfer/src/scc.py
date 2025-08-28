class SCC:
    def __init__(self, block_ids, cfg_ref):
        self.block_ids = sorted(block_ids)
        self._cfg = cfg_ref

    @property
    def blocks(self):
        for block_id in self.block_ids:
            yield self._cfg.blocks[block_id]

    @property
    def is_loop(self):
        if len(self.block_ids) > 1:
            return True
        if len(self.block_ids) == 1:
            block_id = self.block_ids[0]
            block = self._cfg.blocks[block_id]
            return block_id in block.successors
        return False

    def __iter__(self):
        return self.blocks

    def __repr__(self):
        return f"SCC(blocks={self.block_ids})"

    def __len__(self):
        return len(self.block_ids)