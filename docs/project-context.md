# Project context

## Observed baseline and current implementation

At inspection on 2026-11-06, local HEAD and fetched origin/main contained only the
initial README (commit e1bfcef). There was no source code, dependency manifest,
Dockerfile, database configuration, test suite, CI or agent configuration.
This setup adds developer guidance and a repository-check workflow only.
Reinspect actual files as this status evolves; update this page with implementation.

## Required product direction

The assignment's bounded MVP is predictive maintenance/notification in Managed
Services: receive a sensor value, evaluate a rule, produce an anomaly/alarm and
persist domain events/output in a separate database. The API must be callable from
another computer. The assignment allows Azure Cloud or local Docker, requires
CI/CD and a repository containing application and pipeline code. See
[the evidence and acceptance map](course-context.md).

Conceptual responsibilities (not existing directories or deployments):

```text
Remote caller -> REST input/validation -> domain rule -> result/event
                                             |              |
                                             +-- persistence+
                                                   separate DB
```

Keep transport and storage adapters from owning business decisions. A small
modular service is sufficient initially; no event broker, ML model, frontend,
Kubernetes cluster or database VM is required by the assignment.

## Relationship to Delopgave 1

The final student report proposes Predictive Maintenance and Better Maintenance as
two logical contexts, initially deployed together with separate model responsibilities.
It links wind-turbine measurements to cases, work orders and verified normal operation.
Earlier MD notes and API examples are proposals, not implemented contracts.

The report's NT-01 rule prevents work-order closure unless all required tasks are
complete and the latest verification confirms normal operation for their current
revision; changed work invalidates old verification. NH-01 proposes specialist
suggestions, with human assignment. Preserve these meanings if that broader scope
is later selected. Neither requires implementing work orders in this API MVP now.
The report also proposes durable handoffs/outbox and replay handling for a later
cross-context integration. Do not introduce that infrastructure for simple telemetry
without a task that needs it. No Salesforce/Business Central integration is selected.

## Open decisions, not assumptions

| Decision | Current evidence | When to resolve |
| --- | --- | --- |
| Language, framework and versions | Python is used in teaching; FastAPI/Flask are examples, not a mandate | First application increment; document the choice and real commands |
| Database | Separate persistence required; engine and schema not chosen | Persistence contract and deployment decision |
| Threshold, units and equality boundary | Exercise uses wind speed with an illustrative threshold; no validated project threshold | Acceptance examples before rule implementation |
| Notification | An alarm/notification flow required; delivery channel not chosen | Define observable behaviour; no paid email/SMS service by default |
| Deployment | Azure or local Docker permitted; surrounding VM notes are historical preparations | Verify actual access/configuration when deployment is authorized |
| Branch enforcement | Feature branches + PR review are the chosen working convention for this setup | Verify hosting plan/settings before claiming enforcement |

An architecture change should record the problem, alternatives, selected approach,
course/source connection and consequences here or in a focused decision note linked
here. Keep implemented facts separate from proposed changes. Do not add placeholder
runtime directories or pin a framework simply to make this instruction setup look complete.
