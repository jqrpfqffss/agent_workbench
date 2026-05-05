# Debug Experiment Playbook

Use this document to turn a failure into a sequence of small, evidence-producing experiments.

## Experiment Rule

One experiment should answer one question.

Each experiment should define:

- hypothesis
- command or artifact
- expected observation
- interpretation if pass
- interpretation if fail
- next action

## Experiment Template

```markdown
Hypothesis: <specific cause>
Probe: <agent_workbench command or artifact to inspect>
Expected if true: <observable evidence>
Expected if false: <observable evidence>
Decision: <what OpenCode should do next>
```

## Layered Experiments

### Environment Experiment

Question:

- can the workbench operate in this project?

Probe:

- `doctor`

Interpretation:

- fail count above zero means no source diagnosis is trustworthy yet

### Build Experiment

Question:

- can the current firmware be built?

Probe:

- `build`
- `fix-build` if needed

Interpretation:

- compiler or linker failures block runtime investigation

### Flash Experiment

Question:

- can the target be programmed and booted?

Probe:

- `flash` when firmware must be reloaded
- `reset` when supported
- `commands.log`

Interpretation:

- flash failure is a hardware or tooling blocker until proven otherwise

### UART Handshake Experiment

Question:

- can the host observe firmware startup and command prompt?

Probe:

- `uart exec` with scan-derived, source-derived, or user-request-derived probe commands
- `cli_diag.json`
- `cli_transcript.log`

Interpretation:

- `rx_zero` points to connectivity or wrong firmware path
- `ready_missing` points to boot/startup contract
- `prompt_missing` points to CLI lifecycle

### Command Dispatch Experiment

Question:

- does the command reach the expected handler?

Probe:

- command-specific `uart exec`
- command table from `scan-project`
- CLI transcript

Interpretation:

- listed in help but no response suggests handler path
- not listed in help suggests registration or build inclusion

### Runtime State Experiment

Question:

- did the firmware state change after the command or trigger?

Probe:

- status command
- `monitor probe`
- `diag exec`

Interpretation:

- command ack without state change suggests behavior path
- state change without output suggests observability or response formatting

### Regression Experiment

Question:

- what behavior drifted from a previous session?

Probe:

- `compare --latest`
- `compare_delta.json`

Interpretation:

- changed CLI lines point to response contract drift
- changed monitor values point to runtime behavior drift
- new assertion failures point to acceptance mismatch or real regression

## Debug Discipline

- Do not run three experiments at once unless the result can still be interpreted.
- Do not change source code between baseline and diagnostic probes unless the experiment is a source patch.
- Record the artifact path that answered the question.
- Prefer experiments that reduce the search space by half or more.
