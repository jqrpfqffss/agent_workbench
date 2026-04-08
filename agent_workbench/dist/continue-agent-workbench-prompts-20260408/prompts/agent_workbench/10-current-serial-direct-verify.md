```text
你现在只负责验证当前 serial 项目，不要改代码，不要重构，不要新增功能。

严格遵守：
1. 不要自己拼接 cd、&&、; 或多条零散命令。
2. 不要先读一堆大文件。
3. 只运行这一条 PowerShell 安全命令：

cmd /c ".\agent_workbench.bat verify current --task agent_workbench/tasks/cli_automation_regression.yaml"

命令完成后，优先读取：
- agent_workbench/runtime/direct_verify_summary.md
- agent_workbench/runtime/direct_verify_summary.json

如果 summary 里包含 feature_session_dir，再继续读取其中的：
- session_verdict.json
- session_brief.md
- session_summary.md
- feature_summary.md
- assertions.jsonl
- cli_transcript.log
- cli_diag.json
- compare_brief.md
- compare_vs_*.md

最终只按下面结构输出：
1. 总结果：通过、未通过，还是被环境阻塞
2. 证据链：引用 summary 和 evidence 里的关键结论
3. 失败层级：doctor/build/test_run/uart_smoke/feature_session
4. 下一步建议

不要输出长篇背景介绍。
不要建议改代码，除非 evidence 明确指向代码问题。
```
