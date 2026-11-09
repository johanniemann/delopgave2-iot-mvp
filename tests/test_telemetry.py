"""Real SDK collection: bounded attributes, privacy, errors and opt-in isolation."""
from fastapi import FastAPI
from fastapi.testclient import TestClient
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode
import pytest

from app.telemetry import HttpTelemetry, Telemetry


@pytest.fixture
def observed_app():
    spans = InMemorySpanExporter()
    reader = InMemoryMetricReader()
    traces = TracerProvider(shutdown_on_exit=False)
    traces.add_span_processor(SimpleSpanProcessor(spans))
    metrics = MeterProvider(metric_readers=[reader], shutdown_on_exit=False)
    telemetry = Telemetry(traces, metrics)
    app = FastAPI()
    app.state.telemetry = telemetry

    @app.get("/api/example/{item_id}")
    def example(item_id: str):
        return {"ok": True}

    @app.get("/api/failure")
    def failure():
        raise RuntimeError("sensitive-exception-text")

    @app.get("/health")
    def health():
        return {"ok": True}

    app.add_middleware(HttpTelemetry, state=app.state)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, app, spans, reader
    telemetry.shutdown()


def test_trace_and_metrics_use_templates_and_never_capture_input(observed_app):
    client, app, spans, reader = observed_app
    for item in ("private-one", "private-two"):
        assert client.get("/api/example/" + item + "?secret=private-query",
                          headers={"Authorization": "Bearer private-token", "Cookie": "private-cookie"}).status_code == 200
    finished = spans.get_finished_spans()
    assert len(finished) == 2
    assert {span.name for span in finished} == {"GET /api/example/{item_id}"}
    expected = {"http.request.method": "GET", "http.route": "/api/example/{item_id}",
                "http.response.status_code": 200}
    assert all(dict(span.attributes) == expected and not span.events for span in finished)
    data = reader.get_metrics_data()
    measures = {metric.name: metric for resource in data.resource_metrics
                for scope in resource.scope_metrics for metric in scope.metrics}
    count = measures["aeris.http.requests"].data.data_points
    duration = measures["aeris.http.duration"].data.data_points
    assert len(count) == 1 and count[0].value == 2
    assert dict(count[0].attributes) == expected
    assert duration[0].count == 2 and duration[0].sum > 0
    assert "private-" not in str(data) + str([dict(span.attributes) for span in finished])


def test_unknown_urls_are_collapsed_and_health_is_excluded(observed_app):
    client, app, spans, reader = observed_app
    assert client.get("/api/private-missing-one").status_code == 404
    assert client.get("/api/private-missing-two").status_code == 404
    assert client.get("/health").status_code == 200
    assert [s.name for s in spans.get_finished_spans()] == ["GET /api/unmatched"] * 2


def test_unhandled_failure_is_recorded_without_exception_details(observed_app):
    client, app, spans, reader = observed_app
    assert client.get("/api/failure").status_code == 500
    span, = spans.get_finished_spans()
    assert span.status.status_code == StatusCode.ERROR
    assert span.attributes["http.response.status_code"] == 500
    assert span.events == () and span.status.description is None


def test_disabled_instrumentation_leaves_requests_working(observed_app):
    client, app, spans, reader = observed_app
    app.state.telemetry = None
    assert client.get("/api/example/anything").status_code == 200
    assert not spans.get_finished_spans()


@pytest.mark.parametrize("endpoint", ["file:///tmp/telemetry", "http://user:password@localhost",
                                      "http://localhost/v1/traces", "http://localhost?secret=value"])
def test_endpoint_refuses_credentials_paths_and_non_http_schemes(endpoint):
    with pytest.raises(ValueError, match="AERIS_OTLP_ENDPOINT"):
        Telemetry.connect(endpoint)


def test_real_login_never_exports_password_cookie_or_csrf(client, observed_app):
    _, sample, spans, reader = observed_app
    client.app.state.telemetry = sample.state.telemetry
    try:
        caller = TestClient(client.app)
        response = caller.post("/api/auth/login?private=do-not-export", json={
            "username": "technician", "password": client.test_password})
        assert response.status_code == 200
        session = response.json()
        caller.post("/api/auth/logout", json={}, headers={"X-CSRF-Token": session["csrf_token"]})
        cookie = response.cookies.get("aeris-local-session")
        finished = spans.get_finished_spans()
        assert any(s.attributes.get("http.route") == "/api/auth/login" for s in finished)
        evidence = str(reader.get_metrics_data()) + str([(s.name, dict(s.attributes), s.events) for s in finished])
        assert all(secret not in evidence for secret in (client.test_password, session["csrf_token"], cookie, "do-not-export"))
    finally:
        client.app.state.telemetry = None
