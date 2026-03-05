#!/usr/bin/env python3
"""
Comprehensive Demo: Test Agent4Decompile across architectures, LLMs, and complexity levels.

This script runs the pipeline on all example binaries (x86 + ARM64) with both
LLM providers and produces a summary table for the paper.

Usage:
    # Full demo (all combinations)
    python scripts/run_demo.py

    # Quick demo (level1 only, both archs, both LLMs)
    python scripts/run_demo.py --quick

    # Specific levels
    python scripts/run_demo.py --levels 1 2 3

    # Single arch
    python scripts/run_demo.py --arch x86

    # Single LLM
    python scripts/run_demo.py --llm anthropic
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Allow running from any directory
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent4decompile.env_loader import load_env
load_env()

from agent4decompile.pipeline import Agent4DecompilePipeline


# ──────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────
EXAMPLE_DIR = ROOT / "examples" / "bin"

LEVELS = {
    1: "level1_simple_math",
    2: "level2_structs",
    3: "level3_linked_list",
    4: "level4_matrix",
    5: "level5_hashmap",
}

ARCHS = ["x86", "arm64"]
LLMS = ["anthropic", "openai"]
DECOMPILER = "angr"   # Only angr is available
MAX_ITERATIONS = 5


def find_binary(arch: str, level: int) -> Path | None:
    """Find the binary for a given arch + level."""
    name = LEVELS[level]
    p = EXAMPLE_DIR / arch / name
    if p.exists():
        return p
    return None


def run_one(
    binary_path: Path,
    arch_label: str,
    llm: str,
    level: int,
    output_base: Path,
    max_iters: int = MAX_ITERATIONS,
) -> dict:
    """Run a single pipeline invocation and return a result dict."""
    tag = f"{arch_label}_level{level}_{llm}"
    out_dir = output_base / tag
    out_dir.mkdir(parents=True, exist_ok=True)

    arch_val = "aarch64" if arch_label == "arm64" else "x86_64"

    print(f"\n{'─'*60}")
    print(f"  [{tag}] {binary_path.name} | arch={arch_val} | llm={llm}")
    print(f"{'─'*60}")

    result_info = {
        "tag": tag,
        "binary": str(binary_path),
        "arch": arch_val,
        "llm": llm,
        "level": level,
        "level_name": LEVELS[level],
        "success": False,
        "syntax": False,
        "compiles": False,
        "re_executable": False,
        "iterations": 0,
        "elapsed_s": 0.0,
        "error": None,
    }

    try:
        pipeline = Agent4DecompilePipeline(
            decompiler=DECOMPILER,
            llm_provider=llm,
            max_iterations=max_iters,
            constraint_level=3,
            architecture=arch_val,
        )
        r = pipeline.run(
            binary_path=str(binary_path),
            output_dir=str(out_dir),
        )
        result_info.update({
            "success": r.success,
            "syntax": r.syntax_valid,
            "compiles": r.compiles,
            "re_executable": r.re_executable,
            "iterations": r.iterations,
            "elapsed_s": round(r.elapsed_seconds, 1),
        })
    except Exception as e:
        result_info["error"] = str(e)
        print(f"    ✗ Exception: {e}")

    return result_info


def print_table(results: list[dict]):
    """Print a nicely-formatted results table."""
    # Header
    cols = ["Level", "Binary", "Arch", "LLM", "L1", "L2", "L3", "Iters", "Time(s)", "Status"]
    widths = [5, 22, 7, 10, 4, 4, 4, 5, 8, 12]
    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    hdr = "|" + "|".join(f" {c:<{w}} " for c, w in zip(cols, widths)) + "|"

    print("\n" + "=" * 100)
    print("  Agent4Decompile — Comprehensive Demo Results")
    print("=" * 100)
    print(sep)
    print(hdr)
    print(sep)

    for r in sorted(results, key=lambda x: (x['level'], x['arch'], x['llm'])):
        syn = "✓" if r['syntax'] else "✗"
        comp = "✓" if r['compiles'] else "✗"
        exe = "✓" if r['re_executable'] else "✗"
        status = "✅ PASS" if r['success'] else "❌ FAIL"
        if r.get('error'):
            status = "💥 ERR"
        row_vals = [
            f"{r['level']}",
            r['level_name'],
            r['arch'][:7],
            r['llm'],
            syn, comp, exe,
            str(r['iterations']),
            f"{r['elapsed_s']:.1f}",
            status,
        ]
        row = "|" + "|".join(f" {v:<{w}} " for v, w in zip(row_vals, widths)) + "|"
        print(row)

    print(sep)

    # Summary stats
    total = len(results)
    passed = sum(1 for r in results if r['success'])
    l1_pass = sum(1 for r in results if r['syntax'])
    l2_pass = sum(1 for r in results if r['compiles'])
    l3_pass = sum(1 for r in results if r['re_executable'])
    avg_time = sum(r['elapsed_s'] for r in results) / max(total, 1)
    avg_iters = sum(r['iterations'] for r in results) / max(total, 1)

    print(f"\n  Summary: {passed}/{total} re-executable ({100*passed/max(total,1):.0f}%)")
    print(f"  L1 (syntax): {l1_pass}/{total} | L2 (compile): {l2_pass}/{total} | L3 (exec): {l3_pass}/{total}")
    print(f"  Avg iterations: {avg_iters:.1f} | Avg time: {avg_time:.1f}s")

    # Per-arch breakdown
    for a in sorted(set(r['arch'] for r in results)):
        sub = [r for r in results if r['arch'] == a]
        p = sum(1 for r in sub if r['success'])
        print(f"    {a}: {p}/{len(sub)} re-executable")

    # Per-LLM breakdown
    for l in sorted(set(r['llm'] for r in results)):
        sub = [r for r in results if r['llm'] == l]
        p = sum(1 for r in sub if r['success'])
        print(f"    {l}: {p}/{len(sub)} re-executable")

    print()


def main():
    parser = argparse.ArgumentParser(description="Agent4Decompile comprehensive demo")
    parser.add_argument("--quick", action="store_true",
                        help="Quick mode: level 1 only")
    parser.add_argument("--levels", type=int, nargs="+", default=None,
                        help="Specific levels to test (1-5)")
    parser.add_argument("--arch", choices=["x86", "arm64", "all"], default="all",
                        help="Architecture(s) to test")
    parser.add_argument("--llm", choices=["openai", "anthropic", "all"], default="all",
                        help="LLM provider(s) to test")
    parser.add_argument("--max-iters", type=int, default=MAX_ITERATIONS,
                        help="Max iterations per binary")
    parser.add_argument("--output", default=None,
                        help="Output base directory")
    args = parser.parse_args()

    # Resolve parameters
    levels = args.levels or ([1] if args.quick else list(LEVELS.keys()))
    archs = [args.arch] if args.arch != "all" else ARCHS
    llms = [args.llm] if args.llm != "all" else LLMS

    # Validate
    for lv in levels:
        if lv not in LEVELS:
            print(f"Error: Unknown level {lv}. Valid: {list(LEVELS.keys())}")
            sys.exit(1)

    # Output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_base = Path(args.output) if args.output else ROOT / "output" / f"demo_{timestamp}"
    output_base.mkdir(parents=True, exist_ok=True)

    # Count total runs
    runs = []
    for lv in levels:
        for arch in archs:
            binary = find_binary(arch, lv)
            if binary is None:
                continue
            for llm in llms:
                runs.append((binary, arch, llm, lv))

    total = len(runs)
    print(f"\n{'='*60}")
    print(f"  Agent4Decompile — Comprehensive Demo")
    print(f"{'='*60}")
    print(f"  Levels:     {levels}")
    print(f"  Archs:      {archs}")
    print(f"  LLMs:       {llms}")
    print(f"  Decompiler: {DECOMPILER}")
    print(f"  Max iters:  {args.max_iters}")
    print(f"  Total runs: {total}")
    print(f"  Output:     {output_base}")
    print(f"{'='*60}")

    results = []
    t_start = time.time()

    for i, (binary, arch, llm, lv) in enumerate(runs, 1):
        print(f"\n>>> Run {i}/{total}")
        r = run_one(binary, arch, llm, lv, output_base, max_iters=args.max_iters)
        results.append(r)

        # Save intermediate results
        results_path = output_base / "demo_results.json"
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2)

    total_time = time.time() - t_start

    # Final table
    print_table(results)

    print(f"  Total wall time: {total_time:.1f}s ({total_time/60:.1f}min)")
    print(f"  Results saved to: {output_base / 'demo_results.json'}")

    # Generate Markdown table for paper
    md_path = output_base / "demo_results.md"
    with open(md_path, 'w') as f:
        f.write("# Agent4Decompile Demo Results\n\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write("| Level | Binary | Arch | LLM | L1 | L2 | L3 | Iters | Time(s) |\n")
        f.write("|-------|--------|------|-----|----|----|----|----|-----|\n")
        for r in sorted(results, key=lambda x: (x['level'], x['arch'], x['llm'])):
            syn = "✓" if r['syntax'] else "✗"
            comp = "✓" if r['compiles'] else "✗"
            exe = "✓" if r['re_executable'] else "✗"
            f.write(f"| {r['level']} | {r['level_name']} | {r['arch']} | {r['llm']} "
                    f"| {syn} | {comp} | {exe} | {r['iterations']} | {r['elapsed_s']:.1f} |\n")
        f.write(f"\n**Overall: {sum(1 for r in results if r['success'])}/{len(results)} re-executable**\n")

    print(f"  Markdown table: {md_path}")


if __name__ == "__main__":
    main()
