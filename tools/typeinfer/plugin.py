import sys
import os
import shutil
import tempfile
import subprocess
from loguru import logger
import json

local_path = os.path.dirname(__file__)
plugin_path = os.path.abspath(os.path.join(local_path, 'src'))
sys.path.append(plugin_path)
from main import analyze

ghidra_path = os.path.abspath(os.path.join(local_path, '..', 'ghidra'))
sys.path.append(ghidra_path)
import ghidra_run as ghidra

trex_path = os.environ.get("TREX_PATH")

def export_variables(filename, filepath, tempdir):
    (rc, _, stderr) = ghidra.run(filepath, 'VariableExporter.java', extra_args=['allow_default_analysis'])

    if rc != 0:
        print(stderr, file=sys.stderr)
        raise Exception("Problem exporting variables")
    else:
        generated_file = '{}.var-exported'.format(filename)
        shutil.move(generated_file, tempdir)

def export_pcode(filename, filepath, tempdir):
    (rc, _, stderr) = ghidra.run(filepath, 'PCodeExporter.java')

    if rc != 0:
        print(stderr, file=sys.stderr)
        raise Exception("Problem exporting pcode")
    else:
        generated_file = '{}.pcode-exported'.format(filename)
        shutil.move(generated_file, tempdir)

def run_trex(tempdir, filename):
    variables_path = os.path.join(tempdir, '{}.var-exported'.format(filename))
    pcode_path = os.path.join(tempdir, '{}.pcode-exported'.format(filename))

    lifted_ssa_path = os.path.join(tempdir, '{}.ssa'.format(filename))
    varmap_path = os.path.join(tempdir, '{}_varmap.txt'.format(filename))

    output_ssa_argument = '--dump-ssa-lifted={}'.format(lifted_ssa_path)
    output_varmap_argument = '--output-varmap={}'.format(varmap_path)

    command = [trex_path, 'from-ghidra', pcode_path, variables_path, output_ssa_argument, output_varmap_argument]
    completion = subprocess.run(command, text=True, shell=False, capture_output=True)
    
    if completion.returncode != 0:
        print(completion.stderr, file=sys.stderr)
        raise Exception("Problem running trex")
    
    if not os.path.exists(varmap_path):
        raise Exception("No variables found")
    
    return (lifted_ssa_path, varmap_path)


def main():
    try:
        filepath = sys.argv[1]
        filename = os.path.basename(filepath)
        with tempfile.TemporaryDirectory() as tempdir:
            export_variables(filename, filepath, tempdir)
            export_pcode(filename, filepath, tempdir)
            (ssa_filepath, varmap_filepath) = run_trex(tempdir, filename)
            
            output_file = os.path.join(tempdir, 'output.json')

            logger.remove(0)
            analyze(ssa_filepath, varmap_filepath, output_file)

            with open(output_file, 'r') as f:
                for line in f:
                    line = json.loads(line)
                    print(line['type'])
                    print()
    except Exception as e:
        print(str(e), file=sys.stderr)
        exit(1)

if __name__ == '__main__':
    main()