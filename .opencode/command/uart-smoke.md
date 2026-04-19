---
description: 只做 UART CLI 烟测（不编译不烧录）
---

# /uart-smoke 命令

运行:
```
cmd /c ".\agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --json"
```

检查返回 JSON 的 `transcript` 字段：
- [必须] 包含 ready banner: `STM32 UART CLI ready.`
- [必须] 包含 prompt: `cli>`
- [必须] 每条 `--command` 都有非空响应

把 transcript 的前 30 行 + 最后 10 行贴给用户，并给出一行结论：
```
UART CLI 烟测: ok / fail
```
