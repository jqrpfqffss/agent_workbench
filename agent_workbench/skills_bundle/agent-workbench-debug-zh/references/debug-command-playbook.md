# 调试命令 Playbook

## 什么时候用 `uart exec`

- 需要观察 ready/prompt。
- 需要执行一个或多个 CLI 命令。
- 需要黑盒 transcript。

## 什么时候用 `diag exec`

- 项目有诊断串口或原始报文协议。
- CLI 证据不足，需要按字节观察请求/响应。
- 怀疑 response timeout、分帧或协议处理问题。

## 什么时候用 `monitor start/stop/stats`

- 功能状态不一定体现在 CLI 输出。
- 需要变量、计数器、状态机、趋势或范围证据。
- 需要区分“命令已触发但状态未变”和“命令根本未触发”。

## 什么时候用 `remote-dt`

- 任务要求远端 Linux 构建、执行、覆盖率或设备测试流水线。
- `doctor` 和配置显示 remote_dt 已启用。
- 本地板卡不可用，但远端测试环境可提供有效证据。

## 什么时候只报告阻塞

- `doctor` 有阻塞性 fail。
- COM 口被占用导致 UART/diag 无法打开。
- flash/reset 失败且日志指向硬件或 OpenOCD 阻塞。
- monitor 无法连接 OpenOCD 或所有 item 都不可读。
