from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import os
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.main import Settings, create_app


def new_window(client, kind="fault", prepare=True, **extra):
    response = client.post("/api/scenarios", json={"request_id":str(uuid4()), "kind":kind, "prepare":prepare, **extra})
    assert response.status_code == 201, response.text
    return response.json()["scenario_id"]


def detail(client, sid):
    response = client.get(f"/api/scenarios/{sid}")
    assert response.status_code == 200, response.text
    return response.json()


def command(client, sid, **extra):
    return {"request_id":str(uuid4()), "expected_version":detail(client,sid)["scenario"]["version"], **extra}


def review(client, sid, accepted=True, **extra):
    return client.put(f"/api/scenarios/{sid}/review", json=command(client,sid,
        reviewer="Demo specialist", note="Reviewed synthetic evidence for this test.",
        decisions=[{"risk_id":"yaw-drive", "decision":"Accepted" if accepted else "Rejected"},
                   {"risk_id":"pitch-actuator", "decision":"Rejected"}], **extra))


def make_case(client, sid):
    response = client.post(f"/api/scenarios/{sid}/case", json=command(client,sid))
    assert response.status_code == 201, response.text
    return response.json()["case_id"]


def outcome(client, sid, case_id, complete=True, passed=True, **extra):
    payload = command(client,sid, simulated=True, external_reference="DEMO-"+str(uuid4()), all_work_complete=complete,
                      verification="Passed" if passed else "Failed", evidence_reference="DEMO-TEST-EVIDENCE",
                      note="A simulated external maintenance outcome, not a real verification.")
    payload.update(extra)
    return client.post(f"/api/cases/{case_id}/outcomes", json=payload)


def test_health_and_actual_database(client):
    assert client.get("/health").json()["database"] == "connected"
    assert client.get("/api/overview").json()["metrics"]["total_readings"] == 0


def test_full_persisted_workflow_and_request_retry(client):
    sid = new_window(client)
    data = detail(client,sid)
    assert len(data["readings"]) == 96
    assert data["incident"] and data["forecast"]["review_status"] == "Pending"
    assert data["case"] is None
    blocked = client.post(f"/api/scenarios/{sid}/case", json=command(client,sid))
    assert blocked.status_code == 409 and blocked.json()["error"]["code"] == "REVIEW_REQUIRED"
    assert review(client,sid).status_code == 200
    payload = command(client,sid)
    first = client.post(f"/api/scenarios/{sid}/case",json=payload)
    assert first.status_code == 201
    case_id = first.json()["case_id"]
    assert client.post(f"/api/scenarios/{sid}/case",json=payload).json() == first.json()
    case = client.get(f"/api/cases/{case_id}").json()["case"]
    assert case["status"] == "Open" and len(case["accepted_risks"]) == 1
    assert outcome(client,sid,case_id).json()["status"] == "Resolved"
    stored = detail(client,sid)
    assert stored["case"]["resolved_at"]
    assert stored["outcomes"][0]["simulated"] is True
    assert [e["name"] for e in stored["events"]].count("Predictive Case Resolved") == 1


def test_all_risks_can_be_rejected_and_case_still_created(client):
    sid = new_window(client)
    assert review(client,sid,accepted=False).status_code == 200
    make_case(client,sid)
    assert detail(client,sid)["case"]["accepted_risks"] == []


def test_reviewed_forecast_without_a_fault_cannot_create_case(client):
    sid = new_window(client,"normal")
    assert review(client,sid).status_code == 200
    result = client.post(f"/api/scenarios/{sid}/case",json=command(client,sid))
    assert result.status_code == 409 and result.json()["error"]["code"] == "INCIDENT_REQUIRED"


def test_invalid_readings_persist_but_are_not_analysed(client):
    sid = new_window(client,"invalid")
    data = detail(client,sid)
    assert len(data["readings"]) == 96
    assert all(r["quality"] == "Invalid" for r in data["readings"])
    assert data["incident"] is None and data["forecast"] is None
    assert client.post(f"/api/scenarios/{sid}/forecast",json=command(client,sid)).status_code == 409


@pytest.mark.parametrize("paths", [("forecast","assess"),("assess","forecast")])
def test_assessment_paths_work_in_either_order(client, paths):
    sid = new_window(client,prepare=False)
    for path in paths:
        assert client.post(f"/api/scenarios/{sid}/{path}",json=command(client,sid)).status_code == 200
    assert review(client,sid).status_code == 200
    make_case(client,sid)


def test_manual_ingestion_classifies_invalid_values_and_keeps_evidence(client):
    sid = new_window(client,"empty",prepare=False)
    for value,quality in [(None,"Invalid"),(-1,"Invalid"),(100.1,"Invalid"),(28.1,"Usable")]:
        payload = command(client,sid,measured_at=datetime.now(timezone.utc).isoformat(),value=value)
        result = client.post(f"/api/scenarios/{sid}/readings",json=payload)
        assert result.status_code == 201 and result.json()["quality"] == quality
    assert client.post(f"/api/scenarios/{sid}/assess",json=command(client,sid)).status_code == 200
    data = detail(client,sid)
    assert len(data["readings"]) == 4 and data["incident"]["peak"] == 28.1
    assert len(data["incident"]["evidence"]) == 1
    frozen = client.post(f"/api/scenarios/{sid}/readings",json=command(client,sid,measured_at=datetime.now(timezone.utc).isoformat(),value=20))
    assert frozen.status_code == 409


@pytest.mark.parametrize("complete,passed",[(False,True),(True,False),(False,False)])
def test_unsuccessful_maintenance_outcome_does_not_resolve_case(client,complete,passed):
    sid = new_window(client)
    review(client,sid)
    case_id = make_case(client,sid)
    result = outcome(client,sid,case_id,complete,passed)
    assert result.status_code == 200 and result.json()["status"] == "Open"
    data = detail(client,sid)
    assert data["case"]["resolved_at"] is None
    assert not any(e["name"] == "Predictive Case Resolved" for e in data["events"])


def test_outcome_replay_is_deduplicated_by_request_and_external_reference(client):
    sid = new_window(client)
    review(client,sid)
    case_id = make_case(client,sid)
    request_id = str(uuid4())
    version = detail(client,sid)["scenario"]["version"]
    result = outcome(client,sid,case_id,request_id=request_id,expected_version=version,external_reference="DEMO-SAME")
    replay = outcome(client,sid,case_id,request_id=request_id,expected_version=version,external_reference="DEMO-SAME")
    assert replay.json() == result.json()
    assert outcome(client,sid,case_id,external_reference="DEMO-SAME").status_code == 200
    assert outcome(client,sid,case_id,external_reference="DEMO-SAME",note="Different content.").status_code == 409
    data = detail(client,sid)
    assert len(data["outcomes"]) == 1
    assert [e["name"] for e in data["events"]].count("Predictive Case Resolved") == 1
    assert outcome(client,sid,case_id).status_code == 409


def test_stale_reviews_and_modifying_case_evidence_are_blocked(client):
    sid = new_window(client)
    stale = command(client,sid)
    assert review(client,sid).status_code == 200
    response = client.post(f"/api/scenarios/{sid}/case",json=stale)
    assert response.status_code == 409 and response.json()["error"]["code"] == "STALE_VERSION"
    make_case(client,sid)
    assert review(client,sid).status_code == 409


def test_concurrent_case_commands_create_one_case(client):
    sid = new_window(client)
    review(client,sid)
    version = detail(client,sid)["scenario"]["version"]
    def submit(_):
        return client.post(f"/api/scenarios/{sid}/case",json={"request_id":str(uuid4()),"expected_version":version}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit,range(2)))
    assert sorted(results) == [201,409]
    assert len(client.get("/api/overview").json()["cases"]) == 1


def test_concurrent_creation_retry_is_idempotent(client):
    payload = {"request_id":str(uuid4()),"kind":"normal"}
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: client.post("/api/scenarios",json=payload),range(2)))
    assert [r.status_code for r in results] == [201,201]
    assert results[0].json() == results[1].json()
    assert len(client.get("/api/overview").json()["scenarios"]) == 1


def test_request_id_reuse_with_different_content_is_rejected(client):
    payload = {"request_id":str(uuid4()),"kind":"normal"}
    client.post("/api/scenarios",json=payload)
    assert client.post("/api/scenarios",json=payload|{"kind":"fault"}).status_code == 409
    assert len(client.get("/api/overview").json()["scenarios"]) == 1


def test_persistence_survives_a_new_application_instance(client):
    sid = new_window(client)
    review(client,sid)
    make_case(client,sid)
    app = create_app(Settings(database_url=os.environ["DATABASE_URL"],seed_demo=False))
    with TestClient(app) as other:
        other.cookies.update(client.cookies)
        saved = detail(other,sid)
        assert saved["case"]["status"] == "Open" and saved["forecast"]["review_status"] == "Reviewed"
        assert len(saved["readings"]) == 96


def test_seed_history_is_explicit_and_startup_does_not_duplicate_it(client):
    service = client.app.state.maintenance
    service.seed()
    service.seed()
    overview = client.get("/api/overview").json()
    assert len(overview["scenarios"]) == 3 and len(overview["cases"]) == 2
    assert all(s["source"] == "Seeded demo history" for s in overview["scenarios"])
    assert overview["metrics"]["pending_reviews"] == 1


def test_validation_rejects_unknown_fields_unsupported_units_and_naive_time(client):
    assert client.post("/api/scenarios",json={"request_id":str(uuid4()),"kind":"other"}).status_code == 422
    assert client.post("/api/scenarios",json={"request_id":str(uuid4()),"admin":True}).status_code == 422
    sid = new_window(client,"empty",prepare=False)
    for extra in ({"unit":"km/h"},{"measured_at":"2026-11-06T12:00:00"}):
        payload = command(client,sid,measured_at=datetime.now(timezone.utc).isoformat(),value=20)
        response = client.post(f"/api/scenarios/{sid}/readings",json=payload|extra)
        assert response.status_code == 422
        assert "input" not in response.text


def test_duplicate_risk_decisions_are_invalid(client):
    sid = new_window(client)
    response = client.put(f"/api/scenarios/{sid}/review",json=command(client,sid,reviewer="Demo",note="A sample review.",
        decisions=[{"risk_id":"yaw-drive","decision":"Accepted"}]*2))
    assert response.status_code == 422
    assert detail(client,sid)["forecast"]["review_status"] == "Pending"


def test_queries_store_free_text_as_data(client):
    sid = new_window(client)
    note = "<img src=x onerror=alert(1)> '; DROP TABLE aeris.cases; --"
    result = client.put(f"/api/scenarios/{sid}/review",json=command(client,sid,reviewer="Demo specialist",note=note,
        decisions=[{"risk_id":"yaw-drive","decision":"Accepted"},{"risk_id":"pitch-actuator","decision":"Rejected"}]))
    assert result.status_code == 200
    assert detail(client,sid)["forecast"]["review"]["note"] == note
    make_case(client,sid)


def test_json_size_origin_and_host_guards(client):
    url = "/api/scenarios"
    assert client.post(url,content="x",headers={"content-type":"text/plain"}).status_code == 415
    assert client.post(url,json={"request_id":str(uuid4())},headers={"Origin":"https://another.example"}).status_code == 403
    assert client.post(url,content='"'+"x"*17000+'"',headers={"content-type":"application/json"}).status_code == 413
    assert client.get("/api/overview",headers={"Host":"attacker.example"}).status_code == 400
    assert "frame-ancestors 'none'" in client.get("/").headers["content-security-policy"]


def test_write_rate_limit_returns_retry_after(client):
    for _ in range(60):
        client.post("/api/scenarios",json={})
    result = client.post("/api/scenarios",json={})
    assert result.status_code == 429 and result.headers["Retry-After"] == "60"


def test_shared_mode_requires_individual_login_and_https_origin(client):
    with pytest.raises(ValueError):
        Settings(database_url=os.environ["DATABASE_URL"],mode="shared")
    settings = Settings(database_url=os.environ["DATABASE_URL"],mode="shared",
                        public_origin="https://demo.example",allowed_hosts=("demo.example",),seed_demo=False)
    with TestClient(create_app(settings),base_url="https://demo.example") as shared:
        assert shared.get("/api/overview").status_code == 401
        assert shared.get("/api/overview",headers={"Authorization":"Bearer " + "x"*40}).status_code == 401
        login = shared.post("/api/auth/login",json={"username":"technician","password":client.test_password})
        assert login.status_code == 200
        cookie = login.headers["set-cookie"]
        assert "__Host-aeris-session=" in cookie and "Secure" in cookie and "HttpOnly" in cookie and "SameSite=strict" in cookie
        assert shared.get("/api/overview").status_code == 200
        assert shared.get("/health").status_code == 200


def test_missing_records_are_safe_errors(client):
    assert client.get(f"/api/scenarios/{uuid4()}").status_code == 404
    assert client.get("/api/cases/missing").status_code == 404


@pytest.mark.parametrize("kind",["invalid","empty"])
def test_no_usable_data_does_not_claim_a_completed_fault_assessment(client,kind):
    sid = new_window(client,kind)
    result = client.post(f"/api/scenarios/{sid}/assess",json=command(client,sid))
    assert result.status_code == 409 and result.json()["error"]["code"] == "USABLE_DATA_REQUIRED"
    assert detail(client,sid)["scenario"]["fault_assessed_at"] is None


def test_unusable_window_can_receive_a_good_reading_before_analysis(client):
    sid = new_window(client,"invalid")
    result = client.post(f"/api/scenarios/{sid}/readings",json=command(client,sid,measured_at=datetime.now(timezone.utc).isoformat(),value=28.1))
    assert result.status_code == 201
    assert client.post(f"/api/scenarios/{sid}/assess",json=command(client,sid)).status_code == 200
    data = detail(client,sid)
    assert len(data["readings"]) == 97 and len(data["incident"]["evidence"]) == 1


def test_database_failure_returns_a_safe_message(client,monkeypatch):
    from psycopg_pool import PoolTimeout
    def unavailable(*args,**kwargs):
        raise PoolTimeout("This internal diagnostic must never appear in the HTTP response.")
    monkeypatch.setattr(client.app.state.maintenance.pool,"connection",unavailable)
    response = client.get("/api/overview")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DATABASE_UNAVAILABLE"
    assert "internal diagnostic" not in response.text
