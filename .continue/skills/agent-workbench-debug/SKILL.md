# agent-workbench-debug

## 适用场景

当用户需要做以下工作时使用本技能：

- UART CLI 自动化调试
- 串口 smoke 验证
- ready banner / prompt / help / status 交互异常定位
- `cli_diag.json` 分类判断
- 输出“现象 -> 证据链 -> 根因 -> 下一步”

## 目标

快速判断问题属于哪一层：

- 环境阻塞
- UART 接收问题
- CLI 解析问题
- 主机侧接收问题
- 仅为诊断链路缺失

## 默认最短路径

先运行：

```powershell
cmd /c ".\agent_workbench.bat verify current --task <任务文件.yaml>"
```

如果用户明确要求“单独做调试分析”，再运行：

```powershell
cmd /c ".\agent_workbench.bat context --mode debug --stage analyze --task <任务文件.yaml>"
```

然后只读取最新 `*_paste.md`。

## 必读证据

优先顺序：

1. `agent_workbench/runtime/direct_verify_summary.md`
2. 最新 `session_verdict.json`
3. 最新 `session_brief.md`
4. 最新 `cli_diag.json`
5. 最新 `cli_transcript.log`

## 诊断分类规则

如果 `cli_diag.json` 中已经给出分类，优先直接使用。

可使用的分类：

- `rx_zero`
- `parser_no_command`
- `tx_or_host_rx`
- `ready_missing`
- `prompt_missing`
- `diag_unavailable`
- `environment_blocked`

如果出现以下情况，归类为 `environment_blocked`：

- COM 口不存在
- COM 口被占用
- 板子未连接
- 烧录器不可用
- reset / flash 根本没跑起来

## 行为约束

1. 先看 evidence，再谈根因
2. 不要先改代码
3. 不要给出长篇推测
4. 不要一次给多个大方向计划
5. 只给一个最小下一步

## 输出要求

按以下顺序输出：

1. `现象`
2. `证据链`
3. `根因排序`
4. `最小下一步`

如需固定格式，使用：

- `templates/debug-report-template.md`

如需详细分类说明，读取：

- `references/cli-diagnosis.md`
