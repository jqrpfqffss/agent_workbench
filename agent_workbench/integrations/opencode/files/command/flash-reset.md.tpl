---
description: 烧录并复位硬件，不跑测试
---

# /flash-reset

```powershell
.\agent_workbench\bin\agent_workbench.bat doctor --json
```

```powershell
.\agent_workbench\bin\agent_workbench.bat flash --method openocd_cmd --json
```

flash/reset 不需要用户授权。失败时报告 flash JSON、stderr 和 OpenOCD log。
