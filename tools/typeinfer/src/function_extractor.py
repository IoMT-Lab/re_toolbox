import re
from pathlib import Path
from typing import Dict

FUNC_HEADER = re.compile(r'^\s*([A-Za-z_.$][\w.$@]*)\s*:\s*$')
CLOSER_LINE = re.compile(r'^\s*\)\s*\}?\s*$')

def extract_functions_from_debug_program(text: str) -> Dict[str, str]:

    lines = text.splitlines()
    functions: Dict[str, str] = {}

    current_name = None
    buffer = []

    for line in lines:
        m = FUNC_HEADER.match(line)
        if m:
            if current_name is not None:
                body = "\n".join(buffer).rstrip("\n")
                if re.search(r'^\s*input_vars\s*:', body, flags=re.M):
                    functions[current_name] = body
            current_name = m.group(1)
            buffer = []
            continue

        if current_name is not None:
            if CLOSER_LINE.match(line):
                body = "\n".join(buffer).rstrip("\n")
                if re.search(r'^\s*input_vars\s*:', body, flags=re.M):
                    functions[current_name] = body
                current_name, buffer = None, []
                continue

            buffer.append(line)


    if current_name is not None:
        body = "\n".join(buffer).rstrip("\n")
        if re.search(r'^\s*input_vars\s*:', body, flags=re.M):
            functions[current_name] = body

    return functions


def extract_functions_from_file(path: str) -> Dict[str, str]:
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    return extract_functions_from_debug_program(text)

if __name__ == "__main__":
    path = "test/test_input_ssa.txt"
    funcs = extract_functions_from_file(path)

    for fid, (name, code) in enumerate(funcs.items(), start=1):
        print(f"== [{fid}] {name} ==\n{code}\n")

    print(f"Total {len(funcs)} functions.")
