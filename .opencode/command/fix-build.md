---
description: 读取最新 build.log 并生成修复建议
---

# /fix-build

运行：

```powershell
.\agent_workbench\bin\agent_workbench.bat fix-build --json
```

读取返回 JSON 的 `fixes` 数组。每项通常包含 `file`、`line`、`message`、`suggested_change` 或同等字段。

只应用小步修复。每次修改后重新运行：

```powershell
.\agent_workbench\bin\agent_workbench.bat build --json
```

最多 3 轮后仍失败，报告 build log 和剩余错误。
