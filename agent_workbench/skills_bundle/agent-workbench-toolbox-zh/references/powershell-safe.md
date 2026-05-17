# PowerShell 安全规则

Windows PowerShell 下执行 workbench 命令时遵守本文件。

## 单命令原则

一次只运行一条 workbench 命令：

```powershell
./agent_workbench/bin/agent_workbench.bat build --json
```

不要把多条 workbench 命令写成：

```powershell
./agent_workbench/bin/agent_workbench.bat build --json; ./agent_workbench/bin/agent_workbench.bat flash --json
```

也不要用 `&&`、`||` 或管道串联 workbench 命令。

## 引号规则

- 相对 bat 路径不需要引号时，直接执行。
- 路径必须加引号时，使用 `& "path" args`。
- 不要把命令写成单纯字符串加参数。

## JSON 规则

- 支持 `--json` 的命令必须加。
- 报告时引用实际 JSON 字段和 artifact。
- 命令失败时不要捏造 stdout/stderr；读取真实 shell 输出和 workbench artifacts。

## 文件编辑规则

- 可以编辑 `agent_workbench/agent_workbench.yaml` 添加 monitor items。
- 不要用示例项目的寄存器地址、内存地址或符号名。
- 删除或移动文件前，确认目标在当前 workspace 内且与任务相关。
