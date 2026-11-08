"""Opt-in HTTP telemetry with an explicit, bounded set of non-sensitive fields."""
from dataclasses import dataclass
from time import perf_counter
from urllib.parse import urlsplit

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import SpanKind, Status, StatusCode


@dataclass
class Telemetry:
    traces: TracerProvider
    metrics: MeterProvider

    def __post_init__(self):
        self.tracer = self.traces.get_tracer("aeris.http")
        meter = self.metrics.get_meter("aeris.http")
        self.requests = meter.create_counter("aeris.http.requests", unit="{request}",
                                             description="Completed Aeris API requests")
        self.duration = meter.create_histogram("aeris.http.duration", unit="ms",
                                               description="Aeris API response time")

    @classmethod
    def connect(cls, endpoint: str):
        """No global providers or auto-instrumentation; each app owns its lifecycle."""
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        url = urlsplit(endpoint)
        if (url.scheme not in {"http", "https"} or not url.hostname or url.username
                or url.password or url.query or url.fragment or url.path not in {"", "/"}):
            raise ValueError("AERIS_OTLP_ENDPOINT must be an HTTP(S) origin without credentials or a path.")
        origin = endpoint.rstrip("/")
        resource = Resource({"service.name": "aeris-api", "service.version": "0.1.0",
                             "deployment.environment.name": "local-observability"})
        # Explicit non-sensitive headers avoid inheriting OTLP authentication headers.
        options = {"headers": {"x-aeris-telemetry": "local-demo"}, "timeout": 2}
        traces = TracerProvider(resource=resource, shutdown_on_exit=False)
        traces.add_span_processor(BatchSpanProcessor(
            OTLPSpanExporter(endpoint=origin + "/v1/traces", **options),
            schedule_delay_millis=1000, max_queue_size=512, max_export_batch_size=128))
        reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=origin + "/v1/metrics", **options),
            export_interval_millis=5000, export_timeout_millis=2500)
        metrics = MeterProvider(resource=resource, metric_readers=[reader], shutdown_on_exit=False)
        return cls(traces, metrics)

    def shutdown(self):
        self.metrics.shutdown(timeout_millis=3000)
        self.traces.shutdown()


class HttpTelemetry:
    """Measure API requests, including rejected requests, without recording input.

    Only method, matched route template and status are exported. No headers,
    query strings, raw paths, IPs, bodies, SQL or exception text are collected.
    Health probes/static assets are excluded. Exporting happens in background SDK
    workers; a collector outage must not change the application's HTTP result.
    """

    def __init__(self, app, state):
        self.app = app
        self.state = state

    async def __call__(self, scope, receive, send):
        telemetry = getattr(self.state, "telemetry", None)
        if scope["type"] != "http" or not scope["path"].startswith("/api/") or telemetry is None:
            return await self.app(scope, receive, send)
        method = scope["method"] if scope["method"] in {
            "GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"} else "_OTHER"
        status = 500

        async def capture_status(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        start = perf_counter()
        with telemetry.tracer.start_as_current_span("HTTP " + method, kind=SpanKind.SERVER,
                                                    record_exception=False,
                                                    set_status_on_exception=False) as span:
            try:
                await self.app(scope, receive, capture_status)
            finally:
                route = getattr(scope.get("route"), "path", "/api/unmatched")
                attributes = {"http.request.method": method, "http.route": route,
                              "http.response.status_code": status}
                span.update_name(method + " " + route)
                span.set_attributes(attributes)
                if status >= 500:
                    span.set_status(Status(StatusCode.ERROR))
                telemetry.requests.add(1, attributes)
                telemetry.duration.record((perf_counter() - start) * 1000, attributes)
