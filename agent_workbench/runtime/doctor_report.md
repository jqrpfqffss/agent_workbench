# Doctor Report

| check | level | detail |
|---|---|---|
| python | ok | D:\Anaconda1\python.exe |
| yaml | ok | PyYAML available |
| runtime_root | ok | ok |
| evidence_root | ok | ok |
| generated_root | ok | ok |
| cmake | ok | cmake |
| toolchain_file | ok | H:\stm32_RAG\code\serial\cmake\arm-none-eabi-toolchain.cmake |
| artifact_elf | ok | H:\stm32_RAG\code\serial\build\cmake-debug\serial.elf |
| compile_commands | ok | H:\stm32_RAG\code\serial\build\cmake-debug\compile_commands.json |
| openocd | ok | openocd |
| flash_method | ok | openocd_cmd: openocd |
| uart_protocol | ok | ready_banner=STM32 UART CLI ready. prompt=cli> |
| uart_backend | warn | pyserial unavailable: No module named 'serial'. PowerShell UART fallback is available for CLI exec and logging, but interactive console still prefers pyserial. |
| diag_uart_requests | ok | count=2 port=COM3 |
| diag_uart_backend | warn | pyserial unavailable: No module named 'serial'. PowerShell fallback is available for diag exec. |
| diag_uart_port | warn | port availability not checked without pyserial |
| agent_profile | ok | balanced_local missing=none |
| uart_markers | ok | ready=STM32 UART CLI ready. prompt=cli> probe_count=6 |
| agent_state | ok | H:\stm32_RAG\code\serial\agent_workbench\runtime\agent_state.json |
| context_budget | ok | context_pack_feature_timer_led_blink_implement_balanced_local_brief.md words=199 budget=550 |
| paste_card | ok | H:\stm32_RAG\code\serial\agent_workbench\runtime\context_pack_feature_timer_led_blink_implement_balanced_local_paste.md |
| task_scope | ok | include=3 max_edit_files=3 |
| task_candidates | ok | read_candidates=3 edit_candidates=3 |
| integration::continue::.continue/rules/stm32_auto_workflow.md | ok | H:\stm32_RAG\code\serial\.continue\rules\stm32_auto_workflow.md |
| integration::continue::.continue/rules/stm32_weak_model_guard.md | ok | H:\stm32_RAG\code\serial\.continue\rules\stm32_weak_model_guard.md |
| integration::continue::.continue/rules/stm32_task_cookbook.md | ok | H:\stm32_RAG\code\serial\.continue\rules\stm32_task_cookbook.md |
| integration::opencode::AGENTS.md | ok | H:\stm32_RAG\code\serial\AGENTS.md |
| integration::opencode::opencode.json | ok | H:\stm32_RAG\code\serial\opencode.json |
| integration::opencode::.opencode/agent/stm32_auto.md | ok | H:\stm32_RAG\code\serial\.opencode\agent\stm32_auto.md |
| integration::opencode::.opencode/agent/weak_model.md | ok | H:\stm32_RAG\code\serial\.opencode\agent\weak_model.md |
| integration::opencode::.opencode/agent/code_planner.md | ok | H:\stm32_RAG\code\serial\.opencode\agent\code_planner.md |
| integration::opencode::.opencode/agent/hardware_verifier.md | ok | H:\stm32_RAG\code\serial\.opencode\agent\hardware_verifier.md |
| integration::opencode::.opencode/command/plan-stm32.md | ok | H:\stm32_RAG\code\serial\.opencode\command\plan-stm32.md |
| integration::opencode::.opencode/command/verify.md | ok | H:\stm32_RAG\code\serial\.opencode\command\verify.md |
| integration::opencode::.opencode/command/fix-build.md | ok | H:\stm32_RAG\code\serial\.opencode\command\fix-build.md |
| integration::opencode::.opencode/command/uart-smoke.md | ok | H:\stm32_RAG\code\serial\.opencode\command\uart-smoke.md |
| integration::opencode::.opencode/command/flash-reset.md | ok | H:\stm32_RAG\code\serial\.opencode\command\flash-reset.md |
| planner_templates | ok | count=16 minimum=15 |
| migration_docs | ok | migration docs ready |
| unit_command | ok | D:\Anaconda1\python.exe -m unittest discover -s agent_workbench/tests -p "test_*.py" |
