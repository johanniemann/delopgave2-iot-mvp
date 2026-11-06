# Using and maintaining the agent setup

## Start here

1. Accept the repo invitation. Clone the repo or pull the merged setup from main.
2. Open this repo's root folder in your preferred coding tool. Do not open only a
   source subfolder or the entire surrounding school folder as the project.
3. Read README and CONTRIBUTING. Use Git and Python 3.10+ to run the three setup checks
   listed there. Running the app additionally uses Docker as described in README.
   No agent packages or shared agent credentials are required. Each contributor chooses and signs in to their own agent separately.
4. Start a fresh agent session and ask: "Read AGENTS.md and the relevant project and
   course context. State the current implementation status, authority order and checks
   you can run. Do not edit files yet." Confirm the answer before delegating a task.
5. Create a task branch and give one bounded task with acceptance examples. Use the
   common inspect -> plan -> implement -> validate -> review workflow in CONTRIBUTING.

Before this setup is merged, fetch and check out its PR branch instead of assuming
it is on main. After merge, normal `git pull --ff-only` brings it to existing clones.

## Files and loading

| File | Role |
| --- | --- |
| [AGENTS.md](../AGENTS.md) | Single canonical policy for project work |
| [CLAUDE.md](../CLAUDE.md) | Native `@AGENTS.md` import, no duplicated project rules |
| [Copilot adapter](../.github/copilot-instructions.md) | Requests that Copilot read the shared policy; not an automatic Markdown import |
| [Project context](project-context.md) | Actual status, intended scope, open technology decisions, broader domain context |
| [Course context](course-context.md) | Portable requirements and source register, without copying course PDFs |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | Reusable task/PR/review/handoff workflow for humans and agents |
| [AI-use notes](ai-use.md) | Evidence for the course's required AI-use documentation |
| [PR template](../.github/pull_request_template.md) | Small review checklist and evidence prompts |
| [Repository checker](../scripts/check_repository.py) and [tests](../scripts/test_check_repository.py) | Check local Markdown links/anchors, imports and portability; exercise error cases |
| [Guidance workflow](../.github/workflows/repository-checks.yml) | Runs setup checks on push/PR |
| [Application workflow](../.github/workflows/application-checks.yml) | Real PostgreSQL tests, Docker build/deployment and HTTP smoke check in an isolated CI project |
| [Development](development.md) and [API contract](api.md) | Real app commands, architecture, inputs and state rules |
| [.gitignore](../.gitignore) | Excludes common local state and secret files; not a secret scanner |

### Verified formats and per-tool onboarding

Documentation checked 2026-11-06. Format compatibility is documentation-verified;
we have not run all four products or every teammate's version/settings.

- **Codex:** open/start in the repo root. It discovers root AGENTS.md. Global and
  override files can affect precedence; use the discovery check above and inspect
  loaded instructions in your client. No `.codex/config.toml` or permission overrides
  are necessary. [Official discovery documentation](https://developers.openai.com/codex/guides/agents-md).
- **Claude Code:** start in the root. CLAUDE.md imports the same AGENTS.md through
  documented `@path` syntax. Current versions also support native AGENTS discovery,
  but it is version/settings dependent; the import covers those differences without
  symlinks (which are awkward on Windows). Use `/context all` to confirm the memory
  file and read shared context. Managed-only modes can disable project instructions.
  [Official memory/import documentation](https://code.claude.com/docs/en/memory).
- **Cursor Agent:** open the repo root; current documentation supports root and
  nested AGENTS.md. Ask the discovery prompt and inspect applied instructions in
  the client. No `.cursorrules` or redundant `.mdc` files are needed.
  [Official rules documentation](https://cursor.com/docs/rules).
- **GitHub Copilot:** for VS Code agent mode, open the repo root with repository
  instructions enabled. The `.github` adapter explicitly asks it to open AGENTS.md;
  supported agent surfaces also discover AGENTS.md natively. Inspect the response's
  instruction references and use the discovery prompt. If the surface cannot follow
  links, attach AGENTS.md and task-relevant docs explicitly. Do not assume inline
  completion, code review and every IDE share the same instruction features.
  [IDE documentation](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions-in-your-ide/add-repository-instructions-in-your-ide?tool=vscode),
  [GitHub/cloud instructions](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/add-custom-instructions/add-repository-instructions).

A file loading successfully is not proof that every generated change follows it.
Review the diff and run checks. Local/global instructions and product settings are
not managed by this repo. Never weaken them to make a task run unattended.

## Research decisions

| Practice and maturity | Decision for this repo |
| --- | --- |
| Established inspect/plan/validate/review and small increments | Shared workflow plus observable acceptance criteria, test evidence and human PR review |
| Documented AGENTS convention, with differing product discovery | One root policy plus two tiny adapters; no claims of identical cross-tool precedence |
| Progressive disclosure via links and skills | Short root policy; source/context/procedure docs read as needed. No repeated multi-step task yet warrants custom skills |
| Hierarchical instructions | Supported future option. No nested files until real source areas need different rules; repeat critical boundaries locally if a client's loading semantics require it |
| Runtime sandbox, least privilege and deterministic CI | Keep tool controls; read-only CI token, pinned checkout, no persistent credentials, no production secrets |
| Parallel agents and handoffs | Optional isolated branches/worktrees and bounded ownership; human review stays necessary |
| Agent-specific hooks, MCP servers, background swarms, remote memory | Deferred: no demonstrated need in this small prototype, extra permissions/dependencies/maintenance |
| Autonomous deployment or agent self-approval | Not enabled; neither instructions nor a model's review replaces release authorization or independent human review |

The general idea of shared Markdown guidance is established; cross-vendor AGENTS
loading is a documented, evolving convention. Autonomous orchestration and persistent
agent services remain unvalidated for this project and are not adopted.

Research behind these choices:

- [OpenAI customization/skills](https://learn.chatgpt.com/docs/customization/overview):
  metadata-first discovery and on-demand procedures. We use ordinary shared docs until
  a stable repeatable procedure justifies a skill package.
- [Claude Code practices](https://code.claude.com/docs/en/best-practices): concise
  repo-specific context and evidence-based checks; distinguish model instructions
  from deterministic enforcement. This is why CI and human review accompany policy.
- [Cursor rules](https://cursor.com/docs/rules): focused guidance and references,
  avoid copying code/style guides into prompts.
- [GitHub Flow](https://docs.github.com/en/get-started/using-github/github-flow): short
  branches and reviewable changes. It is our working convention, not mandated GitFlow.
- [GitHub Actions secure use](https://docs.github.com/en/actions/reference/security/secure-use):
  least-privilege tokens, immutable action references and no privileged PR execution.
  The workflow pins [checkout v7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1)
  to the release commit verified with `git ls-remote`; updates need review.

## Keep it maintainable

Update the existing source of truth rather than adding a second rule file. New course
material should update the source register and affected acceptance criteria together.
Keep framework/database/runtime choices and actual commands in project context and
development instructions. Maintain application validation; never present guidance
checks alone as full CI/CD.
Use small decision notes for consequential architecture changes, linked from project
context. Keep sensitive task details and credentials out of shared instructions.
If tool behaviour changes, recheck official documentation, update this matrix and
repeat the per-tool discovery check on the affected clients.
