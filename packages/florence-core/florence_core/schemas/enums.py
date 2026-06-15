"""Canonical enumerations for the Florence-X object model.

These literals are the shared vocabulary of the orchestration plane (Florence-X)
and the governance plane (EDENA). Changing a member here is an API-breaking
change and requires an RFC (see docs/rfcs/0001-core-object-model.md).
"""
from __future__ import annotations

from enum import Enum


class RiskTier(str, Enum):
    """EDENA action-risk tiers. Ambiguity always escalates upward."""

    GREEN = "green"
    YELLOW = "yellow"
    ORANGE = "orange"
    RED = "red"
    RED_BLOCKED = "red_blocked"


class DataClass(str, Enum):
    """Data classification that drives the PHI boundary + model routing."""

    PUBLIC = "public"
    INTERNAL = "internal"
    PHI_LOCAL = "phi_local"          # PHI present; must stay inside the perimeter
    PHI_REDACTED = "phi_redacted"    # de-identified / tokenized projection
    RESTRICTED = "restricted"        # secrets, credentials, never-persist


class Urgency(str, Enum):
    STAT = "stat"
    URGENT = "urgent"
    ROUTINE = "routine"


class ActionType(str, Enum):
    """Every consequential thing an agent can propose to do."""

    DRAFT = "draft"
    SUMMARIZE = "summarize"
    RETRIEVE = "retrieve"
    WRITE_RECORD = "write_record"
    SEND_MESSAGE = "send_message"
    CALL_API = "call_api"
    EXECUTE_CODE = "execute_code"
    TRIGGER_ALERT = "trigger_alert"
    HANDOFF_TO_AGENT = "handoff_to_agent"
    STORE_MEMORY = "store_memory"


class EdenaDecisionType(str, Enum):
    """The eight governance outcomes EDENA may return."""

    ALLOW = "allow"
    ALLOW_WITH_CONSTRAINTS = "allow_with_constraints"
    REQUIRE_HUMAN = "require_human"
    ESCALATE = "escalate"
    DENY = "deny"
    THROTTLE = "throttle"
    CONTAIN = "contain"
    STOP = "stop"


class WorkflowRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_HUMAN = "awaiting_human"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CONTAINED = "contained"
    STOPPED = "stopped"


class HumanReviewOutcome(str, Enum):
    APPROVE = "approve"
    EDIT = "edit"
    ESCALATE = "escalate"
    DENY = "deny"
    STOP = "stop"


class ToolRiskClass(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    ORANGE = "orange"
    RED = "red"


class MemoryClass(str, Enum):
    OPERATIONAL_CONTEXT = "operational_context"
    USER_PREFERENCE = "user_preference"
    CLINICAL_SUMMARY = "clinical_summary"
    POLICY_CACHE = "policy_cache"
    SECURITY_STATE = "security_state"


class IncidentCategory(str, Enum):
    SAFETY = "safety"
    SECURITY = "security"
    PRIVACY = "privacy"
    PERFORMANCE = "performance"


class IncidentSeverity(str, Enum):
    SEV1 = "sev1"
    SEV2 = "sev2"
    SEV3 = "sev3"
    SEV4 = "sev4"
