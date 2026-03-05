"""
Agent4Decompile Pipeline — End-to-end: Binary → Re-executable C

This is the main orchestrator that ties together:
  1. Decompilation   (Ghidra / Angr / RetDec)
  2. Post-processing (type fixes, system function removal)
  3. Consensus merge (optional, when using multiple decompilers)
  4. Test generation (pattern / source / dynamic)
  5. LLM iterative refinement (3-level constraint-guided)

Usage:
    from agent4decompile.pipeline import Agent4DecompilePipeline

    pipe = Agent4DecompilePipeline(decompiler="ghidra")
    result = pipe.run("/path/to/binary", output_dir="./output")
"""

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .decompilers.base import DecompilationResult
from .arch import detect_arch
from .refinement.refiner import MCGDRefiner, RefinementResult, preprocess_decompiled_code
from .testing.pattern_generator import PatternTestGenerator
from .testing.source_generator import SourceTestGenerator
from .testing.dynamic_generator import DynamicTestGenerator
from .arch import detect_arch, detect_arch_angr, docker_run


@dataclass
class PipelineResult:
    """Complete result of the Agent4Decompile pipeline."""
    success: bool
    binary_path: str
    decompiler: str
    architecture: str = "x86_64"

    # Stage outputs
    decompiled_code: Optional[str] = None
    refined_code: Optional[str] = None

    # Metrics
    iterations: int = 0
    syntax_valid: bool = False
    compiles: bool = False
    re_executable: bool = False
    elapsed_seconds: float = 0.0

    # Files written
    output_files: Dict[str, str] = field(default_factory=dict)

    # Errors
    error_message: Optional[str] = None

    # History
    iteration_history: List[Dict] = field(default_factory=list)


class Agent4DecompilePipeline:
    """
    End-to-end binary → re-executable C pipeline.

    Args:
        decompiler:       Which decompiler to use: ``"ghidra"``, ``"angr"``, ``"retdec"``
        llm_provider:     ``"openai"`` or ``"anthropic"``
        model:            LLM model name (default auto-selected)
        max_iterations:   Max LLM refinement rounds (default 5)
        constraint_level: 1=syntax, 2=+compile, 3=+execution (default 3)
        multi_decompiler: If True, use all 3 decompilers + consensus merge
        ghidra_path:      Override Ghidra install path
        retdec_path:      Override RetDec install path
        architecture:     Target arch: ``"auto"``, ``"x86_64"``, ``"aarch64"``
    """

    def __init__(
        self,
        decompiler: str = "ghidra",
        llm_provider: str = "openai",
        model: str | None = None,
        max_iterations: int = 5,
        constraint_level: int = 3,
        multi_decompiler: bool = False,
        ghidra_path: str | None = None,
        retdec_path: str | None = None,
        architecture: str = "auto",
    ):
        self.decompiler_name = decompiler.lower()
        self.llm_provider = llm_provider
        self.model = model
        self.max_iterations = max_iterations
        self.constraint_level = constraint_level
        self.multi_decompiler = multi_decompiler
        self.ghidra_path = ghidra_path
        self.retdec_path = retdec_path
        self.architecture = architecture  # "auto" means detect from binary

    # ==================================================================
    # Main entry point
    # ==================================================================
    def run(
        self,
        binary_path: str,
        output_dir: str = "./output",
        test_cases: List[Dict] | None = None,
        skip_refinement: bool = False,
    ) -> PipelineResult:
        """
        Run the full pipeline on a single binary.

        Args:
            binary_path:     Path to ELF binary.
            output_dir:      Directory for output files.
            test_cases:      Pre-defined test cases (auto-generated if None).
            skip_refinement: If True, only decompile + post-process (no LLM).

        Returns:
            ``PipelineResult`` with all outputs and metrics.
        """
        t0 = time.time()
        binary_path = str(Path(binary_path).resolve())
        binary_name = Path(binary_path).stem
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        # ── Detect architecture ───────────────────────────────────────────
        if self.architecture == "auto":
            arch = detect_arch(binary_path)
            print(f"[0/4] Detected architecture: {arch}")
        else:
            arch = self.architecture
            print(f"[0/4] Using specified architecture: {arch}")

        is_arm = arch in ("aarch64", "arm")
        if is_arm:
            from .arch import ensure_arm_docker
            if not ensure_arm_docker():
                return PipelineResult(
                    success=False, binary_path=binary_path,
                    decompiler=self.decompiler_name, architecture=arch,
                    error_message="ARM Docker image not available. Build with: "
                                  "docker build -t agent4decompile-arm -f docker/Dockerfile.arm docker/",
                )
            print(f"    → ARM Docker toolchain ready")

        result = PipelineResult(
            success=False,
            binary_path=binary_path,
            decompiler=self.decompiler_name,
            architecture=arch,
        )

        # ── Stage 1+2: Decompile + Post-process ──────────────────────────
        print(f"[1/4] Decompiling {binary_name} with {self.decompiler_name}…")

        if self.multi_decompiler:
            initial_code = self._decompile_multi(binary_path, out)
        else:
            initial_code = self._decompile_single(binary_path)

        if initial_code is None:
            result.error_message = "Decompilation failed"
            result.elapsed_seconds = time.time() - t0
            return result

        result.decompiled_code = initial_code

        # Save raw decompiled output
        raw_path = out / f"{binary_name}_decompiled.c"
        raw_path.write_text(initial_code)
        result.output_files['decompiled'] = str(raw_path)
        print(f"    → Saved decompiled code to {raw_path}")

        if skip_refinement:
            result.refined_code = initial_code
            result.success = True
            result.elapsed_seconds = time.time() - t0
            return result

        # ── Stage 3: Generate test cases ──────────────────────────────────
        if test_cases is None:
            print(f"[2/4] Generating test cases…")
            test_cases = self._generate_tests(binary_path, binary_name, initial_code, arch)
            print(f"    → Generated {len(test_cases)} test cases")
        else:
            print(f"[2/4] Using {len(test_cases)} provided test cases")

        # ── Stage 4: LLM Iterative Refinement ────────────────────────────
        print(f"[3/4] Running LLM refinement (max {self.max_iterations} iterations)…")
        refiner = MCGDRefiner(
            llm_provider=self.llm_provider,
            model=self.model,
            max_iterations=self.max_iterations,
            constraint_level=self.constraint_level,
            architecture=arch,
        )

        ref_result: RefinementResult = refiner.refine(
            initial_code=initial_code,
            binary_name=binary_name,
            decompiler=self.decompiler_name,
            original_binary_path=binary_path,
            test_cases=test_cases,
        )

        result.iterations = ref_result.iterations
        result.syntax_valid = ref_result.syntax_valid
        result.compiles = ref_result.compiles
        result.re_executable = ref_result.re_executable
        result.iteration_history = ref_result.iteration_history
        result.refined_code = ref_result.refined_code
        result.success = ref_result.success

        # ── Save outputs ──────────────────────────────────────────────────
        print(f"[4/4] Saving results…")
        refined_path = out / f"{binary_name}_refined.c"
        refined_path.write_text(ref_result.refined_code)
        result.output_files['refined'] = str(refined_path)

        tc_path = out / f"{binary_name}_test_cases.json"
        with open(tc_path, 'w') as f:
            json.dump(test_cases, f, indent=2)
        result.output_files['test_cases'] = str(tc_path)

        summary = {
            'binary': binary_name,
            'architecture': arch,
            'decompiler': self.decompiler_name,
            'llm': f"{self.llm_provider}/{self.model or 'default'}",
            'success': result.success,
            'iterations': result.iterations,
            'syntax_valid': result.syntax_valid,
            'compiles': result.compiles,
            're_executable': result.re_executable,
            'elapsed_seconds': round(time.time() - t0, 2),
        }
        summary_path = out / f"{binary_name}_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        result.output_files['summary'] = str(summary_path)

        result.elapsed_seconds = time.time() - t0

        # ── Print summary ─────────────────────────────────────────────────
        status = "✅ SUCCESS" if result.success else "❌ INCOMPLETE"
        print(f"\n{'='*60}")
        print(f"  {status}  |  {result.iterations} iterations  |  {result.elapsed_seconds:.1f}s")
        print(f"  Syntax: {result.syntax_valid}  |  Compiles: {result.compiles}  |  Re-executable: {result.re_executable}")
        print(f"  Output: {refined_path}")
        print(f"{'='*60}\n")

        return result

    # ==================================================================
    # Private helpers
    # ==================================================================

    def _get_decompiler(self, name: str):
        """Lazily instantiate a decompiler wrapper."""
        if name == 'ghidra':
            from .decompilers.ghidra import GhidraDecompiler
            return GhidraDecompiler(ghidra_path=self.ghidra_path)
        elif name == 'angr':
            from .decompilers.angr_decompiler import AngrDecompiler
            return AngrDecompiler()
        elif name == 'retdec':
            from .decompilers.retdec import RetDecDecompiler
            return RetDecDecompiler(retdec_path=self.retdec_path)
        else:
            raise ValueError(f"Unknown decompiler: {name}")

    def _decompile_single(self, binary_path: str) -> Optional[str]:
        """Decompile with a single decompiler."""
        try:
            dec = self._get_decompiler(self.decompiler_name)
            res: DecompilationResult = dec.decompile(binary_path)
            if res.success and res.source_code:
                return res.source_code
            print(f"    ✗ Decompilation failed: {res.error_message}")
            return None
        except Exception as e:
            print(f"    ✗ Decompiler error: {e}")
            return None

    def _decompile_multi(self, binary_path: str, output_dir: Path) -> Optional[str]:
        """Decompile with all available decompilers and merge via consensus."""
        from .consensus.engine import MCGDEngine

        sources: dict[str, str] = {}
        for name in ('ghidra', 'retdec', 'angr'):
            try:
                dec = self._get_decompiler(name)
                res = dec.decompile(binary_path)
                if res.success and res.source_code:
                    sources[name] = res.source_code
                    print(f"    ✓ {name}: decompiled")
                else:
                    print(f"    ✗ {name}: {res.error_message}")
            except Exception as e:
                print(f"    ✗ {name}: {e}")

        if not sources:
            return None

        if len(sources) == 1:
            return next(iter(sources.values()))

        engine = MCGDEngine()
        merged = engine.process(sources, binary_path=binary_path)
        if merged.success:
            print(f"    → Merged {merged.num_functions_merged} functions "
                  f"from {merged.num_decompilers_used} decompilers "
                  f"(consensus: {merged.consensus_agreements})")
            return merged.merged_code
        print(f"    ✗ Merge failed: {merged.error_message}")
        return next(iter(sources.values()))  # fallback to first available

    def _generate_tests(
        self, binary_path: str, binary_name: str, source_code: str,
        architecture: str = "x86_64",
    ) -> List[Dict]:
        """Generate test cases using multiple strategies."""
        tests: list[dict] = []

        # 1. Pattern-based (fast, free)
        pg = PatternTestGenerator()
        tests.extend(pg.generate(binary_name))

        # 2. Source-analysis-based
        sg = SourceTestGenerator()
        source_tests = sg.generate(source_code, binary_name)
        for t in source_tests:
            if t['input'] not in {tc['input'] for tc in tests}:
                tests.append(t)

        # 3. Dynamic fuzzing (runs the actual binary)
        try:
            dg = DynamicTestGenerator(timeout=5, max_tests=5)
            if architecture in ("aarch64", "arm"):
                # For ARM: run via Docker/QEMU
                dyn = dg.generate_for_arm(binary_path)
            else:
                dyn = dg.generate(binary_path)
            for t in dyn:
                if t['input'] not in {tc['input'] for tc in tests}:
                    tests.append(t)
        except Exception:
            pass  # skip if binary can't be executed

        return tests
