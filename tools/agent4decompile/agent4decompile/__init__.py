"""
Agent4Decompile — Multi-Agent Constraint-Guided Decompilation

Transforms compiled ELF binaries (x86-64 and AArch64) into re-executable C
source code using multiple decompilers, consensus merging, and LLM iterative
refinement with 3-level constraint feedback.

Architectures:
  - x86_64:  native GCC compilation + execution
  - aarch64: Docker-based cross-compilation + QEMU emulation
"""

__version__ = "1.1.0"
