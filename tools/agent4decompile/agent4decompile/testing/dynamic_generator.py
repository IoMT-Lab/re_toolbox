"""
Dynamic (fuzzing-based) test case generator.

Runs the binary with a variety of inputs (numeric, structured, random)
and keeps those that succeed (exit code 0).  No source code required —
works purely from binary execution.
"""

import os
import random
import signal
import string
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple


class DynamicTestGenerator:
    """Generate test cases by fuzzing the binary directly."""

    def __init__(self, timeout: int = 5, max_tests: int = 15):
        self.timeout = timeout
        self.max_tests = max_tests

    def generate(self, binary_path: str) -> List[Dict]:
        if not os.path.exists(binary_path) or not os.access(binary_path, os.X_OK):
            return self._defaults()

        ok_base, out_base = self._run(binary_path, '')
        tests: list[dict] = [{'input': '', 'expected_output': out_base if ok_base else '', 'description': 'Empty (baseline)'}]

        # Numeric
        for v in [0, 1, 5, 10, 100, -1]:
            ok, out = self._run(binary_path, f"{v}\n")
            if ok:
                tests.append({'input': f"{v}\n", 'expected_output': out, 'description': f'Numeric: {v}'})

        # Structured
        for inp in ["1\n", "5\n1 2 3 4 5\n", "hello\n", "3\n1 2 3\n"]:
            if len(tests) >= self.max_tests:
                break
            ok, out = self._run(binary_path, inp)
            if ok:
                tests.append({'input': inp, 'expected_output': out, 'description': f'Structured: {inp[:20].strip()}'})

        # Random fuzz
        for i in range(min(5, self.max_tests - len(tests))):
            inp = self._random_input()
            ok, out = self._run(binary_path, inp)
            if ok:
                tests.append({'input': inp, 'expected_output': out, 'description': f'Fuzz {i+1}'})

        # Dedup
        seen: set[str] = set()
        uniq: list[dict] = []
        for t in tests:
            if t['input'] not in seen:
                seen.add(t['input'])
                uniq.append(t)
        return uniq[:self.max_tests]

    # ------------------------------------------------------------------
    def _run(self, binary: str, inp: str) -> Tuple[bool, str]:
        try:
            proc = subprocess.Popen(
                [binary], stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, preexec_fn=os.setsid,
            )
            try:
                out, _ = proc.communicate(input=inp, timeout=self.timeout)
                return proc.returncode == 0, out[:1000]
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                proc.wait()
                return False, "TIMEOUT"
        except Exception as e:
            return False, str(e)

    def _random_input(self) -> str:
        r = random.random()
        if r < 0.25:
            return f"{random.randint(-100, 1000)}\n"
        if r < 0.5:
            n = random.randint(1, 8)
            nums = ' '.join(str(random.randint(0, 100)) for _ in range(n))
            return f"{n}\n{nums}\n"
        if r < 0.75:
            length = random.randint(1, 15)
            return ''.join(random.choice(string.ascii_lowercase) for _ in range(length)) + '\n'
        parts = [str(random.randint(0, 50)) if random.random() < 0.5 else 'test'
                 for _ in range(random.randint(1, 4))]
        return ' '.join(parts) + '\n'

    @staticmethod
    def _defaults() -> List[Dict]:
        return [
            {'input': '', 'description': 'Empty'},
            {'input': '0\n', 'description': '0'},
            {'input': '1\n', 'description': '1'},
            {'input': '5\n', 'description': '5'},
        ]

    # ------------------------------------------------------------------
    # ARM support — run via Docker + QEMU
    # ------------------------------------------------------------------
    def generate_for_arm(self, binary_path: str) -> List[Dict]:
        """Generate test cases for an ARM binary using Docker/QEMU."""
        from ..arch import docker_run

        ok_base, out_base = docker_run(binary_path, stdin_input='', timeout=self.timeout)
        tests: list[dict] = [{'input': '', 'expected_output': out_base if ok_base else '', 'description': 'Empty (baseline)'}]

        for v in [0, 1, 5, 10, 100, -1]:
            ok, out = docker_run(binary_path, stdin_input=f"{v}\n", timeout=self.timeout)
            if ok:
                tests.append({'input': f"{v}\n", 'expected_output': out, 'description': f'Numeric: {v}'})

        for inp in ["1\n", "5\n1 2 3 4 5\n", "hello\n"]:
            if len(tests) >= self.max_tests:
                break
            ok, out = docker_run(binary_path, stdin_input=inp, timeout=self.timeout)
            if ok:
                tests.append({'input': inp, 'expected_output': out, 'description': f'Structured: {inp[:20].strip()}'})

        seen: set[str] = set()
        uniq: list[dict] = []
        for t in tests:
            if t['input'] not in seen:
                seen.add(t['input'])
                uniq.append(t)
        return uniq[:self.max_tests]
