"""Shared OpenTelemetry tracing configuration. Call setup_tracing(name)
once, from an entrypoint's __main__ block, before creating spans.
"""

import atexit
import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

OTLP_ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")


def setup_tracing(service_name):
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    exporter = OTLPSpanExporter(endpoint=f"{OTLP_ENDPOINT}/v1/traces")
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    atexit.register(provider.shutdown)


LLM_PRICING_PER_MTOK = {
    # USD per million tokens. Source: each provider's own pricing page,
    # checked at implementation time (2026-08) -- not guaranteed to stay
    # current, especially gemini-flash-latest since it's a Google-managed
    # alias that can silently repoint to a different underlying model.
    "claude-sonnet-5": {"input": 2.0, "output": 10.0},
    "gemini-flash-latest": {"input": 1.50, "output": 7.50},
}


def _annotate_cost(span):
    attrs = span.attributes
    model = attrs.get("gen_ai.request.model")
    pricing = LLM_PRICING_PER_MTOK.get(model)
    if not pricing or "gen_ai.usage.input_tokens" not in attrs:
        return
    input_tokens = attrs["gen_ai.usage.input_tokens"]
    output_tokens = attrs.get("gen_ai.usage.output_tokens", 0)
    cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000
    span._attributes["gen_ai.usage.cost_usd"] = round(cost, 6)


def setup_llm_tracing(app_name):
    from traceloop.sdk import Traceloop

    Traceloop.init(
        app_name=app_name,
        api_endpoint=OTLP_ENDPOINT,
        disable_batch=True,
        span_postprocess_callback=_annotate_cost,
    )
