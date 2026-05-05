---
description: 读取最新 build.log 并生成修复建议
---

# /fix-build

```powershell
.\agent_workbench\bin\agent_workbench.bat fix-build --json
```

读取 `fixes`，小步修复后运行：

```powershell
.\agent_workbench\bin\agent_workbench.bat build --json
```

最多 3 轮后仍失败则报告剩余 build log。
