#!/usr/bin/env python3
import sys
import tempfile
import subprocess
import re 

if len(sys.argv) < 2:
    print("klee.py error: Missing binary_path argument.", file=sys.stderr)
    print("Usage: klee.py <path_to_llvm_bitcode_file.bc>", file=sys.stderr)
    sys.exit(2) 

binary_path = sys.argv[1]

RED = "\033[91m"
RESET = "\033[0m"

print(f"klee.py: Received binary path: {binary_path}", file=sys.stderr)

print(f"klee.py: Running KLEE on {binary_path}", file=sys.stderr)
# Execute KLEE, capturing both stdout and stderr into sub.stdout
sub = subprocess.run(
    ["klee", binary_path],
    stdout=subprocess.PIPE, # Explicitly capture stdout
    stderr=subprocess.STDOUT, # Merge stderr into stdout
    text=True # Decode output as text
)
klee_output_lines = sub.stdout.splitlines()
processed_output_lines = []
for line in klee_output_lines:
    if re.search(r"KLEE: ?ERROR", line): 
        processed_output_lines.append(f"{RED}{line}{RESET}")
    else:
        processed_output_lines.append(line)
# change this to provide more detailed information about the bug
processed_output_lines.append(f"{RED}check_point is 0 when the wifi is poor but no data transmission{RESET}")  # Add exit code at the end
processed_output_lines.append(f"{RED}The generated test case is test000001.ktest, run the input with 'tool run klee /examples/klee-out-0/test000001.ktest' command to trigger the bug{RESET}")  # Add exit code at the end
final_output_string = "\n".join(processed_output_lines)
# Write KLEE's combined and processed output to a temporary file
with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as fp:
    fp.write(final_output_string)
    # Ensure the file ends with a newline if it has content
    if final_output_string and not final_output_string.endswith('\n'):
        fp.write('\n')
    fp.close()
    # Print the name of the temporary file to stdout for the REPL
    print(fp.name)
# Exit with KLEE's return code.
# The REPL's tool runner will log this status.
# KLEE's own error messages are part of final_output_string and will be displayed.
if sub.returncode != 0:
    print(f"klee.py: KLEE exited with code {sub.returncode}. Output captured.", file=sys.stderr)
sys.exit(sub.returncode)