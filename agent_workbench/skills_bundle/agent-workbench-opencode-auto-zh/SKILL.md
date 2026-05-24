---
name: agent-workbench-opencode-auto-zh
description: 当仓库包含 agent_workbench/agent_workbench.yaml，且需要用 `opencode-auto run --task "..." --json` 把较大的开发、修复、迁移或文档任务拆成串行 OpenCode 子任务执行时使用。本中文 skill 说明 opencode-auto 的 planner/worker 产物、Git 自动暂存与回滚、失败恢复、部分成功后续跑和最终报告要求。
---

# Agent Workbench OpenCode Auto（中文）

本 skill 用于监督 `opencode-auto run --task "..." --json`。它适合把较大的仓库任务交给 OpenCode planner 拆分，再由多个独立 worker 进程串行执行。监督 agent 的职责是：先确认 workbench 可用，启动 opencode-auto，读取真实 JSON/artifact，处理失败恢复和续跑，最后报告实际证据。

它不替代固件功能、调试或测试 workflow。任务需要 build、flash、UART、diag、monitor 或 remote-dt 闭环时，应在父 workflow 中调用对应公开命令，并继续遵守“不要把 build pass 当成完成”。

## 必须先做

从仓库根目录运行：

```powershell
.\agent_workbench\bin\agent_workbench.bat doctor --json
```

如果 batch launcher 启动失败，按项目 README/AGENTS 的兜底顺序只重试一条命令：

```powershell
python ".\agent_workbench\workbench.py" doctor --json
```

仍失败再试：

```powershell
py -3 ".\agent_workbench\workbench.py" doctor --json
```

`doctor` 有阻塞性失败时，先报告阻塞项和 artifact，不要继续启动 opencode-auto。

## 命令边界

本 skill 只覆盖这个公开入口：

```powershell
.\agent_workbench\bin\agent_workbench.bat opencode-auto run --task "<任务>" --json
```

已从当前源码/测试确认的辅助选项：

- `--dry-run`：只生成 dry-run 任务结构和产物，不启动真实 worker。
- `--plan-file <path>`：跳过 planner，使用已有 JSON plan。
- `--max-retries <n>`：覆盖单个 worker 子任务失败后的最大重试次数。

所有 workbench 命令支持 `--json` 时都必须加 `--json`。PowerShell 一次只运行一条 workbench 命令，不用 `;`、`&&` 或管道串联。

## 执行模型

`opencode-auto run` 的基本过程：

1. 在 `agent_workbench/runtime/opencode_auto/<timestamp>/` 创建本次运行目录。
2. 写入原始任务 `task.md`。
3. 如果没有 `--plan-file`，启动 planner，让 OpenCode 输出严格 JSON tasks。
4. 将计划规范化为 `plan.json`。
5. 依次为每个 task 启动独立 OpenCode worker。
6. 每个 attempt 记录 stdout、stderr、解析后的 JSON 和退出码。
7. 子任务成功后对配置的 Git paths 执行 stage。
8. 子任务失败时回滚到 attempt 开始前的 Git 基线，必要时重试。
9. 写入 `summary.json` 和 `summary.md`。

运行后监督 agent 必须读取 `summary.json`，必要时继续读取 `planner_stdout.log`、`planner_stderr.log`、每个子任务的 `task.md` 和 attempt 下的 `result.json/stdout.log/stderr.log`。不要只根据终端摘要判断成功。

## Git 自动管理

当前配置位于 `agent_workbench/agent_workbench.yaml` 的 `opencode_auto.git`：

- `enabled`：是否启用自动 Git 管理。
- `worktree`：Git 工作树，当前项目通常为 `.`。
- `paths`：成功后 stage、失败后 rollback/clean 的路径范围。
- `exclude_paths`：不参与 clean 检查、stage 和 rollback 的 glob，例如 `**/__pycache__/**`、`**/*.pyc`。
- `require_clean`：启动前是否要求配置路径没有未暂存/未跟踪变更。当前配置为 `true`。

重要行为：

- 启动前检查配置 paths。未暂存的 tracked 变更和 untracked 文件会阻塞执行。
- 已经 staged 的 baseline 变更不会阻塞；测试覆盖了 staged user work 可以继续执行。
- 子任务成功后，opencode-auto 对配置 paths 执行 `git add -A`。
- worker attempt 失败时，会按 attempt 开始时捕获的 index tree 恢复 tracked/index 状态，并清理配置 paths 下的 untracked 文件，同时保留当前 run_dir 诊断产物。
- 如果 `git_add` 失败，该子任务应视为失败，先修复 index/path 问题再继续。

## 启动前 dirty 阻塞怎么处理

如果 `summary.json` 显示 `status=blocked`，摘要类似 `configured git paths are dirty before opencode-auto run`：

1. 读取 `artifacts.run_dir`、`summary.json` 和 `details.dirty`。
2. 可运行 `git status --short` 做人工核对，但不要捏造输出。
3. 不要盲目丢弃用户工作。
4. 如果 dirty 文件是用户认可的基线改动，先把它们 staged：`git add <path>`，再重新运行 opencode-auto。
5. 如果 dirty 文件是确定可丢弃的生成物，只移除或移动这些已确认安全的文件。
6. 如果无法判断，停止并把 dirty 列表交给监督者/用户决定。

这类失败发生在 worker 开始前，opencode-auto 不会替你回滚这些启动前已有变更。

## 运行中失败怎么处理

失败后先读当前 run 的：

- `summary.json`
- `summary.md`
- `tasks/<task_id>/task.md`
- `tasks/<task_id>/attempt_<n>/result.json`
- `tasks/<task_id>/attempt_<n>/stdout.log`
- `tasks/<task_id>/attempt_<n>/stderr.log`

然后检查：

```powershell
git status --short
git diff
git diff --cached
```

处理原则：

- 保留 `agent_workbench/runtime/opencode_auto/<timestamp>/` 诊断目录。
- 已通过子任务产生并 staged 的改动，可作为后续续跑 baseline。
- 只在确认是失败 attempt 残留时，才恢复或删除配置 paths 下的文件。
- 如果回滚没有恢复干净，先修复工作树和 index，再启动下一轮。
- 如果失败是 transient，可提高或指定 `--max-retries` 后重跑。
- 如果 planner 拆分不合适，使用更窄的 `--task`，或准备人工审阅过的 `--plan-file` 只跑剩余任务。
- 不要编辑旧 `summary.json` 来伪造成功。

## 部分成功后续跑

从 `summary.json` 读取：

- `details.passed_count`
- `details.failed_count`
- `details.retry_count`
- `details.stopped_task`
- `details.tasks[]`

续跑建议：

1. 确认已通过子任务的 staged diff 是预期基线。
2. 修复失败原因或清理失败残留。
3. 让下一轮任务从 `stopped_task` 之后开始，不重复已经完成且 staged 的工作。
4. 对剩余工作写一个更窄的 `--task`，或创建只包含剩余子任务的 `--plan-file`。
5. 重新运行 `opencode-auto run --task "..." --json`。

如果后续任务被前一轮未恢复/未暂存状态影响，先按 Git evidence 还原出清晰 baseline，再继续跑；不要让新的 worker 在混乱 index 上继续叠加。

## 按需读取

- 命令和 artifact 细节：[references/command-and-artifacts.md](references/command-and-artifacts.md)
- Git 失败恢复手册：[references/git-recovery.md](references/git-recovery.md)
- 续跑和报告模板：[references/continuation-and-reporting.md](references/continuation-and-reporting.md)

## 最终报告底线

最终报告必须列出：

- 实际执行的命令、`exit_code` 和关键 artifact 路径。
- `doctor --json` 的结论。
- opencode-auto 的 `summary.json` 路径、passed/failed/retry 摘要和 stopped task。
- Git 状态如何处理：启动前 dirty、成功 staged、失败 rollback、续跑 baseline。
- 未执行的 build/hardware/remote 验证及原因。

只引用真实执行结果和真实 artifact。不要臆测硬件参数、不要编造命令输出。
