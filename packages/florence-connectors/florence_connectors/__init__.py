"""florence-connectors: governed access to tools/data via a single gateway.

All connectors expose actions through the Tool Gateway; agents never call them
directly. Each invocation is a CandidateAction subject to EDENA. Phase 4.
"""
from __future__ import annotations
from .base import Connector
__all__ = ["Connector"]
