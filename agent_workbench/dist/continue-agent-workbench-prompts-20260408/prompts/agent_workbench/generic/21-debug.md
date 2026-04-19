```text
这是一个自动化调试任务。

不要改代码。
不要自己拼接多条命令。
请直接运行：

cmd /c ".\agent_workbench.bat verify current --task <TASK>.yaml"

完成后优先读取：
- agent_workbench/runtime/direct_verify_summary.md
- agent_workbench/runtime/direct_verify_summary.json

如果需要更细的调试分析，再运行：

cmd /c ".\agent_workbench.bat context --mode debug --stage analyze"

然后只读取最新的 *_paste.md。

最终只输出：
- result: ...
- evidence: ...
- classification: ...
- next: ...
```
