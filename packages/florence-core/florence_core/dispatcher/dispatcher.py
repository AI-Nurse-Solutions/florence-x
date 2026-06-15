"""Dispatcher — matches a Signal's type to a registered WorkflowDefinition."""
from __future__ import annotations

from florence_core.schemas import Signal, WorkflowDefinition


class Dispatcher:
    def __init__(self) -> None:
        self._by_signal_type: dict[str, WorkflowDefinition] = {}

    def register(self, workflow: WorkflowDefinition) -> None:
        for st in workflow.signal_types:
            self._by_signal_type[st] = workflow

    def select(self, signal: Signal) -> WorkflowDefinition | None:
        return self._by_signal_type.get(signal.signal_type)
