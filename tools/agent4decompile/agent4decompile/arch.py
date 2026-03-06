"""
Architecture detection and Docker-based cross-compilation / execution.

Supports:
  - x86_64  (native gcc / native execution)
  - aarch64 (Docker: aarch64-linux-gnu-gcc / qemu-aarch64-static)

The Docker image ``agent4decompile-arm`` is built from ``docker/Dockerfile.arm``
and contains the ARM cross-compiler toolchain + QEMU user-mode emulation.
"""

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple

# Docker image name — built from docker/Dockerfile.arm
ARM_DOCKER_IMAGE = "agent4decompile-arm"


# ═══════════════════════════════════════════════════════════════════════════
# Architecture detection
# ═══════════════════════════════════════════════════════════════════════════

def detect_arch(binary_path: str) -> str:
    """
    Detect the architecture of an ELF binary.

    Returns:
        ``"x86_64"``, ``"aarch64"``, or ``"unknown"``
    """
    try:
        result = subprocess.run(
            ["file", binary_path],
            capture_output=True, text=True, timeout=10,
        )
        output = result.stdout.lower()
        if "x86-64" in output or "x86_64" in output:
            return "x86_64"
        if "aarch64" in output or "arm aarch64" in output:
            return "aarch64"
        if "arm" in output:
            return "arm"  # 32-bit ARM
        return "unknown"
    except Exception:
        return "unknown"


def detect_arch_angr(binary_path: str) -> str:
    """Detect architecture using angr's loader (more precise)."""
    try:
        import angr
        proj = angr.Project(
            binary_path, auto_load_libs=False, load_debug_info=False)
        arch_name = proj.arch.name.lower()
        if "amd64" in arch_name or "x86" in arch_name:
            return "x86_64"
        if "aarch64" in arch_name:
            return "aarch64"
        if "arm" in arch_name:
            return "arm"
        return arch_name
    except Exception:
        return detect_arch(binary_path)


# ═══════════════════════════════════════════════════════════════════════════
# Docker availability check
# ═══════════════════════════════════════════════════════════════════════════

def docker_available() -> bool:
    """Check if Docker is available and the ARM image exists."""
    try:
        r = subprocess.run(
            ["docker", "image", "inspect", ARM_DOCKER_IMAGE],
            capture_output=True, timeout=10,
        )
        return r.returncode == 0
    except Exception:
        return False


def ensure_arm_docker() -> bool:
    """
    Ensure the ARM Docker image is available; build it if not.
    Returns True if image is ready.
    """
    if docker_available():
        return True

    # Try to build it
    dockerfile = Path(__file__).resolve().parent.parent / \
        "docker" / "Dockerfile.arm"
    if not dockerfile.exists():
        return False

    try:
        r = subprocess.run(
            ["docker", "build", "-t", ARM_DOCKER_IMAGE, "-f", str(dockerfile),
             str(dockerfile.parent)],
            capture_output=True, text=True, timeout=300,
        )
        return r.returncode == 0
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════════
# Cross-compilation via Docker
# ═══════════════════════════════════════════════════════════════════════════

def get_gcc_for_arch(arch: str) -> list[str]:
    """
    Get the GCC command for a given architecture.

    For x86_64: native gcc
    For aarch64: runs inside Docker with aarch64-linux-gnu-gcc
    """
    if arch in ("x86_64", "x86", "unknown"):
        return ["gcc"]
    return ['arm-none-eabi-gcc']  # ARM uses docker_compile


def docker_compile(
    source_path: str,
    output_path: str,
    arch: str = "aarch64",
    syntax_only: bool = False,
    extra_flags: list[str] | None = None,
) -> Tuple[bool, str]:
    """
    Compile a C source file using Docker (for ARM cross-compilation).

    Args:
        source_path:  Absolute path to the .c file on the host.
        output_path:  Absolute path for the output binary on the host.
        arch:         Target architecture (``"aarch64"``).
        syntax_only:  If True, only check syntax (``-fsyntax-only``).
        extra_flags:  Additional GCC flags.

    Returns:
        (success, stderr_output)
    """
    source_path = str(Path(source_path).resolve())
    output_path = str(Path(output_path).resolve())
    source_dir = str(Path(source_path).parent)
    output_dir = str(Path(output_path).parent)
    source_name = Path(source_path).name
    output_name = Path(output_path).name

    if arch == "aarch64":
        compiler = "aarch64-linux-gnu-gcc"
    else:
        compiler = "gcc"

    # Build the gcc command to run inside Docker
    if syntax_only:
        gcc_cmd = f"{compiler} -fsyntax-only -w /src/{source_name}"
    else:
        gcc_cmd = f"{compiler} -w -o /out/{output_name} /src/{source_name} -lm"
        if extra_flags:
            gcc_cmd += " " + " ".join(extra_flags)

    # Docker volumes: mount source dir and output dir
    volumes = [f"{source_dir}:/src:ro"]
    if not syntax_only:
        volumes.append(f"{output_dir}:/out")

    cmd = ["docker", "run", "--rm"]
    for v in volumes:
        cmd.extend(["-v", v])
    cmd.extend([ARM_DOCKER_IMAGE, "sh", "-c", gcc_cmd])

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0:
            return True, ""
        return False, result.stderr[:500]
    except subprocess.TimeoutExpired:
        return False, "Compilation timed out"
    except Exception as e:
        return False, str(e)


def docker_run(
    binary_path: str,
    stdin_input: str = "",
    timeout: int = 10,
) -> Tuple[bool, str]:
    """
    Run an ARM binary using QEMU inside Docker.

    Args:
        binary_path:  Absolute path to the ARM ELF binary on the host.
        stdin_input:  Input to feed via stdin.
        timeout:      Execution timeout in seconds.

    Returns:
        (success, stdout_output_or_error)
    """
    binary_path = str(Path(binary_path).resolve())
    binary_dir = str(Path(binary_path).parent)
    binary_name = Path(binary_path).name

    cmd = [
        "docker", "run", "--rm", "-i",
        "-v", f"{binary_dir}:/work:ro",
        "-e", "QEMU_LD_PREFIX=/usr/aarch64-linux-gnu",
        ARM_DOCKER_IMAGE,
        "qemu-aarch64-static", f"/work/{binary_name}",
    ]

    try:
        result = subprocess.run(
            cmd,
            input=stdin_input.encode() if stdin_input else None,
            capture_output=True,
            timeout=timeout,
        )
        stdout = result.stdout.decode("utf-8", errors="ignore")
        if result.returncode == 0:
            return True, stdout
        stderr = result.stderr.decode("utf-8", errors="ignore")
        return False, f"EXIT_{result.returncode}: {stderr[:200]}"
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT"
    except Exception as e:
        return False, f"ERROR: {e}"


# ═══════════════════════════════════════════════════════════════════════════
# Cross-compile example binaries (convenience)
# ═══════════════════════════════════════════════════════════════════════════

def cross_compile_examples(examples_dir: str, arch: str = "aarch64") -> dict:
    """
    Cross-compile all .c files in examples_dir for the given architecture.

    Returns:
        dict mapping source_name → (success, binary_path_or_error)
    """
    examples_dir = Path(examples_dir)
    out_dir = examples_dir / "bin" / ("arm64" if arch == "aarch64" else arch)
    out_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    for src in sorted(examples_dir.glob("*.c")):
        name = src.stem
        out_bin = out_dir / name
        ok, err = docker_compile(str(src), str(out_bin), arch=arch)
        if ok:
            results[name] = (True, str(out_bin))
        else:
            results[name] = (False, err)
    return results
