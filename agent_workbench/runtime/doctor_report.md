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
| unit_command | ok | D:\Anaconda1\python.exe -m unittest discover -s agent_workbench/tests -p "test_*.py" |
