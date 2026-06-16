"""Ollama adapter — local model inference over the Ollama HTTP API.

Talks to a local Ollama daemon (default http://localhost:11434). Local-only by
construction, so PHI-bearing prompts may be sent without redaction. Uses stdlib
urllib to keep florence-model-router dependency-free; the daemon is mocked in
tests (no live model in CI).
"""
from __future__ import annotations

import json
import urllib.request

DEFAULT_HOST = "http://localhost:11434"


class OllamaAdapter:
    name = "ollama"
    locality = "local_slm"

    def __init__(self, model: str = "llama3.1", host: str = DEFAULT_HOST,
                 timeout_s: float = 30.0) -> None:
        self.model = model
        self.host = host.rstrip("/")
        self.timeout_s = timeout_s

    def generate(self, prompt: str, **kw) -> str:
        body = json.dumps({"model": self.model, "prompt": prompt, "stream": False}).encode()
        req = urllib.request.Request(
            f"{self.host}/api/generate", data=body,
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:  # noqa: S310
            payload = json.loads(resp.read().decode())
        return payload.get("response", "")
