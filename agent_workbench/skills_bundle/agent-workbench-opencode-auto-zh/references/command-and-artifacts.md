# opencode-auto 命令与产物

## 基本命令

从仓库根目录运行：

```powershell
.\agent_workbench\bin\agent_workbench.bat opencode-auto run --task "<任务>" --json
```

常用变体：

```powershell
.\agent_workbench\bin\agent_workbench.bat opencode-auto run --task "<任务>" --dry-run --json
.\agent_workbench\bin\agent_workbench.bat opencode-auto run --task "<任务>" --plan-file ".\plan.json" --json
.\agent_workbench\bin\agent_workbench.bat opencode-auto run --task "<任务>" --max-retries 2 --json
```

不要把这些命令和其他 workbench 命令串联。需要 `doctor`、build 或硬件验证时，逐条单独运行。

## plan 文件格式

`--plan-file` 应包含可解析的 JSON object，核心字段是 `tasks`：

```json
{
  "tasks": [
    {
      "id": "task_001",
      "title": "实现最小改动",
      "prompt": "只修改指定文件并运行相关验证。",
      "acceptance": ["验证命令通过", "diff 只包含预期文件"]
    }
  ]
}
```

`id` 会被规范化为安全目录名。`acceptance` 可以是字符串数组。不要把空 prompt、`TODO` 或含糊任务交给 worker。

## 运行目录

每次运行创建：

```text
agent_workbench/runtime/opencode_auto/<timestamp>/
```

常见文件：

- `task.md`：原始 `--task` 文本。
- `plan.json`：planner 输出或 `--plan-file` 规范化后的任务列表。
- `planner_stdout.log`：planner 标准输出。
- `planner_stderr.log`：planner 标准错误。
- `summary.json`：机器可读总结果。
- `summary.md`：人工摘要。
- `tasks/<task_id>/task.md`：单个 worker 的完整 prompt。
- `tasks/<task_id>/attempt_<n>/stdout.log`：worker stdout。
- `tasks/<task_id>/attempt_<n>/stderr.log`：worker stderr。
- `tasks/<task_id>/attempt_<n>/result.json`：attempt 退出码、耗时、timeout、解析 JSON 和 rollback 结果。

## summary.json 重点字段

优先读取：

- `status`
- `exit_code`
- `summary`
- `artifacts.run_dir`
- `artifacts.task`
- `artifacts.plan`
- `artifacts.summary_json`
- `details.task_count`
- `details.passed_count`
- `details.failed_count`
- `details.retry_count`
- `details.stopped_task`
- `details.git`
- `details.tasks[]`

如果 `status=blocked`，重点看 `details.dirty` 和 `details.git`。

如果 `status=fail`，重点看失败 task 的 `attempt_results[]`、`rollback`、`git_add` 和最后 attempt artifact。

## planner 失败

planner 失败或没有返回可用 tasks 时，`exit_code` 通常非 0，summary 类似：

```text
planner failed or returned no tasks exit=<n>
```

处理方式：

- 读 `planner_stdout.log` 和 `planner_stderr.log`。
- 检查 planner 是否输出了严格 JSON。
- 如果 planner 漏掉用户明确指定的文件名，当前服务会退回单任务 fallback；仍需人工审阅 `plan.json`。
- 可以手写 `--plan-file` 绕过不稳定 planner。

