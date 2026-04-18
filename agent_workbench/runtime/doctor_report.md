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
| unit_command | ok | D:\Anaconda1\python.exe -m unittest discover -s agent_workbench/tests -p "test_*.py" |
