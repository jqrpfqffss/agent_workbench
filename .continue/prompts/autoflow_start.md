# Autoflow Start

- goal: 请通过 CLI 点亮红灯
- task_id: `autoflow_cli_red_on`
- task_path: `H:\stm32_RAG\code\serial\agent_workbench\generated\requests\cli_20260412_200632\task_draft.yaml`
- current_stage: `verify`
- stage_sequence: `analyze, verify`
- current_subtasks: S3, S4
- next_stage: `verify`

## Read First
- `H:\stm32_RAG\code\serial\agent_workbench\runtime\context_pack_feature_autoflow_cli_red_on_verify_balanced_local_paste.md`
- `H:\stm32_RAG\code\serial\agent_workbench\generated\tasks\autoflow_cli_red_on\task_breakdown.md`
- `H:\stm32_RAG\code\serial\agent_workbench\generated\requests\cli_20260412_200632\task_draft.yaml`

## Continue Rules
1. Read the current stage paste card first.
2. Complete only the listed current_subtasks for this round.
3. Use agent_workbench.bat for every automation action.
4. When the stage command advances to the next context stage, run `agent_workbench.bat autoflow --resume` and reopen this start card.
5. Stop immediately if a command fails or if manual checks become pending.

## Next Commands
- `cmd /c ".\agent_workbench.bat uart exec --reset-first --expect-ready --command ""red on"" --command ""status"""`
