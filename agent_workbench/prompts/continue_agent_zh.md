# Continue Agent 中文提示模板

把下面的模板直接粘贴给 Continue 的 `Agent` 模式即可使用。

使用前建议先打开：

- `agent_workbench/agent_workbench.yaml`
- `agent_workbench/README.md`
- `agent_workbench/VS_CODE_CONTINUE_GUIDE_ZH.md`

## 通用总控模板

```text
你现在在这个 STM32 HAL 工程中工作，请严格按 agent_workbench 的工作方式执行，不要绕开它直接拼接零散命令。

先阅读以下文件，再开始行动：
- agent_workbench/agent_workbench.yaml
- agent_workbench/README.md
- agent_workbench/VS_CODE_CONTINUE_GUIDE_ZH.md
- agent_workbench/prompts/continue_debug.md
- agent_workbench/prompts/continue_feature.md
- agent_workbench/prompts/continue_test_author.md
- agent_workbench/prompts/continue_report.md
- agent_workbench/tasks/ 下与当前任务相关的 task yaml
- agent_workbench/evidence/sessions/ 下最新 session 目录中的证据文件

你必须遵守以下规则：
1. 所有自动化调试、自动化测试、自动化功能验证，优先通过 agent_workbench.bat 执行。
2. 先读证据，再分析问题，再决定是否改代码。
3. 修改代码后必须重新验证，不能只说“理论上已修复”。
4. 结论必须基于 evidence 文件，而不是只凭源代码印象。
5. 如果 CLI 握手失败，优先读取 cli_diag.json 判断是 rx_zero、parser_no_command、tx_or_host_rx、ready_missing 还是 prompt_missing。
6. 输出结论时，默认按“问题现象 -> 证据链 -> 根因 -> 修改 -> 验证结果 -> 剩余风险”组织。

默认执行顺序：
- agent_workbench.bat doctor
- agent_workbench.bat build

如果是调试任务，再执行：
- agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --command "red on" --command "green on" --command "blue on" --command "all off"
- agent_workbench.bat session debug
- agent_workbench.bat compare --latest

如果是功能任务，再执行：
- agent_workbench.bat test generate --task <TASK>
- agent_workbench.bat test run
- agent_workbench.bat session feature --task <TASK>
- agent_workbench.bat compare --latest

如果是测试资产编写任务，再执行：
- agent_workbench.bat test generate --task <TASK>
- agent_workbench.bat test run

输出要求：
1. 先说明当前现象。
2. 再给出证据链，明确引用 cli_transcript.log、cli_diag.json、assertions.jsonl、session_summary.md、feature_summary.md、compare_vs_*.md 中的关键信息。
3. 再给出最可能根因。
4. 再给出最小安全修改。
5. 修改后重新执行验证。
6. 最终给出闭环结论。
```

## 自动化调试模板

```text
这是一个自动化调试任务。

请先阅读：
- agent_workbench/agent_workbench.yaml
- agent_workbench/prompts/continue_debug.md
- agent_workbench/evidence/sessions/ 下最新 session
- 最新的 cli_transcript.log
- 最新的 cli_diag.json
- 最新的 session_summary.md

然后按以下顺序执行：
- agent_workbench.bat doctor
- agent_workbench.bat build
- agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --command "red on" --command "green on" --command "blue on" --command "all off"
- agent_workbench.bat session debug
- agent_workbench.bat compare --latest

不要先改代码。先根据证据判断问题位于：
- 串口路径 / COM 口 / 接线
- ready banner / prompt
- CLI 接收与解析
- 主机接收链路
- agent_workbench 配置或工具链

如果确实需要改代码，只做最小安全修改。改完后重新完整验证，并基于新 evidence 输出结论。
```

## 自动化功能实现模板

```text
这是一个自动化功能任务，任务文件是：<TASK>

请先阅读：
- agent_workbench/agent_workbench.yaml
- agent_workbench/prompts/continue_feature.md
- <TASK>
- agent_workbench/generated/tasks/ 下对应 task 目录
- agent_workbench/evidence/sessions/ 下最新 session 及其 evidence 文件

然后执行：
- agent_workbench.bat doctor
- agent_workbench.bat build
- agent_workbench.bat test generate --task <TASK>
- agent_workbench.bat test run

读懂 task 中的 goal、scope、acceptance、observability、verify.sequence 后，再做最小实现。

实现完成后执行：
- agent_workbench.bat session feature --task <TASK>
- agent_workbench.bat compare --latest

最后基于 feature_summary.md、session_summary.md、assertions.jsonl、cli_transcript.log、cli_diag.json、compare_vs_*.md 输出结论。
```

## 自动化测试资产模板

```text
这是一个自动化测试任务，任务文件是：<TASK>

请先阅读：
- agent_workbench/agent_workbench.yaml
- agent_workbench/prompts/continue_test_author.md
- <TASK>
- agent_workbench/evidence/sessions/ 下最新 session

然后执行：
- agent_workbench.bat doctor
- agent_workbench.bat build
- agent_workbench.bat test generate --task <TASK>
- agent_workbench.bat test run

如果需要补测试资产，请优先修改：
- agent_workbench/tasks/
- agent_workbench/generated/tasks/
- agent_workbench/tests/

最后说明：
- 新生成了哪些测试资产
- 哪些测试已经运行通过
- 哪些仍需实板验证
```

## 自动化报告模板

```text
这是一个报告整理任务。

请先阅读：
- agent_workbench/prompts/continue_report.md
- 最新 session 目录下的 session_summary.md
- feature_summary.md
- cli_transcript.log
- cli_diag.json
- assertions.jsonl
- compare_vs_*.md

不要先改代码。先整理证据，再输出一份“现象 -> 证据链 -> 根因 -> 修改 -> 验证结果”的结论。

如果证据不足，请明确指出缺少哪类 evidence，而不是猜测。
```

## 常用 Task 路径

```text
agent_workbench/tasks/cli_hardware_smoke.yaml
agent_workbench/tasks/cli_automation_regression.yaml
agent_workbench/tasks/example_feature.yaml
```
