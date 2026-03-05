"""
Function Matcher — matches functions across multiple decompiler outputs.

Uses weighted SequenceMatcher similarity on normalized names (0.2),
signatures (0.3), and bodies (0.5).  Greedy matching with a configurable
threshold (default 0.6) groups corresponding functions from different
decompilers.
"""

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Dict, List


@dataclass
class Function:
    """A single function extracted from decompiled C code."""
    name: str
    signature: str
    body: str
    decompiler: str
    start_line: int
    end_line: int

    @property
    def normalized_name(self) -> str:
        name = re.sub(r'^(sub_|FUN_|func_|function_)', '', self.name)
        return name.lower()


class FunctionMatcher:
    """Match functions across multiple decompiler outputs."""

    SYSTEM_PATTERNS = [
        r'^__', r'^_init', r'^_fini', r'^_start',
        r'^register_tm_clones', r'^deregister_tm_clones', r'^frame_dummy',
    ]

    def extract_functions(self, source_code: str, decompiler: str) -> List[Function]:
        """Extract all function definitions from *source_code*."""
        functions: list[Function] = []
        lines = source_code.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('//'):
                i += 1
                continue
            # Match function definitions:
            #   int main()  |  long long factorial(unsigned int a0)  |  int *foo(char *s)
            # Use non-greedy match for return type, greedy for function name before (
            match = re.match(
                r'^([\w][\w\s*]*?(\w+)\s*\([^)]*\))\s*(\{|;)', line,
            )
            if match and match.group(3) == '{':
                func_name = match.group(2)
                # Skip control-flow keywords that look like function calls
                if func_name in ('if', 'while', 'for', 'switch', 'return', 'sizeof'):
                    i += 1
                    continue
                signature = match.group(1).strip()
                start_line = i
                brace_count = line.count('{') - line.count('}')
                body_lines = [line]
                i += 1
                while i < len(lines) and brace_count > 0:
                    body_lines.append(lines[i])
                    brace_count += lines[i].count('{') - lines[i].count('}')
                    i += 1
                functions.append(Function(
                    name=func_name, signature=signature,
                    body='\n'.join(body_lines), decompiler=decompiler,
                    start_line=start_line, end_line=i,
                ))
            else:
                i += 1
        return functions

    def is_user_function(self, func: Function) -> bool:
        return not any(re.match(p, func.name) for p in self.SYSTEM_PATTERNS)

    def compute_similarity(self, f1: Function, f2: Function) -> float:
        name_sim = SequenceMatcher(None, f1.normalized_name, f2.normalized_name).ratio()
        sig_sim = SequenceMatcher(None, f1.signature, f2.signature).ratio()
        b1 = ' '.join(f1.body.split())
        b2 = ' '.join(f2.body.split())
        body_sim = SequenceMatcher(None, b1, b2).ratio()
        return 0.2 * name_sim + 0.3 * sig_sim + 0.5 * body_sim

    def match_functions(
        self,
        sources: Dict[str, str],
        threshold: float = 0.6,
    ) -> Dict[str, List[Function]]:
        """
        Match functions across decompiler outputs.

        Args:
            sources: ``{decompiler_name: source_code}``
            threshold: minimum similarity to consider a match

        Returns:
            ``{group_id: [Function, ...]}`` — one list per matched function.
        """
        all_funcs: dict[str, list[Function]] = {}
        for name, code in sources.items():
            all_funcs[name] = self.extract_functions(code, name)

        decomp_names = list(all_funcs.keys())
        if not decomp_names:
            return {}

        ref = decomp_names[0]
        others = decomp_names[1:]
        matched: dict[str, list[Function]] = {}
        assigned: set[tuple[str, int]] = set()
        gid = 0

        for ref_idx, ref_func in enumerate(all_funcs[ref]):
            if not self.is_user_function(ref_func):
                continue
            group_id = f"func_{gid}"
            gid += 1
            matched[group_id] = [ref_func]
            assigned.add((ref, ref_idx))

            for other in others:
                best_match = None
                best_score = threshold
                best_idx = -1
                for oi, of in enumerate(all_funcs[other]):
                    if (other, oi) in assigned or not self.is_user_function(of):
                        continue
                    sim = self.compute_similarity(ref_func, of)
                    if sim > best_score:
                        best_score = sim
                        best_match = of
                        best_idx = oi
                if best_match:
                    matched[group_id].append(best_match)
                    assigned.add((other, best_idx))

        return matched
