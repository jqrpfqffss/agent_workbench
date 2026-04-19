---
name: agent-workbench-general
description: Use for any STM32 task driven by agent_workbench: select task yaml, run PowerShell-safe workbench commands, use staged context packs, perform evidence-first validation, and summarize results without hallucinating.
---

# Agent Workbench General

Use this skill when the repository contains `agent_workbench/agent_workbench.yaml` and the user wants any automation workflow such as debug, test, feature work, or direct verification.

## First Read

Read only the smallest control files first:

- `agent_workbench/agent_workbench.yaml`
- the selected task yaml under `agent_workbench/tasks/`
- `agent_workbench/runtime/direct_verify_summary.md` if it exists
- otherwise the latest `session_verdict.json` or `session_brief.md`

Do not start by reading README, large guides, or many evidence files unless the task truly needs them.

## PowerShell Safe Rule

When the shell is PowerShell, always execute batch entry points like this:

```powershell
cmd /c ".\agent_workbench.bat <subcommand> ..."
```

Never do any of these:

- `cd ... && agent_workbench.bat ...`
- bare `agent_workbench.bat ...` in PowerShell
- long multi-command chains joined by `&&`

Assume the working directory is already the repo root unless evidence says otherwise.

## Task Selection

- If the user names a task file, use it.
- Otherwise inspect `agent_workbench/tasks/` and choose the closest match.
- State the assumed task path in one short sentence before running substantial work.

## Preferred Flows

### Fastest Current Validation

Use this first when the user mainly wants to know whether the current project passes:

```powershell
cmd /c ".\agent_workbench.bat verify current --task <task.yaml>"
```

Then read:

- `agent_workbench/runtime/direct_verify_summary.md`
- `agent_workbench/runtime/direct_verify_summary.json`

### Staged Low-Context Flow

Use this when the user wants analysis, implementation, or stepwise work:

```powershell
cmd /c ".\agent_workbench.bat context --mode <debug|feature|test> --stage <analyze|implement|verify> --task <task.yaml>"
```

Then read only the newest `*_paste.md` under `agent_workbench/runtime/`.

### Resume Flow

When the chat is getting full:

```powershell
cmd /c ".\agent_workbench.bat context --stage resume"
```

Read only the newest `*_resume.md` and `*_paste.md`.

## Evidence Priority

Prefer evidence in this order:

1. `direct_verify_summary.md`
2. `direct_verify_summary.json`
3. `session_verdict.json`
4. `session_brief.md`
5. `session_summary.md`
6. `feature_summary.md`
7. `assertions.jsonl`
8. `cli_transcript.log`
9. `cli_diag.json`
10. `compare_brief.md`
11. `compare_vs_*.md`

## Guardrails

- Evidence before code changes.
- If `doctor`, `build`, or `test run` fails, stop and report that layer first.
- If UART/COM is unavailable, report environment blocking, not source failure.
- If `cli_diag.json` provides a classification code, use it.
- Do not invent results that are not present in evidence files.
- Do not widen the scope beyond the user task.

## Default Output

Respond in this order:

1. Result
2. Evidence chain
3. Failure layer
4. Next step
