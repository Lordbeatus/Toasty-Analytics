"""
Distributed Tracing with OpenTelemetry

Provides end-to-end tracing across microservices using OpenTelemetry.
Integrates with Jaeger, Zipkin, and other tracing backends.
"""

import logging
import os
from contextlib import contextmanager
from typing import Any, Optional

from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.zipkin.json import ZipkinExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.kafka import KafkaInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)


class TracingConfig:
    """Configuration for distributed tracing"""

    def __init__(
        self,
        service_name: str = "toastyanalytics",
        jaeger_host: str = "localhost",
        jaeger_port: int = 6831,
        zipkin_url: Optional[str] = None,
        enable_jaeger: bool = True,
        enable_zipkin: bool = False,
        sample_rate: float = 1.0,
    ):
        """
        Initialize tracing configuration.

        Args:
            service_name: Name of the service for tracing
            jaeger_host: Jaeger agent host
            jaeger_port: Jaeger agent port
            zipkin_url: Zipkin endpoint URL
            enable_jaeger: Whether to enable Jaeger exporter
            enable_zipkin: Whether to enable Zipkin exporter
            sample_rate: Sampling rate (0.0 to 1.0)
        """
        self.service_name = service_name
        self.jaeger_host = jaeger_host
        self.jaeger_port = jaeger_port
        self.zipkin_url = zipkin_url
        self.enable_jaeger = enable_jaeger
        self.enable_zipkin = enable_zipkin
        self.sample_rate = sample_rate


class DistributedTracer:
    """
    Manages distributed tracing setup and instrumentation.

    Features:
    - Automatic instrumentation of FastAPI, Redis, SQLAlchemy, Kafka
    - Support for Jaeger and Zipkin backends
    - Custom span creation and annotation
    - Trace context propagation
    """

    def __init__(self, config: TracingConfig):
        """
        Initialize distributed tracer.

        Args:
            config: Tracing configuration
        """
        self.config = config
        self.tracer_provider: Optional[TracerProvider] = None
        self.tracer: Optional[trace.Tracer] = None

    def setup(self) -> trace.Tracer:
        """
        Set up OpenTelemetry tracing.

        Returns:
            Configured tracer instance
        """
        # Create resource with service name
        resource = Resource.create({SERVICE_NAME: self.config.service_name})

        # Create tracer provider
        self.tracer_provider = TracerProvider(resource=resource)

        # Add exporters
        if self.config.enable_jaeger:
            self._add_jaeger_exporter()

        if self.config.enable_zipkin and self.config.zipkin_url:
            self._add_zipkin_exporter()

        # Set global tracer provider
        trace.set_tracer_provider(self.tracer_provider)

        # Get tracer
        self.tracer = trace.get_tracer(__name__)

        logger.info(
            f"Distributed tracing initialized for service: {self.config.service_name}"
        )

        return self.tracer

    def _add_jaeger_exporter(self):
        """Add Jaeger exporter to tracer provider"""
        try:
            jaeger_exporter = JaegerExporter(
                agent_host_name=self.config.jaeger_host,
                agent_port=self.config.jaeger_port,
            )

            span_processor = BatchSpanProcessor(jaeger_exporter)
            if self.tracer_provider:
                self.tracer_provider.add_span_processor(span_processor)

            logger.info(
                f"Jaeger exporter configured: {self.config.jaeger_host}:{self.config.jaeger_port}"
            )
        except Exception as e:
            logger.error(f"Failed to configure Jaeger exporter: {e}")

    def _add_zipkin_exporter(self):
        """Add Zipkin exporter to tracer provider"""
        try:
            zipkin_exporter = ZipkinExporter(endpoint=self.config.zipkin_url)

            span_processor = BatchSpanProcessor(zipkin_exporter)
            if self.tracer_provider:
                self.tracer_provider.add_span_processor(span_processor)

            logger.info(f"Zipkin exporter configured: {self.config.zipkin_url}")
        except Exception as e:
            logger.error(f"Failed to configure Zipkin exporter: {e}")

    def instrument_fastapi(self, app):
        """
        Instrument FastAPI application for automatic tracing.

        Args:
            app: FastAPI application instance
        """
        try:
            FastAPIInstrumentor.instrument_app(app)
            logger.info("FastAPI instrumented for tracing")
        except Exception as e:
            logger.error(f"Failed to instrument FastAPI: {e}")

    def instrument_all(self, app=None, engine=None):
        """
        Instrument all supported libraries.

        Args:
            app: Optional FastAPI application
            engine: Optional SQLAlchemy engine
        """
        try:
            # FastAPI
            if app:
                self.instrument_fastapi(app)

            # HTTP requests
            RequestsInstrumentor().instrument()
            logger.info("HTTP requests instrumented for tracing")

            # Redis
            RedisInstrumentor().instrument()
            logger.info("Redis instrumented for tracing")

            # SQLAlchemy
            if engine:
                SQLAlchemyInstrumentor().instrument(engine=engine)
                logger.info("SQLAlchemy instrumented for tracing")

            # Kafka (optional)
            try:
                KafkaInstrumentor().instrument()
                logger.info("Kafka instrumented for tracing")
            except Exception as e:
                logger.debug(f"Kafka instrumentation skipped: {e}")

        except Exception as e:
            logger.error(f"Failed to instrument libraries: {e}")

    @contextmanager
    def trace_span(self, name: str, attributes: Optional[dict] = None):
        """
        Context manager for creating custom trace spans.

        Usage:
            with tracer.trace_span("custom_operation", {"key": "value"}):
                # Your code here
                pass

        Args:
            name: Span name
            attributes: Optional span attributes
        """
        if not self.tracer:
            # Tracing not initialized, yield without tracing
            yield None
            return

        with self.tracer.start_as_current_span(name) as span:
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, str(value))

            yield span

    def add_span_event(self, name: str, attributes: Optional[dict] = None):
        """
        Add an event to the current span.

        Args:
            name: Event name
            attributes: Optional event attributes
        """
        span = trace.get_current_span()
        if span:
            span.add_event(name, attributes=attributes or {})

    def set_span_attribute(self, key: str, value: Any):
        """
        Set an attribute on the current span.

        Args:
            key: Attribute key
            value: Attribute value
        """
        span = trace.get_current_span()
        if span:
            span.set_attribute(key, str(value))

    def record_exception(self, exception: Exception):
        """
        Record an exception in the current span.

        Args:
            exception: Exception to record
        """
        span = trace.get_current_span()
        if span:
            span.record_exception(exception)


# Global tracer instance
_tracer: Optional[DistributedTracer] = None


def init_tracing(
    service_name: Optional[str] = None,
    jaeger_host: Optional[str] = None,
    jaeger_port: Optional[int] = None,
    zipkin_url: Optional[str] = None,
    enable_jaeger: bool = True,
    enable_zipkin: bool = False,
) -> DistributedTracer:
    """
    Initialize distributed tracing.

    Args:
        service_name: Service name (default from env)
        jaeger_host: Jaeger host (default from env)
        jaeger_port: Jaeger port (default from env)
        zipkin_url: Zipkin URL (default from env)
        enable_jaeger: Enable Jaeger
        enable_zipkin: Enable Zipkin

    Returns:
        Configured DistributedTracer instance
    """
    global _tracer

    # Get values from environment if not provided
    service_name = service_name or os.getenv("SERVICE_NAME", "toastyanalytics")
    jaeger_host = jaeger_host or os.getenv("JAEGER_HOST", "localhost")
    jaeger_port = jaeger_port or int(os.getenv("JAEGER_PORT", "6831"))
    zipkin_url = zipkin_url or os.getenv("ZIPKIN_URL", "")

    config = TracingConfig(
        service_name=service_name,
        jaeger_host=jaeger_host,
        jaeger_port=jaeger_port,
        zipkin_url=zipkin_url,
        enable_jaeger=enable_jaeger,
        enable_zipkin=enable_zipkin,
    )

    _tracer = DistributedTracer(config)
    _tracer.setup()

    return _tracer


def get_tracer() -> Optional[DistributedTracer]:
    """Get the global tracer instance"""
    return _tracer


# Decorator for automatic function tracing


def trace_function(name: Optional[str] = None, attributes: Optional[dict] = None):
    """
    Decorator for automatic function tracing.

    Usage:
        @trace_function("my_function", {"key": "value"})
        def my_function():
            pass

    Args:
        name: Span name (defaults to function name)
        attributes: Optional span attributes
    """

    def decorator(func):
        import functools

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            span_name = name or func.__name__

            if _tracer:
                with _tracer.trace_span(span_name, attributes):
                    return await func(*args, **kwargs)
            else:
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            span_name = name or func.__name__

            if _tracer:
                with _tracer.trace_span(span_name, attributes):
                    return func(*args, **kwargs)
            else:
                return func(*args, **kwargs)

        # Return appropriate wrapper based on function type
        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Example usage in FastAPI app:
"""
from fastapi import FastAPI
from src.tracing.opentelemetry_tracer import init_tracing

app = FastAPI()

# Initialize tracing
tracer = init_tracing(service_name="grading-service")

# Instrument FastAPI and other libraries
tracer.instrument_all(app=app, engine=db_engine)

# Use in endpoints
@app.get("/grade")
@trace_function("grade_code_endpoint")
async def grade_code():
    with tracer.trace_span("grading_logic"):
        result = perform_grading()
    return result
"""
