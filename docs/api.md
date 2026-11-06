# Prototype API contract

All records are synthetic. Predictive Maintenance only; no Better Maintenance service.
The UI and `/api` share one origin. OpenAPI is at `/docs`. IDs are UUIDs except
readable incident/forecast/case IDs. Times use timezone-aware ISO 8601; storage is UTC.

## Demo rule and case gate

`wind_speed`, `m/s`: a usable reading **strictly above 28.0** opens a current-fault
incident. 27.9 and 28.0 do not; 28.1 does. This is an illustrative demo rule, not a
validated turbine limit. Null/out-of-range readings are retained as Invalid and
excluded from assessment. The permitted synthetic range is 0-100 m/s. With no
usable data, assessment is blocked; this does not mean "no fault detected".
A case requires an incident AND a reviewed forecast for the same scenario, even if
all forecast risks were rejected. Forecast numbers are fixed illustrative fixtures.

## Routes

| Method/path | Result |
| --- | --- |
| `GET /health` | Database readiness, 503 if unavailable |
| `GET /api/overview` | Persisted scenario/case summaries, metrics, recent events, demo rule |
| `GET /api/scenarios/{id}` | Readings, incident, forecast/review, case, outcomes and timeline |
| `GET /api/cases/{id}` | Full evidence bundle for a case |
| `POST /api/scenarios` | New isolated demo window: `kind` fault/normal/invalid/empty; `prepare` optionally runs the two independent assessments |
| `POST /api/scenarios/{id}/readings` | Record one reading before assessments freeze its evidence window |
| `POST /api/scenarios/{id}/assess` | Assess usable readings; store a fault if the demo rule fires |
| `POST /api/scenarios/{id}/forecast` | Generate a labelled simulated forecast; requires usable data |
| `PUT /api/scenarios/{id}/review` | Record a reviewer, note and Accepted/Rejected decision for every risk |
| `POST /api/scenarios/{id}/case` | Create exactly one case once both gates hold |
| `POST /api/cases/{id}/outcomes` | Record a labelled simulated external result; resolve only if all work complete and verification Passed |

Every mutation needs a UUID `request_id`. Existing-scenario mutations also need
`expected_version` from the latest detail. A repeated identical request returns its
stored receipt. Reusing an ID with different content or a stale version returns 409.
State, events and receipts commit atomically under a scenario lock. Assessment paths
may run in either order. Readings cannot be appended after assessment/forecast starts;
create a new window. Reviews cannot change after case creation. A failed/incomplete
outcome leaves the case Open. A resolved case is immutable. External outcome references
are unique per case; replay must not add another resolution event. No reset/wipe API.

## Access and errors

Local mode binds Docker's application port to loopback only. Shared mode requires
`API_TOKEN` (32+ characters) as `Authorization: Bearer …`, explicit allowed hosts and
TLS through a suitable deployment proxy. The browser asks for the token and keeps it
in tab session storage only; no token is embedded in the source or page.
API writes require JSON and a bounded Content-Length (maximum 16 KiB); chunked writes
are not supported. Cross-origin writes are rejected. There are 60 writes/minute/IP
per application process, excluding health/read requests. This is a prototype guard,
not a distributed production access system.

Errors: 401 missing/invalid shared token, 403 foreign origin, 404 unknown record,
409 state/idempotency/version conflict, 411 length required, 413 oversized body,
415 non-JSON write, 422 invalid fields, 429 rate limit, 503 database unavailable.
Validation responses omit request bodies; database/internal details are not returned.
