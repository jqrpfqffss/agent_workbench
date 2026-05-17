# Remote DT 接入契约

## 命令边界

remote-dt 只使用这些公开命令：

```powershell
./agent_workbench/bin/agent_workbench.bat remote-dt build --json
./agent_workbench/bin/agent_workbench.bat remote-dt execute --json
./agent_workbench/bin/agent_workbench.bat remote-dt coverage --json
./agent_workbench/bin/agent_workbench.bat remote-dt pipeline --json
./agent_workbench/bin/agent_workbench.bat remote-dt pull-logs --json
```

PowerShell 一次只运行一条 workbench 命令，不用 `;`、`&&` 或管道串联 workbench 命令。

## 命令矩阵

### `remote-dt build --json`

- 场景：在远程 Linux 执行 `remote_dt.scripts.build`，验证远端构建环境、依赖、源码同步状态。
- 必读：命令 JSON、`dt_remote_result.json`、`dt_remote_summary.md`、`logs/dt_build.log`、`results/dt_build_result.json`。
- 失败：优先区分 remote_dt 配置、SSH/路径阻塞、远端构建脚本失败、依赖缺失或远端代码未同步。

### `remote-dt execute --json`

- 场景：执行远端 DT 用例、host-side 测试、仿真测试或远程设备测试。
- 必读：命令 JSON、`logs/dt_execute.log`、`results/dt_execute_result.json`、`test_failures[]`。
- 失败：先判断是测试断言失败、测试入口没跑到目标用例、远端运行依赖缺失，还是设备/仿真器不可用。

### `remote-dt coverage --json`

- 场景：生成并拉回覆盖率目录。
- 必读：命令 JSON、`logs/dt_coverage.log`、`results/dt_coverage_result.json`、`coverage/`。
- 失败：检查 coverage 脚本是否生成配置中的覆盖率目录，以及 gcov/lcov/genhtml 或项目覆盖率工具是否可用。

### `remote-dt pipeline --json`

- 场景：顺序执行 build、execute、coverage。某阶段失败时后续阶段跳过。
- 必读：`steps[]` 中第一个 `status = fail` 的阶段、`errors[]`、`warnings[]`、`test_failures[]` 和对应日志。
- 失败：报告失败阶段，不要把跳过阶段写成失败或通过。

### `remote-dt pull-logs --json`

- 场景：只拉回远端已有日志、结果和覆盖率目录，用于重新分析 evidence。
- 必读：拉回结果、`dt_remote_result.json`、`dt_remote_summary.md` 和本地 artifact 路径。
- 失败：检查远端日志目录、结果目录、覆盖率目录是否存在，以及本地 artifact 目录是否可写。

## 配置读取

运行前读取 `agent_workbench/agent_workbench.yaml` 中：

- `remote_dt.enabled`
- `host`
- `user`
- `port`
- `remote_project_dir`
- `scripts.build`
- `scripts.execute`
- `scripts.coverage`
- `local_artifact_dir`
- `artifacts.remote_log_dir`
- `artifacts.remote_result_dir`
- `artifacts.remote_coverage_dir`

`remote_dt.enabled = false` 时，不要假装执行了远端测试。可以继续编写 DT 用例和脚本，但验证结论必须是 blocked。

## 脚本要求

远端脚本必须：

- 非交互式。
- 可重复执行。
- 返回码表达阶段成败。
- stdout/stderr 包含失败原因。
- 不依赖临时 shell 状态。
- 在 `remote_project_dir` 下执行时能找到自己的相对路径。

典型职责：

- `build`：准备或构建远端测试目标。
- `execute`：运行 DT 用例，失败返回非 0。
- `coverage`：生成覆盖率目录，失败返回非 0。

## 必读 artifact

每次 remote-dt 后读取：

- `agent_workbench/runtime/remote_dt/dt_remote_result.json`
- `agent_workbench/runtime/remote_dt/dt_remote_summary.md`
- `agent_workbench/runtime/remote_dt/logs/dt_build.log`
- `agent_workbench/runtime/remote_dt/logs/dt_execute.log`
- `agent_workbench/runtime/remote_dt/logs/dt_coverage.log`
- `agent_workbench/runtime/remote_dt/results/dt_*_result.json`
- `agent_workbench/runtime/remote_dt/coverage/`，如果 coverage 阶段运行

失败时先找 `dt_remote_result.json` 中第一个 `steps[].status = fail` 的阶段，再读对应日志。

## 失败路由

- 配置失败：读 `agent_workbench/agent_workbench.yaml`，确认 `enabled`、`host`、`user`、`remote_project_dir`。
- SSH 失败：确认 host、port、identity_file、host key 策略、远端登录用户和交互式提示。
- 远端路径失败：确认 `remote_project_dir` 存在且用户可访问。
- 脚本失败：读对应 `logs/dt_*.log`，找第一个真实失败。
- 测试失败：读 `test_failures[]` 和 `dt_execute.log`，确认是期望过时、用例设计错误、测试入口漏跑还是固件/业务回归。
- 覆盖率失败：读 `dt_coverage.log`，确认覆盖率工具、编译参数、产物路径和 SCP 拉取。

## 同步边界

remote-dt 不同步源码。若本地修改了 DT 用例、脚本或固件代码，而远端是否同步不可确认：

- 不直接声称远端验证了本地改动。
- 报告中写明“远端代码同步未确认，remote-dt 执行结果不能证明本地最新改动”。
- 用户或项目有同步脚本时，先使用项目既有同步流程；没有时不要发明危险同步命令。
