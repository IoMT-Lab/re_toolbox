#!/usr/bin/env python3

import angr
import sys
import tempfile

binary_path = sys.argv[1]

function_name = sys.argv[2] if len(sys.argv) > 2 else None

proj = angr.Project(binary_path, load_options={'auto_load_libs': False})
cfg = proj.analyses.CFG(normalize=True)
with tempfile.NamedTemporaryFile(mode='w', delete=False) as fp:
    for addr, func in proj.kb.functions.items():
        if function_name is None or func.name == function_name:
            dec = proj.analyses.Decompiler(proj.kb.functions[addr])
            if dec.codegen is not None:
                fp.write(dec.codegen.text)
                fp.write('\n')
    print(fp.name)
