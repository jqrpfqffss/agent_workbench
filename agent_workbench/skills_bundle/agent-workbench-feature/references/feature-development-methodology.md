# Feature Development Methodology

Use this document when OpenCode needs to implement a non-trivial STM32 feature with `agent_workbench`.

## Feature Decomposition Model

Before editing code, decompose the request into these dimensions:

- user intent: what behavior the user expects
- control surface: CLI command, diag request, API call, interrupt, timer, or external event
- state surface: variables, flags, handles, counters, peripheral registers, or persistent settings
- hardware surface: pins, clocks, channels, DMA streams, IRQ lines, buses, or external devices
- observability surface: CLI status, diag response, monitor item, log line, or assertion
- regression surface: existing commands or behaviors that might break

The implementation and verification notes should make these surfaces visible whenever they matter.

## Implementation Strategy

Use a vertical-slice sequence:

1. discover current project facts with `doctor` and `scan-project`
2. use `context` and source reading to find the smallest implementation scope
3. implement only one behavior path first
4. add one visible ack or status signal
5. build
6. flash when firmware changed or board evidence matters
7. verify the first slice through UART, diag, or monitor evidence
8. add boundary and regression probes

Avoid starting with broad architecture changes unless discovery proves the existing structure cannot support the requested behavior.

## STM32-Specific Risk Checklist

Check these before claiming a feature is implemented:

- clock source and peripheral clock enable are correct
- GPIO mode and alternate function are project-specific, not guessed
- IRQ handlers and callback paths are registered when interrupts are used
- DMA ownership and buffer lifetime are clear when DMA is used
- shared UART or CLI output remains automation-friendly
- feature state can be queried or monitored
- existing ready banner, prompt, and probe commands still work

## Runtime Verification Quality

A good feature validation path should include:

- exact source files discovered from the current project
- exact commands or probes that exercise the feature
- stable strings or monitor items that prove success
- at least one regression check when touching shared CLI, UART, timing, or interrupt paths

## Validation Strategy

For hardware-visible features, combine evidence types:

- build evidence proves the firmware can be produced
- CLI or diag evidence proves the behavior can be exercised
- monitor evidence proves runtime state when text output is insufficient
- compare evidence proves existing behavior did not drift

## When To Ask For Human Input

Ask only when discovery cannot answer a material decision:

- which physical board or connector is attached
- whether hardware flash/reset evidence was collected
- which external device behavior should count as pass

Do not ask for source paths, command names, or config values that `scan-project`, `doctor`, current source, or runtime evidence can discover.
