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

Both local and shared modes require an individual **Technician** or **Admin**
account. Authenticated users can use all maintenance routes; only Admin can use
`/api/admin/*`. No bearer-token bypass or public registration exists. Login, logout,
password change and user-management routes are specified in
[authentication](authentication.md). Cookies are HttpOnly/SameSite=Strict and Secure
in shared HTTPS mode. Every authenticated write needs `X-CSRF-Token` from login/me.
The optional legacy `reviewer` field is ignored by HTTP: the saved reviewer name and
UUID come from the account. Old saved/seeded names remain unchanged.

API writes require JSON and a bounded Content-Length (maximum 16 KiB); chunked writes
are not supported. Cross-origin writes are rejected. There are 60 writes/minute/IP
per application process, excluding health/read requests. This is a prototype guard,
not a distributed production access system.

Errors: 401 missing/expired session or invalid credentials, 403 insufficient role,
required password change, missing/invalid CSRF or foreign origin, 404 unknown record,
409 state/idempotency/version conflict, 411 length required, 413 oversized body,
415 non-JSON write, 422 invalid fields, 429 rate limit, 503 database unavailable.
Validation responses omit request bodies; database/internal details are not returned.


## Operations and security evidence

`GET /health` also returns `revision`: the exact source commit embedded in a
release image, or `local` for an unlabelled developer build. It exposes no account
or deployment credentials. Compare it with the selected release manifest.

Rejected API requests with status 401, 403 or 429 produce a bounded JSON security
log event on container stderr. Fields are UTC time, event, method, matched route
template, status and an authenticated account UUID when available. Early guard
rejections use `/api/unmatched`. No username, peer IP, raw URL/query, body, cookie,
password or CSRF token is copied. These operational events complement the domain
and account-administration history; they do not replace it.
