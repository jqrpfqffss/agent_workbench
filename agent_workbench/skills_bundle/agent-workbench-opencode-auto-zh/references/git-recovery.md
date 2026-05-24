# Git 失败恢复手册

## 启动前 require_clean 阻塞

当前项目配置 `opencode_auto.git.require_clean: true`。opencode-auto 会在 worker 启动前检查配置 paths。

会阻塞的状态：

- tracked 文件有未暂存改动。
- 配置 paths 下有 untracked 文件。

不会因为这个原因阻塞的状态：

- 已 staged 的 baseline 改动。当前测试覆盖了 staged user work 可以继续执行。
- `exclude_paths` 命中的文件，例如 `**/__pycache__/**` 和 `**/*.pyc`。
- 当前 opencode-auto run_dir 诊断目录。

处理步骤：

1. 读本次 run 的 `summary.json`。
2. 记录 `details.dirty`。
3. 运行 `git status --short` 核对真实状态。
4. 对用户认可的 baseline 改动执行 `git add <path>`。
5. 对确定可丢弃的生成物，移除或移动这些具体文件。
6. 不确定时停止并报告，不要自动丢弃。
7. 重新运行 `opencode-auto run --task "..." --json`。

## worker 失败后的自动 rollback

每个 worker attempt 开始时会捕获 index tree。attempt 失败后：

- tracked 文件按 baseline tree 恢复。
- index 中新增的文件会取消暂存。
- 配置 paths 下的 untracked 文件会被 `git clean -fd` 清理。
- 当前 run_dir 会被排除，保留诊断日志。

如果 rollback 成功，下一次 retry 应从干净的 attempt baseline 开始。

如果 rollback 失败或不完整：

1. 读 `attempt_<n>/result.json` 中的 `rollback`。
2. 查看 `rollback.restore`、`rollback.unstage_added`、`rollback.clean` 的 `exit_code/stdout/stderr`。
3. 运行 `git status --short`、`git diff`、`git diff --cached`。
4. 保留 runtime 诊断目录。
5. 只恢复已确认属于失败 attempt 的残留，不要覆盖用户 staged baseline。

## git_add 失败

子任务成功后会 stage 配置 paths。`git_add.exit_code != 0` 时：

- 该 task 应视为失败。
- 先读 `details.tasks[].git_add.stderr`。
- 检查路径是否不存在、被锁定、权限异常、index 异常或路径被错误配置。
- 修复后再续跑，不要跳过 stage 继续后面的任务。

## 后续任务被前轮状态影响

症状可能是：

- 新 run 启动时再次 dirty blocked。
- 后续 worker 修改了前一轮残留文件。
- staged diff 同时包含已完成工作和失败残留。
- `git diff --cached` 与 `summary.json` 中 passed tasks 不匹配。

处理顺序：

1. 停止启动新的 worker。
2. 读取前一轮 `summary.json` 和失败 attempt `result.json`。
3. 用 `git diff --cached` 确认已完成任务的 staged baseline。
4. 把确认正确的 completed changes 保持 staged。
5. 把失败残留从 worktree 或 index 中移除；不确定时先报告。
6. 使用更窄的 task 或 curated `--plan-file` 只跑剩余任务。

不要使用全仓库粗暴回滚来“清理一下”，除非监督者明确允许，并且已经确认不会丢用户工作。

