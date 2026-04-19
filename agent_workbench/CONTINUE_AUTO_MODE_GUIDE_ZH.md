# Continue 自动模式指南

这份文档说明如何把 `agent_workbench` 切换到“用户只说一句话，Continue 先规划、再执行、最后验证”的自动模式。

自动模式的核心不是让模型直接上来改代码，而是让它严格走：

`scan-project / plan / build / parse-errors / flash / uart exec / report`

这样的闭环。

## 1. 一次性初始化

先在项目根目录执行：

```powershell
setup_workbench.bat
agent_workbench.bat doctor
agent_workbench.bat init-vscode
agent_workbench.bat init-continue-rules
```

执行完成后，仓库里至少应生成：

- `.vscode/tasks.json`
- `.continue/rules/stm32_auto_workflow.md`
- `.continue/rules/stm32_weak_model_guard.md`
- `.continue/rules/stm32_powershell_syntax.md`
- `.continue/rules/stm32_error_recovery.md`
- `.continue/rules/stm32_hardware_safety.md`
- `.continue/rules/stm32_model_deepseek_r1.md`
- `.continue/rules/stm32_model_qwen7b.md`
- `.continue/rules/stm32_model_glm.md`

这些 rules 会自动注入当前项目的：

- 项目名
- 默认 profile
- build 目录
- source 目录列表
- UART 端口
- 诊断串口端口
- ready banner
- prompt

## 2. 自动模式的执行顺序

Continue 在自动模式下应遵守下面的顺序。

### 2.1 先扫描项目

```powershell
agent_workbench.bat scan-project --json
```

这一步用于了解：

- 当前源码目录
- 已有初始化函数
- 已有 CLI 命令
- planner 模板覆盖情况

### 2.2 再生成计划

```powershell
cmd /c ".\agent_workbench.bat plan ""<用户需求>"" --json"
```

`plan` 会返回结构化 playbook，里面通常包含：

- 对用户需求的理解
- 受影响文件
- 推荐的实现步骤
- 构建与验证命令
- 失败后的重试建议
- 不应破坏的稳定字符串和限制

### 2.3 按 `steps[]` 执行

Continue 应该只根据 `steps[]` 决定读哪些文件、改哪些文件、执行哪些命令，而不是随意扩散。

推荐命令入口：

- `agent_workbench.bat build --json`
- `agent_workbench.bat parse-errors --json`
- `agent_workbench.bat ps-exec "build"`
- `agent_workbench.bat ps-exec "uart exec help status"`
- `agent_workbench.bat uart exec --json ...`

### 2.4 最后再做硬件动作

涉及下面动作时，建议先向用户确认：

- `flash`
- `reset`
- 长时间监控
- 会改变板上实际外设状态的操作

## 3. 现在已经内置的能力

### 3.1 规划模板库

当前模板库已经扩展到 16 个常见任务模板，覆盖：

- GPIO 输出与闪烁
- 基本定时器
- PWM
- ADC 读取
- I2C 设备接入
- SPI 设备接入
- DMA 传输
- EXTI 输入
- 中断处理
- UART echo
- CLI 命令扩展
- 传感器轮询
- 故障诊断
- 监控观察

这意味着弱模型通常只需要填细节，而不是从零发明整个执行方案。

### 3.2 编译错误规则库

`parse-errors --json` 现在会结合 `agent_workbench/templates/build_error_rules.json` 输出：

- 结构化错误列表
- 错误分类
- `suggested_fix`

常见缺失头文件、未定义符号、类型不匹配、重复定义等错误，都会给出更稳定的修复建议。

### 3.3 UART 失败智能诊断

当 `uart exec` 失败时，`cli_diag.json` 现在会带更多上下文：

- `category`
- `possible_causes`
- `suggested_next_step`

这样 Continue 在失败后更容易决定下一步是查串口、查 ready banner，还是查命令解析逻辑。

### 3.4 多模型 rules

当前自动模式除了通用 rules，还会生成三份模型专用规则：

- `stm32_model_deepseek_r1.md`
- `stm32_model_qwen7b.md`
- `stm32_model_glm.md`

这些 rules 会约束不同模型的：

- 单轮改动半径
- 推荐命令写法
- 错误恢复节奏
- 是否优先走 `ps-exec`

## 4. 推荐对话方式

在 Continue Agent 中直接输入一句需求即可，例如：

- `给板子加一个 1Hz LED 闪烁`
- `给 STM32 添加 PWM 蜂鸣器控制，频率 1kHz，PA8 引脚`
- `增加 I2C 传感器寄存器读取`
- `分析为什么 CLI 没有出现 ready banner`

理想情况下，Continue 会按下面顺序自行完成：

1. `scan-project --json`
2. `plan "<需求>" --json`
3. 按计划读取文件
4. 按计划修改文件
5. `build --json`
6. 失败时 `parse-errors --json`
7. 必要时再 `flash` / `uart exec`
8. 输出最终报告

## 5. 对弱模型的执行约束

为了让弱模型更稳，自动模式要尽量遵守这些规则：

- 优先执行 `agent_workbench.bat ... --json`
- 优先从 `plan` 的结果里拿命令，不要自行拼复杂命令链
- 一次只解决一个主错误
- 不要随意改 `ready_banner` 和 `prompt`
- 优先用 `ps-exec` 代替自由发挥的 PowerShell
- 没有用户确认时，不主动执行烧录或复位

## 6. 推荐的验收方式

开启自动模式后，至少跑通下面几条：

```powershell
agent_workbench.bat scan-project --json
agent_workbench.bat plan "增加 I2C 传感器寄存器读取" --json
agent_workbench.bat init-continue-rules --json
agent_workbench.bat doctor --json
py -3.8 -m unittest discover -s agent_workbench/tests -p "test_*.py"
```

如果需要补一次构建闭环，再加：

```powershell
agent_workbench.bat build --json
agent_workbench.bat parse-errors --json
```

## 7. 自动模式跑偏时怎么排查

优先看下面几项：

1. `.continue/rules/` 是否已经重新生成
2. `agent_workbench.bat doctor --json` 是否有 `fail`
3. `agent_workbench.bat scan-project --json` 是否能输出合理快照
4. `agent_workbench.bat plan "<需求>" --json` 是否返回合理的 `steps[]`
5. `agent_workbench.bat build --json` 的 `errors[]` 是否为空
6. `cli_diag.json` 是否已经给出 `possible_causes` 和 `suggested_next_step`

## 8. 和迁移流程的关系

如果你是在新项目里第一次启用自动模式，推荐先读 [MIGRATION_GUIDE_ZH.md](MIGRATION_GUIDE_ZH.md)。

迁移后的标准顺序应该是：

1. 改 `agent_workbench.yaml`
2. 跑 `doctor`
3. 跑 `init-vscode`
4. 跑 `init-continue-rules`
5. 跑 `scan-project --json`
6. 跑 `plan "<需求>" --json`
7. 再交给 Continue 自动执行

## 9. 一句话总结

自动模式的关键不是“让 Continue 更自由”，而是“让 Continue 在更窄、更结构化的轨道里工作”。

轨道主要由三层组成：

1. `plan` 命令和模板库
2. `.continue/rules/` 自动生成规则
3. `--json` / `ps-exec` / `parse-errors` 这些稳定入口
