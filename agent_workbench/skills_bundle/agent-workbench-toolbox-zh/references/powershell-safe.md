# PowerShell 安全调用

每次 OpenCode shell 调用只运行一条命令。

优先：

```powershell
.\agent_workbench\bin\agent_workbench.bat doctor --json
.\agent_workbench\bin\agent_workbench.bat build --json
.\agent_workbench\bin\agent_workbench.bat verify current --json
```

兜底：

```powershell
python ".\agent_workbench\workbench.py" doctor --json
py -3 ".\agent_workbench\workbench.py" doctor --json
```

避免：

- 默认使用 `cmd /c ".\agent_workbench.bat ..."`。
- 写成 `".\agent_workbench\bin\agent_workbench.bat" doctor --json`，这是字符串加参数，会触发 ParserError。
- 在 PowerShell 里裸跑 `agent_workbench.bat ...`。
- 普通 workbench 调用里使用 `cd ... && ...`、`;` 或管道。
- 为了解析 JSON 拼 shell 管道；OpenCode 应直接读取返回 JSON。

只有路径被引号包住时才使用 `& ".\agent_workbench\bin\agent_workbench.bat" doctor --json`。

命令失败时，先判断是 launcher 问题、workbench 失败，还是硬件/环境失败，再决定是否重试。
