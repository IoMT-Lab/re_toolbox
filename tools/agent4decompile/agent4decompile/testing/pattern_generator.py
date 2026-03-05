"""
Pattern-based test case generator.

Generates test inputs based on binary name heuristics (factorial, fibonacci,
sort, matrix, …).  Falls back to generic numeric/string inputs.
"""

import json
from pathlib import Path
from typing import Dict, List


class PatternTestGenerator:
    """Generate test cases based on binary name patterns."""

    def generate(self, binary_name: str) -> List[Dict]:
        """Return ``[{'input': …, 'description': …}, …]`` for *binary_name*."""
        n = binary_name.lower()

        if 'hello' in n:
            return [{'input': '', 'description': 'No input — print only'}]

        if 'factorial' in n:
            return [
                {'input': '0\n', 'description': 'factorial(0)=1'},
                {'input': '5\n', 'description': 'factorial(5)=120'},
                {'input': '10\n', 'description': 'factorial(10)=3628800'},
            ]

        if 'fib' in n:
            return [
                {'input': '0\n', 'description': 'fib(0)=0'},
                {'input': '1\n', 'description': 'fib(1)=1'},
                {'input': '10\n', 'description': 'fib(10)=55'},
            ]

        if 'sort' in n:
            return [
                {'input': '5\n5 2 8 1 9\n', 'description': 'Sort 5 elements'},
                {'input': '3\n3 2 1\n', 'description': 'Reverse order'},
                {'input': '1\n42\n', 'description': 'Single element'},
            ]

        if 'binary_search' in n:
            return [
                {'input': '5\n1 2 3 4 5\n3\n', 'description': 'Search mid'},
                {'input': '5\n1 2 3 4 5\n6\n', 'description': 'Not found'},
            ]

        if 'string' in n:
            return [
                {'input': 'hello\n', 'description': 'Simple string'},
                {'input': 'test123\n', 'description': 'Alphanumeric'},
            ]

        if 'gcd' in n or 'egcd' in n:
            return [
                {'input': '48\n18\n', 'description': 'gcd(48,18)=6'},
                {'input': '100\n50\n', 'description': 'gcd(100,50)=50'},
            ]

        if 'matrix' in n or 'mat' in n:
            return [
                {'input': '2\n1 2\n3 4\n5 6\n7 8\n', 'description': '2×2'},
                {'input': '', 'description': 'Default'},
            ]

        if 'add' in n:
            return [
                {'input': '5\n3\n', 'description': '5+3'},
                {'input': '0\n0\n', 'description': '0+0'},
            ]

        if 'itoa' in n:
            return [
                {'input': '123\n', 'description': '123→string'},
                {'input': '0\n', 'description': '0→string'},
                {'input': '-42\n', 'description': '-42→string'},
            ]

        # Generic fallback
        return [
            {'input': '', 'description': 'Empty input'},
            {'input': '0\n', 'description': 'Input: 0'},
            {'input': '1\n', 'description': 'Input: 1'},
            {'input': '5\n', 'description': 'Input: 5'},
            {'input': '10\n', 'description': 'Input: 10'},
        ]

    def generate_batch(self, binaries_dir: str, output_file: str | None = None) -> Dict:
        """Generate test cases for all binaries in a directory."""
        bd = Path(binaries_dir)
        files = sorted(f for f in bd.iterdir() if f.is_file() and not f.suffix)
        all_tc: dict = {}
        for f in files:
            all_tc[f.stem] = self.generate(f.stem)
        if output_file:
            with open(output_file, 'w') as fp:
                json.dump(all_tc, fp, indent=2)
        return all_tc
