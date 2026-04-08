# Continue Agent 中文提示模板

这份模板适合直接粘给 Continue `Agent` 模式。

推荐流程不是让模型先读很多大文件，而是：

1. 先运行对应的 `agent_workbench.bat context ...`
2. 再把最新的 `*_paste.md` 粘给 Continue
3. 一轮只做一个阶段

如果你用的是 DeepSeek / Qwen 这类本地模型，优先再看 [continue_low_context_zh.md](continue_low_context_zh.md)。

## 0. 当前项目一键直接验证模板

如果你现在只是要验证当前 `serial` 项目，不要让 Continue 自己组织很多命令，直接让它运行这一条 PowerShell 安全命令：

```text
请不要自己拼接 cd、&&、; 或多条零散命令。
请直接运行这一条命令：
cmd /c ".\agent_workbench.bat verify current --task agent_workbench/tasks/cli_automation_regression.yaml"

运行完成后，优先读取：
- agent_workbench/runtime/direct_verify_summary.md
- agent_workbench/runtime/direct_verify_summary.json

如果 summary 里带了 feature session 目录，再继续读取其中的：
- session_verdict.json
- session_brief.md
- session_summary.md
- feature_summary.md
- assertions.jsonl
- cli_transcript.log
- cli_diag.json
- compare_brief.md

最后只按“总结果 -> 证据链 -> 失败层级 -> 下一步建议”输出。
不要改代码。
```

## 1. 通用最短模板

```text
Read only the newest *_paste.md generated under agent_workbench/runtime.
Follow its stage rules exactly.
Use agent_workbench.bat for every automation action.
Do not read extra files unless they are listed in allowed_reads.
Do not claim anything without citing fact_id or evidence files.
```

## 2. 调试分析模板

先在终端执行：

```powershell
agent_workbench.bat context --mode debug --stage analyze
```

然后把最新 `*_paste.md` 粘给 Continue。

如果你想补一句中文说明，可以再加上这段：

```text
本轮只做调试分析。
不要先改代码。
先基于 session_verdict.json、session_brief.md、cli_diag.json、cli_transcript.log 给出问题现象、证据链、根因排序和唯一下一步。
```

## 3. 功能实现模板

先在终端执行：

```powershell
agent_workbench.bat context --mode feature --stage implement --task agent_workbench\tasks\<TASK>.yaml
```

然后把最新 `*_paste.md` 粘给 Continue。

如果你想补一句中文说明，可以再加上这段：

```text
本轮只做最小实现。
只允许读取 constraints.json 里的 allowed_reads。
只允许修改 allowed_edits。
不要扩 scope，不要顺手重构。
改完后只给出改动说明和建议进入 verify 阶段。
```

## 4. 验证模板

先在终端执行：

```powershell
agent_workbench.bat context --mode feature --stage verify --task agent_workbench\tasks\<TASK>.yaml
```

然后把最新 `*_paste.md` 粘给 Continue。

如果你想补一句中文说明，可以再加上这段：

```text
本轮只做验证。
只通过 agent_workbench.bat 执行自动化命令。
结论必须引用最新 evidence，至少包含 session_verdict.json、session_brief.md、assertions.jsonl、cli_transcript.log、compare_brief.md。
不要改代码。
```

## 5. 测试资产模板

先在终端执行：

```powershell
agent_workbench.bat context --mode test --stage analyze --task agent_workbench\tasks\<TASK>.yaml
```

然后把最新 `*_paste.md` 粘给 Continue。

如果你想补一句中文说明，可以再加上这段：

```text
本轮只做测试相关工作。
优先生成或补齐 task 对应的测试资产。
先跑 test generate，再跑 test run。
如果测试设计需要修改，请先改 task yaml，再重新生成。
```

## 6. 续接模板

先在终端执行：

```powershell
agent_workbench.bat context --stage resume
```

然后把最新 `*_paste.md` 粘给 Continue。

如果你想补一句中文说明，可以再加上这段：

```text
不要重新从 README 开始。
只基于最新 agent_state.json 和 resume 卡续接当前阶段。
先复述当前 mode、stage、latest_session、latest_verdict、next_commands，再继续执行。
```
