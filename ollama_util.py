"""Ollama reachability checks (no heavy pipeline imports)."""

from __future__ import annotations

import os


def check_ollama(model: str = "llama3", *, timeout_sec: float = 3.0) -> bool:
    """
    Return True if Ollama is running and the requested model is available.
    Uses the ollama Python client (respects OLLAMA_HOST).
    """
    try:
        import ollama

        client = ollama.Client(
            host=os.getenv("OLLAMA_HOST"),
            timeout=timeout_sec,
        )
        listed = client.list()
        names: set[str] = set()
        for m in listed.models:
            tag = getattr(m, "model", None) or ""
            names.add(tag.split(":")[0])
        base = model.split(":")[0]
        return base in names
    except Exception:
        return False
