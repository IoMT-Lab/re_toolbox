#!/usr/bin/env python3
"""
Run the Agent4Decompile pipeline on a single binary.

Examples:
    # Default: Ghidra + GPT-4o, 5 iterations
    python run_pipeline.py --binary ./test_binary --output ./output/

    # RetDec + Claude
    python run_pipeline.py --binary ./test_binary --decompiler retdec \\
        --llm-provider anthropic --output ./output/

    # Multi-decompiler consensus + 10 iterations
    python run_pipeline.py --binary ./test_binary --multi-decompiler \\
        --max-iterations 10 --output ./output/

    # Decompile only (no LLM refinement)
    python run_pipeline.py --binary ./test_binary --no-refine --output ./output/
"""

import argparse
import json
import sys
from pathlib import Path

# Allow running from the scripts/ directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent4decompile.env_loader import load_env
load_env()

from agent4decompile.pipeline import Agent4DecompilePipeline


def main():
    parser = argparse.ArgumentParser(
        description="Agent4Decompile: Binary → Re-executable C",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--binary", required=True,
                        help="Path to the ELF binary to decompile")
    parser.add_argument("--output", default="./output",
                        help="Output directory (default: ./output)")
    parser.add_argument("--decompiler", default="ghidra",
                        choices=["ghidra", "angr", "retdec"],
                        help="Decompiler to use (default: ghidra)")
    parser.add_argument("--llm-provider", default="openai",
                        choices=["openai", "anthropic"],
                        help="LLM provider (default: openai)")
    parser.add_argument("--model", default=None,
                        help="LLM model name (default: auto)")
    parser.add_argument("--max-iterations", type=int, default=5,
                        help="Max refinement iterations (default: 5)")
    parser.add_argument("--constraint-level", type=int, default=3,
                        choices=[1, 2, 3],
                        help="Constraint level: 1=syntax, 2=+compile, 3=+exec (default: 3)")
    parser.add_argument("--multi-decompiler", action="store_true",
                        help="Use all 3 decompilers + consensus merge")
    parser.add_argument("--no-refine", action="store_true",
                        help="Skip LLM refinement (decompile only)")
    parser.add_argument("--test-cases", default=None,
                        help="JSON file with pre-defined test cases")
    parser.add_argument("--ghidra-path", default=None,
                        help="Override Ghidra installation path")
    parser.add_argument("--retdec-path", default=None,
                        help="Override RetDec installation path")
    parser.add_argument("--arch", default="auto",
                        choices=["auto", "x86_64", "aarch64"],
                        help="Target architecture (default: auto-detect from binary)")

    args = parser.parse_args()

    # Validate binary exists
    if not Path(args.binary).exists():
        print(f"Error: Binary not found: {args.binary}")
        sys.exit(1)

    # Load test cases if provided
    test_cases = None
    if args.test_cases:
        with open(args.test_cases) as f:
            data = json.load(f)
        binary_name = Path(args.binary).stem
        # Handle both flat list and dict-by-name formats
        if isinstance(data, list):
            test_cases = data
        elif isinstance(data, dict):
            test_cases = data.get(binary_name, data.get(Path(args.binary).name, []))

    # Print header
    print("=" * 60)
    print("  Agent4Decompile — Binary → Re-executable C")
    print("=" * 60)
    print(f"  Binary:      {args.binary}")
    print(f"  Decompiler:  {args.decompiler}" + (" (multi)" if args.multi_decompiler else ""))
    print(f"  LLM:         {args.llm_provider}/{args.model or 'default'}")
    print(f"  Iterations:  {args.max_iterations}")
    print(f"  Constraints: L1–L{args.constraint_level}")
    print(f"  Architecture: {args.arch}")
    print(f"  Output:      {args.output}")
    if args.no_refine:
        print(f"  Mode:        Decompile only (no LLM)")
    print("=" * 60 + "\n")

    # Run pipeline
    pipeline = Agent4DecompilePipeline(
        decompiler=args.decompiler,
        llm_provider=args.llm_provider,
        model=args.model,
        max_iterations=args.max_iterations,
        constraint_level=args.constraint_level,
        multi_decompiler=args.multi_decompiler,
        ghidra_path=args.ghidra_path,
        retdec_path=args.retdec_path,
        architecture=args.arch,
    )

    result = pipeline.run(
        binary_path=args.binary,
        output_dir=args.output,
        test_cases=test_cases,
        skip_refinement=args.no_refine,
    )

    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
