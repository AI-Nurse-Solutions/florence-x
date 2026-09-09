"""florence-model-router: model selection, redaction, routing rules, cost controls."""
from __future__ import annotations

from .adapters.ollama import OllamaAdapter
from .boundary import PhiBoundaryViolation, prepare_prompt
from .redaction import Redactor, redact
from .router import ModelRouter

__all__ = [
    "ModelRouter",
    "OllamaAdapter",
    "PhiBoundaryViolation",
    "Redactor",
    "prepare_prompt",
    "redact",
]
