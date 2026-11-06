# Predictive Maintenance prototype plan

Status: implementation authorized by the user on 2026-11-06. This records the agreed
scope and acceptance criteria. The local prototype now implements this flow; see
[development instructions](development.md) and [current project context](project-context.md)
for actual commands, decisions, validation and remaining remote-deployment work.

## Goal and authority

Deliver a simple working prototype that the group can try in a browser: technicians
inspect wind-turbine evidence, review a simulated forecast and follow a predictive
case through to a clearly simulated maintenance outcome. UI language: English.
The REST API, domain rules, review decisions and database persistence must really
work; only the sensor source, prediction and external maintenance outcome are demos.

This scope follows the user's explicit clarification and answers (T1), the supplied
EventStorming diagram (D4), and assignment A1/A2. See [course context](course-context.md)
for source IDs and [project context](project-context.md) for actual implementation status.
T2's DDD/cloud notes provide supporting context, not additional requirements.

## Included and excluded

- Include Predictive Maintenance stages 1, 2a, 2b, 3 and 8 from the diagram.
- Include sensor history/quality, a current-fault rule, simulated failure forecasts,
  human acceptance/rejection of risks, predictive cases and an evidence/event timeline.
- Include a labelled demo input that returns an external maintenance outcome and
  exercises case resolution. No actual repair or verification is claimed.
- Exclude Better Maintenance: work-order registration, assignment, specialist tasks,
  operational verification, coordinator screens and a second application/service.
- Exclude real ML training/inference, physical sensors, paid notifications, fleet
  management and enterprise integrations. Begin with one synthetic turbine scenario.

## Browser walkthrough

| View | What the technician can inspect or do |
| --- | --- |
| Overview | See the turbine, latest reading time/quality, current alerts, pending forecast reviews and open cases; show empty/error/stale-data states |
| Evidence and forecast review | Inspect timestamped sensor history/chart, units, fault evidence and simulated risks with likelihood/horizon; accept/reject each risk and save a review note |
| Case detail | Inspect Case ID/Turbine ID, linked incident, reviewed forecast, accepted risks, retained rejected-risk history and chronological events/evidence |
| Demo controls | Replay normal/fault/invalid-data examples; generate a labelled simulated forecast; later supply a labelled external outcome to demonstrate resolution |

Before a case exists, the review view is attached to the incident/forecast, not to
an invented case. The dashboard must expose this pending work. Case review here
means inspecting the resulting case; it does not replace the earlier forecast review.
Use a named demo technician for the walkthrough; this is not production identity
verification. Real access controls are required before any shared remote deployment.

## Domain behaviour to preserve

1. Validate and record permitted sensor readings with ID, turbine, timestamp,
   signal, value, unit and usability/reason. Retain unusable readings as evidence
   but exclude them from fault/forecast evaluation. Safely reject malformed/oversize
   requests; retaining readings does not mean saving arbitrary raw request bodies.
2. Evaluate a small explicit demo rule on usable readings. Store the resulting
   fault incident and evidence links. Values/thresholds are synthetic configuration,
   not validated turbine limits. Define below/equal/above examples before coding.
3. Independently generate a deterministic simulated forecast with source evidence,
   demo model version, risks, illustrative likelihoods and horizons. Clearly label
   it "Simulated forecast - no real AI analysis". Do not imply statistical accuracy.
4. A human reviews each predicted risk. Save accepted/rejected decisions, note,
   reviewer and time. "Reviewed" is different from "Accepted": all risks may be
   rejected while the forecast is still reviewed. Preserve those decisions.
5. Create a predictive case only when a fault incident exists AND the related
   forecast has been reviewed for the same turbine/scenario. A fault alone or an
   unreviewed forecast is insufficient. Do not invent an additional requirement
   that at least one forecast risk must be accepted. Include faults, reviewed
   accepted risks and evidence references; keep rejected risks available in history.
6. Keep the two assessment paths logically independent. Their ordering must not
   change case eligibility. No queue/broker/parallel worker is needed just to show
   the parallel branches. Retry/replay must not create a second case for one incident.
7. Show the created case as open/ready for external maintenance. A displayed handoff
   summary is not proof of delivery to an existing Better Maintenance service.
8. The demo control submits a correlated external outcome with `simulated=true`,
   external reference, completion/verification result, time and evidence reference.
   An incomplete or failed result leaves the case open. A simulated successful
   outcome confirming all required linked work is complete resolves the case and
   records its history. For this single-case demo, use one external outcome reference;
   do not model the excluded work orders/tasks. Duplicate outcomes must be harmless.

Enforce transitions in the backend, not just by hiding buttons. Save related state
and timeline events transactionally. Reject stale conflicting reviews/transitions
instead of silently overwriting another technician's decision. An event timeline
does not require event sourcing, an outbox or a message broker.

## Architecture direction

```text
Technician browser
       | HTTP: pages, data and actions
       v
One application: dashboard + REST API + domain rules + demo adapters
       | database access on the server
       v
Separate database: readings, incidents, forecasts/reviews, cases, events/outcomes
```

The selected local implementation uses Python/FastAPI with HTML templates, CSS and a little
JavaScript in the same application, plus PostgreSQL as a separate database service.
This keeps the visible prototype and required API together without another frontend
build/deployment. This is a team choice, not a course requirement.
Versions are locked and the working commands are in README/development instructions.

Local Compose can run the app and database reproducibly with persistent demo data.
If the existing Azure VM database is usable, the same app can access it server-side
through private access/an SSH tunnel as appropriate. Verify its engine and configuration
before deciding; do not assume it already contains data. Keep the browser/API contract
the same and provide an explicit local fallback rather than silently changing stores.
Do not publish the database port to the internet. Restrict local access to the Mac;
confirm authentication/TLS, team access, VM schedule/cost and deployment authorization
before remote sharing. No cloud changes or service startup are part of preparation.

Official references checked 2026-11-06:
[FastAPI templates](https://fastapi.tiangolo.com/advanced/templates/),
[static assets](https://fastapi.tiangolo.com/tutorial/static-files/), and
[Compose service networking](https://docs.docker.com/compose/how-tos/networking/).
These confirm available mechanisms, not the completion of any implementation.

## Planned acceptance demonstrations

- Normal readings: history is visible, with no fabricated fault/case.
- Invalid-quality reading: retained/labelled, excluded from analysis.
- Fault plus unreviewed forecast: alert/pending review visible; case blocked.
- Reviewed forecast without a fault: no case created.
- Fault plus reviewed forecast: exactly one persisted, correlated case.
- All forecast risks rejected: review remains recorded; a real demo fault still
  permits the case, with no accepted predicted risks listed.
- Reload/restart: persisted readings, reviews, case and timeline remain visible.
- Repeated demo input/review/outcome: no duplicate case or resolution event.
- Incomplete/failed simulated outcome: case stays open; successful simulated
  outcome: case resolves with the demo origin and evidence visible.
- Two conflicting actions: server reports a conflict; UI refreshes current state.
- Visible controls: browser walkthrough works end to end, including loading,
  empty/error states and clearly marked synthetic/AI-simulation content.
- Final MVP evidence: genuine remote API request, database retrieval, application
  tests/build and CI/CD evidence alongside the dashboard (assignment R1-R6).

## Implementation sequence

1. Agree concrete synthetic signals/rule boundaries and API/state examples; verify
   the VM/database read-only if reuse is selected. Confirm versions and local setup.
2. Build one visible increment: persisted sensor history -> fault -> simulated
   forecast -> human review -> case. Add domain, API and database tests alongside it.
3. Add the labelled simulated outcome, timeline and repeatable scoped demo replay.
   Any reset must target only this prototype's synthetic data, never a shared DB wipe.
4. Run browser acceptance checks, extend CI to actual app/test/build checks, then
   configure the authorized remote demonstration and document the run/deploy process.

The demo rule/units and local stack are selected in the API contract and project
context. The VM database and remote deployment/access approach still need verification.
Keep those separate from the working local prototype; do not claim a real remote
request or Azure deployment until demonstrated.
