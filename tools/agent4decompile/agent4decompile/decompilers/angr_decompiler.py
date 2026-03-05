"""
Angr decompiler wrapper.

Uses the angr Python API directly:
  Project → CFGFast(normalize=True) → CallingConventions → per-function Decompiler

Post-processing comments out system functions and replaces angr-specific
``undefined*`` types with ``void*``.
"""

import re

from .base import DecompilerBase, DecompilationResult

try:
    import angr
    ANGR_AVAILABLE = True
except ImportError:
    ANGR_AVAILABLE = False

# Functions to skip in statically-linked binaries (glibc internals)
STATIC_SKIP_FUNCTIONS = {
    '_init', '_fini', '_start', 'frame_dummy',
    'deregister_tm_clones', 'register_tm_clones',
    '__do_global_dtors_aux', '__libc_csu_init', '__libc_csu_fini',
    'entry', '_entry', '__libc_start_main', '__libc_init_first',
    '__libc_csu_isr', '__stack_chk_fail', '__fortify_fail',
    'abort', 'exit', '_exit', '__assert_fail',
    '__cxa_atexit', '__cxa_finalize', 'atexit',
    'malloc', 'free', 'calloc', 'realloc',
    'memcpy', 'memset', 'memmove', 'memcmp',
    'strlen', 'strcpy', 'strncpy', 'strcmp', 'strncmp', 'strdup',
    'strcat', 'strncat', 'strchr', 'strrchr', 'strstr',
    'printf', 'fprintf', 'sprintf', 'snprintf', 'vprintf',
    'vfprintf', 'vsprintf', 'vsnprintf',
    'scanf', 'fscanf', 'sscanf',
    'puts', 'fputs', 'fputc', 'putchar', 'putc',
    'gets', 'fgets', 'fgetc', 'getchar', 'getc',
    'fopen', 'fclose', 'fread', 'fwrite', 'fseek', 'ftell', 'fflush',
    'open', 'close', 'read', 'write', 'lseek',
    'mmap', 'munmap', 'brk', 'sbrk',
    'signal', 'sigaction', 'raise',
    'setjmp', 'longjmp',
    'strtol', 'strtoul', 'atoi', 'atol',
    'qsort', 'bsearch',
}


# ---------------------------------------------------------------------------
# Post-processing
# ---------------------------------------------------------------------------

def postprocess_angr_code(code: str) -> str:
    """Fix angr-specific artifacts to improve compilability.

    Strategy: angr emits ``// Function: <name> at 0x<addr>`` comments before
    each function.  We split the output into blocks at those markers, then
    comment out blocks that belong to system / compiler-generated functions.
    """

    SYSTEM_FUNCTIONS = {
        '_init', '_fini', '_start', 'frame_dummy',
        'deregister_tm_clones', 'register_tm_clones',
        '__do_global_dtors_aux', '__libc_csu_init', '__libc_csu_fini',
        'entry', '_entry',
    }

    _func_re = re.compile(r'^// Function:\s+(\S+)\s+at\s+0x')

    # ── 1. Split into blocks ──────────────────────────────────────────────
    #  Each block = (func_name | None, [lines])
    blocks: list[tuple[str | None, list[str]]] = []
    current_name: str | None = None
    current_lines: list[str] = []

    for line in code.split('\n'):
        m = _func_re.match(line)
        if m:
            # Save previous block
            blocks.append((current_name, current_lines))
            current_name = m.group(1)
            current_lines = [line]
        else:
            current_lines.append(line)
    blocks.append((current_name, current_lines))

    # ── 2. Comment out system-function blocks ─────────────────────────────
    result_lines: list[str] = []
    for name, lines in blocks:
        is_system = name is not None and (
            name in SYSTEM_FUNCTIONS or name.startswith('sub_')
        )
        if is_system:
            for ln in lines:
                result_lines.append('// ' + ln)
        else:
            result_lines.extend(lines)

    code = '\n'.join(result_lines)

    # ── 3. Replace angr's ``undefined`` types ─────────────────────────────
    code = re.sub(r'\bundefined\d*\b', 'void*', code)

    return code


# ---------------------------------------------------------------------------
# Decompiler class
# ---------------------------------------------------------------------------

class AngrDecompiler(DecompilerBase):
    """Wrapper for the angr lifting-based decompiler."""

    def __init__(self):
        super().__init__("Angr")
        if not ANGR_AVAILABLE:
            raise ImportError("angr is not installed. Run: pip install angr")

    def decompile(self, binary_path: str) -> DecompilationResult:
        """Decompile *binary_path* using angr's Python API."""
        try:
            proj = angr.Project(binary_path, auto_load_libs=False, load_debug_info=False)

            # Detect architecture
            arch_name = proj.arch.name.lower()
            if "amd64" in arch_name or "x86" in arch_name:
                architecture = "x86_64"
            elif "aarch64" in arch_name:
                architecture = "aarch64"
            elif "arm" in arch_name:
                architecture = "arm"
            else:
                architecture = arch_name

            cfg = proj.analyses.CFGFast(normalize=True, data_references=True)

            # Optional calling-convention recovery (improves quality)
            try:
                proj.analyses.CompleteCallingConventions(recover_variables=True, force=False)
            except Exception:
                pass

            # Determine which functions to decompile.
            # For statically-linked binaries, only decompile functions in the
            # main executable segment (skip libc/runtime functions).
            is_static = not any(
                obj.provides for obj in proj.loader.all_elf_objects
                if hasattr(obj, 'provides') and obj.provides
            )
            main_obj = proj.loader.main_object
            min_addr = main_obj.min_addr
            max_addr = main_obj.max_addr

            # Collect function candidates
            candidates = []
            for func_addr, func in proj.kb.functions.items():
                if func.is_plt or func.is_simprocedure or func.size < 5:
                    continue
                # For statically-linked: only keep functions that look "user-level"
                # (skip the hundreds of glibc internal functions)
                if is_static and func.name and (
                    func.name.startswith('__') or
                    func.name.startswith('_dl_') or
                    func.name.startswith('_IO_') or
                    func.name.startswith('_exit') or
                    func.name.startswith('__libc') or
                    func.name in STATIC_SKIP_FUNCTIONS
                ):
                    continue
                candidates.append((func_addr, func))

            # If statically-linked and we have too many candidates, further
            # filter to only functions in the "text" range below a threshold.
            if is_static and len(candidates) > 50:
                # Keep only named non-sub_ functions + main
                user_funcs = [
                    (a, f) for a, f in candidates
                    if f.name and not f.name.startswith('sub_')
                    and f.name not in STATIC_SKIP_FUNCTIONS
                ]
                if user_funcs:
                    candidates = user_funcs

            parts: list[str] = [
                "// Decompiled with Angr\n",
                "#include <stdio.h>\n",
                "#include <stdlib.h>\n",
                "#include <string.h>\n\n",
            ]

            for func_addr, func in candidates:
                try:
                    try:
                        proj.analyses.VariableRecoveryFast(func)
                    except Exception:
                        pass
                    dec = proj.analyses.Decompiler(func, cfg=cfg.model)
                    if dec.codegen and dec.codegen.text:
                        parts.append(f"// Function: {func.name} at {hex(func_addr)}\n")
                        parts.append(dec.codegen.text)
                        parts.append("\n\n")
                except Exception:
                    continue

            source = ''.join(parts)

            if len(parts) > 4:  # more than just headers
                source = postprocess_angr_code(source)
                return DecompilationResult(
                    success=True, source_code=source,
                    decompiler_name="Angr", binary_path=str(binary_path),
                    architecture=architecture,
                )
            return DecompilationResult(
                success=False, error_message="No functions decompiled",
                decompiler_name="Angr", binary_path=str(binary_path),
                architecture=architecture,
            )

        except Exception as e:
            return DecompilationResult(
                success=False, error_message=str(e)[:300],
                decompiler_name="Angr", binary_path=str(binary_path),
                architecture="unknown",
            )
