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
| artifact_file | ok | H:\stm32_RAG\code\serial\build\cmake-debug\serial.elf |
| compile_commands | ok | H:\stm32_RAG\code\serial\build\cmake-debug\compile_commands.json |
| artifact_symbols | ok | H:\stm32_RAG\code\serial\build\cmake-debug\serial.elf |
| monitor_symbol_image | ok | H:\stm32_RAG\code\serial\build\cmake-debug\serial.elf |
| openocd | ok | openocd |
| flash_method | ok | openocd_cmd: openocd |
| monitor_items | ok | count=4 |
| monitor_symbol_items | ok | symbol items=2 |
| monitor_target_selection | ok | not required by current config |
| uart_protocol | ok | ready_banner=STM32 UART CLI ready. prompt=cli> format=8N1 |
| uart_backend | warn | pyserial unavailable: No module named 'serial'. PowerShell UART fallback is available for CLI exec and logging, but interactive console still prefers pyserial. |
| uart_port | ok | COM3 |
| diag_uart_requests | ok | count=2 port=COM3 format=8N1 |
| diag_uart_backend | warn | pyserial unavailable: No module named 'serial'. PowerShell fallback is available for diag exec. |
| diag_uart_port | ok | COM3 |
| uart_markers | ok | ready=STM32 UART CLI ready. prompt=cli> probe_count=6 |
