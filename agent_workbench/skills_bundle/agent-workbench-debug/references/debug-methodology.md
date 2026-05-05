# Debug Methodology

Use this document when you need more than a simple command sequence.

## Core Principle

Debug from the outside in. Do not start by editing source code.

Classify the failure layer first:

1. command launcher
2. environment and tooling
3. build and link
4. flash and boot
5. UART handshake
6. CLI parser and dispatch
7. feature behavior
8. observability and host capture
9. regression drift

## Debug Output Contract

When OpenCode reports a debug finding, include:

- symptom
- layer
- strongest evidence
- top 2-3 hypotheses
- next confirming command or artifact
- whether source edits are justified yet

## Efficient Debug Funnel

### 1. Confirm Command Launcher

Run the preferred batch form. If it fails before workbench starts, retry with direct Python. Do not treat launcher failure as firmware failure.

### 2. Confirm Environment And Tooling

Run `doctor`. Confirm config paths, flash tooling, UART settings, monitor readiness, and artifact locations.

If this layer fails, stop and report the environment blocker.

### 3. Confirm Build Health

Run `build`, then `fix-build` only if the build failed.

Goal: avoid runtime theories when the binary is not trustworthy.

### 4. Confirm Flash And Boot

Use `flash`, `reset`, and latest report artifacts when the failure may be on hardware.

Goal: distinguish "firmware never ran" from "firmware ran but behaved incorrectly".

### 5. Confirm UART Handshake

Run `uart exec` with scan-derived or source-derived probe commands.

Interpretation:

- no bytes: environment or connectivity first
- ready missing: boot or startup contract first
- prompt missing: CLI lifecycle first

### 6. Localize Parser Or Dispatch Problems

Read `cli_diag.json`, `cli_transcript.log`, and current CLI source ownership from `scan-project`.

Common hypotheses:

- command not registered
- parser strips or splits input incorrectly
- handler never reached
- handler ran but stable response drifted

Choose the smallest confirming action before editing code.

### 7. Validate Feature Behavior

If the CLI path is healthy but behavior is wrong, compare the expected behavior contract against actual output.

Use `monitor probe` when the CLI does not expose runtime state cleanly.

Examples:

- control command succeeds but status command is wrong
- command output is right but monitor values never change
- monitor values change but assertion strings drifted

### 8. Separate Observability Failure From Real Feature Failure

Use this when UART, diag, or monitor evidence is absent. Avoid claiming a firmware bug when the evidence path is the real problem.

### 9. Check For Regression Drift

Run or read `compare --latest`, `compare_delta.json`, and `compare_brief.md`.

Identify what changed: output text, prompt behavior, warning-like lines, assertion count, monitor values, or command timing.

## Hypothesis Management

For each failure:

1. write the strongest observed symptom
2. list 2-3 likely causes
3. choose one confirming command or artifact
4. patch code only after evidence points to source behavior

## Layer-To-Tool Map

- command launcher: batch form, direct Python fallback
- environment and tooling: `doctor`
- build and link: `build`, then `fix-build`
- flash and boot: `flash`, `reset`, `report --latest`
- UART handshake: `uart exec`, `cli_diag.json`, `cli_transcript.log`
- CLI parser and dispatch: `scan-project`, `cli_diag.json`, CLI source ownership
- feature behavior: `verify current`, feature-specific CLI or diag command, monitor samples
- observability and host capture: `monitor probe`, `diag exec`, transcript review
- regression drift: `compare --latest`, `compare_delta.json`

Bad debug behavior:

- edit code before reading evidence
- rerun long command chains without learning from artifacts
- assume UART, flash, or monitor is healthy because source looks reasonable

Good debug behavior:

- use verdict and diagnostics to cut the search space
- confirm one layer at a time
- stop immediately on hardware or environment blockers
