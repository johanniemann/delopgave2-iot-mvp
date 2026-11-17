# AI-use development record

This records AI assistance in the technical product under course source C3 in
[course context](course-context.md). Record generated code, configuration, tests
and technical documentation with validation and human assessment. Avoid secrets,
full chat exports and unrelated personal information.

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
  notes. Course PDFs remain outside Git.
- Agent validation: checked assignment pages and relevant teaching/exercise sources;
  verified HTTPS/authenticated data and unchanged complete case response after actual
  VM deallocation/startup, inspected the dashboard, then verified deallocation again.
  Diagram inspection and repository checks are part of this change.
- Human assessment: user selected the hosting direction and merge exception.
  The generated explanation still requires human reading, correction and assessment
  before relying on it for technical work; no completed independent review is claimed.

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

## 2026-11-09: GitHub access and local file-copy verification

- Tool: Codex with the connected GitHub plugin.
- Prompt/purpose: create a small test PR to verify project access and check the
  previously downloaded local files.
- Output: this documentation-only log entry on a separate test branch and draft PR.
- Validation: all 68 local project files matched their Git blob hashes at
  `ddd2a510770c320ecc5d22110bbbe0ade1772d5a`, the verified `main` commit.
- Limitation: the local folder is a file copy without `.git` or Git history.
  This checks file contents and the connector PR workflow; it does not verify
  local Git authentication, cloning, fetching or pushing.
- Human assessment: pending; the PR is an access test and has not been approved
  for merge.

## 2026-11-17: pull request workflow test

- Student responsible: to be confirmed by the contributing group member.
- Tool/model: Codex; exact runtime model/version not recorded in the repository.
- Prompt/purpose: create a test pull request to verify that the GitHub connection
  can create a branch, commit a small change and open a PR.
- Output: this documentation-only entry on a separate test branch and draft PR.
- Validation: inspect the PR diff and GitHub checks; results are recorded in the PR.
  Application behaviour is unchanged.
- Limitation: this tests the connected GitHub plugin workflow. The existing local
  checkout is behind main and has uncommitted changes, so local Git authentication
  and pushing are not tested.
- Human assessment: pending; this is a workflow test awaiting human review.

## Entry template

```text
Date and student:
Tool, model/version (or not recorded):
Prompt/purpose:
Affected files, commit or PR:
Validation evidence:
Human assessment, adaptations and remaining limitations:
```


## 2026-11-17 — complete the technical audit gaps

- Request: implement the eight reviewed technical steps using verified evidence.
  No expansion into Better Maintenance or real ML.
- Tool: Codex; exact runtime model/version not recorded.
- Work: isolated clone; dev/feature workflow; external sensor Postman boundaries;
  bounded security logs and privacy regressions; safe SQL composition; locked
  Bandit/pip-audit gate; tested-image artifact/registry and guarded promotion;
  private pg_dump with actual isolated restore/content comparison; release/demo docs.
- Validation so far: 73 real PostgreSQL app tests; 23 helper/safety tests; Newman
  27 requests/46 assertions, zero failures; HTTP smoke; real local dump/restore;
  medium/high Bandit gate and runtime dependency audit passed. Current CI, shared
  promotion and browser acceptance will be recorded after their actual execution.
- Human assessment: pending. A different group member has not reviewed this work
  merely because the agent implemented/tested it. No student review is invented.


### GitGuardian incident 40194040 follow-up

GitGuardian flagged the new log-privacy test's absence assertion at commit 2477572,
line 21. Static tracing found runtime-generated credentials and fixed noncredential
query/username markers, with no usable secret assigned at that location. The test
now generates those markers and invalid CSRF data at runtime too, preserving all
negative/privacy checks. This specific incident is assessed as a false positive;
scanner-wide or test-directory exclusions are not introduced. Source-system status
and current complete PR checks must be verified separately before merge.


## 2026-11-17 — correct release pointer after real Azure verification

- Codex found that resolving the relative `--releases` argument after changing the
  working directory updated `releases/current` instead of the shared `current`.
  The tested image and database were correct; the authoritative pointer was stale.
- Resolve the releases directory once before `chdir`, then reuse that absolute path.
- A regression test drives the full promotion entry point with relative arguments,
  real temporary archives/directories and mocked Docker/network boundaries. It
  reproduced the stale pointer before the fix and now verifies the shared pointer,
  no nested pointer, and preservation of the prior release. All 24 helper tests pass.
- User approved continuing release/deployment and specifically approved the four
  named Aeris accounts/roles plus the temporary test account. PR 12 was merged by
  Denstoerste; no independent review submission is claimed. This follow-up remains
  part of the same authorized release correction.


## 2026-11-17 — observed shared deployment and evidence documentation

- Codex assisted with the approved feature->dev->main release and actual Azure
  promotion of the CI-tested image, source/manifest/checksum verification, private
  dump/isolated restore, forward migration and external HTTPS verification.
- Concrete user approval named Johan/Admin, Esben/Nix/Bilal/Technician and one
  temporary Technician test account. Tests covered forced change,403 roles/CSRF,
  logout/revocation/reset and old bearer 401. Credentials were privately handed over;
  the test account was deactivated. Johan confirmed personal login/password change.
- External Newman passed 27 requests / 46 assertions. Direct SQL correlated sensor input
  and rule events. A real app/database restart preserved all 4 old complete cases
  and the new complete case. Fresh v1/v2 backups restored successfully on the VM;
  the existing pre-migration off-VM copy remains. A further full export was rejected
  by automatic approval review and was not carried out.
- The release pointer error was observed, reproduced and corrected as recorded
  above and in PR 16/17. Documentation is rewritten around actual deployment facts,
  their dates and limits, preserving the earlier results as historical evidence.
- User approvals authorize the concrete release, not a claim of independent review.
  Formal human code/content review, other members' own computer tests, the recording
  and examiner access remain human work. Technical documentation distinguishes
  real implementation from simulation.


## 2026-11-17 — focus technical guidance

- Codex updated source guidance to focus on runtime functionality, contracts,
  operations, tests and contribution procedures. Earlier non-product delivery text
  was removed, and binary Office/reference formats were excluded from source.
- No application, dependency, account, database or infrastructure behaviour changed.
- Repository reference and whitespace checks passed. Existing technical evidence,
  AI-use accountability and the normal independent review rule are preserved.
