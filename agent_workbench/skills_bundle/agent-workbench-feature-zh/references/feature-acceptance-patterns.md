# 功能验收模式

定义或更新功能验收时使用这些模式。

## CLI 可见功能

优先：

- 使用短稳定字符串做响应判断。
- ack 字符串来自用户可见行为契约。
- status 命令能暴露当前值或模式。

避免：

- 模糊自然语言输出。
- 难以断言的多行输出。
- 没有充分理由就改变 ready/prompt/help 文本。

## Monitor 驱动功能

运行态重要时添加：

- 尽量提供一个人类可读 status 命令。
- 用 monitor items 做数值确认。
- 精确值可能轻微波动时，用范围或趋势期望。
- 添加 liveness counter 或状态迁移标记。

## 状态与控制功能

好的模式：

- 一个 control 命令。
- 一个 status 命令。
- 一个短 ack 字符串。
- 一个 monitor 或 transcript 检查。
- 相关时增加 reset 或 disabled-state 检查。

## Remote DT 功能

适用：

- 需要 Linux host/unit/integration 测试。
- 需要覆盖率。
- 需要远端设备架构提供 evidence。

要求：

- `doctor` 或配置证明 remote_dt 可用。
- 报告 `dt_remote_result.json`、`dt_remote_summary.md` 和阶段日志。

## 稳定字符串

除非用户明确改变公开协议，否则保持稳定：

- ready banner
- prompt
- help headings
- status labels
- ack strings
