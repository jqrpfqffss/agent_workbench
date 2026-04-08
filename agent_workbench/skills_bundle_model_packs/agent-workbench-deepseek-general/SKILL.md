---
name: agent-workbench-deepseek-general
description: Use for DeepSeek local models on agent_workbench STM32 projects. Prefer one-command verification, minimal reads, PowerShell-safe execution, and ultra-short evidence-based output.
---

# Agent Workbench DeepSeek General

Use this skill when the model is DeepSeek and the repo uses `agent_workbench`.

## First Choice

If the user wants the current state, run exactly:

```powershell
cmd /c ".\agent_workbench.bat verify current --task <task.yaml>"
```

Do not create a long command plan first.

## Read Limit

Read in this order and stop as soon as the answer is clear:

1. `agent_workbench/runtime/direct_verify_summary.md`
2. `agent_workbench/runtime/direct_verify_summary.json`
3. if needed, latest `session_verdict.json`
4. if needed, latest `session_brief.md`

Do not start from README or large guides.

## If Code Change Is Explicitly Requested

Only then use staged flow:

```powershell
cmd /c ".\agent_workbench.bat context --mode feature --stage implement --task <task.yaml>"
```

Then read only the newest `*_paste.md`.

## PowerShell Rule

Always call batch files through:

```powershell
cmd /c ".\agent_workbench.bat ..."
```

Never use:

- `cd ... && ...`
- bare `.bat` commands
- multi-line shell chains

## Output Format

Use exactly 4 flat bullets:

- `result: ...`
- `evidence: ...`
- `layer: ...`
- `next: ...`

Each bullet should be one short sentence.

## Guardrails

- Prefer one command over many.
- Prefer summary files over raw logs.
- If blocked by COM port, flasher, or board, say `environment blocked`.
- Do not guess missing evidence.
