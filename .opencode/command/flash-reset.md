---
description: 烧录并复位硬件，不跑测试
---

# /flash-reset

1. 先确认环境和 build 产物：

```powershell
.\agent_workbench\bin\agent_workbench.bat doctor --json
```

2. 直接执行烧录：

```powershell
.\agent_workbench\bin\agent_workbench.bat flash --method openocd_cmd --json
```

3. 检查返回 JSON 的 `exit_code`。非 0 时列出 stderr 或 flash log 关键行并停止。

flash/reset 不需要用户授权。
