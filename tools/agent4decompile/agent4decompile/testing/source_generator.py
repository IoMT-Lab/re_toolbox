"""
Source-analysis-based test case generator.

Parses main() signature from the decompiled C source to determine whether
the program expects argc/argv, stdin, or no input, then generates
type-appropriate test cases.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional


class SourceTestGenerator:
    """Generate test cases by analysing decompiled C source code."""

    def generate(self, source_code: str, binary_name: str | None = None) -> List[Dict]:
        sig = self._extract_main_sig(source_code)
        if sig:
            return self._from_sig(sig)
        return self._defaults()

    def generate_from_file(self, path: str) -> List[Dict]:
        p = Path(path)
        if not p.exists():
            return self._defaults()
        return self.generate(p.read_text(), p.stem)

    # ------------------------------------------------------------------
    def _extract_main_sig(self, code: str) -> Optional[Dict]:
        argc_patterns = [
            r'int\s+main\s*\(\s*int\s+\w+\s*,\s*char\s*\*\*\s*\w+\s*\)',
            r'int\s+main\s*\(\s*int\s+\w+\s*,\s*char\s*\*\s*\w+\s*\[\s*\]\s*\)',
            r'undefined\d+\s+main\s*\(\s*int\s+\w+\s*,',
        ]
        void_patterns = [
            r'int\s+main\s*\(\s*void\s*\)',
            r'int\s+main\s*\(\s*\)',
            r'undefined\d+\s+main\s*\(\s*\)',
        ]
        for p in argc_patterns:
            if re.search(p, code):
                return {'has_argc_argv': True}
        for p in void_patterns:
            if re.search(p, code):
                return {'has_argc_argv': False}
        return None

    def _from_sig(self, sig: Dict) -> List[Dict]:
        if sig['has_argc_argv']:
            return [
                {'input': '', 'description': 'No args'},
                {'input': 'arg1\n', 'description': '1 arg'},
                {'input': 'arg1 arg2\n', 'description': '2 args'},
                {'input': '5\n', 'description': 'Numeric arg'},
            ]
        return [
            {'input': '', 'description': 'Empty'},
            {'input': '0\n', 'description': '0'},
            {'input': '1\n', 'description': '1'},
            {'input': '5\n', 'description': '5'},
            {'input': 'hello\n', 'description': 'String'},
        ]

    @staticmethod
    def _defaults() -> List[Dict]:
        return [
            {'input': '', 'description': 'Empty'},
            {'input': '0\n', 'description': '0'},
            {'input': '1\n', 'description': '1'},
            {'input': '5\n', 'description': '5'},
            {'input': '10\n', 'description': '10'},
        ]
