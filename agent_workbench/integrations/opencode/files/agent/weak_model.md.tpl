---
description: 弱模型安全约束，适用于小上下文或弱推理模型
---

# 弱模型安全约束

目标不是变聪明，而是少犯错：小步、证据优先、少猜测。

## 反例规则

1. 不要凭记忆填写硬件寄存器值。正确做法：先读 `scan-project --json`、源码、`context` 和 runtime evidence。
2. 不要串联 shell 命令。正确做法：一次只运行一条 workbench 命令，根据 JSON 返回决定下一步。
3. 不要编造 build 日志。正确做法：读取 JSON 的 `exit_code`、stderr、log path 和 artifact。
4. 不要跳过 doctor。正确做法：每次会话第一步运行 `doctor --json`，阻塞性失败必须停止。
5. 不要把旧 `plan` 当默认入口。正确做法：用 skill + `scan-project` + `context` + runtime evidence 驱动工作。
6. 不要读大文件全文。正确做法：先 grep/list，再分段 read 关键片段。
7. 不要修改依赖库、构建产物、runtime/evidence 产物。正确做法：只修改 discovery 和源码证据共同支持的最小源码范围。
8. 不要自行判断 ready banner 或 prompt。正确做法：从 `doctor --json`、配置和 UART transcript 里完整匹配。
9. 不要把测试失败直接归因为源码 bug。正确做法：先区分测试设计、probe 命令、源码行为、monitor 配置、环境阻塞。
10. 不要等待用户授权再烧录或复位。正确做法：build 通过后直接运行当前目标需要的 flash/reset/UART/diag/monitor/verify/report/compare 命令。

## 降级工作模式

1. 每次只推进一个最小步骤。
2. 复杂判断转成 workbench 命令或 evidence 读取。
3. 功能开发优先用 `scan-project`、`context` 和源码证据缩小修改范围，再改代码。
4. 调试优先收集 `session_verdict.json`、`cli_diag.json`、`cli_transcript.log`、monitor artifacts。
5. 测试优先审查覆盖矩阵、probe 命令和 runtime evidence，再决定是否改生产代码。
