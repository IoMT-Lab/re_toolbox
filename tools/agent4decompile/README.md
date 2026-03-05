# Agent4Decompile — Complete Pipeline

**Agent4Decompile** (BinThoven) is a multi-agent, constraint-guided decompilation framework
that transforms compiled x86-64 ELF binaries into **re-executable C source code**.

---

## Pipeline Overview

```
Binary (ELF x86-64)
        │
        ▼
┌──────────────────────────────────────────┐
│  Stage 1: DECOMPILATION                  │
│  (Ghidra / Angr / RetDec wrappers)      │
│  → Raw decompiled C code                 │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│  Stage 2: POST-PROCESSING                │
│  Remove system funcs, fix types,         │
│  add headers, clean decompiler artifacts │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│  Stage 3: (Optional) MULTI-DECOMPILER    │
│  CONSENSUS MERGING                       │
│  Match functions across decompilers,     │
│  vote on best implementations, merge     │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│  Stage 4: LLM ITERATIVE REFINEMENT      │
│  (Constraint-Guided, up to N iters)     │
│                                          │
│  L1: gcc -fsyntax-only → syntax ok?     │
│  L2: gcc -o output     → compiles?      │
│  L3: run + compare     → same output?   │
│                                          │
│  If fail → LLM fixes code → repeat      │
│  If all pass → SUCCESS                   │
└──────────────┬───────────────────────────┘
               │
               ▼
        Re-executable C source code
```

---

## Directory Structure

```
agent4decompile/
├── README.md                  ← This file
├── requirements.txt           ← Python dependencies
├── setup.py                   ← Package installer
│
├── agent4decompile/           ← Core Python package
│   ├── __init__.py
│   ├── pipeline.py            ← ★ Main entry point: end-to-end pipeline
│   │
│   ├── decompilers/           ← Decompiler wrappers
│   │   ├── __init__.py
│   │   ├── base.py            ← Abstract base class
│   │   ├── ghidra.py          ← Ghidra headless decompiler
│   │   ├── angr_decompiler.py ← Angr lifting-based decompiler
│   │   └── retdec.py          ← RetDec CLI decompiler
│   │
│   ├── consensus/             ← Multi-decompiler consensus merging
│   │   ├── __init__.py
│   │   ├── engine.py          ← MCGD consensus engine
│   │   ├── function_matcher.py
│   │   ├── consensus_voter.py
│   │   └── code_cleaner.py
│   │
│   ├── refinement/            ← LLM iterative refinement (core innovation)
│   │   ├── __init__.py
│   │   └── refiner.py         ← 3-level constraint-guided LLM refinement
│   │
│   └── testing/               ← Test case generation
│       ├── __init__.py
│       ├── pattern_generator.py   ← Name-based test patterns
│       ├── source_generator.py    ← Source-analysis-based tests
│       └── dynamic_generator.py   ← Fuzzing-based test generation
│
├── scripts/                   ← Ready-to-run scripts
│   ├── run_pipeline.py        ← ★ CLI: full pipeline on one binary
│   ├── run_batch.py           ← Batch processing for many binaries
│   └── run_baseline.py        ← Baseline decompilation (no refinement)
│
└── examples/                  ← Example binaries and usage
    ├── hello_world.c          ← Example source
    └── README.md              ← Quick start examples
```

---

## Quick Start

### 1. Install Dependencies

```bash
cd agent4decompile
pip install -e .
```

### 2. Prerequisites (External Tools)

You need at least ONE of these decompilers installed:

| Tool | Required? | Default Path | Install |
|------|-----------|-------------|---------|
| **Ghidra 11.x** | Recommended | `~/tools/ghidra_11.2.1_PUBLIC` | [ghidra-sre.org](https://ghidra-sre.org/) |
| **RetDec** | Recommended | `~/tools/bin/retdec-decompiler` | [github.com/avast/retdec](https://github.com/avast/retdec) |
| **Angr** | Optional | (Python package) | `pip install angr` |

You also need:
- **GCC** (for compilation testing): `apt install gcc`
- **LLM API Key** (for refinement): Set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`

### 3. Run on a Single Binary

```bash
# Minimal: decompile + refine with Ghidra + GPT-4o (default)
python scripts/run_pipeline.py --binary /path/to/binary --output ./output/

# Use a specific decompiler
python scripts/run_pipeline.py --binary /path/to/binary --decompiler retdec --output ./output/

# Use Anthropic Claude instead of OpenAI
python scripts/run_pipeline.py --binary /path/to/binary --llm-provider anthropic --output ./output/

# Tested example (angr + Anthropic, no external tools required):
cd examples && gcc -O0 -o hello_world hello_world.c && cd ..
python scripts/run_pipeline.py --binary examples/hello_world --decompiler angr --llm-provider anthropic --output ./output/hello_world/

# Control refinement iterations (default=5)
python scripts/run_pipeline.py --binary /path/to/binary --max-iterations 10 --output ./output/

# Multi-decompiler consensus mode (uses all 3 decompilers)
python scripts/run_pipeline.py --binary /path/to/binary --multi-decompiler --output ./output/

# Skip LLM refinement (just decompile + post-process)
python scripts/run_pipeline.py --binary /path/to/binary --no-refine --output ./output/
```

### 4. Run on a Batch of Binaries

```bash
python scripts/run_batch.py \
    --input-dir /path/to/binaries/ \
    --decompiler ghidra \
    --output-dir ./results/ \
    --max-iterations 7
```

---

## How It Works (Methodology)

### Stage 1: Decompilation
Each binary is decompiled using one or more tools:
- **Ghidra**: Rule-based, run via `analyzeHeadless` CLI
- **Angr**: Lifting-based, uses Python API with CFG normalization
- **RetDec**: ML-based, run via CLI

### Stage 2: Post-Processing
Decompiler-specific artifacts are cleaned:
- Ghidra: translate `undefined8` → `void*`, fix `PTR_` references, remove `processEntry`
- Angr: fix `undefined` types, comment out system functions
- RetDec: minimal cleanup (cleanest output)
- All: remove compiler-generated functions (`_init`, `_fini`, `_start`, etc.)

### Stage 3: Multi-Decompiler Consensus (Optional)
When using `--multi-decompiler`:
1. Functions are matched across decompiler outputs by name/signature/body similarity
2. Weighted voting selects the best implementation of each function
3. Headers, globals, and function bodies are merged

### Stage 4: LLM Iterative Refinement
The core innovation — a 3-level constraint hierarchy guides the LLM:

| Level | Check | Command | Feedback |
|-------|-------|---------|----------|
| **L1** | Syntax validity | `gcc -fsyntax-only -w` | Syntax error messages |
| **L2** | Compilation | `gcc -w -o output source.c -lm` | Linker/compilation errors |
| **L3** | Behavioral equivalence | Run both binaries, compare stdout | Output diff + hints |

At each iteration:
1. Evaluate code against all 3 levels (hierarchically)
2. If any level fails → construct structured prompt with error feedback
3. Send to LLM (GPT-4o or Claude) for repair
4. Extract corrected code → repeat
5. Stop when all 3 levels pass OR max iterations reached

---

## Configuration

### Environment Variables

```bash
export OPENAI_API_KEY="sk-..."           # For GPT-4o refinement
export ANTHROPIC_API_KEY="sk-ant-..."    # For Claude refinement (alternative)
export GHIDRA_PATH="/path/to/ghidra"     # Override default Ghidra location
export RETDEC_PATH="/path/to/retdec"     # Override default RetDec location
```

### Programmatic Usage

```python
from agent4decompile.pipeline import Agent4DecompilePipeline

pipeline = Agent4DecompilePipeline(
    decompiler="ghidra",          # "ghidra", "angr", or "retdec"
    llm_provider="openai",        # "openai" or "anthropic"
    model="gpt-4o",               # LLM model name
    max_iterations=5,             # Max refinement iterations
    constraint_level=3,           # 1=syntax, 2=+compile, 3=+execution
)

result = pipeline.run(
    binary_path="/path/to/binary",
    output_dir="./output/"
)

print(f"Success: {result.success}")
print(f"Iterations: {result.iterations}")
print(f"Re-executable: {result.re_executable}")
print(result.refined_code)
```

---

## Citation

If you use this tool in your research, please cite:

```bibtex
@inproceedings{agent4decompile2026,
  title={Agent4Decompile: Multi-Agent Constraint-Guided Decompilation},
  author={...},
  booktitle={USENIX Security Symposium},
  year={2026}
}
```
