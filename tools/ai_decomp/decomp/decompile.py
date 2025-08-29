#!/usr/bin/env python3

import argparse
import os
import time
import gc
import tempfile
import re
from typing import Tuple, List

import torch

from src.utils.decompilers import DecompilerFactory

import os
os.environ['KMP_DUPLICATE_LIB_OK']='True'


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Single-file decompilation script")
    parser.add_argument("input", type=str, help="Path to input assembly file")
    parser.add_argument("command", choices=['list', 'decompile'], help="Command to run")
    parser.add_argument("--multi_function", "-m", action='store_true', help="Whether the input assembly file contains multiple functions")
    parser.add_argument("--output", "-o", type=str, default='data/example.cpp', help="Path to the output decompiled file")
    parser.add_argument("--decompilation_method", "-d", type=str, default='RAG', choices=['RAG', 'general_llm'], help="Decompilation method to use")
    parser.add_argument("--rag_db", type=str, default='exe_bench', choices=['exe_bench', 'mbpp'], help="RAG database selector")

    args = parser.parse_args()

    if args.decompilation_method == 'RAG':
        _inject_rag_paths(args)
        args.rag_prompt_template = 'default'
        args.top_k = 5

    args.api_url = 'https://api.deepseek.com/chat/completions'
    args.api_timeout = 300
    args.api_max_retries = 3
    args.api_retry_delay = 1
    args.temperature = 0.8
    args.max_new_tokens = 2048
    args.max_total_tokens = 10000
    args.gpus = 1
    args.gpu_memory_utilization = 0.7

    return args


def _inject_rag_paths(args: argparse.Namespace) -> None:
    local_path = os.path.dirname(__file__)
    if args.rag_db == 'exe_bench':
        base_path = os.path.join(local_path, 'rag_db/exe_bench')
        args.kb_path = f'{base_path}/raw.jsonl'
        args.embeddings_path = f'{base_path}/embeddings.npz'
        args.chunks_path = f'{base_path}/chunks.jsonl'
    elif args.rag_db == 'mbpp':
        base_path = os.path.join(local_path, 'rag_db/mbpp')
        args.kb_path = f'{base_path}/raw.json'
        args.embeddings_path = f'{base_path}/embeddings.npz'
        args.chunks_path = f'{base_path}/chunks.jsonl'
    else:
        raise ValueError(f"Unsupported rag_db: {args.rag_db}")


def cleanup_gpu_memory() -> None:
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        gc.collect()
        torch.cuda.synchronize()


def _build_prompt(assembly_text: str) -> str:
    before = "# This is the assembly code:\n"
    after = "\n# What is the source code?\n"
    return f"{before}{assembly_text.strip()}{after}"


def _read_assembly_file(path: str) -> str:
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()


def _write_output_file(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def _extract_functions(assembly_text: str) -> List[str]:
    functions = []
    lines = assembly_text.split('\n')
    current_function = []
    in_function = False
    
    for line in lines:
        if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*\(.*\):', line):
            if current_function:
                functions.append('\n'.join(current_function))
            current_function = [line]
            in_function = True
        elif in_function:
            current_function.append(line)
            if line.strip() == 'retq':
                functions.append('\n'.join(current_function))
                current_function = []
                in_function = False
    
    if current_function:
        functions.append('\n'.join(current_function))
    
    return functions

def _extract_functions(assembly_text: str) -> List[str]:
    functions = []
    lines = assembly_text.split('\n')
    current_function = []
    in_function = False
    
    for line in lines:
        if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*\(.*\):', line):
            if current_function:
                functions.append('\n'.join(current_function))
            current_function = [line]
            in_function = True
        elif in_function:
            current_function.append(line)
            if line.strip() == 'retq':
                functions.append('\n'.join(current_function))
                current_function = []
                in_function = False
    
    if current_function:
        functions.append('\n'.join(current_function))
    
    return functions

import re
from typing import List

# Matches headers like:
#   <_init>:
#   0000000000001140 <_init>:
#   func0(std::vector<float, std::allocator<float> >, float):
#   simple_name:
HEADER_RE = re.compile(r"""
^ \s*
(?: [0-9A-Fa-f]+: \s* )?           # optional leading address with colon (rare style)
(?: [0-9A-Fa-f]+ \s+ )?            # optional leading address w/o colon (common objdump)
(?:
    <[^>]+>                        # <symbol>
  | [A-Za-z_][\w$@]* (?:\s*\([^)]*\))?   # name or demangled with (...)
)
: \s*$
""", re.X)

def extract_functions(assembly_text: str) -> List[str]:
    functions: List[str] = []
    current: List[str] = []
    in_function = False

    for line in assembly_text.splitlines():
        if HEADER_RE.match(line):
            if current:
                functions.append("\n".join(current).rstrip())
                current = []
            in_function = True
            current.append(line)
        elif in_function:
            current.append(line)

    if current:
        functions.append("\n".join(current).rstrip())

    return functions


def _format_combined_output(results: List[str]) -> str:
    output = ''
    for i, result in enumerate(results):
        clean_result = result.strip()
        if clean_result:
            output += clean_result + '\n\n'
    return output


def _validate_paths(input_path: str, output_path: str) -> None:
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    if output_path is not None:
        out_parent = os.path.dirname(os.path.abspath(output_path))
        if out_parent and not os.path.isdir(out_parent):
            os.makedirs(out_parent, exist_ok=True)


def run_once(args: argparse.Namespace) -> Tuple[bool, str]:
    assembly_text = _read_assembly_file(args.input)
    
    if args.multi_function:
        return _run_multi_function(args, assembly_text)
    else:
        return _run_single_function(args, assembly_text)


def _run_single_function(args: argparse.Namespace, assembly_text: str) -> Tuple[bool, str]:
    prompt = _build_prompt(assembly_text)
    assembly_lines = assembly_text.splitlines()
    preview = "\n".join(assembly_lines[:10])
    print("Preview of input assembly code:")
    print(preview)
    
    print(f"\nLoading decompiler: {args.decompilation_method}")
    decompiler = DecompilerFactory.create_decompiler(args.decompilation_method, args)
    
    delay = max(0, int(args.api_retry_delay))
    attempts = max(1, int(args.api_max_retries))
    
    try:
        print(f"\nStarting decompilation with {args.decompilation_method}...")
        for attempt in range(1, attempts + 1):
            try:
                result = decompiler.decompile(prompt)
                _write_output_file(args.output, result)
                return True, f"Decompilation succeeded, output saved to {args.output}"
            except Exception as e:
                if attempt >= attempts:
                    raise
                time.sleep(delay)
                delay = max(delay * 2, 1)
    except Exception as e:
        return False, f"Decompilation failed: {e}"
    finally:
        try:
            decompiler.cleanup()
        finally:
            cleanup_gpu_memory()


def _run_multi_function(args: argparse.Namespace, assembly_text: str) -> Tuple[bool, str]:
    functions = extract_functions(assembly_text)
    if not functions:
        return False, "No func0 functions found in assembly file"
    
    print(f"Found {len(functions)} functions")
    
    results = []
    temp_files = []
    
    try:
        for i, func_code in enumerate(functions):
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.s', delete=False)
            temp_file.write(func_code)
            temp_file.close()
            temp_files.append(temp_file.name)
            
            print(f"\nDecompiling function {i+1}/{len(functions)}...")
            
            temp_args = argparse.Namespace(**vars(args))
            temp_args.input = temp_file.name
            
            success, result = _run_single_function(temp_args, func_code)
            if success:
                with open(temp_args.output, 'r') as f:
                    results.append(f.read())
            else:
                return False, f"Failed to decompile function {i+1}: {result}"
        
        combined_output = _format_combined_output(results)
        _write_output_file(args.output, combined_output)
        
        return True, f"Multi-function decompilation succeeded, {len(functions)} functions processed, output saved to {args.output}"
    
    finally:
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass


def main() -> None:
    args = parse_arguments()
    try:
        _validate_paths(args.input, args.output)
        if args.command == 'list':
            assembly_text = _read_assembly_file(args.input)
            functions = extract_functions(assembly_text)
            for function in functions:
                print(function)
        else:
            ok, msg = run_once(args)
            print(msg)
            if not ok:
                raise SystemExit(1)
    except Exception as e:
        print(f"Error: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()