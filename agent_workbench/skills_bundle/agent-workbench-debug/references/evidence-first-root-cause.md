# Evidence-First Root Cause Ranking

Use this ranking model after reading the latest verdict and diagnostics.

## Rank 1: Environment Block

Choose this first when:

- `doctor` has failures
- `verify` is `blocked`
- UART port or flash tooling is unavailable

## Rank 2: Hardware Or Connectivity Block

Choose this when:

- flash failed
- reset failed
- `rx_zero` is present
- monitor items cannot be read

## Rank 3: CLI Protocol Block

Choose this when:

- `parser_no_command`
- `prompt_missing`
- transcript shows malformed or missing command behavior

## Rank 4: Host Capture Or Observability Block

Choose this when:

- `tx_or_host_rx`
- `diag_unavailable`
- monitor outputs are absent but behavior might still exist

## Rank 5: Feature Behavior Regression

Choose this when:

- assertions fail
- `compare_delta.json` shows changed output
- build and environment are healthy

## Output Style

When reporting root causes:

1. list the strongest evidence
2. rank likely causes
3. choose the smallest next confirming action
