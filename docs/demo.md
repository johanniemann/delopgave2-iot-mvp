# Five-minute technical demonstration

Use the actual selected release and synthetic data. Prepare a clean browser,
Postman collection imported from the same commit, personal account, an internal
psql session and the relevant successful GitHub Actions run. Start the shared VM
deliberately if needed and verify `/health` first. No passwords/tokens may appear
in the recording. The video is a separate deliverable; this is its runnable plan.

| Time | Demonstrate | Evidence |
| --- | --- | --- |
| 0:00-0:35 | Open the HTTPS dashboard and sign in as Technician | Actual remote access; synthetic labels; working dashboard |
| 0:35-1:00 | Open `/docs`; identify reading input, assess and saved evidence routes | API boundary and request schema |
| 1:00-2:10 | Run Postman S01-S10 after login 00 | 28.0 does not alarm; invalid unit 422; 101 retained Invalid; 28.1 opens incident |
| 2:10-2:50 | Show SQL rows for the same `sensor_scenario_id` | Input, incident and domain events really stored in separate PostgreSQL |
| 2:50-3:55 | Show forecast review, blocked case before review and resulting case; optionally a failed/successful simulated outcome | Domain gate and clearly simulated external result |
| 3:55-4:30 | Show the successful CI run, SAST/dependency gate, app tests and release commit/image | Traceable tested release; no claim that merge alone deploys |
| 4:30-5:00 | Show backup/restore or controlled-failure evidence and the remaining prototype limits | Persistence/recovery; no real AI, physical sensor or repair claimed |

Rehearse once without recording. Keep the complete 27-request collection as
repeatable evidence, but select the clearest requests for the short video. The
failed verification and subsequent successful resolution are simulated outcomes,
not evidence of real turbine work.

## Inspect the same sensor data safely

Keep the database session on the Docker host. Do not publish port 5432. Select
the same Compose project/settings as the release. For a local demonstration:

```sh
docker compose exec db psql -U prototype -d aeris
```

For shared mode use the explicit `aeris-shared` project, private environment file
and both shared Compose files as shown in [deployment](deployment.md). Inside psql,
replace the placeholder below with the UUID from Postman:

```sql
\set scenario 'PASTE-SENSOR-SCENARIO-UUID'
SELECT id, measured_at, value, unit, quality
FROM aeris.readings WHERE scenario_id = :'scenario'::uuid ORDER BY measured_at, id;
SELECT id, peak, threshold, evidence
FROM aeris.incidents WHERE scenario_id = :'scenario'::uuid;
SELECT name, occurred_at, payload
FROM aeris.events WHERE scenario_id = :'scenario'::uuid ORDER BY position;
```

Show only the selected synthetic domain rows. Do not query users/sessions or
environment settings on-screen. `sensor_scenario_id` identifies the second window;
the first window is available in the S01 response for the equality example.

## Group acceptance checklist

- Another member reviews the feature PR and records observations under their own account.
- Another member uses the selected HTTPS release or a clean local clone on their computer.
- They send a concrete sensor input, find the matching SQL/event evidence and explain the rule.
- Technician administration is denied even when called directly; Admin can manage accounts.
- Reload/restart preserves the selected case. Use the saved evidence comparison.
- Everyone can explain the domain gate, what is simulated, what CI actually tests,
  the current release ID, database separation and recovery limits.
- Confirm the examiner can access the private repo through the agreed submission route.

Leave human acceptance unchecked until it has actually happened. Agent tests and
another GitHub user's unrelated documentation PR are not a substitute for it.
