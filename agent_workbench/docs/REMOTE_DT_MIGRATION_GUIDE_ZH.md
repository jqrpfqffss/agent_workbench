# Remote DT 功能迁移指南

这份文档讲的是：怎么把 `agent_workbench` 里的 `remote_dt` 功能搬到另一个项目里，让本机一条命令就能去远程 Linux 服务器跑构建、测试和覆盖率，并把日志拉回来。

适合小白的理解方式：

- 本机：你现在打开项目、运行 `agent_workbench.bat` 的 Windows 电脑。
- 远端：一台 Linux 服务器，里面放着同一个项目或已经同步好的项目。
- Remote DT：本机通过 SSH 登录远端，依次执行 `build.sh`、`execute.sh`、`gen_coverage.sh`，再用 SCP 把日志和结果拉回本机。

## 1. 什么时候需要 remote_dt

有这些情况时，remote_dt 很适合：

- 项目必须在 Linux 环境编译或测试。
- 测试依赖 Docker、仿真器、覆盖率工具、专用 SDK，Windows 本机不方便装。
- 想让 AI/agent 在本机改代码，但验证放到远程机器上跑。
- 需要保留每次远程验证的日志、JSON 结果和覆盖率网页。

如果你的项目只需要本机 CMake build、烧录、UART 验证，就不一定需要 remote_dt。

## 2. remote_dt 做了什么

执行：

```powershell
.\agent_workbench\bin\agent_workbench.bat remote-dt pipeline --json
```

内部流程是：

1. 检查 `remote_dt.enabled`、`host`、`user`、`remote_project_dir` 是否有效。
2. SSH 到远程服务器。
3. 进入 `remote_project_dir`。
4. 执行 `scripts.build`，默认是 `./build.sh`。
5. 拉回 `dt_build.log` 和 `dt_build_result.json`。
6. 如果 build 通过，继续执行 `scripts.execute`，默认是 `./execute.sh`。
7. 拉回 `dt_execute.log` 和 `dt_execute_result.json`。
8. 如果 execute 通过，继续执行 `scripts.coverage`，默认是 `./gen_coverage.sh`。
9. 拉回 `dt_coverage.log`、`dt_coverage_result.json` 和覆盖率目录。
10. 在本机生成 `dt_remote_result.json` 和 `dt_remote_summary.md`。

如果某一步失败，后面的步骤会跳过。比如 build 失败时，execute 和 coverage 都不会继续跑。

## 3. 迁移前准备

本机需要：

- 能运行 `agent_workbench`。
- 有 `ssh` 和 `scp` 命令。
- 能从本机连上远程 Linux 服务器。
- 推荐配置 SSH key 登录，避免每次输入密码。

远端 Linux 需要：

- 已经放好项目代码。
- 项目目录里有三个脚本：`build.sh`、`execute.sh`、`gen_coverage.sh`。
- 登录用户对项目目录有读写权限。
- 构建、测试、覆盖率工具已经安装好。

最简单的连通性检查：

```powershell
ssh your_user@your_server
```

能登录进去，再继续配置 remote_dt。

## 4. 最小可用配置

在新项目的 `agent_workbench/agent_workbench.yaml` 里找到 `remote_dt`，至少改这些字段：

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
```

先不要急着改所有字段。第一次迁移只改主机、用户名、远程路径和脚本名，跑通后再调超时和产物目录。

## 5. 字段怎么填

| 字段 | 必填 | 小白解释 |
|---|---|---|
| `enabled` | 是 | `true` 表示启用 remote_dt；`false` 表示禁用。 |
| `host` | 是 | 远程 Linux 的 IP 或主机名。 |
| `user` | 是 | SSH 登录用户名。 |
| `port` | 是 | SSH 端口，通常是 22。 |
| `remote_project_dir` | 是 | 远程服务器上的项目目录。 |
| `local_artifact_dir` | 否 | 本机保存远程日志和结果的目录。 |
| `ssh.identity_file` | 否 | 专用 SSH 私钥路径；留空用系统默认 key。 |
| `ssh.connect_timeout_sec` | 否 | SSH/SCP 连接超时秒数。 |
| `ssh.strict_host_key_checking` | 否 | 是否严格检查远程主机 key。新手或内网环境可先用 `false`。 |
| `ssh.ssh_command` | 否 | 特殊情况下覆盖 ssh 命令；真实项目通常留空。 |
| `ssh.scp_command` | 否 | 特殊情况下覆盖 scp 命令；真实项目通常留空。 |
| `scripts.build` | 是 | 远程构建脚本。 |
| `scripts.execute` | 是 | 远程测试或运行脚本。 |
| `scripts.coverage` | 是 | 远程生成覆盖率脚本。 |
| `timeouts.*` | 否 | 每个阶段最大等待时间。 |
| `artifacts.remote_log_dir` | 否 | 远端日志目录。 |
| `artifacts.remote_result_dir` | 否 | 远端阶段结果 JSON 目录。 |
| `artifacts.remote_coverage_dir` | 否 | 远端覆盖率目录。 |

## 6. 远端脚本怎么写

三个脚本都放在 `remote_project_dir` 下，并确保能执行：

```bash
chmod +x build.sh execute.sh gen_coverage.sh
```

最小 `build.sh` 示例：

```bash
#!/usr/bin/env bash
set -euo pipefail

cmake -S . -B build
cmake --build build -j
```

最小 `execute.sh` 示例：

```bash
#!/usr/bin/env bash
set -euo pipefail

ctest --test-dir build --output-on-failure
```

最小 `gen_coverage.sh` 示例：

```bash
#!/usr/bin/env bash
set -euo pipefail

mkdir -p coverage
echo "<html><body><h1>coverage placeholder</h1></body></html>" > coverage/index.html
```

刚迁移时，覆盖率脚本可以先生成一个占位 `index.html`，确认拉取链路通了，再换成真正的 gcov/lcov/genhtml 流程。

## 7. 推荐迁移步骤

1. 在远端准备项目目录。
2. 手动 SSH 登录远端，确认能进入项目目录。
3. 在远端手动跑 `./build.sh`，确认脚本自己能过。
4. 在远端手动跑 `./execute.sh`，确认测试脚本自己能过。
5. 在远端手动跑 `./gen_coverage.sh`，确认会生成 `coverage/`。
6. 回到本机，修改 `agent_workbench/agent_workbench.yaml` 的 `remote_dt`。
7. 在本机运行 doctor：

```powershell
.\agent_workbench\bin\agent_workbench.bat doctor --json
```

8. 先只拉日志测试 SCP 通道：

```powershell
.\agent_workbench\bin\agent_workbench.bat remote-dt pull-logs --json
```

9. 再跑完整流水线：

```powershell
.\agent_workbench\bin\agent_workbench.bat remote-dt pipeline --json
```

10. 如果失败，先看 `agent_workbench/runtime/remote_dt/dt_remote_summary.md`，再看对应 `logs/dt_*.log`。

## 8. 常用命令

只跑远程构建：

```powershell
.\agent_workbench\bin\agent_workbench.bat remote-dt build --json
```

只跑远程测试：

```powershell
.\agent_workbench\bin\agent_workbench.bat remote-dt execute --json
```

只跑远程覆盖率：

```powershell
.\agent_workbench\bin\agent_workbench.bat remote-dt coverage --json
```

完整流水线：

```powershell
.\agent_workbench\bin\agent_workbench.bat remote-dt pipeline --json
```

只拉回已有日志和覆盖率：

```powershell
.\agent_workbench\bin\agent_workbench.bat remote-dt pull-logs --json
```

## 9. 跑完后看哪些文件

默认产物在：

```text
agent_workbench/runtime/remote_dt/
```

重点看：

- `dt_remote_result.json`：完整机器可读结果，适合 agent 分析。
- `dt_remote_summary.md`：人看的摘要，先看这个。
- `logs/dt_build.log`：构建日志。
- `logs/dt_execute.log`：测试/运行日志。
- `logs/dt_coverage.log`：覆盖率生成日志。
- `results/dt_build_result.json`：远端 build 阶段退出码。
- `results/dt_execute_result.json`：远端 execute 阶段退出码。
- `results/dt_coverage_result.json`：远端 coverage 阶段退出码。
- `coverage/index.html`：覆盖率网页入口，前提是你的覆盖率脚本生成了它。

## 10. 常见问题

### 提示 remote_dt is not enabled

说明 `enabled` 还是 `false`。改成：

```yaml
enabled: true
```

### 提示 missing required fields

通常是 `host`、`user` 或 `remote_project_dir` 没填。

### SSH 能登录，但 remote-dt 失败

先看 `dt_remote_result.json` 里的第一失败阶段，再看对应日志：

- build 失败：看 `logs/dt_build.log`。
- execute 失败：看 `logs/dt_execute.log`。
- coverage 失败：看 `logs/dt_coverage.log`。

### permission denied

常见原因：

- 远端脚本没有执行权限，运行 `chmod +x build.sh execute.sh gen_coverage.sh`。
- 登录用户没有项目目录写权限。
- SSH 私钥权限或路径不对。

### No such file or directory

常见原因：

- `remote_project_dir` 写错。
- 脚本名写错。
- 脚本里引用了不存在的工具或路径。

### 覆盖率拉不回来

检查两件事：

- `gen_coverage.sh` 是否真的生成了 `coverage/`。
- `artifacts.remote_coverage_dir` 是否和真实目录一致。

## 11. 迁移检查清单

- `remote_dt.enabled` 已改成 `true`。
- 本机可以 `ssh user@host` 登录远端。
- `remote_project_dir` 在远端真实存在。
- 远端三个脚本都能手动执行。
- 远端三个脚本都有执行权限。
- `local_artifact_dir` 没有写到系统保护目录。
- `remote-dt build --json` 能返回结果。
- `remote-dt pipeline --json` 能生成 `dt_remote_summary.md`。
- 失败时能在 `logs/dt_*.log` 里看到真实错误。

## 12. 一个完整示例

假设远端信息是：

- 服务器：`192.168.1.50`
- 用户：`dtuser`
- 项目目录：`/home/dtuser/projects/serial`
- SSH 端口：`22`

配置可以写成：

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
    pull_patterns:
      - .agent_workbench_remote_dt/logs/dt_*.log
      - .agent_workbench_remote_dt/results/dt_*.json
      - coverage/**
```

第一次跑建议：

```powershell
.\agent_workbench\bin\agent_workbench.bat remote-dt build --json
```

build 单独通过后，再跑：

```powershell
.\agent_workbench\bin\agent_workbench.bat remote-dt pipeline --json
```

这样排错更简单。
