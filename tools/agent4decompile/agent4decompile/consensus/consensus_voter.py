"""
Consensus Voter — weighted voting across decompiler outputs.

Default weights: RetDec 1.2 · Ghidra 1.0 · Angr 0.8

Quality metrics: syntax errors, undefined types, goto statements,
cyclomatic complexity estimate, readability (avg line length).
"""

import re
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class CodeQuality:
    """Quality metrics for a code fragment."""
    has_syntax_errors: bool = False
    has_undefined_types: bool = False
    has_goto_statements: bool = False
    complexity_score: int = 0
    readability_score: float = 0.0

    def overall_score(self) -> float:
        score = 1.0
        if self.has_syntax_errors:
            score *= 0.1
        if self.has_undefined_types:
            score *= 0.5
        if self.has_goto_statements:
            score *= 0.8
        if self.complexity_score > 20:
            score *= 0.7
        elif self.complexity_score > 10:
            score *= 0.9
        score *= self.readability_score
        return max(0.0, min(1.0, score))


class ConsensusVoter:
    """Weighted consensus voting across multiple decompiler outputs."""

    def __init__(self, decompiler_weights: Dict[str, float] | None = None):
        self.decompiler_weights = decompiler_weights or {
            'retdec': 1.2,
            'ghidra': 1.0,
            'angr': 0.8,
        }

    # ------------------------------------------------------------------
    def analyze_code_quality(self, code: str) -> CodeQuality:
        q = CodeQuality()
        q.has_syntax_errors = bool(re.search(r'undefined|UNIMPLEMENTED', code, re.I))
        q.has_undefined_types = bool(re.search(r'undefined\w+|unknown_type', code))
        q.has_goto_statements = 'goto' in code.lower()
        q.complexity_score = (
            code.count('if ') + code.count('while ') + code.count('for ')
            + code.count('case ') + code.count('||') + code.count('&&')
        )
        lines = code.split('\n')
        avg = sum(len(l) for l in lines) / max(len(lines), 1)
        if 60 <= avg <= 80:
            q.readability_score = 1.0
        elif avg < 40:
            q.readability_score = 0.7
        elif avg > 120:
            q.readability_score = 0.6
        else:
            q.readability_score = 0.85
        return q

    # ------------------------------------------------------------------
    def merge_function_bodies(self, versions: List[tuple]) -> str:
        """Select best function body from ``[(decompiler, code), …]``."""
        if not versions:
            return ""
        if len(versions) == 1:
            return versions[0][1]
        best_score, best_code = -1.0, versions[0][1]
        for name, code in versions:
            q = self.analyze_code_quality(code)
            w = self.decompiler_weights.get(name, 1.0)
            s = q.overall_score() * w
            if s > best_score:
                best_score, best_code = s, code
        return best_code

    # ------------------------------------------------------------------
    def select_best_signature(self, signatures: List[tuple]) -> str:
        if not signatures:
            return ""
        if len(signatures) == 1:
            return signatures[0][1]
        scored: list[tuple[float, str]] = []
        for name, sig in signatures:
            score = 0.0
            if re.search(r'\w+\s+\w+\s*[,)]', sig):
                score += 1.0
            if 'undefined' not in sig.lower():
                score += 1.0
            if not sig.startswith('void ') or 'main' in sig:
                score += 0.5
            score *= self.decompiler_weights.get(name, 1.0)
            scored.append((score, sig))
        scored.sort(reverse=True, key=lambda x: x[0])
        return scored[0][1]

    # ------------------------------------------------------------------
    def merge_headers_and_includes(self, source_codes: List[tuple]) -> str:
        """Union of all ``#include``, ``#define``, ``typedef`` directives."""
        includes: set[str] = set()
        defines: set[str] = set()
        typedefs: set[str] = set()
        for _, source in source_codes:
            for line in source.split('\n'):
                s = line.strip()
                if s.startswith('#include'):
                    includes.add(s)
                elif s.startswith('#define'):
                    defines.add(s)
                elif s.startswith('typedef'):
                    typedefs.add(s)
        parts: list[str] = sorted(i for i in includes if '<' in i)
        local = sorted(i for i in includes if '"' in i)
        if local:
            parts.append('')
            parts.extend(local)
        if defines:
            parts.append('')
            parts.extend(sorted(defines))
        if typedefs:
            parts.append('')
            parts.extend(sorted(typedefs))
        return '\n'.join(parts)
