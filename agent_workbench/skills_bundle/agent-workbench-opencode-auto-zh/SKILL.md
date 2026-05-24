---
name: agent-workbench-opencode-auto-zh
description: 当 Codex/OpenCode 需要在包含 agent_workbench 的项目中使用 opencode-auto 拆分大任务、dry-run 验证任务拆分与 artifact、通过 OpenCode command template 执行子任务、或用 retry 对同一个任务进行多轮自动重试时使用。本 skill 只覆盖 `opencode-auto run/retry` 的真实 OpenCode 自动化场景，包括 Windows 模板文件、JSON 输出、runtime artifacts、git cleanup 与失败排查。
---

# Agent Workbench OpenCode Auto

把本 skill 用作 `agent_workbench` 的 OpenCode 自动化编排指南。它只处理 `opencode-auto run/retry`，不要把它扩展成 build、flash、UART、diag 或 monitor workflow。

## 基本规则

- 从仓库根目录运行命令。
- 如果当前项目包含 `agent_workbench/agent_workbench.yaml`，先运行 `doctor --json` 并确认 `exit_code=0`。
- 支持 `--json` 的命令必须加 `--json`，最终报告引用真实 JSON 字段和 artifact 路径。
- Windows 下优先使用 `--opencode-cmd-template-file`，避免把带引号的 OpenCode prompt 直接塞进命令行。
- 非 dry-run 命令会调用模板中的真实 OpenCode 执行器；不要在未确认模板和任务文件前运行。

常用入口：

```powershell
.\agent_workbench\bin\agent_workbench.bat opencode-auto run --task "..." --dry-run --json
python ".\agent_workbench\workbench.py" opencode-auto run --task-file ".\big-task.md" --opencode-cmd-template-file ".\opencode-worker-template.txt" --json
python ".\agent_workbench\workbench.py" opencode-auto retry --task-file ".\big-task.md" --opencode-cmd-template-file ".\opencode-worker-template.txt" --max-attempts 5 --json
python ".\agent_workbench\workbench.py" opencode-auto retry --task-file ".\big-task.md" --opencode-cmd-template-file ".\opencode-worker-template.txt" --no-git-cleanup --json
```

## 命令选择

使用 `opencode-auto run --task "..." --dry-run --json`：

- 在正式执行前检查任务能否被拆分。
- 验证 `summary.json`、`plan.json`、子任务目录和 stdout/stderr artifact 是否按预期生成。
- 不需要真实 OpenCode 执行器，也不会执行生产修改。

使用 `opencode-auto run --task-file path --opencode-cmd-template-file path --json`：

- 处理一个较大的任务，并让 workbench 拆成多个子任务顺序执行。
- 每个子任务有自己的 `task_file`、attempt 目录、stdout/stderr 和 result artifact。
- 适合“迁移多处代码”“逐模块修复”“把长需求拆给 OpenCode 分批落地”。

使用 `opencode-auto retry --task-file path --opencode-cmd-template-file path --max-attempts 5 --json`：

- 对同一个完整任务重复执行，直到某次 OpenCode 返回成功或达到最大尝试次数。
- 适合 flaky executor、模型偶发遗漏、或希望让 OpenCode 多次自修正的任务。
- 默认要求干净 git worktree；失败尝试会被清理，下一轮从干净基线开始。

使用 `opencode-auto retry --task-file path --opencode-cmd-template-file path --no-git-cleanup --json`：

- 仅在 worktree 已经是脏的、项目没有 git、或你明确希望保留失败尝试修改时使用。
- 风险是失败尝试的文件改动会留在工作区，后续 attempt 可能受到污染。
- 报告中必须明确写出使用了 `--no-git-cleanup` 以及剩余风险。

## Template 文件

模板文件内容是一行可执行 OpenCode 命令。OpenCode 1.15.x 的常见模板：

```text
opencode run "Read the attached task file and implement it." -f "{task_file}"
```

可用占位符：

- `{task_file}`：当前要交给 OpenCode 读取的任务 Markdown 文件。
- `{attempt_dir}`：当前 attempt 的 artifact 目录，可让 OpenCode 写补充日志。
- `{run_dir}`：本次 opencode-auto run/retry 的根 artifact 目录。
- `{task_id}`：仅 `run` 的子任务模式可用，表示当前子任务 ID。

模板设计建议：

- 让 OpenCode 从 `{task_file}` 读取任务，不要把长任务内联进 prompt。
- 需要审查器时再配置 review template；没有明确验收器时不要伪造 review 结果。
- 如果模板为空，非 dry-run 会以 `exit_code=2` 失败，并提示 missing opencode command template。

## Artifacts

`run` 模式写入：

- `agent_workbench/runtime/opencode_auto/<timestamp>/task.md`
- `agent_workbench/runtime/opencode_auto/<timestamp>/plan.json`
- `agent_workbench/runtime/opencode_auto/<timestamp>/summary.json`
- `agent_workbench/runtime/opencode_auto/<timestamp>/tasks/<task_id>/attempt_*/stdout.log`
- `agent_workbench/runtime/opencode_auto/<timestamp>/tasks/<task_id>/attempt_*/stderr.log`
- `agent_workbench/runtime/opencode_auto/<timestamp>/tasks/<task_id>/attempt_*/result.json`

`retry` 模式写入：

- `agent_workbench/runtime/opencode_retry/<timestamp>/task.md`
- `agent_workbench/runtime/opencode_retry/<timestamp>/summary.json`
- `agent_workbench/runtime/opencode_retry/<timestamp>/summary.md`
- `agent_workbench/runtime/opencode_retry/<timestamp>/attempt_*/stdout.log`
- `agent_workbench/runtime/opencode_retry/<timestamp>/attempt_*/stderr.log`
- `agent_workbench/runtime/opencode_retry/<timestamp>/attempt_*/result.json`
- `agent_workbench/runtime/opencode_retry/<timestamp>/attempt_*/result.md`

读取顺序：

1. 先读命令 JSON 的 `exit_code`、`summary`、`details`、`artifacts`。
2. 再读 `summary.json` 或 `summary.md` 判断总状态。
3. 失败时读对应 attempt 的 `stderr.log`、`stdout.log`、`result.json`。
4. `run` 拆分异常时读 `plan.json`，确认是 planner 输出还是 fallback split。

## 失败排查

- `exit_code=0`：命令完成。仍要引用 `summary` 和 artifact 路径，不要只说成功。
- `exit_code=1`：OpenCode 子任务或 attempt 失败。读 `details.skipped`、`failed_attempts`、attempt `result.json` 和 stderr。
- `exit_code=2`：调用参数或环境前置条件失败。重点查 task 是否为空、task-file 是否存在、template 是否缺失、retry worktree 是否 dirty。
- `exit_code=124` 或 `timeout=true`：模板命令超时。检查 `--timeout-seconds`、OpenCode 是否卡在交互输入、任务是否过大。
- `dirty git baseline`：默认 retry 需要干净 worktree。选择清理/提交/暂存用户改动，或在明确承担风险时改用 `--no-git-cleanup`。
- `missing opencode command template`：非 dry-run 必须传 `--opencode-cmd-template` 或 `--opencode-cmd-template-file`。

## 按需读取

只读取当前工作需要的 reference：

- 执行流程、模式选择、关键判断点：[references/opencode-auto-flow.md](references/opencode-auto-flow.md)
- 任务拆分设计方法论、模板设计、git 隔离策略：[references/opencode-auto-methodology.md](references/opencode-auto-methodology.md)
- 命令参数、模板变量和完整用法：[references/opencode-auto-command-reference.md](references/opencode-auto-command-reference.md)
- Planner 与 fallback 任务拆解细节：[references/opencode-auto-task-splitting.md](references/opencode-auto-task-splitting.md)
- 错误分类、git cleanup 机制与恢复策略：[references/opencode-auto-error-recovery.md](references/opencode-auto-error-recovery.md)
- 产物目录结构、关键 artifact JSON 格式：[references/opencode-auto-artifact-map.md](references/opencode-auto-artifact-map.md)
- 报告模板与必要字段：[references/opencode-auto-report-template.md](references/opencode-auto-report-template.md)
- workbench 通用命令：`agent-workbench-toolbox-zh/references/command-matrix.md`
- 证据产物地图：`agent-workbench-toolbox-zh/references/artifact-map.md`

## 协作规则

- opencode-auto 自动化执行：组合 `agent-workbench-toolbox-zh` + `agent-workbench-opencode-auto-zh`。
- DT 测试用例：使用 `agent-workbench-dt-test-zh`。
- 功能开发：使用 `agent-workbench-feature-zh`。
- 自动调试：使用 `agent-workbench-debug-zh`。

## 最终报告

报告必须包含：

- 实际执行的完整命令。
- 每条命令的 `exit_code` 和 `summary`。
- `run_dir`、`summary_json`、`summary_md`、`plan_file` 或关键 attempt artifact 路径。
- 是否使用 dry-run。
- 是否使用默认 git cleanup；若使用 `--no-git-cleanup`，说明原因和风险。
- 未执行真实 OpenCode 时明确写“未执行非 dry-run OpenCode”。
