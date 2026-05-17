# Remote DT 迁移与运维指南

Remote DT 用于从本地 Windows 项目触发远程 Linux 服务器上的构建、执行和覆盖率流程，并把日志与结果拉回 `agent_workbench/runtime/remote_dt/`。它适合把 agent 的代码修改留在本地，把较重的验证环境放在远端。

当前公开命令只有：

```powershell
.\agent_workbench\bin\agent_workbench.bat remote-dt build --json
.\agent_workbench\bin\agent_workbench.bat remote-dt execute --json
.\agent_workbench\bin\agent_workbench.bat remote-dt coverage --json
.\agent_workbench\bin\agent_workbench.bat remote-dt pipeline --json
.\agent_workbench\bin\agent_workbench.bat remote-dt pull-logs --json
```

## 1. 什么时候使用 Remote DT

适合使用：

- 项目必须在 Linux 上构建、仿真、测试或生成覆盖率。
- 远端已有 Docker、SDK、仿真器、交叉工具链或测试环境。
- 本地 Windows 不方便安装完整验证依赖。
- 需要把远端执行日志、结果 JSON 和覆盖率目录拉回本地供 agent 分析。

不适合使用：

- 只需要本地 CMake 构建。
- 只需要本地 flash、reset、UART、diag 或 monitor。
- 远端项目目录没有同步到当前待验证代码。
- 远端脚本无法手动执行。

Remote DT 不负责同步源码。运行前必须确保 `remote_project_dir` 中的代码就是你要验证的版本。

## 2. 流水线模型

`remote-dt pipeline --json` 顺序执行三个阶段：

1. `build`：执行 `remote_dt.scripts.build`
2. `execute`：执行 `remote_dt.scripts.execute`
3. `coverage`：执行 `remote_dt.scripts.coverage`

如果某个阶段失败，后续阶段会跳过。例如 build 失败时 execute 和 coverage 都不会运行。

每个阶段都会：

- 通过 SSH 登录远端。
- `cd` 到 `remote_project_dir`。
- 创建远端日志目录和结果目录。
- 执行配置的脚本。
- 将 stdout/stderr 写入远端 `dt_*.log`。
- 写入远端 `dt_*_result.json`。
- 使用 SCP 拉回本地。
- 解析日志中的 error、warning 和测试失败模式。

## 3. 本地和远端要求

本地 Windows：

- 能运行 `agent_workbench`。
- PATH 中有 `ssh` 和 `scp`，或在配置里提供 `ssh_command`、`scp_command`。
- 能连接远端 Linux。
- 建议配置 SSH key，避免交互式密码阻塞自动化。

远端 Linux：

- `remote_project_dir` 真实存在。
- 登录用户对项目目录有读写权限。
- 构建、测试和覆盖率依赖已经安装。
- 配置的脚本能在远端手动执行。
- 脚本有可执行权限。

手动连通性检查：

```powershell
ssh your_user@your_host
```

远端脚本权限：

```bash
chmod +x build.sh execute.sh gen_coverage.sh
```

## 4. 最小配置

在 `agent_workbench/agent_workbench.yaml` 中配置：

```yaml
remote_dt:
  enabled: true
  host: "192.168.1.50"
  user: "dtuser"
  port: 22
  remote_project_dir: "/home/dtuser/projects/your_project"
  local_artifact_dir: agent_workbench/runtime/remote_dt
  ssh:
    identity_file: ""
    connect_timeout_sec: 10
    strict_host_key_checking: false
    ssh_command: ""
    scp_command: ""
  scripts:
    build: ./build.sh
    execute: ./execute.sh
    coverage: ./gen_coverage.sh
  timeouts:
    build_sec: 600
    execute_sec: 1200
    coverage_sec: 600
    pull_sec: 300
  artifacts:
    remote_work_dir: .agent_workbench_remote_dt
    remote_log_dir: .agent_workbench_remote_dt/logs
    remote_result_dir: .agent_workbench_remote_dt/results
    remote_coverage_dir: coverage
```

第一次迁移只建议先改：

- `enabled`
- `host`
- `user`
- `port`
- `remote_project_dir`
- `scripts.*`

连通后再调整 timeout、artifact 目录和 SSH 高级参数。

## 5. 字段说明

| 字段 | 必填 | 说明 |
|---|---|---|
| `enabled` | 是 | `true` 启用 remote-dt；`false` 时所有 remote-dt 命令返回配置失败 |
| `host` | 是 | 远程 Linux 主机 IP 或主机名 |
| `user` | 是 | SSH 登录用户 |
| `port` | 是 | SSH 端口，默认 22 |
| `remote_project_dir` | 是 | 远端项目目录，命令会先 `cd` 到这里 |
| `local_artifact_dir` | 否 | 本地拉回日志、结果和覆盖率的目录 |
| `ssh.identity_file` | 否 | 专用 SSH 私钥路径，空值表示使用系统默认 key |
| `ssh.connect_timeout_sec` | 否 | SSH/SCP 建连超时 |
| `ssh.strict_host_key_checking` | 否 | 是否严格校验 host key |
| `ssh.ssh_command` | 否 | 覆盖默认 `ssh` 命令，通常留空 |
| `ssh.scp_command` | 否 | 覆盖默认 `scp` 命令，通常留空 |
| `scripts.build` | 是 | 远端构建脚本或命令 |
| `scripts.execute` | 是 | 远端测试、仿真或执行脚本 |
| `scripts.coverage` | 是 | 远端覆盖率脚本 |
| `timeouts.build_sec` | 否 | build 阶段最大耗时 |
| `timeouts.execute_sec` | 否 | execute 阶段最大耗时 |
| `timeouts.coverage_sec` | 否 | coverage 阶段最大耗时 |
| `timeouts.pull_sec` | 否 | 每次 SCP 拉取超时 |
| `artifacts.remote_log_dir` | 否 | 远端日志目录，相对 `remote_project_dir` |
| `artifacts.remote_result_dir` | 否 | 远端结果 JSON 目录 |
| `artifacts.remote_coverage_dir` | 否 | 远端覆盖率目录 |

## 6. 远端脚本规范

脚本应该满足：

- 非交互式执行。
- 返回码表达成败。
- stdout/stderr 能说明失败原因。
- 不依赖当前 shell 的临时状态。
- 可以重复运行。

最小 `build.sh`：

```bash
#!/usr/bin/env bash
set -euo pipefail

cmake -S . -B build
cmake --build build -j
```

最小 `execute.sh`：

```bash
#!/usr/bin/env bash
set -euo pipefail

ctest --test-dir build --output-on-failure
```

最小 `gen_coverage.sh`：

```bash
#!/usr/bin/env bash
set -euo pipefail

mkdir -p coverage
echo "<html><body><h1>coverage placeholder</h1></body></html>" > coverage/index.html
```

迁移早期可以先用占位 coverage，确认 SCP 拉取链路正常后，再替换成真实 gcov/lcov/genhtml 流程。

## 7. 推荐迁移步骤

1. 在远端准备项目目录。
2. 手动 SSH 登录远端，确认用户和权限。
3. 在远端手动运行 `./build.sh`。
4. 在远端手动运行 `./execute.sh`。
5. 在远端手动运行 `./gen_coverage.sh`。
6. 回到本地，修改 `agent_workbench/agent_workbench.yaml` 的 `remote_dt`。
7. 本地运行：

```powershell
.\agent_workbench\bin\agent_workbench.bat doctor --json
```

8. 先跑远程构建：

```powershell
.\agent_workbench\bin\agent_workbench.bat remote-dt build --json
```

9. build 成功后跑完整流水线：

```powershell
.\agent_workbench\bin\agent_workbench.bat remote-dt pipeline --json
```

10. 如果只是需要重新拉取已有远端产物：

```powershell
.\agent_workbench\bin\agent_workbench.bat remote-dt pull-logs --json
```

## 8. 本地产物

默认目录：

```text
agent_workbench/runtime/remote_dt/
```

重点文件：

| 文件 | 说明 |
|---|---|
| `dt_remote_result.json` | 完整机器可读结果，包含阶段状态、错误、告警、测试失败、artifact |
| `dt_remote_summary.md` | 人工可读摘要，优先阅读 |
| `logs/dt_build.log` | 远端 build 阶段 stdout/stderr |
| `logs/dt_execute.log` | 远端 execute 阶段 stdout/stderr |
| `logs/dt_coverage.log` | 远端 coverage 阶段 stdout/stderr |
| `results/dt_build_result.json` | 远端 build 阶段返回码和时间 |
| `results/dt_execute_result.json` | 远端 execute 阶段返回码和时间 |
| `results/dt_coverage_result.json` | 远端 coverage 阶段返回码和时间 |
| `coverage/` | 从远端拉回的覆盖率目录 |

报告时应引用这些路径，而不是只说“远端通过/失败”。

## 9. JSON 结果解读

`remote-dt` JSON 输出通常包含：

- `command`: 固定为 `remote-dt`
- `action`: `build`、`execute`、`coverage`、`pipeline` 或 `pull-logs`
- `status`: `pass` 或 `fail`
- `exit_code`: 本地命令退出码
- `summary`: 阶段摘要
- `steps[]`: 各阶段执行结果
- `errors[]`: 从日志中解析出的关键错误
- `warnings[]`: 从日志中解析出的告警
- `test_failures[]`: 从日志中解析出的测试失败
- `artifacts`: 本地结果、摘要、日志和覆盖率路径

`pipeline` 失败时先找 `steps[]` 中第一个 `status = fail` 的阶段，再读对应日志。

## 10. 故障处理

### 10.1 `remote_dt is not enabled`

说明配置中：

```yaml
remote_dt:
  enabled: false
```

改为 `true`，并确认必填字段。

### 10.2 `missing required fields`

通常缺少：

- `host`
- `user`
- `remote_project_dir`

### 10.3 SSH 手动能登录，但 remote-dt 失败

检查：

- `ssh_command` 是否配置了错误 wrapper。
- `port` 是否正确。
- `remote_project_dir` 是否对该用户可访问。
- 远端 shell 是否支持 `bash -lc`。
- 是否存在交互式提示阻塞，例如首次 host key 确认、密码输入、sudo 密码。

### 10.4 `permission denied`

常见原因：

- SSH key 权限或路径错误。
- 远端脚本没有执行权限。
- 登录用户没有项目目录写权限。
- `remote_log_dir` 或 `remote_result_dir` 无法创建。

### 10.5 `No such file or directory`

常见原因：

- `remote_project_dir` 写错。
- `scripts.*` 文件名写错。
- 脚本内部引用不存在的工具或路径。
- 远端项目没有同步到预期版本。

### 10.6 build 失败

优先读：

```text
agent_workbench/runtime/remote_dt/logs/dt_build.log
```

处理顺序：

1. 找第一个真实编译/链接错误。
2. 确认远端依赖和工具链。
3. 确认远端源码版本。
4. 修改本地或远端代码后重新同步，再跑 `remote-dt build --json`。

### 10.7 execute 失败

优先读：

```text
agent_workbench/runtime/remote_dt/logs/dt_execute.log
```

区分：

- 测试断言失败。
- 运行环境缺依赖。
- 测试数据缺失。
- 仿真器或外部服务不可用。

### 10.8 coverage 失败

优先读：

```text
agent_workbench/runtime/remote_dt/logs/dt_coverage.log
```

检查：

- coverage 脚本是否生成了 `remote_coverage_dir`。
- gcov/lcov/genhtml 是否安装。
- build 是否带覆盖率编译参数。
- SCP 是否能递归拉取覆盖率目录。

### 10.9 pull-logs 失败

检查：

- `artifacts.remote_log_dir`
- `artifacts.remote_result_dir`
- `artifacts.remote_coverage_dir`
- 远端文件是否已经生成
- 本地 `local_artifact_dir` 是否可写

## 11. 迁移验收清单

- `remote_dt.enabled = true`。
- 本地可以 `ssh user@host` 登录远端。
- `remote_project_dir` 在远端真实存在。
- 远端 `build.sh`、`execute.sh`、`gen_coverage.sh` 可手动运行。
- 远端脚本返回码能准确表达成功或失败。
- 本地 `doctor --json` 没有 remote-dt 相关配置阻塞。
- `remote-dt build --json` 能生成 `dt_build.log`。
- `remote-dt pipeline --json` 能生成 `dt_remote_result.json` 和 `dt_remote_summary.md`。
- 失败时可以在 `logs/dt_*.log` 中找到真实错误。
- 报告引用真实 JSON 和日志路径。

## 12. 完整示例

假设：

- 远端主机：`192.168.1.50`
- 用户：`dtuser`
- 远端项目目录：`/home/dtuser/projects/serial`
- SSH 端口：`22`

配置：

```yaml
remote_dt:
  enabled: true
  host: "192.168.1.50"
  user: "dtuser"
  port: 22
  remote_project_dir: "/home/dtuser/projects/serial"
  local_artifact_dir: agent_workbench/runtime/remote_dt
  ssh:
    identity_file: ""
    connect_timeout_sec: 10
    strict_host_key_checking: false
    ssh_command: ""
    scp_command: ""
  scripts:
    build: ./build.sh
    execute: ./execute.sh
    coverage: ./gen_coverage.sh
  timeouts:
    build_sec: 600
    execute_sec: 1200
    coverage_sec: 600
    pull_sec: 300
  artifacts:
    remote_work_dir: .agent_workbench_remote_dt
    remote_log_dir: .agent_workbench_remote_dt/logs
    remote_result_dir: .agent_workbench_remote_dt/results
    remote_coverage_dir: coverage
```

第一次运行：

```powershell
.\agent_workbench\bin\agent_workbench.bat remote-dt build --json
```

build 通过后：

```powershell
.\agent_workbench\bin\agent_workbench.bat remote-dt pipeline --json
```

最终报告应写明：

- build、execute、coverage 各阶段状态。
- `dt_remote_result.json` 路径。
- `dt_remote_summary.md` 路径。
- 失败阶段对应 `logs/dt_*.log` 路径。
