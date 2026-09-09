"""Latency budget instrumentation (Phase 4).

Latency is a clinical-safety concern: point-of-care paths target ≤ 2–3s end to
end (CLAUDE.md). `LatencyBudget` times a span of work, records the result on the
active OpenTelemetry span (when present), and reports whether the budget held.
"""
from __future__ import annotations

import logging
import time
from typing import Self

log = logging.getLogger(__name__)

# Point-of-care end-to-end target (upper bound of the 2–3s window).
POINT_OF_CARE_BUDGET_MS = 3000


class LatencyBudget:
    def __init__(self, budget_ms: int = POINT_OF_CARE_BUDGET_MS, label: str = "point_of_care") -> None:
        self.budget_ms = budget_ms
        self.label = label
        self.elapsed_ms: float | None = None
        self._t0: float | None = None

    def __enter__(self) -> Self:
        self._t0 = time.monotonic()
        return self

    def __exit__(self, *exc) -> bool:
        self.elapsed_ms = (time.monotonic() - (self._t0 or time.monotonic())) * 1000.0
        self._annotate_span()
        return False

    @property
    def within_budget(self) -> bool:
        return self.elapsed_ms is not None and self.elapsed_ms <= self.budget_ms

    @property
    def overage_ms(self) -> float:
        if self.elapsed_ms is None:
            return 0.0
        return max(0.0, self.elapsed_ms - self.budget_ms)

    def _annotate_span(self) -> None:
        from .tracing import HAVE_OTEL

        if not HAVE_OTEL:
            return
        try:
            from opentelemetry import trace

            span = trace.get_current_span()
            span.set_attribute(f"florence.latency.{self.label}_ms", round(self.elapsed_ms or 0.0, 2))
            span.set_attribute("florence.latency.budget_ms", self.budget_ms)
            span.set_attribute("florence.latency.within_budget", self.within_budget)
        except Exception:  # noqa: BLE001 - instrumentation must never break the path
            # Keep failure visible without logging labels, payloads, or exception text.
            log.warning("Latency span annotation failed; workflow execution is unchanged")
