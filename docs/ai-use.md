# AI-use development record

This collects evidence for the AI disclosure required by course source C3 in
[course context](course-context.md). Adapt it into the submission's method section
or appendix; it is not a claim that the final submission disclosure is complete.
Full chat exports are unnecessary. Avoid secrets and unrelated personal information.

For each meaningful generated contribution record the student responsible, date,
short prompt description, tool/model/version if known, purpose, affected files or PR,
and how a human assessed, changed or rejected the output. Use "not recorded" for
unknown technical metadata, not a guessed version. Link detailed validation from the
PR to avoid duplicating logs. Unused brainstorming and the policy's other exemptions
need not create entries.

## 2026-11-06: shared agent development setup

- Student responsible: to be confirmed by the contributing group member.
- Tool/model: Codex; exact runtime model/version not recorded in the repository.
- Prompt: investigate the repo and teaching material, research current official agent
  guidance, implement a minimal cross-agent setup, validate and document onboarding.
- Purpose: shared academic/project context, consistent contribution/review procedure,
  portable agent entry points and validation without changing application behaviour.
- Output: AGENTS.md, tool adapters, README/contribution/context/setup docs, PR template,
  ignore rules and the repository-check script/tests/workflow in this change.
- Agent validation: see the setup PR's validation section for exact commands/results.
- Human assessment/adaptations: pending group review. The reviewer must record what
  they checked or changed; this agent-generated entry is not evidence of human approval.

## 2026-11-06: Predictive Maintenance prototype preparation

- Student responsible: to be confirmed by the contributing group member.
- Tool/model: Codex; exact runtime model/version not recorded in the repository.
- Prompt/purpose: prepare, without building, the Predictive Maintenance-only visual
  prototype using the supplied diagram and teammate notes. The user selected English
  UI and a labelled simulated external maintenance outcome for case resolution.
- Output: prototype plan and corresponding AGENTS/README/project/course context
  updates. No runtime code, dependency, container or cloud change.
- Agent validation: repository checker, existing checker tests, whitespace and
  manual consistency review of scope, diagram gates and linked references.
- Human assessment/adaptations: pending review of the written plan. The user's scope
  answers are recorded as decisions, not as approval of unreviewed generated content.

## 2026-11-06: working local Predictive Maintenance prototype

- Student responsible: to be confirmed by the contributing group member.
- Tool/model: Codex; exact runtime model/version not recorded in the repository.
- Prompt/purpose: "Start building" the previously agreed visual Predictive
  Maintenance prototype, preserving the single-context scope and explicit simulation.
- Output: FastAPI app, dashboard, PostgreSQL schema/transactions, Docker runtime/test
  configuration, application tests, CI and updated API/development/context docs.
- Agent validation: real PostgreSQL domain/API tests, actual Docker deployment and
  HTTP smoke check, browser walkthrough, syntax/portability/whitespace checks.
  See the implementation PR for results and limits. Browser QA uses a clearly
  simulated reviewer label; it does not claim real specialist/human approval.
- Human assessment/adaptations: pending independent group review. Sample history
  and generated likelihoods are synthetic; no true ML/repair/verification is claimed.

## 2026-11-06: shared Azure deployment preparation

- Student responsible: to be confirmed by the contributing group member.
- Tool/model: Codex; exact runtime model/version not recorded in the repository.
- Prompt/purpose: move the accepted local prototype to the existing study-group VM,
  protect shared access, verify persistence and enable nightly shutdown.
- Output: optional shared Compose/Caddy configuration, private setup and release
  helpers, authenticated live smoke check, CI coverage and deployment documentation.
- Infrastructure: approved restricted SSH and web firewall changes; user selected
  00:00 Copenhagen nightly shutdown and personally submitted SSH key registration.
  The existing VM now runs the shared HTTPS demo. The user explicitly approved
  copying only its dashboard token to a private ignored file on their Mac for
  access/testing. See the deployment guide for actual evidence and remaining limits.
- Human assessment/adaptations: user accepted the local experience and selected the
  shutdown time. On 2026-11-07 the owner explicitly authorized merge after passing
  checks while the others were unavailable. No independent review is claimed;
  retrospective teammate review remains follow-up work.

## 2026-11-07: continuation and Danish beginner explanation

- Student responsible: to be confirmed by the contributing group member.
- Tool/model: Codex; exact runtime model/version not recorded in the repository.
- Prompt/purpose: continue with the owner as the only available group member,
  investigate a GitHub Pages address, and explain the work of November 6-7 for
  someone without coding/GitHub knowledge, including the teaching rationale.
- Decisions: the user chose to retain the existing Azure hostname after the Pages
  options/limitations were explained. No public repository, paid upgrade or Pages
  deployment was authorized or created. PR #4's owner-authorized merge exception
  is recorded separately from independent review.
- Output: Danish walkthrough, architecture illustration, updated deployment/context
  notes and an editable Word copy in the supplied school folder outside this clone.
  The walkthrough is the prose source for that copy; course PDFs remain outside Git.
- Agent validation: checked assignment pages and relevant teaching/exercise sources;
  verified HTTPS/authenticated data and unchanged complete case response after actual
  VM deallocation/startup, inspected the dashboard, then verified deallocation again.
  Document rendering/visual QA and repository checks are part of this change.
- Human assessment: user selected the hosting direction and merge exception.
  The generated explanation still requires human reading, correction and assessment
  before use in an academic submission; no completed independent review is claimed.

## 2026-11-08: optional local observability and Postman walkthrough

- Student responsible: to be confirmed by the contributing group member.
- Tool/model: Codex; exact runtime model/version not recorded in the repository.
- Prompt/purpose: implement the selected small local SigNoz demonstration, one
  dashboard and one controlled-failure alarm; provide a repeatable Postman API flow.
- Output: opt-in OpenTelemetry HTTP metrics/traces, isolated local Compose/Foundry
  setup, privacy/isolation tests, dashboard/rule references, Postman collection,
  CI validation and contributor guides. No Azure deployment or paid service.
- Agent validation: see this change's PR and monitoring/Postman guides for actual
  commands, results and limitations. Local API success is distinct from live alarm
  verification. No external notification delivery is claimed.
- Human assessment: the user selected the increment and personally created their
  local SigNoz account. Independent code/content review remains pending; account
  setup is not a claim of review or approval of generated implementation.

## 2026-11-08: individual logins and two application roles

- Student responsible: to be confirmed by the contributing group member.
- Tool/model: Codex; exact runtime model/version not recorded in the repository.
- Prompt/purpose: implement Technician/Maintenance specialist and Admin access,
  with Admin able to inspect and manage users; preserve the simple prototype.
- Output: individual password/session authentication, CSRF and API role checks,
  user administration UI, forward migration, account history, host bootstrap/recovery,
  authenticated Postman/CI/helpers, integration tests and updated guides.
- Agent validation: real PostgreSQL authorization/revocation/expiry/migration tests,
  actual local Admin and Technician browser views, authenticated HTTP/Postman checks,
  and a complete existing-case comparison before/after the live local upgrade.
  See the PR for exact results and remaining limits; no Azure promotion claimed.
- Scanner follow-up: incident #39832719 was statically traced to a negative
  password-length test (not a usable credential). Fixed test-password literals were
  replaced by generated valid/invalid values; secret scanning remains enabled.
- Human assessment: pending group review. Local generated demo accounts and synthetic
  tests are not evidence of other group members' review or real-world identity checks.

## Entry template

```text
Date and student:
Tool, model/version (or not recorded):
Prompt/purpose:
Affected files, commit or PR:
Validation evidence:
Human assessment, adaptations and remaining limitations:
```
