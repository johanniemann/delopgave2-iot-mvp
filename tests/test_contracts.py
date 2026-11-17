"""Generated contracts must describe the real persisted HTTP representation."""
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi.encoders import jsonable_encoder

from app.responses import (
    AssessmentReceipt, CaseReceipt, ErrorResponse, ForecastReceipt, HealthResponse,
    OutcomeReceipt, OverviewResponse, ReadingReceipt, ReviewReceipt,
    ScenarioCreatedReceipt, ScenarioDetailResponse,
)


SUCCESS_CONTRACTS = [
    ("/health", "get", "200", HealthResponse),
    ("/api/overview", "get", "200", OverviewResponse),
    ("/api/scenarios/{scenario_id}", "get", "200", ScenarioDetailResponse),
    ("/api/cases/{case_id}", "get", "200", ScenarioDetailResponse),
    ("/api/scenarios", "post", "201", ScenarioCreatedReceipt),
    ("/api/scenarios/{scenario_id}/readings", "post", "201", ReadingReceipt),
    ("/api/scenarios/{scenario_id}/assess", "post", "200", AssessmentReceipt),
    ("/api/scenarios/{scenario_id}/forecast", "post", "200", ForecastReceipt),
    ("/api/scenarios/{scenario_id}/review", "put", "200", ReviewReceipt),
    ("/api/scenarios/{scenario_id}/case", "post", "201", CaseReceipt),
    ("/api/cases/{case_id}/outcomes", "post", "200", OutcomeReceipt),
]


def validate_response(response, status, model):
    assert response.status_code == status, response.text
    body = response.json()
    # This also catches changed timestamp notation, absent-vs-null changes and
    # silently dropped stored fields, not just successful Pydantic parsing.
    assert model.model_validate(body).model_dump(mode="json", exclude_unset=True) == body
    return body


def test_openapi_describes_domain_successes_and_safe_errors(client):
    spec = client.get("/openapi.json").json()
    for path, method, status, model in SUCCESS_CONTRACTS:
        operation = spec["paths"][path][method]
        schema = operation["responses"][status]["content"]["application/json"]["schema"]
        assert schema == {"$ref": f"#/components/schemas/{model.__name__}"}
        # Override FastAPI's default body-echoing HTTPValidationError schema.
        if path.startswith("/api/"):
            validation = operation["responses"]["422"]["content"]["application/json"]["schema"]
            assert validation == {"$ref": "#/components/schemas/ErrorResponse"}
    health_failure = spec["paths"]["/health"]["get"]["responses"]["503"]
    assert health_failure["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ErrorResponse"
    }
    created = spec["components"]["schemas"]["ScenarioCreatedReceipt"]
    assert set(created["properties"]) == {"scenario_id", "version"}
    assert created["additionalProperties"] is False
    scenario = spec["components"]["schemas"]["Scenario"]
    assert scenario["properties"]["created_at"]["format"] == "date-time"
    for path, operations in spec["paths"].items():
        for method, operation in operations.items():
            if path.startswith("/api/") and method in {"post", "put", "patch", "delete"}:
                csrf = [p for p in operation.get("parameters", []) if p["name"] == "X-CSRF-Token"]
                assert bool(csrf) == (path != "/api/auth/login")
                if csrf:
                    assert csrf[0]["in"] == "header" and csrf[0]["required"] is True


def test_typed_http_responses_preserve_complete_stored_evidence(client):
    validate_response(client.get("/health"), 200, HealthResponse)
    empty_overview = validate_response(client.get("/api/overview"), 200, OverviewResponse)
    assert empty_overview["active_scenario_id"] is None
    assert empty_overview["cases"] == []
    created = validate_response(client.post("/api/scenarios", json={
        "request_id": str(uuid4()), "kind": "empty", "prepare": False,
    }), 201, ScenarioCreatedReceipt)
    assert set(created) == {"scenario_id", "version"}
    sid, version = created["scenario_id"], created["version"]
    initial = validate_response(client.get(f"/api/scenarios/{sid}"), 200, ScenarioDetailResponse)
    assert initial["incident"] is None and initial["forecast"] is None and initial["case"] is None

    def mutate(path, model, status=200, method="post", **fields):
        nonlocal version
        payload = {"request_id": str(uuid4()), "expected_version": version, **fields}
        response = getattr(client, method)(path, json=payload)
        receipt = validate_response(response, status, model)
        assert receipt["scenario_id"] == sid
        assert receipt["version"] == version + 1
        # An identical retry retains the exact operation-specific fields/version.
        assert getattr(client, method)(path, json=payload).json() == receipt
        version = receipt["version"]
        return receipt

    reading = mutate(f"/api/scenarios/{sid}/readings", ReadingReceipt, 201,
                     measured_at=datetime.now(timezone.utc).isoformat(), value=28.1)
    assert set(reading) == {"scenario_id", "version", "reading_id", "quality"}
    assessment = mutate(f"/api/scenarios/{sid}/assess", AssessmentReceipt)
    assert assessment["incident_id"]
    forecast = mutate(f"/api/scenarios/{sid}/forecast", ForecastReceipt)
    assert set(forecast) == {"scenario_id", "version", "forecast_id"}
    mutate(f"/api/scenarios/{sid}/review", ReviewReceipt, method="put",
           note="Reviewed this synthetic contract example.", decisions=[
               {"risk_id": "yaw-drive", "decision": "Accepted"},
               {"risk_id": "pitch-actuator", "decision": "Rejected"},
           ])
    case = mutate(f"/api/scenarios/{sid}/case", CaseReceipt, 201)
    case_id = case["case_id"]
    mutate(f"/api/cases/{case_id}/outcomes", OutcomeReceipt, simulated=True,
           external_reference="DEMO-CONTRACT-" + str(uuid4()), all_work_complete=True,
           verification="Passed", evidence_reference="DEMO-CONTRACT-EVIDENCE",
           note="Simulated outcome for the persisted response contract.")

    service = client.app.state.maintenance
    expected_detail = jsonable_encoder(service.detail(UUID(sid)))
    stored = validate_response(client.get(f"/api/scenarios/{sid}"), 200, ScenarioDetailResponse)
    assert stored == expected_detail
    assert validate_response(client.get(f"/api/cases/{case_id}"), 200, ScenarioDetailResponse) == expected_detail
    assert stored["forecast"]["review"]["reviewer_id"]
    assert stored["case"]["status"] == "Resolved"
    assert stored["outcomes"][0]["simulated"] is True
    assert validate_response(client.get("/api/overview"), 200, OverviewResponse) == jsonable_encoder(service.overview())


def test_safe_error_contract_preserves_validation_fields_and_ordinary_absence(client):
    unknown = validate_response(client.get(f"/api/scenarios/{uuid4()}"), 404, ErrorResponse)
    assert set(unknown["error"]) == {"code", "message"}
    invalid = validate_response(client.post("/api/scenarios", json={
        "request_id": str(uuid4()), "kind": "unsupported", "unexpected": "private test input",
    }), 422, ErrorResponse)
    assert invalid["error"]["code"] == "INVALID_INPUT"
    assert {field["field"] for field in invalid["error"]["fields"]} == {"body.kind", "body.unexpected"}
    assert "private test input" not in str(invalid)

    created = validate_response(client.post("/api/scenarios", json={
        "request_id": str(uuid4()), "kind": "empty", "prepare": False,
    }), 201, ScenarioCreatedReceipt)
    blocked = validate_response(client.post(f"/api/scenarios/{created['scenario_id']}/assess", json={
        "request_id": str(uuid4()), "expected_version": created["version"],
    }), 409, ErrorResponse)
    assert blocked["error"]["code"] == "USABLE_DATA_REQUIRED"
    assert set(blocked["error"]) == {"code", "message"}

    # Assessing a usable value at the boundary completes with an explicit null
    # incident, while unrelated receipt fields remain absent.
    sid = created["scenario_id"]
    reading = validate_response(client.post(f"/api/scenarios/{sid}/readings", json={
        "request_id": str(uuid4()), "expected_version": created["version"],
        "measured_at": datetime.now(timezone.utc).isoformat(), "value": 28.0,
    }), 201, ReadingReceipt)
    assessed = validate_response(client.post(f"/api/scenarios/{sid}/assess", json={
        "request_id": str(uuid4()), "expected_version": reading["version"],
    }), 200, AssessmentReceipt)
    assert assessed["incident_id"] is None
    assert set(assessed) == {"scenario_id", "version", "incident_id"}
