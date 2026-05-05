# Monitor Configuration

Use monitor whenever a feature or failure needs runtime state that is not visible through UART text alone: counters, state variables, flags, control outputs, memory-mapped registers, CPU registers, or trends over time.

OpenCode should configure monitor automatically by editing `agent_workbench/agent_workbench.yaml`. Do not ask the user to manually add monitor items.

## Configuration Checklist

Before `monitor probe` or `monitor run`:

1. Run `doctor --json` and `scan-project --json`.
2. Run `build --json` so the ELF and symbols are current.
3. Confirm the configured ELF in `monitor.symbols.path` or `monitor.symbols.elf_path` points to the same firmware artifact that was built and flashed.
4. Ensure `monitor.enabled: true`.
5. Add only the items needed for the current investigation.
6. Run `monitor probe --json` first; only run longer sampling after every item is readable or the unreadable items have been intentionally removed.

## Item Types

Global symbol:

```yaml
monitor:
  enabled: true
  symbols:
    path: build/cmake-debug/<firmware>.elf
    elf_path: build/cmake-debug/<firmware>.elf
  items:
    - name: app_state
      source: symbol
      symbol: g_app_state
      value_type: u32
```

Field inside a global structure, using byte offset:

```yaml
    - name: control_error
      source: symbol
      symbol: g_control
      offset: 8
      value_type: s32
```

Raw memory or peripheral register address:

```yaml
    - name: tim_ccr1
      source: memory
      target: 0x40012C34
      value_type: u32
```

CPU register:

```yaml
    - name: pc
      source: register
      target: pc
      value_type: u32
```

Supported value types commonly include `u32`, `s32`, `float`, `u16`, `s16`, `u8`, and `s8`.

## How To Discover Items

- Prefer stable global `volatile` variables, counters, flags, and state structs that already exist in the current project.
- If a variable is local-only and must be observed, make the smallest safe source change to expose a debug counter or state mirror with a stable name.
- Confirm symbols after build using the ELF/map file or toolchain symbol output. Do not assume a symbol exists because it appears in source.
- For peripheral registers, derive addresses from the current MCU's CMSIS headers, generated device headers, linker map, or explicit project documentation. Do not reuse STM32F1 example addresses in a migrated project.
- For CPU registers, use names supported by the debug backend, such as `pc`, `sp`, and general registers, only when they answer the current question.

## Good Monitor Design

- Keep item count small during triage: 3 to 8 high-signal items is usually better than dumping everything.
- Name items by meaning, not just source, for example `motor_pwm_duty` instead of `var1`.
- Include at least one liveness signal, such as a tick counter, loop counter, command counter, or state transition counter.
- Pair cause and effect when possible: command counter plus state variable, input flag plus output register, error code plus retry counter.
- For trend tests, define the expected direction or range before reading the samples.

## Failure Handling

- Symbol not found: rebuild, verify ELF path, check spelling and visibility, then inspect map/symbol output.
- Read timeout: verify OpenOCD/debug connection and target run state, then try `monitor probe` with one item.
- Constant zero: decide whether it is a legitimate value, reset state, stale ELF, dead code path, or optimizer issue.
- Peripheral address invalid: re-derive from current MCU headers instead of copying an example.
- Samples missing: read monitor artifacts and `doctor_report.json` before changing source.
