# PowerShell 调用速查

## 正确示例

- `cmd /c ".\agent_workbench.bat build --json"`
- `cmd /c ".\agent_workbench.bat plan ""给板子加 1Hz LED 闪烁"" --json"`
- `cmd /c ".\agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --json"`
- `cmd /c ".\agent_workbench.bat ps-exec ""build"""`

## 错误示例

- `agent_workbench.bat build && agent_workbench.bat flash`
- `cd agent_workbench; python workbench.py build`
- `agent_workbench\tasks\example.yaml`
- `powershell ... | ConvertFrom-Json`
