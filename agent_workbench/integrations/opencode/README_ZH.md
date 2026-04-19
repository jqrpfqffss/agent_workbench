# OpenCode 集成说明

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

## 检查与卸载

```powershell
cmd /c ".\agent_workbench.bat integration check opencode --json"
cmd /c ".\agent_workbench.bat integration remove opencode --json"
```

这个 integration 只写入 `AGENTS.md`、`opencode.json` 和 `.opencode/`，可以与 `.continue/` 并存。
