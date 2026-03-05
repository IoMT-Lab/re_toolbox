#!/usr/bin/env python3
"""
Baseline decompilation — raw decompiler output without LLM refinement.

Useful for:
  - Measuring improvement from LLM refinement vs. raw decompiler output
  - Generating initial decompilation for manual inspection
  - Comparing decompiler quality (Ghidra vs Angr vs RetDec)

Examples:
    python run_baseline.py --binary ./test_binary --output ./baseline_output/
    python run_baseline.py --binary ./test_binary --decompiler angr --output ./out/
    python run_baseline.py --binary ./test_binary --all-decompilers --output ./out/
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent4decompile.decompilers.ghidra import GhidraDecompiler
from agent4decompile.decompilers.angr_decompiler import AngrDecompiler
from agent4decompile.decompilers.retdec import RetDecDecompiler


DECOMPILER_MAP = {
    "ghidra": GhidraDecompiler,
    "angr": AngrDecompiler,
    "retdec": RetDecDecompiler,
}


def check_compilability(source_path: str) -> dict:
    """Check if decompiled code compiles at L1 and L2."""
    results = {}

    # L1: syntax check
    r1 = subprocess.run(
        ["gcc", "-fsyntax-only", "-w", source_path],
        capture_output=True, text=True, timeout=30,
    )
    results["L1_syntax"] = r1.returncode == 0
    if not results["L1_syntax"]:
        results["L1_errors"] = r1.stderr[:500]

    # L2: full compilation
    out_bin = source_path + ".out"
    r2 = subprocess.run(
        ["gcc", "-w", "-o", out_bin, source_path, "-lm"],
        capture_output=True, text=True, timeout=30,
    )
    results["L2_compile"] = r2.returncode == 0
    if not results["L2_compile"]:
        results["L2_errors"] = r2.stderr[:500]
    else:
        # Clean up
        try:
            os.remove(out_bin)
        except OSError:
            pass

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Baseline decompilation (no LLM refinement)",
    )
    parser.add_argument("--binary", required=True,
                        help="Path to the ELF binary")
    parser.add_argument("--output", default="./baseline_output",
                        help="Output directory")
    parser.add_argument("--decompiler", default="ghidra",
                        choices=["ghidra", "angr", "retdec"])
    parser.add_argument("--all-decompilers", action="store_true",
                        help="Run all available decompilers")
    parser.add_argument("--check-compile", action="store_true",
                        help="Check if output compiles (gcc required)")
    parser.add_argument("--ghidra-path", default=None)
    parser.add_argument("--retdec-path", default=None)

    args = parser.parse_args()

    binary_path = Path(args.binary).resolve()
    if not binary_path.exists():
        print(f"Error: binary not found: {args.binary}")
        sys.exit(1)

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    decompilers_to_run = (
        ["ghidra", "angr", "retdec"] if args.all_decompilers
        else [args.decompiler]
    )

    report = {}

    for name in decompilers_to_run:
        print(f"\n[{name}] Decompiling {binary_path.name} ...")
        cls = DECOMPILER_MAP[name]

        kwargs = {}
        if name == "ghidra" and args.ghidra_path:
            kwargs["ghidra_path"] = args.ghidra_path
        if name == "retdec" and args.retdec_path:
            kwargs["retdec_path"] = args.retdec_path

        try:
            dec = cls(**kwargs)
            result = dec.decompile(str(binary_path))

            if result.success and result.source_code:
                out_file = out_dir / f"{binary_path.stem}_{name}.c"
                with open(out_file, "w") as f:
                    f.write(result.source_code)
                print(f"  ✓ Wrote {out_file} ({len(result.source_code)} chars)")

                entry = {
                    "success": True,
                    "output_file": str(out_file),
                    "code_length": len(result.source_code),
                    "functions_found": result.source_code.count("\n{"),
                }

                if args.check_compile:
                    comp = check_compilability(str(out_file))
                    entry.update(comp)
                    l1 = "✓" if comp["L1_syntax"] else "✗"
                    l2 = "✓" if comp["L2_compile"] else "✗"
                    print(f"  Compile check: L1={l1}  L2={l2}")

                report[name] = entry
            else:
                print(f"  ✗ Decompilation failed: {result.error_message}")
                report[name] = {"success": False, "error": result.error_message}

        except Exception as e:
            print(f"  ✗ Error: {e}")
            report[name] = {"success": False, "error": str(e)}

    # Save report
    report_path = out_dir / "baseline_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved to {report_path}")


if __name__ == "__main__":
    main()
