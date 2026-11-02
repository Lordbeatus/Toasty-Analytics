"""Tracing module initialization"""

from .opentelemetry_tracer import (
    DistributedTracer,
    TracingConfig,
    get_tracer,
    init_tracing,
    trace_function,
)

__all__ = [
    "init_tracing",
    "get_tracer",
    "trace_function",
    "DistributedTracer",
    "TracingConfig",
]
