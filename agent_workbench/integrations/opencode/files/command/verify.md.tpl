---
description: 运行完整 STM32 验证流程：doctor + build + flash + UART 烟测
---

# /verify

顺序执行，任意一步失败都停下并汇报证据。

```powershell
.\agent_workbench\bin\agent_workbench.bat doctor --json
```

```powershell
.\agent_workbench\bin\agent_workbench.bat build --json
```

```powershell
.\agent_workbench\bin\agent_workbench.bat flash --method openocd_cmd --json
```

```powershell
.\agent_workbench\bin\agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --json
```

bat 入口失败时，用 `python ".\agent_workbench\workbench.py" <command> --json` 兜底。flash 不需要用户授权。
