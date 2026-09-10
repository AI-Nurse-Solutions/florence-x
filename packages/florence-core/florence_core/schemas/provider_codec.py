"""SS-05B records for offline wire-format tests; never an execution permission."""
from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import Field, StringConstraints, model_validator

from .catalog import CatalogRecord, Digest, Identifier
from .inference import Count, ReviewProposal

Protocol = Literal["ollama_chat_v1", "openai_chat_completions_v1"]
ModelName = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=128,
                                            pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:/-]*$")]


class ProviderCodecSpec(CatalogRecord):
    profile_id: Identifier
    protocol: Protocol
    request_model: ModelName
    expected_response_model: ModelName
    # The date identifies our inspected subset, not a vendor API version guarantee.
    interface_baseline: Literal["inspected-2026-09-10"] = "inspected-2026-09-10"
    mode: Literal["offline_codec_only"] = "offline_codec_only"
    authority: Literal["no_execution_permission"] = "no_execution_permission"


class PreparedProviderRequest(CatalogRecord):
    request_sha256: Digest
    mission_sha256: Digest
    spec: ProviderCodecSpec
    relative_path: Literal["/api/chat", "/v1/chat/completions"]
    body_json: str = Field(min_length=1, max_length=65536, strict=True)
    body_sha256: Digest
    transmission: Literal["not_implemented"] = "not_implemented"
    authority: Literal["no_execution_permission"] = "no_execution_permission"


class CodecTokenCounts(CatalogRecord):
    """Counts declared by the supplied fixture, not measured model usage or cost."""
    input_tokens: Count | None = None
    output_tokens: Count | None = None
    basis: Literal["authored_provider_format_fixture"] = "authored_provider_format_fixture"


class ProviderCodecResult(CatalogRecord):
    request_sha256: Digest
    mission_sha256: Digest
    prepared_sha256: Digest
    protocol: Protocol
    outcome: Literal["proposal_ready", "refused", "incomplete", "unsupported_response",
                     "invalid_response", "budget_exceeded", "provider_error"]
    proposal: ReviewProposal | None = None
    token_counts: CodecTokenCounts | None = None
    discarded_fields: tuple[str, ...] = ()
    next_action: Literal["human_review", "stop_no_fallback"]
    response_origin: Literal["authored_provider_format_fixture"] = "authored_provider_format_fixture"
    transport_calls: Literal[0] = 0
    authority: Literal["no_execution_permission"] = "no_execution_permission"

    @model_validator(mode="after")
    def state_is_honest(self) -> Self:
        if self.outcome == "proposal_ready":
            if self.proposal is None or self.next_action != "human_review":
                raise ValueError("proposal requires human review")
        elif self.proposal is not None or self.next_action != "stop_no_fallback":
            raise ValueError("non-success cannot retain a proposal or request fallback")
        if type(self.transport_calls) is not int or self.transport_calls != 0:
            raise ValueError("offline codec cannot report a transport call")
        return self
