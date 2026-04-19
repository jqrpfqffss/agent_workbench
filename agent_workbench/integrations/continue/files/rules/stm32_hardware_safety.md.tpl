# STM32 Hardware Safety

这是带硬件的项目，必须保守执行：

1. flash / reset 前必须征得用户同意。
2. 不要假设开发板在线、串口空闲、OpenOCD 一定可用。
3. 不要凭记忆填写外设参数；定时器、GPIO、ADC 映射必须有证据来源。
4. UART CLI 验证至少确认 `ready banner` 与 `prompt`：
   - ready banner: `{ready_banner}`
   - prompt: `{prompt}`
5. 需要串口验证时，优先使用项目配置里的端口：
   - CLI UART: `{uart_port}`
   - DIAG UART: `{diag_uart_port}`
6. 如果证据指向硬件阻塞，应该明确写出“环境阻塞”，而不是继续猜测代码问题。
