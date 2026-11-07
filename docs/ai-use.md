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
  shutdown time. Independent review of this deployment change is still pending.

## Entry template

```text
Date and student:
Tool, model/version (or not recorded):
Prompt/purpose:
Affected files, commit or PR:
Validation evidence:
Human assessment, adaptations and remaining limitations:
```
