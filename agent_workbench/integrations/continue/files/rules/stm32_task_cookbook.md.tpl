# STM32 Task Cookbook

## 当前状态验证

```powershell
cmd /c ".\agent_workbench.bat verify current --task agent_workbench/tasks/cli_automation_regression.yaml --json"
```

优先读取：

- `agent_workbench/runtime/direct_verify_summary.md`
- `agent_workbench/runtime/direct_verify_summary.json`

## 调试分析

```powershell
cmd /c ".\agent_workbench.bat verify current --task agent_workbench/tasks/cli_automation_regression.yaml --json"
cmd /c ".\agent_workbench.bat context --mode debug --stage analyze --json"
```

优先读取：

- `cli_diag.json`
- `cli_transcript.log`
- 最新的 `*_paste.md`

## 功能实现

```powershell
cmd /c ".\agent_workbench.bat context --mode feature --stage implement --task <TASK>.yaml --json"
cmd /c ".\agent_workbench.bat build --json"
```

只读取当前阶段生成的：

- `*_paste.md`
- `*_constraints.json`
- `*_facts.json`

## 功能验证

```powershell
cmd /c ".\agent_workbench.bat verify current --task <TASK>.yaml --json"
```

## 测试生成与执行

```powershell
cmd /c ".\agent_workbench.bat test generate --task <TASK>.yaml --json"
cmd /c ".\agent_workbench.bat test run --json"
```
