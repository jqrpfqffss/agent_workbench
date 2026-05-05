# Debug Command Playbook

## When To Use `uart exec`

Use it when:

- you need ready banner or prompt confirmation
- the feature is surfaced through CLI commands
- you want the simplest transcript-backed smoke check

Command selection rule:

- first use `scan-project` probe commands
- otherwise choose one harmless status-style command
- add one feature-specific command when the changed behavior is CLI-visible

## When To Use `diag exec`

Use it when:

- the protocol is not standard CLI text
- the repo already defines diagnostic requests
- the failure is below the normal command parser layer

Do not invent diag requests. Only use requests already defined by the current project.

## When To Use `monitor probe`

Use it when:

- runtime state is not fully visible from CLI output
- you need variable, register, or memory-backed confirmation
- a feature should change counters, flags, state variables, or registers

If needed items are missing, OpenCode should edit `agent_workbench/agent_workbench.yaml` and then run `monitor probe --json`.

## When To Use `compare --latest`

Use it when:

- the behavior used to pass
- a regression is suspected
- assertions, CLI output, or monitor values drift between sessions

## When To Use `report --latest`

Use it when:

- you need the latest verdict, summary, and evidence pointers collected in one place

## Suggested Minimal Sequences

- CLI handshake issue: `doctor` -> `uart exec` -> `report --latest`
- Parser issue: `doctor` -> `build` -> `uart exec` -> read `cli_diag.json`
- Runtime state mismatch: `doctor` -> `build` -> update monitor YAML -> `monitor probe` -> `report --latest`
