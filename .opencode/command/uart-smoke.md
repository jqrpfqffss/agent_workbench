---
description: 只做 UART CLI 烟测，不编译不烧录
---

# /uart-smoke

运行：

```powershell
.\agent_workbench\bin\agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --json
```

检查返回 JSON 和 transcript artifact：

- 必须包含当前配置的 ready banner。
- 必须包含当前配置的 prompt。
- 每条 `--command` 都应有非空响应。

输出 transcript 前 30 行、最后 10 行，以及 `UART CLI smoke: ok / fail`。
