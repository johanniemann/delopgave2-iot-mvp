# Local API observability demonstration

This optional demonstration sends real API timings, request counts and HTTP traces
to **self-hosted SigNoz on the developer's own computer**. It uses synthetic Aeris
data. GitGuardian remains responsible for secret scanning; GitHub Actions remains
responsible for build/test checks. SigNoz is for understanding the running service.

No Azure resource, shared release, firewall, paid account or external notification
channel is created. The small shared VM does not run this stack. Observability is
disabled in the default app and shared deployment unless `AERIS_OTLP_ENDPOINT` is
explicitly supplied. A collector outage does not change API/domain decisions.

## Start and stop

Prerequisites: Git, Python 3.10+, Docker Engine/Desktop with Compose v2, Internet for
initial downloads and at least 4 GB allocated to Docker. The verified Mac had 8 GB
allocated to Docker and 16 GB total memory. On Windows use WSL 2 with **native Docker
inside WSL**, following SigNoz's current ClickHouse Keeper guidance; Windows was not
tested here. Linux launch support is supplied but was not exercised on this Mac.

From the repository root:

```sh
python3 scripts/observability.py up
python3 scripts/observability.py status
```

- Aeris: `http://localhost:8766`
- SigNoz: `http://localhost:3301`

First startup downloads **Foundry 0.5.0 from the official SigNoz release**, verifies
its pinned SHA-256, and renders [casting.yaml](../ops/observability/casting.yaml).
This is the currently supported SigNoz installation path. Foundry is kept in ignored
local runtime storage; it is not installed globally. Its usage ledger and update
notifier are disabled. SigNoz/collector/ClickHouse images are pinned by digest.
The initial histogram helper is downloaded by the upstream setup from its fixed
official `histogram-quantile/v0.0.1` release.

The helper creates a separate ignored, owner-readable `.env.observability` once.
It preserves existing settings. The helper also prepares individual local
Admin/Technician accounts; passwords stay in ignored `.env.accounts-8766.json`.
Sign in to Aeris using those accounts, separate from the SigNoz account. Generated configuration lives in
`.codex-log/observability/`; do not edit it manually. Change the versioned casting
file and rerun `up`. Startup dependencies wait for ClickHouse/migrations/SigNoz.

Two deliberately named Compose projects keep the demonstration isolated:

| Project | Responsibility | Saved data |
| --- | --- | --- |
| `aeris-observed` | Aeris app and its own PostgreSQL | Separate demo volume |
| `aeris-monitoring` | SigNoz, collector, ClickHouse and internal metadata | Separate telemetry/account volumes |

Neither project reuses the original `aeris-prototype` or Azure `aeris-shared` volumes.
Only loopback app/UI ports are published. The collector, ClickHouse and database
stay on private Docker networks. SigNoz uses its supported SQLite option for its
own local account/dashboard metadata; **Aeris domain data still uses PostgreSQL**.
This is a single-computer learning setup, not a production monitoring service.

To stop everything while preserving the data and your local SigNoz account:

```sh
python3 scripts/observability.py stop
```

The local stack has no automatic restart policy. It must be started deliberately.
Do not prune/delete its volumes or the original demo to free resources. Closing a
browser does not stop the containers. Stopping this local demo does not control Azure.

## Set up the dashboard and alarm once

Create your own first admin account in the **local** SigNoz page. Each contributor
uses their own account/password on their installation; no password goes in Git or
group messages. All current SigNoz browser access stays on this computer.

In SigNoz choose Dashboards → New dashboard → Import JSON and load
[dashboard.json](../ops/observability/dashboard.json). It contains two panels:

- API requests per second, from the request counter's rate.
- Estimated p95 response time in milliseconds, from the recorded histogram. This
  is a histogram estimate, not an exact percentile of a large production workload.

Set the time window to Last 30 minutes and enable a 30-second refresh while trying
the demo. Generate a short burst of harmless reads with:

```sh
python3 scripts/observability.py traffic
```

For the one local alert, use New Alert → Metrics and the values recorded in
[alert-rule.json](../ops/observability/alert-rule.json):

1. Name: `Aeris local API HTTP 503`.
2. Metric: `aeris.http.requests`; rate within each series and sum across series.
3. Filter: `service.name = 'aeris-api' AND http.response.status_code = '503'` (metric labels
   are strings; use equality with a quoted status).
4. Trigger above `0`, at least once in the last `1 minute`; evaluate every `1 minute`.
5. Enable **Use Routing Policies** so SigNoz accepts the rule without assigning a
   channel. On this fresh local installation there are no notification channels or
   routes: the alarm is visible in SigNoz only. No email/webhook delivery is claimed.
6. Leave no-data alerts and repeat notifications off. No-data is expected when this
   optional stack is stopped. Save the rule and use its History tab to inspect changes.

The JSON is the verified saved rule payload/reference, not an automatically applied
rule or a promise of a UI import feature. The guide supplies the short UI procedure.
The owner's account, imported dashboard and saved alarm persist locally in volumes;
new clones still need this one-time UI setup. There are no stored admin API keys.

## Controlled failure and recovery

```sh
python3 scripts/observability.py failure-demo
```

This command first verifies that the isolated app owns `127.0.0.1:8766`. It saves a
complete case response, stops **only** the `aeris-observed` database, makes five
requests that must receive HTTP 503, and restarts that database in a `finally`
block. It then requires HTTP 200 and an unchanged complete saved case response.
There is no failure-injection endpoint in the product and no shared database is stopped.

Allow several minutes when checking the SigNoz alarm history: this pinned version
adds a two-minute evaluation delay before the one-minute rolling window.
This one rule detects HTTP 503 specifically. Other status codes, including the
expected HTTP 409 case gate before review, do not trigger it. It is not a complete
production alert policy. See [Postman walkthrough](postman.md)
for the complete normal business flow.

## Verification record (2026-11-08)

- The actual isolated FastAPI/PostgreSQL service exported traffic and timing data
  displayed in both SigNoz dashboard panels.
- The controlled database interruption returned five HTTP 503 responses. Recovery
  returned HTTP 200 and an unchanged complete saved case, including its evidence.
- The saved HTTP-503 rule recorded **Firing at 19:52:08** and **Resolved at
  19:53:08 Copenhagen time** in SigNoz History (one trigger, 1.0-minute resolution
  interval). The UI timestamps describe the delayed evaluation window; this is not
  immediate notification or external delivery.
- Stopping only the local collector left all three API probes successful (HTTP 200);
  the collector was restarted afterwards. Monitoring is not an API availability dependency.
- The initial telemetry increment passed 51 PostgreSQL application tests and 15
  helper tests. The later individual-account increment passed 70 application tests
  and 18 helper tests, including real login telemetry privacy.
- The original Postman walkthrough passed 13 requests/23 assertions. After the
  individual-account change it passed 17 requests/28 assertions, including sign-in,
  Technician admin denial and sign-out. Helpers now authenticate before traffic/failure tests.

## What is collected

[app/telemetry.py](../app/telemetry.py) owns app-scoped OpenTelemetry SDK providers
and background OTLP/HTTP exporters. Only `http.request.method`, the matched
`http.route` template and `http.response.status_code` are recorded, with the fixed
service identity `aeris-api`. Unknown API routes collapse to `/api/unmatched`.
Health probes and static files are excluded. There are no query strings, raw IDs,
client IPs, headers, tokens, request/response bodies, SQL statements or exception
messages in the exported telemetry. Trace errors indicate HTTP 5xx without an
exception stack. Metrics/traces stay within the local Docker network.

Current traces cover the HTTP request, not individual database queries. Existing
container logs and the business event timeline remain separate; they are not
exported to SigNoz. This is not an audit-grade identity or incident-response system.
There is no external uptime check, so this same-computer stack cannot independently
report the host's own shutdown. Retention uses SigNoz defaults; the demo is for short
sessions, not unattended data collection. Container logs are capped at 2 × 10 MB.

## Course rationale and maintenance

The user selected this increment on 2026-11-08. SigNoz is a team choice, not an
assignment mandate. It makes course E3's logging/safe-failure work and C1/C2's early
validation/operability visible: introduce a controlled failure, see the signal and
verify recovery without losing business evidence. No new domain, work-order system
or real predictive model is introduced. See [course context](course-context.md).

Keep instrumentation off by default, update the lockfile when changing SDK versions,
and rerun real PostgreSQL tests plus the local demonstration when telemetry changes.
The HTTP privacy tests collect actual SDK spans/metrics in memory; helper tests
check isolation, checksum rejection and database restoration after an interrupted
failure test. Do not describe a successful unit test as a verified live alarm.

Official references checked 2026-11-08:
[SigNoz installation](https://signoz.io/docs/install/docker/),
[Foundry 0.5.0](https://github.com/SigNoz/foundry/releases/tag/v0.5.0),
[OpenTelemetry Python instrumentation](https://opentelemetry.io/docs/languages/python/instrumentation/),
[OTLP exporters](https://opentelemetry.io/docs/languages/python/exporters/),
[SigNoz alerts](https://signoz.io/docs/alerts/), and the pinned version's
[evaluation implementation](https://github.com/SigNoz/signoz/blob/v0.149.0/pkg/query-service/rules/base_rule.go).
