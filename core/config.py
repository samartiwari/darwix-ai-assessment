"""Environment loading, done once at import.

`core/__init__.py` imports this, so anything that touches the core layer has the
environment loaded without each entrypoint remembering to do it. The path is
explicit rather than discovered: `load_dotenv()` walks up the call stack to guess
the location and fails outright when there is no calling frame, such as code run
from standard input.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"

_loaded = False


def load(override: bool = False) -> bool:
    """Load .env if present. Returns whether a file was found."""
    global _loaded
    if _loaded and not override:
        return ENV_FILE.exists()

    if ENV_FILE.exists():
        from dotenv import load_dotenv

        load_dotenv(ENV_FILE, override=override)
    _loaded = True
    return ENV_FILE.exists()


def missing_keys() -> list[str]:
    """Keys that are absent and have no local fallback.

    Only Groq is genuinely required: speech recognition and embeddings have local
    fallbacks, and edge-tts needs no key at all.
    """
    required = ["GROQ_API_KEY"]
    return [key for key in required if not os.getenv(key)]


load()
