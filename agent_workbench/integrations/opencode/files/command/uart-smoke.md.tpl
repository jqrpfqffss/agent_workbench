---
description: 只做 UART CLI 烟测，不编译不烧录
---

# /uart-smoke

运行：

```powershell
.\agent_workbench\bin\agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --json
```

检查 ready banner、prompt、命令响应和 transcript artifact。
