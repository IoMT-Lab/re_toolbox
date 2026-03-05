"""
Abstract base class for all decompiler wrappers.

Every decompiler (Ghidra, Angr, RetDec) implements the `decompile()` method
which takes a binary path and returns a `DecompilationResult`.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class DecompilationResult:
    """Result of a decompilation operation."""
    success: bool
    source_code: Optional[str] = None
    error_message: Optional[str] = None
    decompiler_name: str = ""
    binary_path: str = ""
    architecture: str = "x86_64"  # "x86_64", "aarch64", "arm", "unknown"


class DecompilerBase:
    """Base class for decompiler wrappers."""

    def __init__(self, name: str):
        self.name = name

    def decompile(self, binary_path: str) -> DecompilationResult:
        """
        Decompile a binary file to C source code.

        Args:
            binary_path: Absolute path to the ELF binary.

        Returns:
            DecompilationResult with source_code on success.
        """
        raise NotImplementedError("Subclasses must implement decompile()")
