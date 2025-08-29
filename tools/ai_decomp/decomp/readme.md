# Decompilation Project

A machine learning-based assembly code decompilation project that supports multiple decompilation methods, including RAG (Retrieval-Augmented Generation) and general LLM API.

## Features

  - **Multiple Decompilation Methods**:
    - RAG (Retrieval-Augmented Generation) - Uses similarity search to enhance decompilation quality
      - Two knowledge data base available: MBPP and exe_bench 
    - General LLM API - Calls general large language model API

## Requirements

- Python 3.9+
- CUDA support

## Environment Setup

```bash
conda create -n decomp-env python=3.9 -y
conda activate decomp-env
pip install -r requirements.txt
```

## Usage

### Command Line Arguments

- `--input, -i`: Input assembly file path (default: `data/example.s`)
- `--output, -o`: Output decompiled file path (default: `data/example_mbpp.cpp`)
- `--multi_function, -m`: Whether the input assembly file contains multiple functions (flag)
- `--decompilation_method, -d`: Decompilation method selection
  - `general_llm`: Use general LLM API
  - `RAG`: Use retrieval-augmented generation
- `--rag_db`: RAG database selection (`exe_bench` or `mbpp`)

### Examples

```bash
# Decompile using RAG method
python decompile.py \
  --input data/example_single.s \
  --output results/decompiled.cpp \
  --decompilation_method RAG \
  --rag_db mbpp

# Use General LLM API
python decompile.py \
  --input data/example_single.s \
  --output results/decompiled.cpp \
  --decompilation_method general_llm

# Decompile multi-function assembly file
python decompile.py \
  --input data/example_multi.s \
  --output results/multi_decompiled.cpp \
  --m \
  --decompilation_method RAG \
  --rag_db mbpp
