from setuptools import setup, find_packages

setup(
    name="agent4decompile",
    version="1.0.0",
    description="Multi-Agent Constraint-Guided Decompilation: Binary → Re-executable C",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "openai>=1.0.0",
        "anthropic>=0.18.0",
        "loguru>=0.7.0",
    ],
    extras_require={
        "angr": ["angr>=9.2.0"],
    },
    entry_points={
        "console_scripts": [
            "agent4decompile=scripts.run_pipeline:main",
        ],
    },
)
