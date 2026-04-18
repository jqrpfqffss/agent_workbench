# Task Breakdown

- task_id: `autoflow_feature_tim3_red_led_pb0_1_hz`
- mode: `feature`
- goal: 使用 TIM3 定时器让 RED LED(PB0) 以约 1 Hz 闪烁
- task_path: `H:\stm32_RAG\code\serial\agent_workbench\generated\requests\tim3_red_led_pb0_1_hz_20260412_131012\task_draft.yaml`

## Stage Map
- analyze: S1, S2
- implement: S3, S4
- verify: S5, S6

## Subtasks
### S1 [analyze]
- title: Read the task and the latest evidence.
- objective: Confirm the goal, scope, stable strings, and the first blocking layer before planning edits.
- inputs: task yaml, implementation_brief.md, latest session evidence if present
- done_when: The task goal, allowed scope, and first blocking layer can be stated in one short paragraph.

### S2 [analyze]
- title: Lock the smallest edit scope.
- objective: Choose the minimal set of files needed for this round so the model does not expand scope too early.
- inputs: Core/Src/main.c, Core/Src/stm32f1xx_it.c, Core/Inc/stm32f1xx_hal_conf.h
- done_when: The files needed for this round are explicit and stable output strings are protected.

### S3 [implement]
- title: Implement the feature only in allowed files.
- objective: Apply the smallest code change that satisfies the task goal without widening scope.
- inputs: Core/Src/main.c, Core/Src/stm32f1xx_it.c, Core/Inc/stm32f1xx_hal_conf.h
- done_when: Code changes are limited to allowed files and map directly to the task goal.

### S4 [implement]
- title: Pass local build and automation checks first.
- objective: Confirm build and local checks are healthy before running the full hardware validation loop.
- inputs: doctor, build, uart_smoke
- done_when: At least doctor and build are complete, plus test when the task requires it.

### S5 [verify]
- title: Run task-specific validation commands.
- objective: Use the task CLI commands or session flow to confirm the user-visible behavior.
- inputs: help, status
- done_when: Fresh transcript, diagnostic, assertions, or session summary files have been generated.

### S6 [verify]
- title: Close the loop with evidence only.
- objective: Use the latest evidence to report pass, fail, or blocked together with the smallest next step.
- inputs: session_verdict.json, session_brief.md, session_summary.md, feature_summary.md
- done_when: The conclusion names the result, evidence chain, and one concrete next step.

