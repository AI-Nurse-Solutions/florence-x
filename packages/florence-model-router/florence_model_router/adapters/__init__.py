"""Model adapters. Phase 4: Ollama (local), llama.cpp, vLLM, and cloud adapters."""
from __future__ import annotations
from typing import Protocol


class ModelAdapter(Protocol):
    name: str
    def generate(self, prompt: str, **kw) -> str: ...
