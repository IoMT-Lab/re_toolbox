#!/usr/bin/env python3

import os
import argparse
import tempfile
import subprocess
import sys

parent_directory = os.environ.get("GHIDRA_DIR")
scripts_path = os.path.join(parent_directory,"ghidra_11.2.1_PUBLIC/Ghidra/Features/Base/ghidra_scripts")
local_script_path = os.path.join(parent_directory, "scripts")
command_path = os.path.join(parent_directory, 'ghidra_11.2.1_PUBLIC/support/analyzeHeadless')

def run(filename, script_name, extra_args = None, stdout_file = None, stderr_file = None):
    with tempfile.TemporaryDirectory() as tempdir:
        command = [command_path, tempdir, 'project',
                '-import', filename,
                '-scriptPath', scripts_path, 
                '-scriptPath', local_script_path, 
                '-postScript', script_name]
        if extra_args is not None:
            command.extend(extra_args)

        command.append('deleteProject')
        capture_output = (stdout_file is None) and (stderr_file is None)
        completion = subprocess.run(command, text=True, shell=False, capture_output=capture_output, stdout=stdout_file, stderr=stderr_file)

        return (completion.returncode, completion.stdout, completion.stderr)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("filename")
    parser.add_argument("script_name")
    parser.add_argument('--stdout_file')
    parser.add_argument('--stderr_file')
    parser.add_argument('--extra_args', nargs='*')
    
    args = parser.parse_args()

    stdout_file = None
    stderr_file = None
    try:
        if args.stdout_file is not None:
            stdout_file = open(args.stdout_file, 'w')
        
        if args.stderr_file is not None:
            stderr_file = open(args.stderr_file, 'w')

        (return_code, stdout, stderr) = run(args.filename, args.script_name, args.extra_args, stdout_file, stderr_file)
        if stdout:
            print(stdout, file=sys.stdout)

        if stderr:
            print(stderr, file=sys.stderr)

        exit(return_code)
    finally:
        if stdout_file is not None:
            stdout_file.close()
        if stderr_file is not None:
            stderr_file.close()


if __name__ == '__main__':
    main()