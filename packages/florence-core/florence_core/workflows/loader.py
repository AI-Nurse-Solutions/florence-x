"""Load WorkflowDefinition / AgentDefinition objects from YAML files."""
from __future__ import annotations

from pathlib import Path

import yaml

from florence_core.schemas import AgentDefinition, WorkflowDefinition


def load_workflow(path: str | Path) -> WorkflowDefinition:
    return WorkflowDefinition.model_validate(yaml.safe_load(Path(path).read_text()))


def load_agent(path: str | Path) -> AgentDefinition:
    return AgentDefinition.model_validate(yaml.safe_load(Path(path).read_text()))
