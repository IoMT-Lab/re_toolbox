"""
Code Cleaner — post-merge cleanup for decompiled C code.

Responsibilities:
  - Extract includes / typedefs / globals / functions
  - Deduplicate each component
  - Remove malformed typedefs (``struct_0``, ``undefined``)
  - Detect usage of printf/malloc/strcpy/… and add missing ``#include``
  - Reassemble in correct order
"""

import re
from typing import List


class CodeCleaner:
    """Clean and fix merged decompiled code."""

    STANDARD_HEADERS = {'stdio.h', 'stdlib.h', 'string.h', 'stdint.h', 'stdbool.h', 'math.h'}

    # ------------------------------------------------------------------
    def clean(self, source_code: str) -> str:
        includes = self._extract_includes(source_code)
        typedefs = self._extract_typedefs(source_code)
        globals_code = self._extract_globals(source_code)
        functions = self._extract_functions(source_code)

        includes = self._dedup(includes)
        typedefs = self._clean_typedefs(typedefs)
        globals_code = self._dedup_lines(globals_code)
        functions = self._clean_functions(functions)

        parts: list[str] = []
        if includes:
            parts.append('\n'.join(sorted(includes)))
            parts.append('')
        if typedefs:
            parts.append('\n'.join(typedefs))
            parts.append('')
        if globals_code:
            parts.append(globals_code)
            parts.append('')
        if functions:
            parts.append('\n\n'.join(functions))
        return '\n'.join(parts)

    # ------------------------------------------------------------------
    def add_standard_headers(self, code: str) -> str:
        """Ensure needed standard headers are present."""
        lines = code.split('\n')
        needs: list[str] = []
        header_check = {
            ('printf', 'puts', 'scanf', 'fprintf', 'sprintf'): 'stdio.h',
            ('malloc', 'free', 'exit', 'atoi', 'atof'): 'stdlib.h',
            ('strcpy', 'strlen', 'memcpy', 'strcmp', 'strcat'): 'string.h',
            ('int64_t', 'uint32_t', 'int32_t', 'uint8_t'): 'stdint.h',
        }
        for funcs, header in header_check.items():
            if any(f in code for f in funcs):
                inc = f'#include <{header}>'
                if not any(inc in l for l in lines):
                    needs.append(inc)
        if needs:
            idx = 0
            for i, l in enumerate(lines):
                if l.strip() and not l.strip().startswith('#include'):
                    idx = i
                    break
            lines = lines[:idx] + needs + lines[idx:]
        return '\n'.join(lines)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _extract_includes(self, code: str) -> List[str]:
        return [l.strip() for l in code.split('\n') if l.strip().startswith('#include')]

    def _extract_typedefs(self, code: str) -> List[str]:
        typedefs: list[str] = []
        lines = code.split('\n')
        i = 0
        while i < len(lines):
            if lines[i].strip().startswith('typedef'):
                parts = [lines[i]]
                i += 1
                while i < len(lines) and ';' not in parts[-1]:
                    parts.append(lines[i])
                    i += 1
                typedefs.append(' '.join(parts))
            else:
                i += 1
        return typedefs

    def _extract_globals(self, code: str) -> str:
        out: list[str] = []
        in_func = False
        depth = 0
        for line in code.split('\n'):
            s = line.strip()
            if s.startswith(('#include', 'typedef')):
                continue
            if s.startswith('//'):
                continue
            # Detect function definitions
            if re.match(r'^\w[\w\s*]*?\w+\s*\([^)]*\)\s*\{?', s):
                in_func = True
            depth += line.count('{') - line.count('}')
            if depth == 0:
                in_func = False
            if not in_func and s and re.match(
                r'^(extern\s+)?(static\s+)?(const\s+)?[\w\s*]+\s+\w+(\s*=|\s*;|\[)', s,
            ):
                out.append(line)
        return '\n'.join(out)

    def _extract_functions(self, code: str) -> List[str]:
        functions: list[str] = []
        lines = code.split('\n')
        i = 0
        while i < len(lines):
            s = lines[i].strip()
            # Match function defs: 'int main() {', 'long long f(int a) {', etc.
            if (not s.startswith(('//', '#', 'typedef', 'extern'))
                    and re.match(r'^\w[\w\s*]*?\w+\s*\([^)]*\)\s*\{', s)):
                buf = [lines[i]]
                bc = lines[i].count('{') - lines[i].count('}')
                i += 1
                while i < len(lines) and bc > 0:
                    buf.append(lines[i])
                    bc += lines[i].count('{') - lines[i].count('}')
                    i += 1
                functions.append('\n'.join(buf))
            else:
                i += 1
        return functions

    @staticmethod
    def _dedup(items: List[str]) -> List[str]:
        seen: set[str] = set()
        out: list[str] = []
        for x in items:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    def _dedup_lines(self, text: str) -> str:
        seen: set[str] = set()
        out: list[str] = []
        for line in text.split('\n'):
            n = ' '.join(line.split())
            if n and n not in seen:
                seen.add(n)
                out.append(line)
        return '\n'.join(out)

    def _clean_typedefs(self, typedefs: List[str]) -> List[str]:
        seen: set[str] = set()
        out: list[str] = []
        for td in typedefs:
            n = ' '.join(td.split())
            if n in seen or 'struct_0' in td or 'undefined' in td.lower():
                continue
            seen.add(n)
            out.append(td)
        return out

    def _clean_functions(self, functions: List[str]) -> List[str]:
        seen_names: set[str] = set()
        out: list[str] = []
        for func in functions:
            m = re.match(r'^(\w[\w\s*]*?(\w+)\s*\([^)]*\))', func, re.MULTILINE)
            if not m:
                continue
            name = m.group(2)
            if name in seen_names:
                continue
            seen_names.add(name)
            # light cleanup
            func = re.sub(r'\n\n\n+', '\n\n', func)
            out.append(func.strip())
        return out
