```text
这是调试任务。

默认先运行：
cmd /c ".\agent_workbench.bat verify current --task <TASK>.yaml"

如果需要更细分析，再运行：
cmd /c ".\agent_workbench.bat context --mode debug --stage analyze"

优先读取：
- direct_verify_summary.md
- session_verdict.json
- cli_diag.json
- cli_transcript.log

最终只输出：
- result: ...
- classification: ...
- evidence: ...
- layer: ...
- next: ...
```
