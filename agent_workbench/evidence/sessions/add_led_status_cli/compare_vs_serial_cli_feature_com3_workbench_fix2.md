# Session Compare Report

- generated_at: 2026-04-08T11:31:30.132+00:00
- old_session: `H:\stm32_RAG\code\serial\agent_workbench\evidence\sessions\serial_cli_feature_com3_workbench_fix2`
- new_session: `H:\stm32_RAG\code\serial\agent_workbench\evidence\sessions\add_led_status_cli`

## Verdict Delta
- old: `pass` | CLI probe completed successfully.
- new: `fail` | 3 black-box assertions failed.

## UART Metrics
| metric | old | new | delta |
|---|---:|---:|---:|
| lines | 2 | 8 | 6 |
| warn_like | 0 | 0 | 0 |

## CLI Metrics
| metric | old | new | delta |
|---|---:|---:|---:|
| rx_lines | 77 | 68 | -9 |
| diag_code | none | none | n/a |

## Assertion Metrics
| metric | old | new | delta |
|---|---:|---:|---:|
| passed | 10 | 33 | 23 |
| failed | 0 | 3 | 3 |
| skipped | 0 | 0 | 0 |

## Monitor Metrics
| item | old_count | new_count | old_last | new_last | delta_last |
|---|---:|---:|---:|---:|---:|

## New Unique CLI Lines
- �Type 'help' to list commands.
-   led_status Print the on/off state of all LEDs.
- led_status
- LED status:
