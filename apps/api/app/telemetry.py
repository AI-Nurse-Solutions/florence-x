"""OpenTelemetry SDK wiring for the API (P1-10).

`setup_telemetry()` installs a TracerProvider that exports the spans emitted by
the runtime loop (florence_core.observability) to an OTLP collector. It is a safe
no-op when the SDK/exporter is not installed or no endpoint is configured, so the
API still boots in minimal environments.

Enable by setting OTEL_EXPORTER_OTLP_ENDPOINT (standard OTel env var), e.g.
`OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318`. Set FLORENCE_OTEL_CONSOLE=1
to additionally print spans to stdout for local debugging.
"""
from __future__ import annotations

import os

_CONFIGURED = False


def setup_telemetry(service_name: str = "florence-x") -> bool:
    """Configure the global TracerProvider once. Returns True if tracing is active."""
    global _CONFIGURED
    if _CONFIGURED:
        return True

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    console = os.getenv("FLORENCE_OTEL_CONSOLE", "").lower() in {"1", "true", "yes"}
    if not endpoint and not console:
        return False  # nothing to export to; leave the no-op tracer in place.

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    except ImportError:
        return False  # SDK not installed; runtime spans stay no-ops.

    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    if endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    if console:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    _CONFIGURED = True
    return True
