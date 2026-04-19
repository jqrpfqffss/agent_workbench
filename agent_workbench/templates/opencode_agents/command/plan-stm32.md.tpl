---
description: 从自然语言需求生成 STM32 执行计划（不执行，只生成）
argument-hint: <用户需求描述>
---

# /plan-stm32 命令

当用户输入 `/plan-stm32 <需求>`，你的动作：

1. 运行 shell:
   ```
   cmd /c ".\agent_workbench.bat plan ""$ARGUMENTS"" --json"
   ```

2. 解析返回 JSON，关注 3 个字段：
   - `parameter_extractions`: 识别到的参数
   - `hardware_context`: 对应的硬件方案（Prescaler/Period/GPIO Mode 等）
   - `steps`: 具体步骤数组

3. 以**摘要形式**把结果展示给用户（不要贴整个 JSON）：
   ```
   ✓ 已生成执行计划

   识别参数:
     - pin: PA8
     - freq: 1 kHz
     - duty: 50%

   硬件方案: TIM1_CH1
     - APB2 clock: 72 MHz
     - Prescaler: 71
     - Period: 999
     - CCR: 500

   计划步骤: 6 步
     1. read Core/Inc/main.h
     2. read Core/Src/main.c
     3. edit Core/Inc/main.h (加 #include)
     4. edit Core/Src/main.c (加 HAL_TIM_PWM_Start)
     5. shell agent_workbench.bat build
     6. shell agent_workbench.bat uart exec

   是否开始执行？(yes/step1/no)
   ```

4. 不要自动执行后续步骤。等用户明确回复 `yes` 再继续。
