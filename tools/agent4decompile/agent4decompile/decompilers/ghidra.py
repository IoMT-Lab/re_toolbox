"""
Ghidra decompiler wrapper.

Invokes Ghidra in headless mode via `analyzeHeadless` CLI.  A temporary
Jython script is written that uses Ghidra's `DecompInterface` to decompile
every non-external, non-thunk function in the binary.

Post-processing fixes Ghidra-specific artifacts:
  - Translates internal types (undefined8, byte, dword, …) to standard C
  - Comments out compiler-generated functions (_init, _fini, _start, …)
  - Replaces PTR_ references, processEntry keywords, EVP_PKEY_CTX types
"""

import subprocess
import tempfile
import os
import re
from pathlib import Path

from .base import DecompilerBase, DecompilationResult


# ---------------------------------------------------------------------------
# Post-processing
# ---------------------------------------------------------------------------

def postprocess_ghidra_code(code: str) -> str:
    """Fix Ghidra-specific artifacts so the code is closer to compilable C."""

    # ── Typedefs for Ghidra internal types ─────────────────────────────────
    typedefs = """
// Ghidra type definitions
typedef void* undefined;
typedef void* undefined1;
typedef void* undefined2;
typedef void* undefined4;
typedef void* undefined8;
typedef unsigned char byte;
typedef unsigned short word;
typedef unsigned int dword;
typedef unsigned long long qword;
typedef unsigned int uint;
typedef unsigned long ulong;
typedef long long longlong;
typedef unsigned long long ulonglong;
typedef unsigned char uchar;
typedef unsigned short ushort;
"""

    # ── Fix erroneous OpenSSL type references ──────────────────────────────
    code = re.sub(r'\bEVP_PKEY_CTX\s*\*\s*', 'void *', code)
    code = re.sub(r'\bEVP_PKEY_CTX\b', 'void', code)

    # ── Fix function-pointer casts via 'code *' ───────────────────────────
    code = re.sub(
        r'\(?\*?\(code\s*\*?\)([^)]+)\)\(',
        r'((void(*)())\1)(',
        code,
    )

    # ── Remove invalid keywords ────────────────────────────────────────────
    code = re.sub(r'\bprocessEntry\s+', '', code)

    # ── Comment out compiler-generated functions ───────────────────────────
    problematic_functions = [
        '_init', '_fini', '_start', 'frame_dummy',
        'deregister_tm_clones', 'register_tm_clones',
        '__do_global_dtors_aux', '__libc_csu_init', '__libc_csu_fini',
        'FUN_00101020', 'FUN_00101030', 'FUN_00101040',
    ]

    lines = code.split('\n')
    result_lines: list[str] = []
    in_problematic = False
    waiting_for_brace = False
    brace_count = 0

    for line in lines:
        is_problematic = any(
            f' {fn}(' in line or f'*{fn}(' in line or f'_{fn}(' in line
            for fn in problematic_functions
        )

        if is_problematic:
            waiting_for_brace = True
            result_lines.append(
                '// ' + line + '  // REMOVED: Compiler-generated')
            if '{' in line:
                in_problematic = True
                waiting_for_brace = False
                brace_count = line.count('{') - line.count('}')
            continue

        if waiting_for_brace:
            result_lines.append('// ' + line)
            if '{' in line:
                in_problematic = True
                waiting_for_brace = False
                brace_count = line.count('{') - line.count('}')
            continue

        if in_problematic:
            brace_count += line.count('{') - line.count('}')
            result_lines.append('// ' + line)
            if brace_count <= 0:
                in_problematic = False
            continue

        result_lines.append(line)

    code = '\n'.join(result_lines)

    # ── Replace undefined global pointers ──────────────────────────────────
    code = re.sub(r'\bPTR_\w+', 'NULL', code)

    # ── Fix stack variable references ──────────────────────────────────────
    code = re.sub(r'&stack0x[0-9a-f]+', '&auStack_8', code)

    # ── Prepend typedefs after the first #include block ────────────────────
    include_end = code.find('\n\n')
    if include_end > 0:
        code = code[:include_end] + '\n' + typedefs + code[include_end:]
    else:
        code = typedefs + code

    return code


# ---------------------------------------------------------------------------
# Decompiler class
# ---------------------------------------------------------------------------

class GhidraDecompiler(DecompilerBase):
    """Wrapper for the Ghidra headless decompiler."""

    def __init__(self, ghidra_path: str | None = None):
        super().__init__("Ghidra")
        if ghidra_path is None:
            ghidra_path = os.environ.get(
                "GHIDRA_PATH",
                os.path.expanduser("~/tools/ghidra_11.2.1_PUBLIC"),
            )
        self.ghidra_path = Path(ghidra_path)
        self.analyze_headless = self.ghidra_path / "support" / "analyzeHeadless"
        if not self.analyze_headless.exists():
            raise RuntimeError(
                f"Ghidra analyzeHeadless not found at {self.analyze_headless}"
            )

    def decompile(self, binary_path: str) -> DecompilationResult:
        """Decompile *binary_path* using Ghidra headless mode."""
        try:
            tmp_root = os.environ.get("TMPDIR", "/tmp")
            with tempfile.TemporaryDirectory(prefix="ghidra_", dir=tmp_root) as tmpdir:
                tmpdir = Path(tmpdir)
                project_dir = tmpdir / "project"
                output_file = tmpdir / "output.c"
                project_dir.mkdir(exist_ok=True)

                # Jython script executed inside Ghidra
                script_content = self._ghidra_script(str(output_file))
                script_file = project_dir / "DecompileBinary.py"
                script_file.write_text(script_content)

                env = os.environ.copy()
                env['JAVA_TOOL_OPTIONS'] = f'-Djava.io.tmpdir={tmpdir}'

                cmd = [
                    str(self.analyze_headless),
                    str(project_dir), "DecompProject",
                    "-import", str(Path(binary_path).absolute()),
                    "-scriptPath", str(project_dir),
                    "-postScript", "DecompileBinary.py",
                    "-deleteProject",
                    "-max-cpu", "1",
                ]

                proc = subprocess.run(
                    cmd, capture_output=True, text=True,
                    timeout=180, env=env, cwd=str(project_dir),
                )

                if output_file.exists():
                    source = output_file.read_text()
                    if len(source) > 100:
                        source = postprocess_ghidra_code(source)
                        return DecompilationResult(
                            success=True, source_code=source,
                            decompiler_name="Ghidra", binary_path=str(binary_path),
                        )
                    return DecompilationResult(
                        success=False, error_message="No functions decompiled",
                        decompiler_name="Ghidra", binary_path=str(binary_path),
                    )
                return DecompilationResult(
                    success=False, error_message="Output file not created",
                    decompiler_name="Ghidra", binary_path=str(binary_path),
                )

        except subprocess.TimeoutExpired:
            return DecompilationResult(
                success=False, error_message="Ghidra timeout (>180 s)",
                decompiler_name="Ghidra", binary_path=str(binary_path),
            )
        except Exception as e:
            return DecompilationResult(
                success=False, error_message=f"Exception: {str(e)[:200]}",
                decompiler_name="Ghidra", binary_path=str(binary_path),
            )

    # ------------------------------------------------------------------
    @staticmethod
    def _ghidra_script(output_path: str) -> str:
        """Return the Jython script executed inside Ghidra."""
        return f'''# Decompile binary to C - Ghidra Jython script
#@category Decompilation

from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor
import java.io.PrintWriter as PrintWriter
import java.io.File as File

output_file = "{output_path}"
writer = PrintWriter(File(output_file))

writer.println("// Decompiled with Ghidra")
writer.println("#include <stdio.h>")
writer.println("#include <stdlib.h>")
writer.println("#include <string.h>")
writer.println("")

if currentProgram is not None:
    decompiler = DecompInterface()
    decompiler.openProgram(currentProgram)
    func_manager = currentProgram.getFunctionManager()
    functions = func_manager.getFunctions(True)
    count = 0
    for func in functions:
        if func.isExternal() or func.isThunk():
            continue
        try:
            results = decompiler.decompileFunction(func, 30, ConsoleTaskMonitor())
            if results and results.decompileCompleted():
                writer.println("// Function: " + func.getName()
                               + " at " + str(func.getEntryPoint()))
                writer.println(results.getDecompiledFunction().getC())
                writer.println("")
                count += 1
        except:
            pass
    print("Decompiled " + str(count) + " functions")
    decompiler.dispose()

writer.close()
'''
