# Task Breakdown

- task_id: `autoflow_cli_red_on`
- mode: `feature`
- goal: 请通过 CLI 点亮红灯
- task_path: `H:\stm32_RAG\code\serial\agent_workbench\generated\requests\cli_20260412_200632\task_draft.yaml`

## Stage Map
- analyze: S1, S2
- implement: none
- verify: S3, S4

## Subtasks
### S1 [analyze]
- title: Confirm the exact existing CLI command.
- objective: Map the natural-language goal to a built-in UART CLI command without inventing code work.
- inputs: task yaml, verify.cli_commands
- done_when: The exact UART command is fixed for this run.

### S2 [analyze]
- title: Lock the verify-only path.
- objective: Confirm that no code edits are required and the next round should jump directly to verification.
- inputs: implementation.max_edit_files, stable_strings
- done_when: The task is confirmed as verify-only.

### S3 [verify]
- title: Run the UART CLI command.
- objective: Execute the exact UART command and capture transcript evidence.
- inputs: red on, status
- done_when: A fresh transcript shows the command response.

### S4 [verify]
- title: Report from transcript evidence only.
- objective: Use the transcript and diagnostics to report pass, fail, blocked, or needs_review.
- inputs: cli_transcript.log, cli_diag.json
- done_when: The result is supported by fresh UART evidence.

