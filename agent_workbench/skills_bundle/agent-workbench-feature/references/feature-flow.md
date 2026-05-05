# Feature Flow

## Normal Path

1. Discover the project with `doctor --json` and `scan-project --json`.
2. Read the relevant source, generated headers, linker/map files, and existing runtime evidence.
3. Identify the smallest set of files to change.
4. Preserve stable user-facing strings that automation depends on, especially ready banner, prompt, help/status command names, and documented response prefixes.
5. Implement in user-code-safe regions where the project has generated files.
6. Build, repair narrowly, and rebuild.
7. Flash and run UART/diag probes that exercise the changed behavior.
8. Add monitor items when internal state, registers, counters, or trends are required to prove the feature.
9. Run verify/report/compare and produce the feature report.

## What To Avoid

- Do not derive timer, GPIO, ADC, DMA, or register parameters from memory. Read project configuration, generated headers, CMSIS headers, or existing code.
- Do not validate only through build success.
- Do not ask the user to manually edit workbench config when OpenCode can update it.
- Do not make broad refactors before establishing a passing baseline.

## Evidence Strategy

- CLI feature: UART command response plus transcript.
- Protocol feature: diag exchange plus log/result artifact.
- Runtime state feature: monitor probe/run plus UART or diag trigger.
- Timing/trend feature: monitor samples with expected range or direction.
- Regression-sensitive feature: latest report plus compare delta.
