"""Transactional application operations. SQL stays parameterized; rules stay in domain."""
from datetime import datetime, timedelta, timezone
import math
from uuid import UUID, NAMESPACE_URL, uuid4, uuid5

from psycopg.types.json import Jsonb
from psycopg import sql

from .domain import (DEMO_THRESHOLD, MODEL_VERSION, DomainError, current_fault,
                     require_case_gate, resolves_case, simulated_risks)


def utc_now():
    return datetime.now(timezone.utc)


def readable_id(prefix, scenario):
    return f"{prefix}-{str(scenario['id']).replace('-', '')[:12].upper()}"


class Maintenance:
    def __init__(self, pool, clock=utc_now):
        self.pool = pool
        self.clock = clock

    def _event(self, conn, scenario_id, name, payload):
        conn.execute("INSERT INTO aeris.events(id,scenario_id,name,occurred_at,payload) VALUES (%s,%s,%s,%s,%s)",
                     (uuid4(), scenario_id, name, self.clock(), Jsonb(payload)))

    def _receipt(self, conn, operation, payload):
        # A global request lock also protects two concurrent retries creating a window.
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (payload["request_id"],))
        row = conn.execute("SELECT * FROM aeris.commands WHERE request_id=%s", (payload["request_id"],)).fetchone()
        if row:
            if row["operation"] != operation or row["payload"] != payload:
                raise DomainError("REQUEST_ID_REUSED", "This request ID was already used for different content.")
            return row["result"]
        return None

    def _save_receipt(self, conn, operation, payload, result):
        conn.execute("INSERT INTO aeris.commands(request_id,scenario_id,operation,payload,result) VALUES (%s,%s,%s,%s,%s)",
                     (payload["request_id"], result["scenario_id"], operation, Jsonb(payload), Jsonb(result)))

    def _perform(self, scenario_id, operation, command, action):
        payload = command.model_dump(mode="json") | {"scenario_id": str(scenario_id)}
        with self.pool.connection() as conn:
            cached = self._receipt(conn, operation, payload)
            if cached:
                return cached
            scenario = conn.execute("SELECT * FROM aeris.scenarios WHERE id=%s FOR UPDATE", (scenario_id,)).fetchone()
            if not scenario:
                raise DomainError("NOT_FOUND", "This analysis window does not exist.", 404)
            if scenario["version"] != command.expected_version:
                raise DomainError("STALE_VERSION", "This record has changed. Refresh it before trying again.")
            result = action(conn, scenario)
            version = conn.execute("UPDATE aeris.scenarios SET version=version+1 WHERE id=%s RETURNING version", (scenario_id,)).fetchone()["version"]
            result |= {"scenario_id": str(scenario_id), "version": version}
            self._save_receipt(conn, operation, payload, result)
            return result

    def _readings(self, conn, scenario_id):
        return conn.execute("SELECT * FROM aeris.readings WHERE scenario_id=%s ORDER BY measured_at,id", (scenario_id,)).fetchall()

    def _assess(self, conn, scenario):
        previous = conn.execute("SELECT * FROM aeris.incidents WHERE scenario_id=%s", (scenario["id"],)).fetchone()
        if previous:
            return {"incident_id": previous["id"]}
        readings = self._readings(conn, scenario["id"])
        if not any(r["quality"] == "Usable" for r in readings):
            raise DomainError("USABLE_DATA_REQUIRED", "Current-fault assessment needs at least one usable reading.")
        fault = current_fault(readings)
        incident_id = None
        if fault:
            incident_id = readable_id("INC", scenario)
            conn.execute("""INSERT INTO aeris.incidents(id,scenario_id,detected_at,peak,threshold,code,summary,evidence)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                         (incident_id, scenario["id"], self.clock(), fault["peak"], fault["threshold"],
                          fault["code"], fault["summary"], Jsonb(fault["evidence"])))
            self._event(conn, scenario["id"], "Fault Incident Opened", {"incident_id": incident_id, "peak": fault["peak"]})
        elif not scenario["fault_assessed_at"]:
            self._event(conn, scenario["id"], "Current Faults Assessed", {"fault_detected": False})
        conn.execute("UPDATE aeris.scenarios SET fault_assessed_at=%s WHERE id=%s", (self.clock(), scenario["id"]))
        return {"incident_id": incident_id}

    def _forecast(self, conn, scenario):
        previous = conn.execute("SELECT id FROM aeris.forecasts WHERE scenario_id=%s", (scenario["id"],)).fetchone()
        if previous:
            return {"forecast_id": previous["id"]}
        evidence = [str(r["id"]) for r in self._readings(conn, scenario["id"]) if r["quality"] == "Usable"]
        if not evidence:
            raise DomainError("USABLE_DATA_REQUIRED", "A simulated forecast needs at least one usable reading.")
        forecast_id = readable_id("FC", scenario)
        conn.execute("""INSERT INTO aeris.forecasts(id,scenario_id,generated_at,model_version,risks,source_reading_ids)
                        VALUES (%s,%s,%s,%s,%s,%s)""",
                     (forecast_id, scenario["id"], self.clock(), MODEL_VERSION, Jsonb(simulated_risks()), Jsonb(evidence)))
        self._event(conn, scenario["id"], "Failure Forecast Generated", {"forecast_id": forecast_id, "simulated": True, "model_version": MODEL_VERSION})
        return {"forecast_id": forecast_id}

    def create_scenario(self, command, source="Interactive demo"):
        payload = command.model_dump(mode="json")
        with self.pool.connection() as conn:
            cached = self._receipt(conn, "create", payload)
            if cached:
                return cached
            scenario_id = uuid4()
            titles = {"fault": "High-wind event", "normal": "Normal operation", "invalid": "Unusable telemetry", "empty": "Custom analysis window"}
            now = self.clock()
            scenario = conn.execute("""INSERT INTO aeris.scenarios(id,title,kind,created_at,source,version)
                                       VALUES (%s,%s,%s,%s,%s,1) RETURNING *""",
                                    (scenario_id, command.title or titles[command.kind], command.kind, now, source)).fetchone()
            samples = []
            if command.kind != "empty":
                for i in range(96):
                    value = round(18.5 + math.sin(i * .22) * 3.3 + math.cos(i * .61) * 1.4, 1)
                    if command.kind == "fault" and 62 <= i <= 70:
                        value = [26.1, 28.0, 30.4, 32.8, 34.6, 33.1, 31.6, 29.8, 27.3][i-62]
                    if i == 95:
                        value = 22.4
                    invalid = command.kind == "invalid"
                    samples.append((uuid4(), scenario_id, now - timedelta(minutes=(95-i)*15),
                                    None if invalid else value, "Invalid" if invalid else "Usable",
                                    "Synthetic sensor reported a missing value." if invalid else ""))
                conn.cursor().executemany("""INSERT INTO aeris.readings(id,scenario_id,measured_at,value,quality,reason)
                                             VALUES (%s,%s,%s,%s,%s,%s)""", samples)
            self._event(conn, scenario_id, "Sensor Readings Recorded", {"count": len(samples), "synthetic": True, "source": source})
            if command.prepare and samples and command.kind != "invalid":
                self._assess(conn, scenario)
                self._forecast(conn, scenario)
            result = {"scenario_id": str(scenario_id), "version": 1}
            self._save_receipt(conn, "create", payload, result)
            return result

    def record_reading(self, scenario_id, command):
        def action(conn, scenario):
            started = scenario["fault_assessed_at"] or conn.execute("SELECT 1 FROM aeris.forecasts WHERE scenario_id=%s", (scenario_id,)).fetchone()
            if started:
                raise DomainError("EVIDENCE_FROZEN", "Assessment has started. Use a new window for new readings.")
            if len(self._readings(conn, scenario_id)) >= 512:
                raise DomainError("WINDOW_FULL", "This demo window has reached 512 readings. Create another window.")
            conn.execute("""INSERT INTO aeris.readings(id,scenario_id,measured_at,signal,value,unit,quality,reason)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                         (command.request_id, scenario_id, command.measured_at, command.signal, command.value,
                          command.unit, command.quality, command.reason))
            self._event(conn, scenario_id, "Sensor Readings Recorded", {"count": 1, "quality": command.quality, "synthetic": True})
            return {"reading_id": str(command.request_id), "quality": command.quality}
        return self._perform(scenario_id, "reading", command, action)

    def assess(self, scenario_id, command):
        return self._perform(scenario_id, "assess", command, self._assess)

    def forecast(self, scenario_id, command):
        return self._perform(scenario_id, "forecast", command, self._forecast)

    def review(self, scenario_id, command, actor_id=None):
        def action(conn, scenario):
            if conn.execute("SELECT 1 FROM aeris.cases WHERE scenario_id=%s", (scenario_id,)).fetchone():
                raise DomainError("CASE_ALREADY_CREATED", "The case preserves this review. Start another analysis window for new decisions.")
            forecast = conn.execute("SELECT * FROM aeris.forecasts WHERE scenario_id=%s", (scenario_id,)).fetchone()
            if not forecast:
                raise DomainError("FORECAST_REQUIRED", "Generate a simulated forecast before reviewing it.")
            review = {"reviewer": command.reviewer, "reviewer_id": actor_id, "note": command.note,
                      "decisions": [d.model_dump() for d in command.decisions],
                      "reviewed_at": self.clock().isoformat()}
            conn.execute("UPDATE aeris.forecasts SET review_status='Reviewed',review=%s WHERE id=%s", (Jsonb(review), forecast["id"]))
            self._event(conn, scenario_id, "Failure Forecast Reviewed", {"forecast_id": forecast["id"], "reviewer": command.reviewer, "reviewer_id": actor_id,
                                                                         "accepted": sum(d.decision == "Accepted" for d in command.decisions)})
            return {"forecast_id": forecast["id"], "review_status": "Reviewed"}
        return self._perform(scenario_id, "review", command, action)

    def create_case(self, scenario_id, command):
        def action(conn, scenario):
            existing = conn.execute("SELECT id FROM aeris.cases WHERE scenario_id=%s", (scenario_id,)).fetchone()
            if existing:
                return {"case_id": existing["id"]}
            incident = conn.execute("SELECT * FROM aeris.incidents WHERE scenario_id=%s", (scenario_id,)).fetchone()
            forecast = conn.execute("SELECT * FROM aeris.forecasts WHERE scenario_id=%s", (scenario_id,)).fetchone()
            require_case_gate(incident, forecast)
            accepted = {d["risk_id"] for d in forecast["review"]["decisions"] if d["decision"] == "Accepted"}
            risks = [r for r in forecast["risks"] if r["id"] in accepted]
            case_id = readable_id("PC", scenario)
            conn.execute("""INSERT INTO aeris.cases(id,scenario_id,incident_id,forecast_id,created_at,accepted_risks)
                            VALUES (%s,%s,%s,%s,%s,%s)""",
                         (case_id, scenario_id, incident["id"], forecast["id"], self.clock(), Jsonb(risks)))
            self._event(conn, scenario_id, "Predictive Maintenance Case Created", {"case_id": case_id, "accepted_risks": len(risks), "handoff": "Ready; no external service connected"})
            return {"case_id": case_id}
        return self._perform(scenario_id, "case", command, action)

    def record_outcome(self, case_id, command):
        with self.pool.connection() as conn:
            case = conn.execute("SELECT scenario_id FROM aeris.cases WHERE id=%s", (case_id,)).fetchone()
        if not case:
            raise DomainError("NOT_FOUND", "This predictive case does not exist.", 404)
        scenario_id = case["scenario_id"]

        def action(conn, scenario):
            current = conn.execute("SELECT * FROM aeris.cases WHERE id=%s", (case_id,)).fetchone()
            previous = conn.execute("SELECT * FROM aeris.outcomes WHERE case_id=%s AND external_reference=%s", (case_id, command.external_reference)).fetchone()
            if previous:
                keys = ("all_work_complete", "verification", "evidence_reference", "note", "simulated")
                if any(previous[k] != getattr(command, k) for k in keys):
                    raise DomainError("OUTCOME_REFERENCE_REUSED", "This external reference already describes a different outcome.")
                return {"case_id": case_id, "status": current["status"], "outcome_id": str(previous["id"])}
            if current["status"] == "Resolved":
                raise DomainError("CASE_RESOLVED", "This case is already resolved. Its evidence is preserved.")
            outcome_id = uuid4()
            conn.execute("""INSERT INTO aeris.outcomes(id,case_id,external_reference,all_work_complete,verification,evidence_reference,note,created_at,simulated)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,TRUE)""",
                         (outcome_id, case_id, command.external_reference, command.all_work_complete, command.verification,
                          command.evidence_reference, command.note, self.clock()))
            self._event(conn, scenario_id, "Maintenance Outcome Recorded", {"case_id": case_id, "simulated": True, "verification": command.verification,
                                                                          "all_work_complete": command.all_work_complete, "external_reference": command.external_reference})
            status = "Open"
            if resolves_case(command.all_work_complete, command.verification):
                status = "Resolved"
                conn.execute("UPDATE aeris.cases SET status='Resolved',resolved_at=%s WHERE id=%s", (self.clock(), case_id))
                self._event(conn, scenario_id, "Predictive Case Resolved", {"case_id": case_id, "simulated_outcome": True})
            return {"case_id": case_id, "status": status, "outcome_id": str(outcome_id)}
        return self._perform(scenario_id, "outcome", command, action)

    def detail(self, scenario_id):
        with self.pool.connection() as conn:
            # One snapshot prevents evidence assembled across concurrent transactions.
            conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            scenario = conn.execute("SELECT * FROM aeris.scenarios WHERE id=%s", (scenario_id,)).fetchone()
            if not scenario:
                raise DomainError("NOT_FOUND", "This analysis window does not exist.", 404)
            result = {"scenario": scenario, "readings": self._readings(conn, scenario_id)}
            for table, key in (("incidents", "incident"), ("forecasts", "forecast"), ("cases", "case")):
                # table names are closed constants, never supplied by a caller.
                query = sql.SQL("SELECT * FROM aeris.{} WHERE scenario_id=%s").format(sql.Identifier(table))
                result[key] = conn.execute(query, (scenario_id,)).fetchone()
            result["events"] = conn.execute("SELECT * FROM aeris.events WHERE scenario_id=%s ORDER BY position", (scenario_id,)).fetchall()
            result["outcomes"] = [] if not result["case"] else conn.execute("SELECT * FROM aeris.outcomes WHERE case_id=%s ORDER BY created_at,id", (result["case"]["id"],)).fetchall()
            return result

    def case_detail(self, case_id):
        with self.pool.connection() as conn:
            row = conn.execute("SELECT scenario_id FROM aeris.cases WHERE id=%s", (case_id,)).fetchone()
        if not row:
            raise DomainError("NOT_FOUND", "This predictive case does not exist.", 404)
        return self.detail(row["scenario_id"])

    def overview(self):
        with self.pool.connection() as conn:
            conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            scenarios = conn.execute("""SELECT s.*,i.id incident_id,i.peak,f.id forecast_id,f.review_status,
                c.id case_id,c.status case_status,
                (SELECT count(*) FROM aeris.readings r WHERE r.scenario_id=s.id) reading_count,
                (SELECT count(*) FROM aeris.readings r WHERE r.scenario_id=s.id AND r.quality='Usable') usable_count
                FROM aeris.scenarios s LEFT JOIN aeris.incidents i ON i.scenario_id=s.id
                LEFT JOIN aeris.forecasts f ON f.scenario_id=s.id LEFT JOIN aeris.cases c ON c.scenario_id=s.id
                ORDER BY s.created_at DESC,s.id LIMIT 100""").fetchall()
            cases = conn.execute("""SELECT c.*,s.turbine_id,s.title,s.source FROM aeris.cases c
                                    JOIN aeris.scenarios s ON s.id=c.scenario_id ORDER BY c.created_at DESC LIMIT 100""").fetchall()
            counts = conn.execute("""SELECT
                (SELECT count(*) FROM aeris.incidents i LEFT JOIN aeris.cases c ON c.scenario_id=i.scenario_id WHERE c.status IS DISTINCT FROM 'Resolved') alerts,
                (SELECT count(*) FROM aeris.forecasts WHERE review_status='Pending') pending_reviews,
                (SELECT count(*) FROM aeris.cases WHERE status='Open') open_cases,
                (SELECT count(*) FROM aeris.readings) total_readings""").fetchone()
            events = conn.execute("""SELECT e.*,s.title,s.turbine_id FROM aeris.events e
                                     JOIN aeris.scenarios s ON s.id=e.scenario_id ORDER BY e.position DESC LIMIT 30""").fetchall()
            return {"scenarios": scenarios, "cases": cases, "metrics": counts, "events": events,
                    "rule": {"signal": "wind_speed", "threshold": DEMO_THRESHOLD, "unit": "m/s", "comparison": ">", "synthetic": True},
                    "active_scenario_id": str(scenarios[0]["id"]) if scenarios else None,
                    "simulation": True, "turbine_id": "WT-017"}

    def seed(self):
        from .schemas import Command, NewScenario, Outcome, Review
        with self.pool.connection() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(814018)")
            if conn.execute("SELECT 1 FROM aeris.scenarios LIMIT 1").fetchone():
                return
            now = self.clock()
            for label, days, case_status in (("Current gust event", 0, None), ("Earlier gust event", 2, "Open"), ("Resolved demonstration", 8, "Resolved")):
                sample = Maintenance(self.pool, clock=lambda days=days: now - timedelta(days=days))
                request_id = uuid5(NAMESPACE_URL, f"aeris-seed-v1/{label}")
                result = sample.create_scenario(NewScenario(request_id=request_id, title=label), source="Seeded demo history")
                sid, version = UUID(result["scenario_id"]), result["version"]
                if case_status:
                    result = sample.review(sid, Review(request_id=uuid4(), expected_version=version, reviewer="Seeded demo specialist",
                        note="Synthetic historical review for the demonstration, not a real person's assessment.",
                        decisions=[{"risk_id": "yaw-drive", "decision": "Accepted"}, {"risk_id": "pitch-actuator", "decision": "Rejected"}]))
                    result = sample.create_case(sid, Command(request_id=uuid4(), expected_version=result["version"]))
                    if case_status == "Resolved":
                        sample.record_outcome(result["case_id"], Outcome(request_id=uuid4(), expected_version=result["version"], simulated=True,
                            external_reference="DEMO-HISTORY-OUTCOME", all_work_complete=True, verification="Passed", evidence_reference="DEMO-HISTORY-EVIDENCE",
                            note="Synthetic example of an external maintenance outcome. No real turbine was repaired or verified."))
