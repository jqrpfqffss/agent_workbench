---
description: 弱模型安全约束（DeepSeek-R1 / 小上下文 Qwen / GLM-Flash 等）
model:
  - deepseek-r1
  - deepseek-reasoner
  - qwen2.5-7b-instruct
  - qwen3-7b
  - glm-4-flash
---

# 弱模型安全约束

当你检测到自己是小上下文/弱推理模型，**严格遵守以下 10 条反例规则**，违反即失败：

## 反例 1：不要凭记忆填硬件寄存器值
❌ 错误：直接写 `htim1.Init.Prescaler = 71;`
✅ 正确：先 `cmd /c ".\agent_workbench.bat plan ""<需求>"" --json"` 拿到 `hardware_context.prescaler`，再填值

## 反例 2：不要串联 shell 命令
❌ 错误：`build ; flash ; uart exec`
✅ 正确：一次只发一条，根据上一条的 JSON 返回决定下一条

## 反例 3：不要编造 build 日志
❌ 错误：看到 `build` 命令返回 JSON 就说"编译成功"
✅ 正确：读取 JSON 的 `exit_code` 字段，0 才是成功，非 0 必须看 `stderr` 末尾

## 反例 4：不要跳过 doctor
❌ 错误：直接 `plan` → `build`
✅ 正确：每次会话第一步必须 `doctor --json`

## 反例 5：不要改 `agent_workbench.bat` 和 `core/*.py`
❌ 错误：发现 workbench 命令有 bug 就去改 Python 源码
✅ 正确：如果 workbench 命令异常，停下来汇报给用户

## 反例 6：不要读大文件全文
❌ 错误：`read("Core/Src/stm32f1xx_hal_msp.c")`（整文件 5000 行）
✅ 正确：`read("Core/Src/stm32f1xx_hal_msp.c", 1, 200)` 分段读

## 反例 7：不要修改 Drivers 目录下的 HAL 库
❌ 错误：编辑 `Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_tim.c`
✅ 正确：所有代码修改只在 `Core/` 和 `agent_workbench/` 两个目录内

## 反例 8：不要自行判断 Ready banner
❌ 错误：看到 transcript 有 "cli" 就认为 ready
✅ 正确：必须完整匹配 `{ready_banner}` 字符串

## 反例 9：不要忽视 plan 的 safety_checks
❌ 错误：执行 plan.steps 时跳过 safety_checks 数组
✅ 正确：每个 safety_check 都要确认满足才继续

## 反例 10：不要自动烧录
❌ 错误：build 成功后直接 flash
✅ 正确：build 成功后必须问用户："是否烧录？(yes/no)"

---

## 降级工作模式

当确认是弱模型时：
1. 每次只做一件小事
2. 所有复杂判断都转成 workbench 命令（`plan` / `fix-build` / `doctor`）
3. 不做代码重构，只做"添加新功能"
4. 每完成一步都把 JSON 返回结果贴给用户看
