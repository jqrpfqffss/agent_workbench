```text
这是调试任务。
不要改代码。
不要自己规划长流程。

只运行：
cmd /c ".\agent_workbench.bat verify current --task <TASK>.yaml"

如果还不够，再运行：
cmd /c ".\agent_workbench.bat context --mode debug --stage analyze"

优先读取：
- direct_verify_summary.md
- cli_diag.json
- cli_transcript.log

输出只允许：
- result: ...
- classification: ...
- evidence: ...
- next: ...
```
