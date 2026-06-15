"""Thin OpenTelemetry wrapper with a graceful no-op fallback.

`span(name, **attrs)` is a context manager that starts a span when OTel is
available and yields it (or None when it is not). Span *duration* is recorded
automatically by OTel, which is how per-step latency is captured (P1-10).
"""
from __future__ import annotations

from contextlib import contextmanager
from enum import Enum

try:  # opentelemetry-api only; the SDK/exporter is configured by the app.
    from opentelemetry import trace as _otel_trace

    HAVE_OTEL = True
except ImportError:  # pragma: no cover - exercised in dependency-free envs
    _otel_trace = None
    HAVE_OTEL = False

_TRACER_NAME = "florence-x"


def get_tracer(name: str = _TRACER_NAME):
    """Return an OTel tracer, or None when OpenTelemetry is not installed."""
    return _otel_trace.get_tracer(name) if HAVE_OTEL else None


def _coerce(value):
    """OTel attributes accept str/bool/int/float; coerce enums and other types."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (str, bool, int, float)):
        return value
    return str(value)


def set_attributes(sp, **attributes) -> None:
    """Set span attributes, skipping Nones. Safe when sp is None (no-op mode)."""
    if sp is None:
        return
    for key, value in attributes.items():
        if value is not None:
            sp.set_attribute(key, _coerce(value))


@contextmanager
def span(name: str, **attributes):
    """Start a span named `name` with the given attributes; yields the span (or
    None when OpenTelemetry is unavailable)."""
    if not HAVE_OTEL:
        yield None
        return
    tracer = _otel_trace.get_tracer(_TRACER_NAME)
    with tracer.start_as_current_span(name) as sp:
        set_attributes(sp, **attributes)
        yield sp
