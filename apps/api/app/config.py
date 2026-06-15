from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Settings:
    database_url: str = os.getenv("FLORENCE_DATABASE_URL", "")  # empty => in-memory repo
    redis_url: str = os.getenv("FLORENCE_REDIS_URL", "")
    edena_base_url: str = os.getenv("EDENA_BASE_URL", "")        # empty => in-process LocalRuleBackend
    require_identity: bool = os.getenv("FLORENCE_REQUIRE_IDENTITY", "true").lower() == "true"
    examples_dir: str = os.getenv("FLORENCE_EXAMPLES_DIR", "examples")
    event_log_path: str = os.getenv("FLORENCE_EVENT_LOG", ".florence/events.jsonl")
    # Execution engine (P1-9): "graph" = durable LangGraph runtime, "minimal" = the
    # in-process step runner. Checkpoint store: empty => in-memory; sqlite:///path or
    # a postgres URL => durable, restart-safe checkpoints.
    runtime: str = os.getenv("FLORENCE_RUNTIME", "graph")
    langgraph_checkpoint: str = os.getenv("FLORENCE_LANGGRAPH_CHECKPOINT", "")


settings = Settings()
