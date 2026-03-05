"""Load .env file from the project root."""

import os
from pathlib import Path


def load_env(env_path: str | None = None):
    """Load key=value pairs from a .env file into os.environ."""
    if env_path is None:
        # Walk up from this file to find .env
        p = Path(__file__).resolve().parent
        while p != p.parent:
            candidate = p / ".env"
            if candidate.exists():
                env_path = str(candidate)
                break
            p = p.parent
    if env_path is None or not os.path.exists(env_path):
        return

    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                # Only set if not already in environment
                if key not in os.environ:
                    os.environ[key] = value
