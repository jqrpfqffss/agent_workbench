# OpenCode 集成说明

## Remote DT 开发闭环

当 DT 编译、用例执行和覆盖率生成都在 Linux 服务器上完成时，优先使用：

```powershell
cmd /c ".\agent_workbench.bat remote-dt pipeline --json"
```

标准闭环：
1. 修改本地 DT 用例或业务代码。
2. 等待 RemoteDevPlus 将代码同步到 Linux 服务器。
3. 执行 `remote-dt pipeline --json`。
4. 如果失败，读取 `agent_workbench/runtime/remote_dt/dt_remote_result.json`、`agent_workbench/runtime/remote_dt/dt_remote_summary.md` 和 `agent_workbench/runtime/remote_dt/logs/dt_*.log`。
5. 根据第一失败阶段修复本地代码，再次等待同步并执行 pipeline。
6. 直到 build、execute、coverage 全部通过。

约束：
- 不允许只根据源码静态检查判断 DT 通过，必须以 `remote-dt pipeline` 的 JSON 结果和 DT 日志为准。
- 失败时优先分析第一失败阶段。
- build 失败先修 build；execute 失败再修用例或业务逻辑；coverage 失败再修覆盖率脚本或产物路径。

迁移提示：默认使用系统 `ssh` 和 `scp`，并依赖 SSH key。若 Windows 环境需要指定特殊客户端，可在 `remote_dt.ssh.ssh_command` 和 `remote_dt.ssh.scp_command` 中覆盖；一般真实项目保持为空即可。

这个集成包会为当前 STM32 项目生成 OpenCode 所需的项目级配置：

- `AGENTS.md`
- `opencode.json`
- `.opencode/agent/*.md`
- `.opencode/command/*.md`

## 前置条件

- 本机已安装 OpenCode CLI
- 项目已经通过 `agent_workbench.bat doctor --json`

## 一键安装

推荐命令：

```powershell
cmd /c ".\agent_workbench.bat integration install opencode --json"
```

兼容旧命令：

```powershell
cmd /c ".\agent_workbench.bat init-opencode-agents --json"
```

## 生成内容

安装后会写入：

- `AGENTS.md`
- `opencode.json`
- `.opencode/agent/stm32_auto.md`
- `.opencode/agent/weak_model.md`
- `.opencode/agent/code_planner.md`
- `.opencode/agent/hardware_verifier.md`
- `.opencode/agent/model_deepseek_r1.md`
- `.opencode/agent/model_glm.md`
- `.opencode/agent/model_qwen7b.md`
- `.opencode/command/plan-stm32.md`
- `.opencode/command/verify.md`
- `.opencode/command/fix-build.md`
- `.opencode/command/uart-smoke.md`
- `.opencode/command/flash-reset.md`

## 使用方式

1. 在项目根目录执行 OpenCode。
2. OpenCode 会自动加载 `AGENTS.md`。
3. 你可以直接提需求，或调用 slash 命令：
   - `/plan-stm32 <需求>`
   - `/verify`
   - `/fix-build`
   - `/uart-smoke`
   - `/flash-reset`

## 与四个 Skill 配合使用

推荐同时安装 `agent_workbench/skills_bundle` 中的四个 skill：

- `agent-workbench-toolbox`
- `agent-workbench-feature`
- `agent-workbench-debug`
- `agent-workbench-test`

OpenCode 执行复杂任务时应优先使用：

- 功能开发：`agent-workbench-toolbox` + `agent-workbench-feature`
- 自动调试：`agent-workbench-toolbox` + `agent-workbench-debug`
- 测试生成与实机验证：`agent-workbench-toolbox` + `agent-workbench-test`

`/plan-stm32` 仅保留为兼容入口，适合简单标准硬件任务的参数探索；复杂任务默认走 skill、task yaml、verify/report/compare 的证据闭环。

## 检查与卸载

```powershell
cmd /c ".\agent_workbench.bat integration check opencode --json"
cmd /c ".\agent_workbench.bat integration remove opencode --json"
```

这个 integration 只写入 `AGENTS.md`、`opencode.json` 和 `.opencode/`，可以与 `.continue/` 并存。
