"""
RetDec decompiler wrapper.

Invokes the ``retdec-decompiler`` CLI tool which produces a ``.c`` file.
RetDec generally produces the cleanest output, so minimal post-processing
is required.
"""

import subprocess
import tempfile
import shutil
import os
from pathlib import Path

from .base import DecompilerBase, DecompilationResult


class RetDecDecompiler(DecompilerBase):
    """Wrapper for the RetDec CLI decompiler."""

    def __init__(self, retdec_path: str | None = None):
        super().__init__("RetDec")
        if retdec_path is None:
            retdec_path = os.environ.get(
                "RETDEC_PATH",
                os.path.expanduser("~/tools/bin/retdec-decompiler"),
            )
        self.retdec_decompiler = Path(retdec_path)
        if not self.retdec_decompiler.exists():
            raise RuntimeError(
                f"RetDec decompiler not found at {self.retdec_decompiler}"
            )

    def decompile(self, binary_path: str) -> DecompilationResult:
        """Decompile *binary_path* using the RetDec CLI."""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                binary_name = Path(binary_path).name
                tmp_binary = Path(tmpdir) / binary_name
                shutil.copy(binary_path, tmp_binary)

                cmd = [str(self.retdec_decompiler), str(tmp_binary)]
                result = subprocess.run(
                    cmd, capture_output=True, text=True,
                    timeout=300, cwd=tmpdir,
                )

                output_file = tmp_binary.with_suffix('.c')
                if output_file.exists():
                    source = output_file.read_text()
                    if len(source) > 100:
                        return DecompilationResult(
                            success=True, source_code=source,
                            decompiler_name="RetDec", binary_path=str(binary_path),
                        )
                    return DecompilationResult(
                        success=False, error_message="No code decompiled",
                        decompiler_name="RetDec", binary_path=str(binary_path),
                    )
                return DecompilationResult(
                    success=False,
                    error_message=f"Output not created. stderr: {result.stderr[:200]}",
                    decompiler_name="RetDec", binary_path=str(binary_path),
                )

        except subprocess.TimeoutExpired:
            return DecompilationResult(
                success=False, error_message="RetDec timeout (>300 s)",
                decompiler_name="RetDec", binary_path=str(binary_path),
            )
        except Exception as e:
            return DecompilationResult(
                success=False, error_message=str(e)[:300],
                decompiler_name="RetDec", binary_path=str(binary_path),
            )
