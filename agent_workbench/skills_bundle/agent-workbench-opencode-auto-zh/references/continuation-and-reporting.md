# 续跑与报告

## 部分成功后如何续跑

先读 `summary.json`：

```text
details.passed_count
details.failed_count
details.retry_count
details.stopped_task
details.tasks[]
```

再读失败 task 的最后一次 attempt：

```text
tasks/<task_id>/attempt_<n>/result.json
tasks/<task_id>/attempt_<n>/stdout.log
tasks/<task_id>/attempt_<n>/stderr.log
```

续跑策略：

- 如果失败是临时工具错误或模型偶发失败，修复环境后用同一 task 加 `--max-retries <n>` 重跑。
- 如果失败是任务拆分过大，改用更小的 `--task`。
- 如果 planner 计划不可靠，写一个只包含剩余工作的 `--plan-file`。
- 如果已经有通过任务的 staged diff，下一轮 prompt 应声明“已完成并暂存的部分不要重复修改”。
- 如果 staged diff 不可信，先审阅并恢复出明确 baseline，再续跑。

## 剩余任务 plan-file 示例

```json
{
  "tasks": [
    {
      "id": "task_003",
      "title": "补齐失败后的文档说明",
      "prompt": "基于已经 staged 的前两步结果，只补齐 opencode-auto 失败恢复说明，不修改其他目录。",
      "acceptance": [
        "只修改目标 skill 目录",
        "说明 startup dirty、rollback 不完整和续跑流程"
      ]
    }
  ]
}
```

## 报告模板

```text
结论：PASS / PASS WITH RISKS / FAIL / BLOCKED

实际执行：
- .\agent_workbench\bin\agent_workbench.bat doctor --json -> exit_code=<n>, artifact=<path>
- .\agent_workbench\bin\agent_workbench.bat opencode-auto run --task "..." --json -> exit_code=<n>, artifact=<summary.json>

opencode-auto 摘要：
- run_dir: <path>
- tasks: <task_count>
- passed: <passed_count>
- failed: <failed_count>
- retries: <retry_count>
- stopped_task: <id/title 或 none>

Git 状态：
- startup dirty: <none 或 details.dirty 摘要>
- staged baseline: <说明是否存在>
- rollback/git_add: <关键结论和 artifact>
- 续跑方式: <无 / narrowed task / plan-file / blocked>

验证：
- build/hardware/remote 是否执行。
- 未执行时说明原因，不要暗示已通过。

改动：
- <文件和要点>

风险：
- <仍需人工确认或硬件验证的事项>
```

## 不可做

- 不要改写旧 runtime summary 来制造成功记录。
- 不要把 planner stdout 中的自然语言当成已通过证据。
- 不要在没有 artifact 的情况下声称 rollback 成功。
- 不要把 `agent_workbench/tests/*.py` 当成 STM32 固件验证入口，除非任务是在修改 workbench 平台本身。
- 不要捏造 exit_code、日志路径或硬件输出。
