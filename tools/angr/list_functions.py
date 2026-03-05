#!/usr/bin/env python3

import angr
import sys
import tempfile

binary_path = sys.argv[1]
proj = angr.Project(binary_path, load_options={'auto_load_libs': False})
cfg = proj.analyses.CFG(normalize=True)

with tempfile.NamedTemporaryFile(mode='w', delete=False) as fp:
    fp.writelines([f"{fun.name}\n" for fun in cfg.kb.functions.values()])
    print(fp.name)
