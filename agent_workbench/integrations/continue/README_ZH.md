# Continue 集成说明

这个集成包会为当前 STM32 项目生成 Continue 规则文件到 `.continue/rules/*.md`，让 Continue 在 Windows PowerShell 下优先走 `agent_workbench.bat` 的标准工作流。

## 前置条件

- 本机已安装 Continue 插件
- 项目已经跑过 `agent_workbench.bat doctor --json`

## 一键安装

```powershell
cmd /c ".\agent_workbench.bat integration install continue --json"
```

安装后会生成 9 个规则文件，包括：

- `stm32_auto_workflow.md`
- `stm32_weak_model_guard.md`
- `stm32_task_cookbook.md`
- `stm32_powershell_syntax.md`
- `stm32_error_recovery.md`
- `stm32_hardware_safety.md`
- `stm32_model_deepseek_r1.md`
- `stm32_model_qwen7b.md`
- `stm32_model_glm.md`

## 建议用法

1. 在 Continue 中启用项目规则。
2. 优先让模型通过 `cmd /c ".\agent_workbench.bat ... --json"` 执行自动化动作。
3. 需要低上下文工作流时，继续使用 `agent_workbench.bat context ...` 生成的 `*_paste.md` 也可以。

## 常用检查

```powershell
cmd /c ".\agent_workbench.bat integration check continue --json"
cmd /c ".\agent_workbench.bat integration remove continue --json"
```

若你同时使用 OpenCode 和 Continue，这两个 integration 可以并存；它们分别写入 `.opencode/` 和 `.continue/`，互不覆盖。
