---
name: agent-workbench-feature
description: Use for task-driven feature implementation or feature validation in STM32 projects that use agent_workbench, with staged context packs, minimal edits, and evidence-first verification.
---

# Agent Workbench Feature

Use this skill when the user wants feature work tied to a task yaml: implement a small change, validate a feature, or close the loop with session evidence.

## Decide The Path

### Validation Only

If the user mainly wants to validate the current feature state, use:

```powershell
cmd /c ".\agent_workbench.bat verify current --task <task.yaml>"
```

This is the default validation path.

### Implementation + Validation

If the user explicitly wants code changes, use the staged feature flow:

```powershell
cmd /c ".\agent_workbench.bat context --mode feature --stage implement --task <task.yaml>"
```

Read only the newest `*_paste.md`, then:

- edit only `allowed_edits`
- keep the change minimal
- preserve stable strings listed in the task or implementation brief

After the edit, validate with:

```powershell
cmd /c ".\agent_workbench.bat verify current --task <task.yaml>"
```

Use the longer explicit flow only when needed:

```powershell
cmd /c ".\agent_workbench.bat test generate --task <task.yaml>"
cmd /c ".\agent_workbench.bat test run"
cmd /c ".\agent_workbench.bat session feature --task <task.yaml>"
cmd /c ".\agent_workbench.bat compare --latest"
cmd /c ".\agent_workbench.bat report --latest"
```

## Read These First

- task yaml
- generated `implementation_brief.md`
- `direct_verify_summary.md` if available
- otherwise latest `session_verdict.json` and `feature_summary.md`

## Guardrails

- Respect `implementation.read_candidates`.
- Respect `implementation.edit_candidates`.
- Respect `implementation.max_edit_files`.
- Keep help text, prompts, ready banners, and assertion strings stable unless the task explicitly changes them.
- Do not use large ad-hoc shell chains.

## Output

Respond in this order:

1. Feature result
2. Evidence chain
3. Change scope
4. Validation result
5. Next step
