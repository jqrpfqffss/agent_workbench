# CLI Diagnostic Codes

Use these interpretations after reading `cli_diag.json`.

## `rx_zero`

- Likely no bytes reached the host
- Most likely causes:
  - wrong COM port
  - board not running expected firmware
  - broken UART path

## `parser_no_command`

- Bytes likely arrived
- Most likely causes:
  - command parsing failed
  - command registration is missing
  - dispatch path is broken

## `tx_or_host_rx`

- The target may have processed the command, but the host did not capture a clean response
- Most likely causes:
  - target TX path
  - host receive path
  - framing or transcript capture issue

## `ready_missing`

- Boot path or startup UART behavior did not expose the configured ready banner

## `prompt_missing`

- CLI likely initialized partially, but prompt emission or prompt recovery failed

## `diag_unavailable`

- The diagnostic backend could not produce a reliable classification
- Do not over-claim root cause from this state alone
