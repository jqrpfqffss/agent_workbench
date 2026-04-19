# STM32 PowerShell Syntax

Windows PowerShell 下使用本项目时，必须遵守：

1. 不要自己拼 `cd ... && ...`、`;`、多段复合命令。
2. 一次只运行一条命令。
3. 所有 workbench 命令都优先写成：

```powershell
cmd /c ".\agent_workbench.bat <subcommand> --json"
```

4. 路径包含空格时，用双引号包裹。
5. 不要把 PowerShell 变量展开和 `cmd /c` 混在一条复杂命令里。
6. 不要捏造 shell 输出；必须基于真实命令结果总结。
