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
| agent_profile | ok | balanced_local missing=none |
| uart_markers | ok | ready=STM32 UART CLI ready. prompt=cli> probe_count=6 |
| agent_state | ok | H:\stm32_RAG\code\serial\agent_workbench\runtime\agent_state.json |
| context_budget | ok | context_pack_feature_autoflow_cli_red_on_verify_balanced_local_brief.md words=197 budget=550 |
| paste_card | ok | H:\stm32_RAG\code\serial\agent_workbench\runtime\context_pack_feature_autoflow_cli_red_on_verify_balanced_local_paste.md |
| task_scope | ok | include=0 max_edit_files=0 |
| task_candidates | warn | read_candidates=0 edit_candidates=0 |
| autoflow_state | ok | H:\stm32_RAG\code\serial\agent_workbench\runtime\autoflow_state.json |
| autoflow_start | ok | H:\stm32_RAG\code\serial\agent_workbench\runtime\autoflow_start.md |
| unit_command | ok | D:\Anaconda1\python.exe -m unittest discover -s agent_workbench/tests -p "test_*.py" |
