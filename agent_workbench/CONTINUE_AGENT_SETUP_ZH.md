# Continue Agent 模式启用指南

本文档说明如何在 Continue 中正确使用本项目的自动化规则。

## 前提

- 已安装 Continue VS Code 插件
- 已能在 Continue 中使用支持工具调用的模型
- 已在项目根目录执行过 `agent_workbench.bat init-continue-rules`

## 第一步: 开启 Agent 模式

1. 打开 VS Code 侧边栏中的 Continue。
2. 在聊天输入区域切换到 `Agent` 模式。
3. 不要停留在纯 `Chat` 模式。

## 第二步: 确认 rules 已生成

检查项目下是否存在:

- `.continue/rules/stm32_auto_workflow.md`
- `.continue/rules/stm32_weak_model_guard.md`
- `.continue/rules/stm32_task_cookbook.md`

如果没有，先运行:

`cmd /c ".\agent_workbench.bat init-continue-rules"`

## 第三步: 做一个最小探测

在 Continue 里输入:

`请运行 scan-project 看看当前项目结构`

预期行为:

- Continue 自动运行 `cmd /c ".\agent_workbench.bat scan-project --json"`
- 返回结构化摘要
- 不只是告诉你“应该运行什么”

## 第四步: 验证自动计划

在 Continue 里输入:

`给STM32添加PWM蜂鸣器控制，频率1kHz，PA8引脚`

预期行为:

- 先运行 `plan --json`
- 再按 `steps` 逐步读文件与改文件
- build 失败时会再调用 `fix-build --json`

## 常见问题

### Continue 不执行命令

- 确认当前真的是 Agent 模式
- 确认模型支持工具调用
- 确认终端/工具权限没有被禁用

### Continue 会执行，但不按结构化字段做决定

- 确认 `.continue/rules/` 已刷新到最新版本
- 确认主规则里已经包含 `parameter_extractions`、`hardware_context`、`code_change_hints`、`fix-build`

### 弱模型经常乱改

- 确认 `stm32_weak_model_guard.md` 已生成
- 让它严格按 rules 执行
- 尽量一次只给一个明确目标
