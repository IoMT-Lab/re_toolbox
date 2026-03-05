#!/usr/bin/env python3
"""
Run the Agent4Decompile pipeline on a directory of binaries.

Examples:
    # Process all binaries in a directory
    python run_batch.py --input-dir ./binaries/ --output-dir ./results/

    # Multi-decompiler + Anthropic, parallel workers
    python run_batch.py --input-dir ./binaries/ --output-dir ./results/ \\
        --multi-decompiler --llm-provider anthropic --workers 4
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent4decompile.pipeline import Agent4DecompilePipeline


def is_elf_binary(path: str) -> bool:
    """Check if a file is an ELF binary."""
    try:
        with open(path, "rb") as f:
            magic = f.read(4)
        return magic == b"\x7fELF"
    except Exception:
        return False


def process_one(args_dict: dict) -> dict:
    """Process a single binary (used by workers)."""
    binary_path = args_dict["binary_path"]
    output_dir = args_dict["output_dir"]
    name = Path(binary_path).stem

    try:
        pipeline = Agent4DecompilePipeline(
            decompiler=args_dict["decompiler"],
            llm_provider=args_dict["llm_provider"],
            model=args_dict.get("model"),
            max_iterations=args_dict["max_iterations"],
            constraint_level=args_dict["constraint_level"],
            multi_decompiler=args_dict["multi_decompiler"],
            ghidra_path=args_dict.get("ghidra_path"),
            retdec_path=args_dict.get("retdec_path"),
        )

        test_cases = args_dict.get("test_cases", {}).get(name)
        result = pipeline.run(
            binary_path=binary_path,
            output_dir=os.path.join(output_dir, name),
            test_cases=test_cases,
            skip_refinement=args_dict.get("no_refine", False),
        )

        # Derive constraint level reached from result flags
        if result.re_executable:
            level_reached = 3
        elif result.compiles:
            level_reached = 2
        elif result.syntax_valid:
            level_reached = 1
        else:
            level_reached = 0

        return {
            "binary": name,
            "success": result.success,
            "constraint_level_reached": level_reached,
            "iterations": result.iterations,
            "decompiler": result.decompiler,
        }
    except Exception as e:
        return {
            "binary": name,
            "success": False,
            "error": str(e),
        }


def main():
    parser = argparse.ArgumentParser(
        description="Batch Agent4Decompile: decompile a directory of binaries",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--input-dir", required=True,
                        help="Directory containing ELF binaries")
    parser.add_argument("--output-dir", default="./batch_output",
                        help="Output root directory")
    parser.add_argument("--decompiler", default="ghidra",
                        choices=["ghidra", "angr", "retdec"])
    parser.add_argument("--llm-provider", default="openai",
                        choices=["openai", "anthropic"])
    parser.add_argument("--model", default=None)
    parser.add_argument("--max-iterations", type=int, default=5)
    parser.add_argument("--constraint-level", type=int, default=3,
                        choices=[1, 2, 3])
    parser.add_argument("--multi-decompiler", action="store_true")
    parser.add_argument("--no-refine", action="store_true")
    parser.add_argument("--workers", type=int, default=1,
                        help="Parallel workers (default: 1)")
    parser.add_argument("--test-cases", default=None,
                        help="JSON dict of {binary_name: [test_cases]}")
    parser.add_argument("--ghidra-path", default=None)
    parser.add_argument("--retdec-path", default=None)

    args = parser.parse_args()

    # Discover binaries
    input_dir = Path(args.input_dir)
    if not input_dir.is_dir():
        print(f"Error: not a directory: {args.input_dir}")
        sys.exit(1)

    binaries = sorted(
        str(p) for p in input_dir.iterdir()
        if p.is_file() and is_elf_binary(str(p))
    )

    if not binaries:
        print(f"No ELF binaries found in {args.input_dir}")
        sys.exit(1)

    print(f"Found {len(binaries)} ELF binaries in {args.input_dir}")

    # Load test cases
    test_cases = {}
    if args.test_cases:
        with open(args.test_cases) as f:
            test_cases = json.load(f)

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    # Build work items
    work = []
    for b in binaries:
        work.append({
            "binary_path": b,
            "output_dir": args.output_dir,
            "decompiler": args.decompiler,
            "llm_provider": args.llm_provider,
            "model": args.model,
            "max_iterations": args.max_iterations,
            "constraint_level": args.constraint_level,
            "multi_decompiler": args.multi_decompiler,
            "no_refine": args.no_refine,
            "test_cases": test_cases,
            "ghidra_path": args.ghidra_path,
            "retdec_path": args.retdec_path,
        })

    # Execute
    results = []
    t0 = time.time()

    if args.workers <= 1:
        for i, item in enumerate(work, 1):
            print(f"[{i}/{len(work)}] Processing {Path(item['binary_path']).name} ...")
            r = process_one(item)
            results.append(r)
            status = "✓" if r["success"] else "✗"
            print(f"  {status}  L{r.get('constraint_level_reached', '?')} "
                  f"({r.get('iterations', '?')} iter)")
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(process_one, item): item for item in work}
            for i, future in enumerate(as_completed(futures), 1):
                r = future.result()
                results.append(r)
                status = "✓" if r["success"] else "✗"
                print(f"[{i}/{len(work)}] {r['binary']}: {status}")

    elapsed = time.time() - t0

    # Summary
    success = sum(1 for r in results if r["success"])
    print("\n" + "=" * 50)
    print(f"  Completed {len(results)} binaries in {elapsed:.1f}s")
    print(f"  Success: {success}/{len(results)} "
          f"({100 * success / len(results):.1f}%)")
    print("=" * 50)

    # Save results
    report_path = Path(args.output_dir) / "batch_results.json"
    with open(report_path, "w") as f:
        json.dump({
            "config": {
                "decompiler": args.decompiler,
                "llm_provider": args.llm_provider,
                "max_iterations": args.max_iterations,
                "constraint_level": args.constraint_level,
                "multi_decompiler": args.multi_decompiler,
            },
            "summary": {
                "total": len(results),
                "success": success,
                "rate": success / len(results) if results else 0,
                "elapsed_seconds": elapsed,
            },
            "results": results,
        }, f, indent=2)
    print(f"  Report: {report_path}")


if __name__ == "__main__":
    main()
