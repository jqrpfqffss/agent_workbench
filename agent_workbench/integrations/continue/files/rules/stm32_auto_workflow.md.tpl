# STM32 Auto Workflow

项目: {project_name}
源码目录: {source_dirs_csv}
构建目录: {build_dir}
UART CLI: {uart_port}
诊断串口: {diag_uart_port}
ready banner: {ready_banner}
prompt: {prompt}
默认 profile: {default_profile}

在这个项目里工作时，默认遵守下面流程：

1. 所有自动化动作优先通过 `agent_workbench.bat`。
2. PowerShell 下只使用 `cmd /c ".\agent_workbench.bat ... --json"`。
3. 先 `doctor`，再 `plan` / `context`，最后 `build` / `verify`。
4. 不要臆测 TIM、GPIO、ADC、DMA 参数，必须来自 `plan`、现有源码或明确日志证据。
5. 烧录、复位、UART 烟测属于硬件动作；其中 flash / reset 必须先征得用户同意。
6. 输出结论时先给证据，再给判断，再给下一步建议。

推荐命令模板：

```powershell
cmd /c ".\agent_workbench.bat doctor --json"
cmd /c ".\agent_workbench.bat scan-project --json"
cmd /c ".\agent_workbench.bat plan ""<用户需求>"" --json"
cmd /c ".\agent_workbench.bat build --json"
cmd /c ".\agent_workbench.bat verify current --task agent_workbench/tasks/cli_automation_regression.yaml --json"
```
