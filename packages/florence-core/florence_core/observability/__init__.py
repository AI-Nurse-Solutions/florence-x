"""Observability helpers (OpenTelemetry tracing) for the runtime loop.

Tracing is optional: if opentelemetry-api is not installed the helpers degrade to
no-ops, so the MVP and the test suite run without the dependency. When the SDK is
configured (see apps/api telemetry setup) spans are exported to a collector.
"""
from __future__ import annotations

from .latency import POINT_OF_CARE_BUDGET_MS, LatencyBudget
from .tracing import HAVE_OTEL, get_tracer, set_attributes, span

__all__ = ["HAVE_OTEL", "get_tracer", "set_attributes", "span",
           "LatencyBudget", "POINT_OF_CARE_BUDGET_MS"]
