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

## Entry template

```text
Date and student:
Tool, model/version (or not recorded):
Prompt/purpose:
Affected files, commit or PR:
Validation evidence:
Human assessment, adaptations and remaining limitations:
```
