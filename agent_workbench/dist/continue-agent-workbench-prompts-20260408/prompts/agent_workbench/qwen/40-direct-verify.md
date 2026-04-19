```text
这是一个当前状态验证任务。

请不要自己拼接 cd、&&、; 或多条零散命令。
请直接运行：

cmd /c ".\agent_workbench.bat verify current --task <TASK>.yaml"

完成后优先读取：
- agent_workbench/runtime/direct_verify_summary.md
- agent_workbench/runtime/direct_verify_summary.json

如果 summary 引用了 feature session，再继续读对应 evidence。

最终只输出：
- result: ...
- task: ...
- evidence: ...
- layer: ...
- next: ...
```
