---
name: agent-workbench-toolbox
description: Use when a repository contains agent_workbench/agent_workbench.yaml and Codex or OpenCode needs the command matrix, stable PowerShell invocation, monitor configuration guidance, runtime evidence map, or failure routing for STM32 automation workflows. This is the base skill for build, flash, reset, UART, diag, monitor, verify, report, compare, context, and session commands.
---

# Agent Workbench Toolbox

Use this as the base skill for any STM32 repository driven by `agent_workbench`.

This skill does not decide the feature, debug, or test strategy. It teaches OpenCode how to invoke `agent_workbench`, how to configure runtime probes, and how to read evidence without relying on project-specific paths copied from examples.

## First Rules

- Treat `agent_workbench` as the primary control plane.
- Prefer the inner batch entry from the repository root: `.\agent_workbench\bin\agent_workbench.bat <command> --json`.
- Do not write `".\agent_workbench\bin\agent_workbench.bat" <command>`; PowerShell treats that as a string. Use `& ".\agent_workbench\bin\agent_workbench.bat" <command>` only when the path must be quoted.
- If the batch entry fails because OpenCode or PowerShell mis-parses it, immediately retry with the direct Python fallback: `python ".\agent_workbench\workbench.py" <command> --json`, then `py -3 ".\agent_workbench\workbench.py" <command> --json` if needed.
- Do not use `cmd /c ".\agent_workbench.bat ..."` as the default form; it has proven fragile in OpenCode sessions.
- Read structured artifacts before inferring state from source code.
- Do not ask for user approval before flash, reset, UART, diag, monitor, verify, report, or compare. Run the needed workbench command directly unless the environment blocks it.

## First Command

Start from the repository root:

```powershell
.\agent_workbench\bin\agent_workbench.bat doctor --json
```

If that fails because of command invocation, retry:

```powershell
python ".\agent_workbench\workbench.py" doctor --json
```

Then choose the next command from [references/command-matrix.md](references/command-matrix.md).

## Read Next

Read only the reference file needed for the current work:

- Command selection and JSON fields: [references/command-matrix.md](references/command-matrix.md)
- Stable OpenCode command invocation: [references/opencode-command-execution.md](references/opencode-command-execution.md)
- Runtime, evidence, and generated outputs: [references/artifact-map.md](references/artifact-map.md)
- Failure-specific next steps: [references/failure-routing.md](references/failure-routing.md)
- Monitor variable, register, and address configuration: [references/monitor-configuration.md](references/monitor-configuration.md)
- Windows invocation rules: [references/powershell-safe.md](references/powershell-safe.md)
- OpenCode skill orchestration: [references/opencode-orchestration.md](references/opencode-orchestration.md)
- Real hardware verification gate: [references/hardware-verification.md](references/hardware-verification.md)

Always derive project-specific values from the current repository:

- use `doctor` for configured ready banner, prompt, flash method, and enabled subsystems
- use `scan-project` for source paths, CLI commands, handles, symbols, monitor candidates, and project capabilities
- use runtime evidence from `uart exec`, `diag exec`, `monitor probe`, `monitor run`, `verify current`, `report --latest`, and `compare --latest` as the primary validation surface
- when monitor coverage is needed, OpenCode should inspect and edit `agent_workbench/agent_workbench.yaml` itself; do not ask the user to manually add monitor items

## Coordination

- For feature implementation, combine this skill with `agent-workbench-feature`.
- For automated debug, combine this skill with `agent-workbench-debug`.
- For test design or validation, combine this skill with `agent-workbench-test`.

Those workflow skills should reuse this skill's command, monitor, artifact, and failure references instead of repeating them.

When OpenCode is unsure which workflow skill to pair with this toolbox, use [references/opencode-orchestration.md](references/opencode-orchestration.md).

## Guardrails

- Always prefer JSON output.
- Do not invent hardware state, UART state, monitor samples, or verification results.
- Do not invent STM32 timer, GPIO, register, or memory addresses. Discover them from the current project, generated headers, linker map, ELF symbols, CMSIS headers, or explicit user input.
- Stop on environment or hardware blockers and report them explicitly.
- Do not copy example file paths, probe commands, monitor items, or strings from the skill into a new repository without first replacing them from discovery output.
