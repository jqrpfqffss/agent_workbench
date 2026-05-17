# DT 用例断言模式

本 skill 只使用 remote-dt 五条命令。所有断言都必须落在 remote-dt 阶段结果、阶段日志、结构化用例输出或覆盖率产物上。

## Build 阶段模式

适合验证远端构建环境、依赖、源码同步和测试目标生成：

- 触发：`remote-dt build --json` 或 `remote-dt pipeline --json`。
- 断言：build 阶段 `exit_code = 0`，`steps[].status = pass`，`dt_build.log` 没有明确 fatal/error。
- 失败线索：优先读 `logs/dt_build.log` 和 `results/dt_build_result.json`。

## Execute 阶段模式

适合验证 DT 用例、host-side 测试、仿真测试或远端设备测试：

- 触发：`remote-dt execute --json` 或 `remote-dt pipeline --json`。
- 断言：execute 阶段 `exit_code = 0`，目标 case verdict 为 `pass`，`test_failures[]` 为空。
- 推荐日志摘要：`DT_RESULT suite=... total=... pass=... fail=0 blocked=0`。
- 失败线索：优先读 `logs/dt_execute.log`、`results/dt_execute_result.json` 和 `test_failures[]`。

## Coverage 阶段模式

适合证明新增逻辑分支被远端测试触达：

- 触发：`remote-dt coverage --json` 或 `remote-dt pipeline --json`。
- 断言：coverage 阶段 `exit_code = 0`，`coverage/` 被拉回，覆盖率报告达到用户定义门槛。
- 失败线索：优先读 `logs/dt_coverage.log` 和 `results/dt_coverage_result.json`。
- 注意：覆盖率通过不等于行为正确；应配套 execute 阶段的行为断言。

## Pipeline 模式

适合完整闭环：

- 触发：`remote-dt pipeline --json`。
- 断言：build、execute、coverage 三个阶段都为 pass；若任一阶段 fail，后续 skipped 不写成 fail 或 pass。
- 失败线索：先找 `dt_remote_result.json` 中第一个 `steps[].status = fail` 的阶段，再读对应 `logs/dt_*.log`。

## Pull Logs 模式

适合重新分析远端已有结果：

- 触发：`remote-dt pull-logs --json`。
- 断言：本地成功拉回 `dt_remote_result.json`、`dt_remote_summary.md`、`logs/dt_*.log`、`results/dt_*_result.json`，如适用还有 `coverage/`。
- 注意：pull-logs 只能证明证据被拉回，不能证明新用例刚刚执行。
