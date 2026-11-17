# Working together

## Branches: feature -> dev -> main

The team selected this strategy on 2026-11-17, including for the exam project:

- `main`: stable release/production code.
- `dev`: integrated development and validation.
- `feature/*`: individual or focused task development, created from `dev`.

Inspect your working tree first and preserve unfinished work. With a clean checkout:

```sh
git switch dev
git pull --ff-only origin dev
git switch -c feature/short-task-name
```

Push ongoing work to the feature branch, open a PR **to `dev`**, obtain another
member's review, then merge after the required checks pass. When integration is
ready for release, open a separate **`dev` -> `main` PR**. Release the tested image
for that approved commit. See [release and recovery](docs/release.md).

Names such as `feature/johan`, `feature/esben`, `feature/nix` and `feature/bilal`
match the team's diagram. Agree task ownership before sharing a branch; a focused
suffix is useful when one person has multiple tasks. No direct development on main.

## A change from request to review

1. Read AGENTS.md and the task-relevant course/project context. State scope and
   acceptance criteria; record material assumptions before implementing them.
2. Implement a small complete increment. Agree API contracts and rule examples before
   coupling code to them. Explain new dependencies or architectural changes.
3. Run relevant checks locally. For behaviour changes, add regression/boundary tests;
   for docs-only changes, use repository checks and review accuracy manually.
4. Inspect `git diff` and stage only the intended files. Commit a descriptive change
   (for example, `fix: reject negative sensor readings`). Commit saves locally.
5. Push your task branch and open a PR to `dev` when authorized. Push sends commits;
   the PR proposes integrating them. Include acceptance evidence and AI-use details.
6. A different group member reviews the code, meaning and test results. Resolve
   feedback; reassess approval after substantive changes. The author cannot supply
   an independent review with their own agent.
7. After human approval and successful applicable checks, an authorized person merges
   (prefer squash for one focused change). Delete the completed branch, then update
   local dev with `git pull --ff-only origin dev` before the next task.

Current setup checks, from the repo root (Git and Python 3.10+, standard library only):

```sh
python3 -m unittest discover -s scripts -p 'test_*.py'
python3 scripts/check_repository.py
git diff --check
```

On Windows use the installed `python` or `py -3` equivalent. For application changes
also run `docker compose --profile test run --rm --build tests`; with the app running,
run `python3 scripts/smoke_test.py`. See [development instructions](docs/development.md).
Review normal/error paths, rule boundaries and actual PostgreSQL persistence. A
guidance-check pass alone is not an API test or deployment result.

## Review and deployment boundaries

The intended main-branch guardrails are PRs, one other member's approval, successful
required checks, resolved conversations, and no force-push or deletion of main.
On 2026-11-17 GitHub explicitly reported that the saved main rule is not enforced
under the current private-repository plan. These remain **team review/merge rules**
until effective hosting enforcement is available and verified. Do not change plan,
visibility or access as an implicit workaround. Private-repo
rule enforcement depends on the owner's GitHub plan. Do not claim rules are active
because a Markdown file describes them. No agent should bypass a failing check.

CI checks guidance, real PostgreSQL behaviour, Docker builds and an isolated local
deployment/HTTP smoke test. Keep PR verification separate from shared/production
release/deployment. Do not give PR jobs production
secrets or deploy arbitrary feature branches. Test/build/publish/deploy are distinct
operations, and real infrastructure changes require the task's authorization.

## Multiple people or agents

Each person uses their own GitHub account and agent. Agree task ownership before
parallel edits. For concurrent tasks use separate clones/worktrees and branches,
not multiple agents modifying the same checkout. Coordinate shared contracts and
migrations before splitting implementation. A handoff should include:

- Goal, acceptance examples and relevant course/source/decision IDs.
- Branch/commit, files changed, and any files another contributor is editing.
- Exact checks run, outcomes, remaining risks and next action.

An additional agent review is useful feedback; another group member still performs
the human review. Subagents inherit this project's context and authorized scope;
delegation does not authorize deployments, access changes or extra features.

## Evidence and documentation

Update contract/docs when behaviour changes, project context when a decision becomes
real, and [AI-use notes](docs/ai-use.md) for substantive generated contributions.
Use the PR template to link requirements, show validation and identify human review
still needed. Keep synthetic examples clearly labelled. Record unresolved thresholds,
units, data policies and integrations instead of inventing customer requirements.

## Routine maintenance

Edit shared policy in AGENTS.md, facts/decisions in project context, source evidence
in course context, and tool guidance in the agent setup guide. Keep adapters thin.
Use a focused PR for instruction changes. Remove stale rules and commands as the code
changes; add directory-specific instructions only when a real area needs a different
rule. Verify links, onboarding and discovery after changing any entry point.
