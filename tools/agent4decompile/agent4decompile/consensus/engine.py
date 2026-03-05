"""
MCGD Consensus Engine — multi-decompiler merging.

Pipeline:
  1. Take decompiled C from 2–3 decompilers
  2. Match functions across outputs (name + signature + body similarity)
  3. Vote on best implementation per function (quality × decompiler weight)
  4. Merge headers (union), globals (priority order), function bodies
  5. Clean: deduplicate, fix includes, remove artifacts
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .function_matcher import FunctionMatcher
from .consensus_voter import ConsensusVoter
from .code_cleaner import CodeCleaner


@dataclass
class ConsensusResult:
    """Result of multi-decompiler consensus merging."""
    success: bool
    merged_code: str
    error_message: Optional[str] = None
    num_functions_merged: int = 0
    num_decompilers_used: int = 0
    consensus_agreements: int = 0
    quality_score: float = 0.0
    function_sources: Dict[str, List[str]] = field(default_factory=dict)


class MCGDEngine:
    """Coordinate multi-decompiler consensus to produce high-quality C code."""

    def __init__(self, decompiler_weights: Dict[str, float] | None = None):
        self.matcher = FunctionMatcher()
        self.voter = ConsensusVoter(decompiler_weights)
        self.cleaner = CodeCleaner()

    # ------------------------------------------------------------------
    def process(
        self,
        decompiled_sources: Dict[str, str],
        binary_path: Optional[str] = None,
    ) -> ConsensusResult:
        """
        Merge multiple decompiler outputs into one high-quality C source.

        Args:
            decompiled_sources: ``{decompiler_name: source_code}``
        """
        try:
            if not decompiled_sources:
                return ConsensusResult(False, "", error_message="No sources provided")

            if len(decompiled_sources) == 1:
                name = next(iter(decompiled_sources))
                return ConsensusResult(
                    True, decompiled_sources[name],
                    num_decompilers_used=1, quality_score=0.8,
                )

            matched = self.matcher.match_functions(decompiled_sources)
            if not matched:
                return self._fallback(decompiled_sources)

            # Headers
            src_tuples = list(decompiled_sources.items())
            header = self.voter.merge_headers_and_includes(src_tuples)

            # Functions
            merged_funcs: list[str] = []
            func_sources: dict[str, list[str]] = {}
            consensus = 0

            for gid, versions in matched.items():
                sigs = [(f.decompiler, f.signature) for f in versions]
                bodies = [(f.decompiler, f.body) for f in versions]
                best_sig = self.voter.select_best_signature(sigs)
                best_body = self.voter.merge_function_bodies(bodies)

                if len(versions) == len(decompiled_sources):
                    consensus += 1

                body_m = re.search(r'\{(.*)\}', best_body, re.DOTALL)
                if body_m:
                    merged_funcs.append(f"{best_sig} {{\n{body_m.group(1)}\n}}")
                else:
                    merged_funcs.append(best_body)

                func_sources[versions[0].name] = [f.decompiler for f in versions]

            globals_code = self._extract_globals(decompiled_sources)

            code = '\n'.join(
                p for p in [header, '', globals_code, '', *merged_funcs] if p
            )
            code = self.cleaner.clean(code)
            code = self.cleaner.add_standard_headers(code)
            quality = self.voter.analyze_code_quality(code).overall_score()

            return ConsensusResult(
                success=True, merged_code=code,
                num_functions_merged=len(merged_funcs),
                num_decompilers_used=len(decompiled_sources),
                consensus_agreements=consensus,
                quality_score=quality,
                function_sources=func_sources,
            )

        except Exception as e:
            return ConsensusResult(False, "", error_message=str(e))

    # ------------------------------------------------------------------
    def _fallback(self, sources: Dict[str, str]) -> ConsensusResult:
        best_score, best_name, best_code = -1.0, "", ""
        for name, code in sources.items():
            q = self.voter.analyze_code_quality(code)
            w = self.voter.decompiler_weights.get(name, 1.0)
            s = q.overall_score() * w
            if s > best_score:
                best_score, best_name, best_code = s, name, code
        return ConsensusResult(
            True, best_code, quality_score=best_score,
            num_decompilers_used=1,
            error_message=f"Fallback to {best_name} (matching failed)",
        )

    @staticmethod
    def _extract_globals(sources: Dict[str, str]) -> str:
        for pref in ('retdec', 'ghidra', 'angr'):
            if pref not in sources:
                continue
            lines = sources[pref].split('\n')
            out: list[str] = []
            in_func = False
            depth = 0
            for line in lines:
                s = line.strip()
                if s.startswith(('#include', '#define', 'typedef')):
                    continue
                if s.startswith('//'):
                    continue
                # Detect function definitions (handles: int main(), long long f(int a), etc.)
                if re.match(r'^\w[\w\s*]*?\w+\s*\([^)]*\)\s*\{?', s):
                    in_func = True
                depth += line.count('{') - line.count('}')
                if depth == 0:
                    in_func = False
                if not in_func and s and not s.startswith('//'):
                    out.append(line)
            if out:
                return '\n'.join(out)
        return ""
