"""
Constraint-Guided LLM Refinement Engine — the core innovation of Agent4Decompile.

Iteratively repairs decompiled C code using an LLM (GPT-4o or Claude) guided
by a 3-level constraint hierarchy:

  L1  Syntax     — ``gcc -fsyntax-only -w``
  L2  Compilation — ``gcc -w -o output source.c -lm``
  L3  Execution  — run original + recompiled binary, compare stdout

Each iteration:
  1. Evaluate code against all 3 levels (hierarchically)
  2. If fail → build structured prompt with error feedback
  3. Call LLM → extract corrected code
  4. Repeat until all pass or max iterations
"""

import difflib
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from openai import OpenAI
    _OPENAI = True
except ImportError:
    _OPENAI = False

try:
    import anthropic
    _ANTHROPIC = True
except ImportError:
    _ANTHROPIC = False


# ═══════════════════════════════════════════════════════════════════════════
# Pre-processing helper
# ═══════════════════════════════════════════════════════════════════════════

def preprocess_decompiled_code(code: str, decompiler: str) -> str:
    """
    Clean up raw decompiled C code before sending to the LLM.

    Handles all decompilers:
      - Comment out compiler-generated functions (``_init``, ``_fini``, …)
      - Remove dangling extern / typedef declarations for commented-out types
      - Ensure standard headers are present
    """
    import re

    # ── 1. Comment out compiler-generated functions ────────────────────────
    problematic = [
        '_init', '_fini', '_start', 'frame_dummy',
        'deregister_tm_clones', 'register_tm_clones',
        '__do_global_dtors_aux', '__libc_csu_init', '__libc_csu_fini',
    ]

    lines = code.split('\n')
    result: list[str] = []
    in_prob = False
    brace_count = 0

    for line in lines:
        # If inside a problematic function, track braces
        if in_prob:
            brace_count += line.count('{') - line.count('}')
            result.append('// ' + line)
            if brace_count <= 0:
                in_prob = False
            continue

        # Detect function definitions (not calls) for problematic names
        stripped = line.strip()
        is_func_def = (
            not stripped.startswith('//')
            and '(' in stripped
            and any(f' {fn}(' in line or f'*{fn}(' in line for fn in problematic)
        )

        if is_func_def:
            result.append('// ' + line + '  // REMOVED: compiler-generated')
            if '{' in line:
                in_prob = True
                brace_count = line.count('{') - line.count('}')
            else:
                # Opening brace will be on the next line
                in_prob = True
                brace_count = 0
            continue

        result.append(line)

    code = '\n'.join(result)

    # ── 2. Remove dangling extern declarations for runtime globals ─────────
    cleaned: list[str] = []
    for line in code.split('\n'):
        stripped = line.strip()
        if stripped.startswith('extern') and re.search(r'\bg_[0-9a-fA-F]+\b', stripped):
            cleaned.append('// ' + line + '  // REMOVED: dangling extern')
            continue
        cleaned.append(line)
    code = '\n'.join(cleaned)

    # ── 3. Ensure standard headers ────────────────────────────────────────
    headers = ['<stdio.h>', '<stdlib.h>', '<string.h>']
    for h in headers:
        if h not in code:
            code = f'#include {h}\n' + code

    return code


# ═══════════════════════════════════════════════════════════════════════════
# Data classes
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class RefinementResult:
    """Result of the iterative refinement process."""
    success: bool
    refined_code: str
    iterations: int
    error_message: Optional[str] = None
    syntax_valid: bool = False
    compiles: bool = False
    re_executable: bool = False
    iteration_history: List[Dict] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# Constraint Evaluator (L1 / L2 / L3)
# ═══════════════════════════════════════════════════════════════════════════

class ConstraintEvaluator:
    """Evaluates code against the 3-level constraint hierarchy.

    Supports both x86_64 (native) and aarch64 (via Docker cross-compilation + QEMU).
    """

    def __init__(self, temp_dir: str | None = None, architecture: str = "x86_64"):
        self.temp_dir = Path(temp_dir or os.environ.get("TMPDIR", "/tmp"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self._last_compiled: Optional[str] = None
        self.architecture = architecture
        self._is_arm = architecture in ("aarch64", "arm")

    # ── L1: Syntax ────────────────────────────────────────────────────────
    def evaluate_syntax(self, code: str) -> Tuple[bool, str]:
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.c', delete=False, dir=self.temp_dir,
            ) as f:
                f.write(code)
                path = f.name

            if self._is_arm:
                from ..arch import docker_compile
                ok, err = docker_compile(
                    path, "/dev/null", arch=self.architecture, syntax_only=True)
                os.unlink(path)
                if ok:
                    return True, "✅ Valid C syntax (ARM cross-check)"
                return False, f"❌ Syntax errors (ARM):\n{err[:500]}"
            else:
                res = subprocess.run(
                    ['gcc', '-fsyntax-only', '-w', path],
                    capture_output=True, text=True, timeout=30,
                )
                os.unlink(path)
                if res.returncode == 0:
                    return True, "✅ Valid C syntax"
                return False, f"❌ Syntax errors:\n{res.stderr[:500]}"
        except Exception as e:
            return False, f"❌ Syntax check failed: {e}"

    # ── L2: Compilation ───────────────────────────────────────────────────
    def evaluate_compilation(self, code: str) -> Tuple[bool, str]:
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.c', delete=False, dir=self.temp_dir,
            ) as f:
                f.write(code)
                c_path = f.name
            bin_path = str(self.temp_dir / f"{Path(c_path).stem}.out")

            if self._is_arm:
                from ..arch import docker_compile
                ok, err = docker_compile(
                    c_path, bin_path, arch=self.architecture)
                os.unlink(c_path)
                if ok:
                    self._last_compiled = bin_path
                    return True, "✅ Compiles successfully (ARM cross-compile)"
                if os.path.exists(bin_path):
                    os.unlink(bin_path)
                return False, f"❌ Compilation errors (ARM):\n{err[:500]}"
            else:
                env = {**os.environ, 'TMPDIR': str(self.temp_dir)}
                res = subprocess.run(
                    ['gcc', '-w', '-o', bin_path, c_path, '-lm'],
                    capture_output=True, text=True, timeout=60, env=env,
                )
                os.unlink(c_path)
                if res.returncode == 0:
                    self._last_compiled = bin_path
                    return True, "✅ Compiles successfully"
                if os.path.exists(bin_path):
                    os.unlink(bin_path)
                return False, f"❌ Compilation errors:\n{res.stderr[:500]}"
        except Exception as e:
            return False, f"❌ Compilation check failed: {e}"

    # ── L3: Execution (behavioral equivalence) ────────────────────────────
    def evaluate_execution(
        self,
        original_binary: str,
        test_cases: List[Dict],
    ) -> Tuple[bool, str, Dict]:
        if not self._last_compiled or not os.path.exists(self._last_compiled):
            return False, "❌ No compiled binary available", {}
        if not os.path.exists(original_binary):
            return False, f"❌ Original binary not found: {original_binary}", {}
        if not test_cases:
            # type: ignore[return-value]
            return None, "⏭️  No test cases provided", {}

        recomp = self._last_compiled
        results: dict = {'total': len(
            test_cases), 'passed': 0, 'failed': 0, 'failures': []}

        for idx, tc in enumerate(test_cases):
            inp = tc.get('input', '')
            ok_o, out_o = self._run(original_binary, inp)
            ok_r, out_r = self._run(recomp, inp)

            if ok_o and ok_r and out_o == out_r:
                results['passed'] += 1
            else:
                results['failed'] += 1
                info: dict = {'test_id': idx, 'input': str(inp)[:100]}
                info['orig'] = out_o[:200] if ok_o else f"FAIL: {out_o}"
                info['recomp'] = out_r[:200] if ok_r else f"FAIL: {out_r}"
                if ok_o and ok_r:
                    info['diff'] = self._diff(out_o, out_r)
                results['failures'].append(info)

        if results['failed'] == 0:
            return True, f"✅ All {results['total']} tests pass!", results

        parts = [
            f"❌ {results['failed']}/{results['total']} tests failed",
            "\n" + "=" * 60,
            "CRITICAL: Code compiles but produces WRONG OUTPUT!",
            "Fix LOGIC/SEMANTICS, not just syntax.",
            "=" * 60 + "\n",
        ]
        for f in results['failures'][:2]:
            parts.append(f"\n🔍 Test #{f['test_id']}:")
            parts.append(f"   Input: {f['input']}")
            parts.append(f"   Original: {f['orig']}")
            parts.append(f"   Recompiled: {f['recomp']}")
            if 'diff' in f:
                parts.append(f"   Diff:\n{f['diff']}")
        if results['failed'] > 2:
            parts.append(f"\n… and {results['failed'] - 2} more failures")
        parts += [
            "\n" + "=" * 60,
            "Check: wrong init, control flow, arithmetic, types, off-by-one",
            "=" * 60,
        ]
        return False, '\n'.join(parts), results

    # ── Helpers ────────────────────────────────────────────────────────────
    def _run(self, binary: str, inp: str, timeout: int = 10) -> Tuple[bool, str]:
        """Run a binary, dispatching to Docker/QEMU for ARM."""
        if self._is_arm:
            from ..arch import docker_run
            return docker_run(binary, stdin_input=inp, timeout=timeout)
        try:
            res = subprocess.run(
                [binary], input=inp.encode(), capture_output=True, timeout=timeout,
            )
            out = res.stdout.decode('utf-8', errors='ignore')
            if res.returncode == 0:
                return True, out
            return False, f"EXIT_{res.returncode}: {res.stderr.decode(errors='ignore')[:100]}"
        except subprocess.TimeoutExpired:
            return False, "TIMEOUT"
        except Exception as e:
            return False, f"ERROR: {e}"

    @staticmethod
    def _diff(expected: str, actual: str) -> str:
        d = list(difflib.unified_diff(
            expected.splitlines(True), actual.splitlines(True),
            fromfile='original', tofile='recompiled', lineterm='',
        ))
        return ''.join(d[:10]) or '(outputs differ)'

    # ── Combined evaluation ───────────────────────────────────────────────
    def evaluate_all(
        self,
        code: str,
        original_binary: str | None = None,
        test_cases: List[Dict] | None = None,
        constraint_level: int = 3,
    ) -> Dict:
        r: dict = {}

        syn_ok, syn_msg = self.evaluate_syntax(code)
        r['syntax'] = {'pass': syn_ok, 'message': syn_msg}
        if not syn_ok or constraint_level == 1:
            r['compilation'] = {'pass': False,
                                'message': '⏭️  Fix syntax first'}
            r['execution'] = {'pass': None,
                              'message': '⏭️  Skipped', 'details': {}}
            return r

        comp_ok, comp_msg = self.evaluate_compilation(code)
        r['compilation'] = {'pass': comp_ok, 'message': comp_msg}
        if not comp_ok or constraint_level == 2:
            r['execution'] = {'pass': None,
                              'message': '⏭️  Skipped', 'details': {}}
            return r

        if constraint_level >= 3 and original_binary and test_cases:
            ex_ok, ex_msg, ex_det = self.evaluate_execution(
                original_binary, test_cases)
            r['execution'] = {'pass': ex_ok,
                              'message': ex_msg, 'details': ex_det}
        else:
            r['execution'] = {'pass': None,
                              'message': '⏭️  No test cases', 'details': {}}
        return r


# ═══════════════════════════════════════════════════════════════════════════
# LLM Refiner
# ═══════════════════════════════════════════════════════════════════════════

class MCGDRefiner:
    """
    Iteratively refine decompiled C code using an LLM with constraint feedback.

    Args:
        llm_provider:    ``"openai"`` or ``"anthropic"``
        model:           Model name (default: gpt-4o / claude-3-5-sonnet)
        max_iterations:  Maximum refinement rounds
        constraint_level: 1 = syntax only, 2 = + compile, 3 = + execution
    """

    SYSTEM_PROMPT = (
        "You are an expert C programmer and reverse engineering specialist. "
        "Your task is to fix decompiled C code to make it syntactically valid, "
        "compilable, and functionally equivalent to the original binary.\n\n"
        "CRITICAL RULES:\n"
        "1. Output ONLY the fixed C code — NO explanations, NO markdown.\n"
        "2. Do NOT wrap code in ```c or ``` blocks.\n"
        "3. Preserve the original logic as much as possible.\n"
        "4. Add necessary #include statements and type declarations.\n"
        "5. Return ONLY the corrected C code."
    )

    def __init__(
        self,
        llm_provider: str = "openai",
        model: str | None = None,
        max_iterations: int = 5,
        constraint_level: int = 3,
        architecture: str = "x86_64",
    ):
        self.llm_provider = llm_provider.lower()
        self.max_iterations = max_iterations
        self.constraint_level = constraint_level
        self.architecture = architecture
        self.evaluator = ConstraintEvaluator(architecture=architecture)

        if self.llm_provider == "openai":
            if not _OPENAI:
                raise ImportError("pip install openai")
            self._client = OpenAI()
            self.model = model or "gpt-4o"
        elif self.llm_provider == "anthropic":
            if not _ANTHROPIC:
                raise ImportError("pip install anthropic")
            self._client = anthropic.Anthropic()
            self.model = model or "claude-sonnet-4-20250514"
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")

    # ── LLM call ──────────────────────────────────────────────────────────
    def _call_llm(self, prompt: str) -> str:
        if self.llm_provider == "openai":
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2, max_tokens=8000,
            )
            return resp.choices[0].message.content
        else:
            resp = self._client.messages.create(
                model=self.model, max_tokens=8000, temperature=0.2,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text

    # ── Prompt construction ───────────────────────────────────────────────
    def _build_prompt(
        self, code: str, constraints: Dict,
        iteration: int, binary_name: str, decompiler: str,
    ) -> str:
        syn = constraints['syntax']['pass']
        comp = constraints['compilation']['pass']
        exc = constraints['execution']['pass']

        parts = [
            f"# Decompiled Code Refinement — Iteration {iteration + 1}",
            f"\n**Binary:** {binary_name}  |  **Decompiler:** {decompiler}",
            f"\n## Constraint Status",
            f"- L1 Syntax:      {'✅ PASS' if syn else '❌ FAIL'}",
            f"- L2 Compilation: {'✅ PASS' if comp else ('⏭️' if not syn else '❌ FAIL')}",
            f"- L3 Execution:   "
            + ('✅ PASS' if exc is True else '❌ FAIL' if exc is False else '⏭️ SKIPPED'),
        ]

        if not syn:
            parts += ["\n## L1 Feedback", constraints['syntax']['message'],
                      "\n**Task**: Fix the SYNTAX errors."]
        elif not comp:
            parts += ["\n## L2 Feedback",
                      constraints['compilation']['message']]
            if 'multiple definition' in constraints['compilation']['message']:
                parts += [
                    "\n⚠️  Multiple-definition errors detected.",
                    "Remove or rename compiler-generated functions (_init, _fini, _start, …).",
                ]
            parts.append("\n**Task**: Fix the COMPILATION errors.")
        elif exc is False:
            parts += [
                "\n## L3 Feedback", constraints['execution']['message'],
                "\n⚠️  Code compiles but output is WRONG. Fix LOGIC, not syntax.",
            ]

        parts += [
            "\n## Current Code", "```c", code, "```",
            "\nOutput ONLY the corrected C code (no explanations, no markdown).",
        ]
        return '\n'.join(parts)

    # ── Extract code from LLM response ────────────────────────────────────
    @staticmethod
    def _extract_code(response: str) -> str:
        lines = response.strip().split('\n')
        if lines[0].strip().startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        return '\n'.join(lines)

    # ══════════════════════════════════════════════════════════════════════
    # Main refinement loop
    # ══════════════════════════════════════════════════════════════════════
    def refine(
        self,
        initial_code: str,
        binary_name: str = "unknown",
        decompiler: str = "unknown",
        original_binary_path: str | None = None,
        test_cases: List[Dict] | None = None,
    ) -> RefinementResult:
        """
        Apply iterative LLM refinement with 3-level constraint feedback.

        Args:
            initial_code:         Raw / post-processed decompiled C code.
            binary_name:          Name of the binary (for logging / prompts).
            decompiler:           Which decompiler produced this code.
            original_binary_path: Path to original ELF binary (for L3).
            test_cases:           ``[{'input': '…'}, …]`` for L3 testing.

        Returns:
            ``RefinementResult`` with the best code found.
        """
        current = preprocess_decompiled_code(initial_code, decompiler)
        history: list[dict] = []
        best_code = current
        best_score = 0  # 0=nothing, 1=syntax, 2=compiles, 3=re-executable

        for it in range(self.max_iterations):
            cons = self.evaluator.evaluate_all(
                current,
                original_binary=original_binary_path,
                test_cases=test_cases,
                constraint_level=self.constraint_level,
            )

            score = 0
            if cons['syntax']['pass']:
                score = 1
            if cons['compilation']['pass']:
                score = 2
            if cons['execution']['pass'] is True:
                score = 3

            if score > best_score:
                best_score, best_code = score, current

            history.append({
                'iteration': it,
                'syntax_pass': cons['syntax']['pass'],
                'compilation_pass': cons['compilation']['pass'],
                'execution_pass': cons['execution']['pass'],
                'score': score,
            })

            # All levels pass → done
            if (cons['syntax']['pass']
                    and cons['compilation']['pass']
                    and cons['execution']['pass'] is True):
                return RefinementResult(
                    success=True, refined_code=current, iterations=it + 1,
                    syntax_valid=True, compiles=True, re_executable=True,
                    iteration_history=history,
                )

            # Compiles but no test cases → success at L2
            if (cons['syntax']['pass']
                    and cons['compilation']['pass']
                    and cons['execution']['pass'] is None):
                return RefinementResult(
                    success=True, refined_code=current, iterations=it + 1,
                    syntax_valid=True, compiles=True, re_executable=False,
                    iteration_history=history,
                )

            # Ask LLM to fix
            try:
                prompt = self._build_prompt(
                    current, cons, it, binary_name, decompiler)
                resp = self._call_llm(prompt)
                current = self._extract_code(resp)
            except Exception as e:
                return RefinementResult(
                    success=False, refined_code=best_code, iterations=it + 1,
                    syntax_valid=best_score >= 1, compiles=best_score >= 2,
                    re_executable=best_score >= 3, iteration_history=history,
                    error_message=f"LLM failed at iteration {it}: {e}",
                )

        # Max iterations reached
        final = self.evaluator.evaluate_all(
            best_code, original_binary=original_binary_path,
            test_cases=test_cases, constraint_level=self.constraint_level,
        )
        return RefinementResult(
            success=(best_score == 3), refined_code=best_code,
            iterations=len(history),
            syntax_valid=final['syntax']['pass'],
            compiles=final['compilation']['pass'],
            re_executable=final['execution']['pass'] or False,
            iteration_history=history,
            error_message="Max iterations reached" if best_score < 3 else None,
        )
