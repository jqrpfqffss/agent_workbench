# diag 分类码

## `rx_zero`

主机没有收到目标输出。优先怀疑：

- 目标未启动或未复位到预期固件。
- 串口号/波特率错误。
- TX/RX 连接或 USB 串口问题。
- 固件没有初始化 UART。

## `ready_missing`

没有看到配置的 ready banner。优先怀疑：

- 启动路径没有走到 CLI 初始化。
- reset/startup drain 配置不合适。
- ready 字符串变更但配置或稳定字符串期望未更新。

## `prompt_missing`

有输出但没有 prompt。优先怀疑：

- CLI loop 没有恢复 prompt。
- command handler 阻塞。
- 错误路径返回前漏掉 prompt。

## `parser_no_command`

有输入但 parser 没识别命令。优先怀疑：

- 命令名未注册。
- 换行/回车规则不匹配。
- 输入缓冲、大小写或空格处理异常。

## `tx_or_host_rx`

发送或主机接收链路异常。优先怀疑：

- host 串口驱动/占用。
- 目标 TX 方向。
- 波特率或串口参数。

## `diag_unavailable`

diag 子系统不可用。退回 `uart exec` 和 `monitor probe` 建证据链。
