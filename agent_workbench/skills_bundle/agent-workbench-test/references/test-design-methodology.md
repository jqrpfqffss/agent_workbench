# Test Design Methodology

Use this document to design professional runtime-verifiable STM32 validation.

## Core Principle

A good automated test proves behavior, not implementation trivia.

Design tests so that OpenCode can answer these questions:

1. what user-visible behavior should hold
2. what command or probe exercises it
3. what evidence proves it
4. what failure message will be most useful if it breaks

## Coverage Model

For each feature or regression target, try to cover these dimensions when they matter:

### 1. Happy Path

- the expected command or trigger works
- the feature reports success in a stable way

### 2. State Visibility

- there is a status command, monitor signal, or deterministic output that exposes the resulting state

### 3. Boundary Or Range Behavior

- values near limits
- on/off or enabled/disabled transitions
- valid min, nominal, and max when the feature accepts parameters

### 4. Invalid Input Or Misuse

- unsupported command arguments
- malformed CLI input
- missing parameters

Only include these when the feature actually exposes an input surface.

### 5. Regression Surface

- help output still lists the command
- prompt and ready behavior remain stable
- existing commands still work if the feature touched shared paths

### 6. Observability

- if the feature changes runtime state, decide whether CLI output alone is enough
- if not, add monitor-based or diag-based confirmation

## Test Case Types

Use these case types as a checklist. Include only the types that match the feature's risk.

### Smoke Case

Purpose:

- prove the board or host path can exercise the feature at all

Typical evidence:

- ready and prompt
- one command ack
- one status line

### Functional Case

Purpose:

- prove the requested behavior works under nominal inputs

Typical evidence:

- CLI response
- diag response
- monitor value

### State Transition Case

Purpose:

- prove enable, disable, toggle, start, stop, reset, or mode transitions work

Typical evidence:

- command sequence plus status confirmation
- monitor last value before and after

### Boundary Case

Purpose:

- prove limits are handled safely

Typical evidence:

- min, nominal, max values
- invalid value rejection when applicable

### Regression Case

Purpose:

- prove shared behavior was not broken

Typical evidence:

- existing help/status/probe commands still pass
- `compare_delta.json` shows no unexpected drift

### Fault Or Negative Case

Purpose:

- prove invalid input fails predictably

Typical evidence:

- stable error string
- no timeout
- prompt recovery

## How To Write Strong Assertions

Prefer assertions that are:

- short
- deterministic
- single-purpose
- easy to diagnose

Good examples:

- one CLI ack string
- one status label
- one monitor range
- one file existence check for generated evidence

Each assertion should have a diagnostic purpose. If it fails, OpenCode should know which layer to inspect next.

Weak examples:

- multi-line prose blocks
- unstable timestamps
- assertions that combine several independent behaviors into one vague string match

## How To Choose Evidence Type

### Use CLI Assertions When

- the behavior is intentionally user-visible
- the command path is the behavior surface

### Use Monitor Assertions When

- the runtime state matters more than the text output
- exact counters, flags, or values must be confirmed

### Use Unit Expectations When

- command registration, parser behavior, or small deterministic logic needs host-side coverage

### Use Verify Current When

- you need the whole chain:
  - build
  - tests
  - UART behavior
  - evidence summary

### Use Real Hardware Evidence When

- the behavior depends on pins, clocks, interrupts, DMA, UART, ADC, timers, or external devices
- a host test can only prove command parsing, not board behavior

## Runtime Test Design Checklist

Before executing tests, confirm the test design answers these:

1. what files are in scope
2. what CLI or diag commands exercise the behavior
3. what stable strings must not drift
4. what runtime signals matter
5. what should count as pass or fail

## Coverage Matrix Requirement

For complex work, OpenCode should draft a small coverage matrix before executing or accepting tests.

The matrix should connect:

- behavior
- stimulus
- expected evidence
- assertion type
- evidence artifact
- likely failure layer

Use [test-coverage-matrix.md](test-coverage-matrix.md) for the required shape.

## Best Practice For Generated Assets

When OpenCode reviews runtime tests:

- check whether each assertion maps to one behavior
- remove duplicate assertions
- keep acceptance centered on behavior that matters to users or system stability
- expand coverage only where the feature actually exposes risk

## Failure Interpretation

If a test fails, do not jump straight to source edits.

Ask:

1. is the test design wrong
2. is the probe or assertion too weak or too strong
3. is the source behavior wrong
4. is the environment blocking the evidence path
