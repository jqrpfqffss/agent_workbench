---
description: 小上下文模型安全约束
---

# 小上下文模型安全约束

1. 每轮先运行 `doctor --json`；阻塞性失败必须停止。
2. 一次只运行一条 workbench 命令，并以 JSON 返回为准。
3. 不要凭记忆填写硬件参数；从源码、配置、ELF/map 或 runtime evidence 确认。
4. build 通过后，按目标选择 `flash`、`reset`、`uart exec`、`diag exec`、`monitor start/stop/stats` 或 `remote-dt` 建证据链。
5. 可用入口仅限 `doctor`、`build`、`fix-build`、`flash`、`reset`、`uart exec`、`diag exec`、`monitor start/stop/stats`、`remote-dt build/execute/coverage/pipeline/pull-logs`。
