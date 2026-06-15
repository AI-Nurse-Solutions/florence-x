"""Append-only event log using CloudEvents envelopes.

Every step of the canonical runtime loop emits a CloudEvent. The log is
append-only by contract; in production the JSONL sink is replaced by an
immutable store mapped to HIPAA / HTI-1 / EU AI Act controls.
"""
from __future__ import annotations

import json
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

SPEC_VERSION = "1.0"
SOURCE_PREFIX = "florence-x"


@dataclass
class CloudEvent:
    type: str                       # e.g. florence-x.candidate_action.created
    subject: str                    # e.g. workflow_run_id
    data: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: f"evt_{uuid.uuid4().hex}")
    source: str = SOURCE_PREFIX
    time: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    specversion: str = SPEC_VERSION

    def to_dict(self) -> dict:
        return {
            "specversion": self.specversion,
            "id": self.id,
            "source": self.source,
            "type": self.type,
            "subject": self.subject,
            "time": self.time,
            "datacontenttype": "application/json",
            "data": self.data,
        }


class EventSink(Protocol):
    def write(self, event: CloudEvent) -> None: ...


class NullSink:
    def write(self, event: CloudEvent) -> None:  # noqa: D401
        return None


class StdoutSink:
    def write(self, event: CloudEvent) -> None:
        sys.stdout.write(json.dumps(event.to_dict()) + "\n")


class JsonlSink:
    """Append-only JSONL sink. Opens in append mode; never truncates."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event: CloudEvent) -> None:
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event.to_dict()) + "\n")


class EventLog:
    def __init__(self, *sinks: EventSink) -> None:
        self.sinks: list[EventSink] = list(sinks) or [StdoutSink()]

    def emit(self, type: str, subject: str, **data) -> CloudEvent:
        evt = CloudEvent(type=f"{SOURCE_PREFIX}.{type}", subject=subject, data=data)
        for sink in self.sinks:
            sink.write(evt)
        return evt
