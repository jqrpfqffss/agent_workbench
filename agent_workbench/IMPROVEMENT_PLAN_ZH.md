# Agent Workbench 改进计划（正式版）

> 本文档是 agent_workbench 项目的详细改进计划，参考开源 Claude Code 的优秀实践，旨在实现"用户只需输入一句自然语言需求，即可自动完成 STM32 调试/功能开发/测试验证"的最终目标。
>
> 本文档为规划阶段产物，**尚未修改任何代码**。

---

## 目录

1. [当前系统的核心问题](#一当前系统的核心问题)
2. [改造后的目标体验](#二改造后的目标体验)
3. [设计原则与硬性约束](#三设计原则与硬性约束)
4. [解决方案：3 个核心改造](#四解决方案3-个核心改造)
5. [完整使用流程](#五完整使用流程)
6. [迁移到新项目（改造后）](#六迁移到新项目改造后)
7. [实施路线图](#七实施路线图)
8. [需求逐项检验](#八需求逐项检验)
9. [附录：参考 Claude Code 的借鉴点](#九附录参考-claude-code-的借鉴点)

---

## 一、当前系统的核心问题

经过对 `agent_workbench/` 源码的深入分析（`workbench.py`、`core/task_spec.py`、`core/context_service.py`、`core/session_service.py`、`core/vscode_service.py`、prompts、tasks、runtime 产物等），识别出以下根本性缺陷：

### 1.1 用户必须手写 YAML 任务文件，门槛高

`core/task_spec.py` 中硬性要求 7 个字段：

```python
required = ["id", "mode", "goal", "scope", "acceptance", "observability", "verify"]
```

用户在 Continue 里说一句"给板子加 PWM 蜂鸣器"之前，必须先：
- 确定 `task_id`
- 写好 `scope.include/exclude` 列表
- 定义 `acceptance.blackbox` 断言
- 列出 `verify.cli_commands`

对迁移到新项目的用户来说，这是巨大的门槛。

### 1.2 Continue 当前是"被动文本生成器"，不是"自主执行器"

当前工作流：

```
用户手动运行 agent_workbench.bat context
  → 生成 paste.md
    → 用户手动复制 paste.md
      → 粘贴到 Continue 聊天窗口
        → Continue 给出一段文字建议（不会自己执行）
          → 用户再手动运行 agent_workbench.bat build
            → 用户再手动复制结果给 Continue
              → …（每一步都靠人搬运）
```

**全程都是人力搬运，根本谈不上"自动化"。**

### 1.3 paste.md 只告诉模型"读什么"，不告诉"下一步怎么做"

当前 `runtime/*_paste.md` 内容：

```text
Read only these files first:
- xxx_brief.md
- xxx_facts.json

This round must: implement the smallest safe change only.
```

这只是"请你读这些文件"级别的提示，完全没有告诉 Continue：

- 接下来该运行哪条 PowerShell 命令？
- 命令失败了该怎么办？
- 如何判断任务完成？
- 命令的完整格式是怎样？

弱模型（DeepSeek-R1、本地 Qwen）拿到这种模糊指令，只会输出文本建议，不会真的执行 PowerShell 命令。

### 1.4 PowerShell 命令执行脆弱，弱模型经常出错

典型错误（在实际使用中观察到）：

- 路径斜杠混用：`agent_workbench\tasks/xxx.yaml`
- 拼错命令前缀：`cd xxx && agent_workbench.bat ...`
- 不加 `cmd /c` 包装导致 PowerShell 解析错误
- 把多条命令用 `;` 或 `&&` 串联，一个失败全失败
- 返回的是文本而非结构化数据，模型难以解析

### 1.5 没有自主错误恢复

当前 `run_build()` 返回非零退出码后，整个流程就停止了：

```python
if build_code != 0:
    write_session_summary(session_dir)
    return build_code
```

没有"读错误 → 分析 → 自动修复 → 重编译"的内循环。

### 1.6 没有自然语言 → 任务拆解能力

`task_spec.py` 只会加载已存在的 YAML 文件，不能根据用户的一句自然语言描述自动生成任务。

---

## 二、改造后的目标体验

### 2.1 完整使用流程

```
┌────────────────────────────────────────────────────────────┐
│ 用户在 Continue 聊天窗口输入:                               │
│ "给STM32添加PWM蜂鸣器控制，频率1kHz，PA8引脚"               │
└──────────────────────────┬─────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│ Continue 根据 .continue/rules/ 自动执行（通过 PowerShell）  │
│                                                             │
│ Step 1: 运行 PowerShell                                     │
│   cmd /c ".\agent_workbench.bat plan ""<用户需求>"" --json" │
│   → 得到拆解后的步骤列表                                    │
│                                                             │
│ Step 2: 按步骤依次执行                                      │
│   - 读文件: Continue 用内置 read_file 工具                  │
│   - 改文件: Continue 用内置 edit_file 工具                  │
│   - 编译:   PowerShell: agent_workbench.bat build --json    │
│   - 烧录:   PowerShell: agent_workbench.bat flash --json    │
│   - 验证:   PowerShell: agent_workbench.bat uart exec --json│
│                                                             │
│ Step 3: 错误恢复                                            │
│   编译失败 → 读 errors[] → 修复代码 → 再编译（最多 3 次）    │
│                                                             │
│ Step 4: 在聊天窗口输出最终报告                              │
└────────────────────────────────────────────────────────────┘

全程特点:
✅ 用户只输入一句话，其余全自动
✅ 用户不需要写任何 task YAML 文件
✅ 用户不需要安装 MCP 或任何额外服务
✅ 命令都是 PowerShell 执行 agent_workbench.bat xxx
✅ 所有现有命令保留，用户随时可以手动运行
```

### 2.2 示例对话

```
👤 [Continue 聊天窗口]
给STM32添加PWM蜂鸣器控制，频率1kHz，PA8引脚

🤖 [Continue 自动执行]
下一步执行: cmd /c ".\agent_workbench.bat plan ""给STM32添加PWM蜂鸣器控制，频率1kHz，PA8引脚"" --json"
返回: {"plan_id":"...","steps":[7个步骤],...}

✅ Step 1: 已读取 Core/Src/main.c (287 行)
✅ Step 2: 已读取 Core/Inc/main.h (84 行)
✅ Step 3: 已修改 Core/Src/main.c (添加 MX_TIM1_PWM_Init 函数)
✅ Step 4: 已修改 Core/Inc/main.h (添加 htim1 extern 声明)

下一步执行: cmd /c ".\agent_workbench.bat build --json"
返回: {"exit_code":0,"status":"pass"}
✅ Step 5: 编译成功 (0 errors, 0 warnings)

⚠️ Step 6 需要确认: 即将烧录到硬件，是否继续? [用户点"继续"]

下一步执行: cmd /c ".\agent_workbench.bat flash --json"
返回: {"exit_code":0,"status":"pass"}
✅ Step 6: 烧录成功

下一步执行: cmd /c ".\agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --json"
返回: {"exit_code":0,"transcript":"..."}
✅ Step 7: CLI 验证通过

## 任务完成报告
- 用户需求: 给STM32添加PWM蜂鸣器控制，频率1kHz，PA8引脚
- 修改的文件: Core/Src/main.c, Core/Inc/main.h
- 编译结果: pass (0 errors)
- 烧录结果: pass
- CLI 验证结果: pass (ready banner 和 cli> prompt 均出现)
- 证据文件:
  - agent_workbench/runtime/build.log
  - agent_workbench/runtime/cli_transcript.log
```

---

## 三、设计原则与硬性约束

本次改造必须严格遵守的原则：

| 约束 | 含义 |
|------|------|
| ❌ **不做 MCP Server** | 保持极简部署，不新增服务进程 |
| ❌ **不让用户写 task YAML** | 完全从自然语言自动拆解 |
| ❌ **不做新的交互界面** | 全部在 Continue 聊天窗口内完成 |
| ✅ **执行全用 PowerShell** | 所有命令都是 `cmd /c ".\agent_workbench.bat xxx"` |
| ✅ **迁移零额外配置** | 拷贝目录 + 改 `agent_workbench.yaml` 即可 |
| ✅ **现有 CLI 全部保留** | `build` / `flash` / `session` / `uart` 等手动可用 |
| ✅ **支持弱模型** | 通过 rules + 模板 + 结构化输出降低出错率 |

---

## 四、解决方案：3 个核心改造

### 改造 1：新增 `plan` 命令 — 自然语言 → 可执行步骤清单 【最核心】

**位置：** `agent_workbench/core/planner.py`（新建）

#### 1.1 命令入口

```powershell
# 用户（或 Continue）在 PowerShell 里跑:
./agent_workbench.bat plan "给STM32添加PWM蜂鸣器控制，频率1kHz，PA8引脚" --json
```

#### 1.2 输出格式（关键设计）

**不输出 YAML 任务文件，而是一份 Continue 可直接执行的 Playbook JSON：**

```json
{
  "plan_id": "plan_20260418_153012",
  "user_request": "给STM32添加PWM蜂鸣器控制，频率1kHz，PA8引脚",
  "understanding": "在PA8引脚用TIM1_CH1输出1kHz PWM信号驱动蜂鸣器",
  "mode": "feature",

  "context": {
    "related_files": [
      "Core/Src/main.c",
      "Core/Inc/main.h"
    ],
    "existing_peripherals": ["USART2", "GPIO_LED_RED/GREEN/BLUE"],
    "stable_strings_to_preserve": [
      "STM32 UART CLI ready.",
      "cli>",
      "Available commands:"
    ]
  },

  "steps": [
    {
      "id": 1,
      "name": "读取现有 main.c 了解初始化流程",
      "action_type": "read_file",
      "file": "Core/Src/main.c",
      "why": "需要找到合适的位置插入 PWM 初始化调用"
    },
    {
      "id": 2,
      "name": "读取 main.h 了解外设句柄",
      "action_type": "read_file",
      "file": "Core/Inc/main.h",
      "why": "需要添加 TIM_HandleTypeDef htim1 声明"
    },
    {
      "id": 3,
      "name": "在 main.c 添加 MX_TIM1_PWM_Init 函数",
      "action_type": "edit_file",
      "file": "Core/Src/main.c",
      "instructions": "添加函数 void MX_TIM1_PWM_Init(void): htim1.Instance=TIM1; htim1.Init.Prescaler=71; htim1.Init.Period=999; HAL_TIM_PWM_Init(&htim1); HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1); 并在 main() 的 USER CODE BEGIN 2 后调用"
    },
    {
      "id": 4,
      "name": "在 main.h 添加 htim1 声明",
      "action_type": "edit_file",
      "file": "Core/Inc/main.h",
      "instructions": "在已有 extern 声明附近添加: extern TIM_HandleTypeDef htim1;"
    },
    {
      "id": 5,
      "name": "编译验证",
      "action_type": "shell",
      "command": "./agent_workbench.bat build --json",
      "success_criteria": "exit_code == 0",
      "on_failure": {
        "max_retries": 3,
        "retry_strategy": "读取返回的 errors[0]，用 edit_file 修复对应位置后回到当前步骤"
      }
    },
    {
      "id": 6,
      "name": "烧录到硬件",
      "action_type": "shell",
      "command": "./agent_workbench.bat flash --json",
      "success_criteria": "exit_code == 0",
      "requires_confirmation": true
    },
    {
      "id": 7,
      "name": "UART CLI 验证基本功能未受影响",
      "action_type": "shell",
      "command": "./agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --json",
      "success_criteria": "transcript 包含 'STM32 UART CLI ready.' 和 'cli>'"
    }
  ],

  "final_report_template": {
    "required_fields": [
      "修改的文件",
      "编译结果",
      "烧录结果",
      "CLI 验证结果",
      "证据路径"
    ]
  },

  "constraints": {
    "allowed_edit_files": ["Core/Src/main.c", "Core/Inc/main.h"],
    "max_total_steps": 15,
    "forbidden_operations": [
      "删除已有 CLI 命令",
      "修改 ready_banner 或 prompt 字符串",
      "改动 Drivers 目录"
    ]
  }
}
```

#### 1.3 实现方式（混合策略，不完全依赖 LLM）

```python
class Planner:
    def plan(self, user_request: str) -> Plan:
        # Step 1: 项目扫描（确定性）
        snapshot = scan_project(self.project_root)
        # → 知道有哪些文件、已有哪些 CLI 命令、已有哪些外设

        # Step 2: 关键词识别匹配模板（确定性）
        template = match_template(user_request)
        # → "PWM" → pwm_template
        # → "LED 闪烁" → gpio_blink_template
        # → "定时器" → timer_template
        # → "添加 CLI 命令" → cli_command_template

        # Step 3: 如果模板匹配，用 LLM 填充细节
        if template:
            return fill_template_with_llm(template, user_request, snapshot)

        # Step 4: 如果无匹配，让 LLM 完整生成（兜底）
        return llm_full_plan(user_request, snapshot)
```

**关键：模板库覆盖 80% 常见需求，弱模型只需要做简单填充。**

#### 1.4 任务模板库（预置，用户不用写）

```
agent_workbench/templates/task_templates/
  ├── gpio_blink.yaml        # LED 闪烁类需求
  ├── gpio_output.yaml       # GPIO 输出控制
  ├── timer_basic.yaml       # 基本定时器
  ├── timer_pwm.yaml         # PWM 输出
  ├── uart_cli_command.yaml  # 添加 CLI 命令
  ├── adc_read.yaml          # ADC 采样
  ├── interrupt_handler.yaml # 中断处理
  ├── i2c_device.yaml        # I2C 设备驱动
  ├── spi_device.yaml        # SPI 设备驱动
  └── debug_analyze.yaml     # 调试分析类
```

每个模板包含：
- 触发关键词列表（如 `[PWM, pwm, 蜂鸣器, 方波, 占空比]`）
- 标准步骤序列
- 该步骤的 PowerShell 命令
- 失败重试策略
- 验证方式

---

### 改造 2：Continue Rules 文件 — 告诉 Continue 如何自主执行 【核心】

**位置：** `.continue/rules/stm32_auto_workflow.md`（新建）

这是把"给 Continue 一个 paste.md"改造成"给 Continue 一套完整执行规则"的关键。
Continue 每次对话都会自动读到这些 rules。

#### 2.1 主规则文件 `stm32_auto_workflow.md`

```markdown
# STM32 Agent Workbench 自动执行规则

你是 STM32 开发助手。用户只会给你一句自然语言需求。
你必须按以下步骤**自主执行**，不能只输出文本建议：

## 核心原则
1. **必须用 PowerShell 执行命令**: 通过 VS Code 集成终端运行 agent_workbench.bat
2. **路径必须用 POSIX 风格**: `agent_workbench/tasks/xxx.yaml`，不用反斜杠
3. **命令必须用 cmd /c 包装**: `cmd /c ".\agent_workbench.bat build --json"`
4. **一次只运行一条命令**: 禁止用 `;` 或 `&&` 串接
5. **每条命令都加 --json 选项**: 解析结构化输出

## 第一步: 永远先生成执行计划

收到用户需求后，第一件事必须运行:

    cmd /c ".\agent_workbench.bat plan ""<用户的原话>"" --json"

把返回的 JSON 保存为你的执行脚本。

## 第二步: 严格按 Plan 的 steps 数组顺序执行

对每个 step，根据 action_type 执行对应操作:

### action_type: "read_file"
调用你的 read_file 工具读取 step.file
读完后在回复里写一行: "✅ Step N: 已读取 <文件名>，共 X 行"

### action_type: "edit_file"
调用你的 edit_file 工具按 step.instructions 修改
修改后在回复里写一行: "✅ Step N: 已修改 <文件名>"

### action_type: "shell"
在 PowerShell 里运行 step.command
解析返回的 JSON:
- 如果满足 success_criteria: 继续下一步
- 如果失败且有 on_failure:
  - 读取 errors 数组
  - 按 retry_strategy 修复
  - 重新运行当前 step
  - 达到 max_retries 后停止并报告
- 如果 requires_confirmation=true:
  - 先向用户显示将要执行的命令
  - 等用户确认后才执行

## 第三步: 生成最终报告

所有步骤完成后，按 plan.final_report_template 格式输出:

    ## 任务完成报告
    - 用户需求: <plan.user_request>
    - 修改的文件: <实际修改列表>
    - 编译结果: <pass/fail>
    - 烧录结果: <pass/fail/skipped>
    - CLI 验证结果: <pass/fail>
    - 证据文件:
      - cli_transcript: agent_workbench/runtime/cli_transcript.log
      - build log: agent_workbench/runtime/build.log

## 禁止行为
❌ 不要跳过 plan 步骤，直接开始改代码
❌ 不要超出 plan.constraints.allowed_edit_files 范围
❌ 不要删除 plan.context.stable_strings_to_preserve 里的字符串
❌ 不要把多条 shell 命令串起来执行
❌ 不要用"我建议您运行..."这种话，直接去运行
❌ 不要在没看到 build 返回 exit_code=0 前声称"代码完成"

## PowerShell 命令速查

所有可用命令都通过 `cmd /c ".\agent_workbench.bat <cmd>"`:

### 新增自动化入口
- `plan "<需求>" --json`                    生成执行计划
- `ps-exec "<简化命令>"`                    容错命令包装

### 现有命令（全部支持 --json）
- `doctor --json`                           环境检查
- `build --json`                            编译
- `flash --json`                            烧录
- `reset --json`                            复位
- `uart exec --reset-first --expect-ready --command <cmd> --json`
- `diag exec --json`                        诊断口发送
- `session debug --json`                    运行调试 session
- `session feature --task <yaml> --json`    运行 feature session
- `test generate --task <yaml> --json`      生成测试
- `test run --json`                         运行测试
- `verify current --task <yaml> --json`     直接验证
- `compare --latest --json`                 对比上次会话
- `report --latest --json`                  生成报告
- `context --mode debug --stage analyze`    (老的 paste.md 流程，保留)
```

#### 2.2 辅助规则文件

```
.continue/rules/
  ├── stm32_auto_workflow.md        # 主规则（上面那份）
  ├── stm32_weak_model_guard.md     # 弱模型额外约束
  ├── stm32_powershell_syntax.md    # PowerShell 正确语法示例库
  ├── stm32_error_recovery.md       # 各类错误的修复指引
  └── stm32_hardware_safety.md      # 硬件操作安全规则
```

#### 2.3 弱模型专用规则 `stm32_weak_model_guard.md`

```markdown
# 弱模型安全约束

如果你是弱模型（DeepSeek-R1 / 本地 Qwen），必须额外遵守:

## 防止 PowerShell 出错
1. 命令前永远加 `cmd /c` 前缀
2. 路径永远用正斜杠 `/`
3. 命令参数里的空格必须用双引号包裹
4. 绝对不要使用 `cd xxx; command` 模式
5. 不要用 PowerShell 的 `| ConvertFrom-Json`，workbench 内置 --json

## 防止"伪执行"
1. 运行命令前，先在回复里写: "下一步执行: <完整命令>"
2. 运行后必须写: "返回: <JSON 摘要>"
3. 严禁"我已经运行了..."但没有真的调用工具
4. 严禁基于"假设命令会返回什么"做推理

## 防止循环/死机
1. 同一步骤连续失败 3 次后，必须停止并报告
2. 总步骤数超过 plan.constraints.max_total_steps 后停止
3. 遇到无法理解的错误，直接向用户汇报
```

---

### 改造 3：PowerShell 命令层加固 — 让弱模型稳定调用 【核心】

这是解决"执行 PowerShell 指令经常出错"的根本办法。

#### 3.1 所有现有命令添加 `--json` 输出选项（向后兼容）

**位置：** `agent_workbench/workbench.py` 所有 `_cmd_*` 函数

```python
def _cmd_build(args):
    cfg = _cfg(args.config)
    code = run_build(cfg, log_path)

    if args.json:  # 新增分支
        from core.build_errors import parse_build_log
        errors = parse_build_log(log_path)
        output = {
            "command": "build",
            "exit_code": code,
            "status": "pass" if code == 0 else "fail",
            "errors": [e.to_dict() for e in errors],
            "log_path": str(log_path),
            "timestamp": utc_now_iso()
        }
        print(json.dumps(output, ensure_ascii=False))
    else:  # 保持原样，给人看
        print(f"build exit={code}")
    return code
```

**统一输出格式:**

```json
{
  "command": "<命令名>",
  "exit_code": 0,
  "status": "pass|fail|blocked|skipped",
  "summary": "人类可读的一句话结果",
  "details": { },
  "artifacts": { },
  "timestamp": "..."
}
```

#### 3.2 新增 `agent_workbench.bat ps-exec` 容错包装

弱模型拼命令容易出错。新增一个"命令修正代理":

```powershell
# Continue 可以这样简化调用:
./agent_workbench.bat ps-exec "build"
./agent_workbench.bat ps-exec "uart exec help"
./agent_workbench.bat ps-exec "flash"

# 内部自动:
# 1. 修正路径分隔符
# 2. 自动添加 --json
# 3. 自动处理引号转义
# 4. 捕获所有输出 (包括 stderr)
# 5. 返回标准 JSON 格式
```

#### 3.3 编译错误结构化解析

**位置：** `agent_workbench/core/build_errors.py`（新建）

```python
from dataclasses import dataclass

@dataclass
class BuildError:
    file: str
    line: int
    column: int
    level: str                # "error" / "warning"
    error_code: str           # "undeclared_identifier"
    message: str
    category: str             # "syntax" / "link" / "include" / "type" / "undefined"
    context_lines: list[str]  # 错误行前后几行代码
    suggested_fix: str        # 基于规则库的修复建议

def parse_build_log(log_path: Path) -> list[BuildError]:
    """解析 cmake/arm-none-eabi-gcc 的错误输出"""
    ...
```

Continue 拿到的结构化错误:

```json
{
  "exit_code": 1,
  "errors": [{
    "file": "Core/Src/main.c",
    "line": 123,
    "message": "'htim1' undeclared",
    "suggested_fix": "在文件顶部添加: extern TIM_HandleTypeDef htim1;"
  }]
}
```

有了 `suggested_fix`，弱模型也能精确修复。

#### 3.4 UART 验证失败的结构化诊断

利用现有 `cli_diag_service` 增强：

```json
{
  "command": "uart exec",
  "exit_code": 12,
  "status": "fail",
  "diagnosis": {
    "category": "ready_missing",
    "summary": "未收到 ready banner 'STM32 UART CLI ready.'",
    "possible_causes": [
      "板子没有真正复位",
      "ready_banner 字符串被修改",
      "UART 初始化代码被破坏"
    ],
    "suggested_next_step": "检查 cli_transcript.log 前 10 行"
  }
}
```

---

## 五、完整使用流程

### 5.1 首次配置（一次性，极简）

```powershell
# 从旧项目拷贝这些文件到新项目:
#   - agent_workbench.bat
#   - setup_workbench.bat
#   - agent_workbench/ 整个目录（删掉 runtime/evidence/generated）

setup_workbench.bat                      # 装依赖
agent_workbench.bat doctor               # 环境检查
agent_workbench.bat init-vscode          # 生成 .vscode/tasks.json
agent_workbench.bat init-continue-rules  # 【新增】生成 .continue/rules/*.md
agent_workbench.bat build                # 首次编译
```

就这些。**没有 MCP，没有额外服务进程。**

### 5.2 日常使用 — 自动模式（主要方式）

```
👤 在 VS Code Continue 聊天窗口直接输入:
"给STM32添加PWM蜂鸣器控制，频率1kHz，PA8引脚"

🤖 Continue 根据 rules 自主完成全流程，只在烧录等关键节点向用户确认
   最终在聊天窗口输出任务完成报告
```

### 5.3 日常使用 — 手动模式（保留，调试时用）

**所有现有命令继续可用**：

```powershell
./agent_workbench.bat doctor
./agent_workbench.bat build
./agent_workbench.bat flash --method openocd_cmd
./agent_workbench.bat uart exec --reset-first --expect-ready --command help
./agent_workbench.bat uart console
./agent_workbench.bat session debug
./agent_workbench.bat session feature --task xxx.yaml      # 老方式继续可用
./agent_workbench.bat test generate --task xxx.yaml
./agent_workbench.bat test run
./agent_workbench.bat diag exec
./agent_workbench.bat monitor start/stop/status
./agent_workbench.bat openocd start/stop/status
./agent_workbench.bat compare --latest
./agent_workbench.bat report --latest
./agent_workbench.bat verify current --task xxx.yaml
./agent_workbench.bat context --mode debug --stage analyze # 老 paste.md 方式继续可用

# 新增命令也可以手动使用:
./agent_workbench.bat plan "需求描述"                       # 手动生成计划看看
./agent_workbench.bat parse-errors --log xxx                # 手动解析编译错误
./agent_workbench.bat scan-project                          # 手动扫描项目结构
./agent_workbench.bat ps-exec "build"                       # 手动用简化命令
./agent_workbench.bat init-continue-rules                   # 手动刷新 rules
```

### 5.4 混合模式

```
Continue: "分析当前代码结构"  → Continue 自动扫描并汇报
  ↓
用户手动: ./agent_workbench.bat build  → 手动验证
  ↓
Continue: "帮我加上测试用例"  → Continue 继续自主执行
```

---

## 六、迁移到新项目（改造后）

```powershell
# 1. 从旧项目拷贝（就这 3 样）
cp agent_workbench.bat <新项目>/
cp setup_workbench.bat <新项目>/
cp -r agent_workbench/ <新项目>/
# 注意: 删掉 agent_workbench/runtime, evidence, generated 等运行产物

# 2. 修改一个配置文件
vim agent_workbench/agent_workbench.yaml
#   - project.name
#   - uart.port (COM 口)
#   - tools.openocd.daemon_cmd (target cfg 可能变)
#   - 其它保持默认就行

# 3. 一次性初始化
setup_workbench.bat
agent_workbench.bat doctor
agent_workbench.bat init-vscode
agent_workbench.bat init-continue-rules   # 【关键】生成 .continue/rules/

# 完成!
# 现在可以在 Continue 说: "给新板子加个串口回显功能"
# Continue 会自动完成
```

**零额外服务、零额外配置。**

---

## 七、实施路线图

### 第一阶段：核心功能闭环（2–3 周）

**目标：** 用户在 Continue 说一句话 → 自动完成一个简单功能（如 LED 闪烁）

| 天数 | 任务 | 产出 |
|------|------|------|
| 1 | 所有现有命令添加 `--json` 选项 | `workbench.py` 所有 `_cmd_*` 改造 |
| 2 | 编译错误结构化解析 | `core/build_errors.py` |
| 3 | Planner 核心 + 5 个模板 | `core/planner.py` + `templates/task_templates/*.yaml` |
| 1 | 新增 `plan` CLI 子命令 | `workbench.py` 新 subparser |
| 2 | 新增 `ps-exec` 容错包装 | `workbench.py` 新 subparser |
| 2 | 编写主 rules 文件 | `.continue/rules/stm32_auto_workflow.md` |
| 1 | 编写弱模型 rules | `.continue/rules/stm32_weak_model_guard.md` |
| 1 | 新增 `init-continue-rules` 命令 | `core/vscode_service.py` 扩展 |
| 2 | 端到端联调 | 实际需求跑通 |

**验收标准：** 在 Continue 说"给板子加个 1Hz LED 闪烁"，5 分钟内看到板子真的闪起来。

### 第二阶段：稳定性和覆盖度（2 周）

| 任务 | 产出 |
|------|------|
| 扩展模板库到 15 个 | `templates/task_templates/` 新增 ADC/I2C/SPI/中断/DMA 等 |
| 编译错误修复规则库 | 常见 10 类错误的标准修复策略 |
| UART 验证失败智能诊断 | 基于现有 `cli_diag` 增强 |
| 多模型 rules 调优 | DeepSeek-R1 / Qwen 7B / GLM 专用 rules |
| 回归测试套件 | 10 类需求 × 3 个模型的成功率测试 |

**验收标准：** 10 类常见需求在 3 个不同能力模型上成功率 >= 80%。

### 第三阶段：迁移友好性 + 文档（1 周）

| 任务 | 产出 |
|------|------|
| `init-continue-rules` 自动生成项目专属 rules | 根据 `agent_workbench.yaml` 填模板 |
| `doctor` 命令检查 rules 文件完整性 | `core/doctor.py` 扩展 |
| 更新迁移指南 | `MIGRATION_GUIDE_ZH.md` |
| 新建自动模式教程 | `CONTINUE_AUTO_MODE_GUIDE_ZH.md` |

**验收标准：** 新人迁移到新项目后，15 分钟内跑通第一个自动化需求。

---

## 八、需求逐项检验

| 用户要求 | 本方案是否满足 | 如何实现 |
|---------|--------------|---------|
| 用户只输入一句话需求 | ✅ | Continue 聊天窗口输入即可 |
| 自动拆解成小任务 | ✅ | `plan` 命令 + 模板库 |
| 自动依次执行 | ✅ | Rules 文件指导 Continue 按 plan 执行 |
| 最终结果返回 | ✅ | Rules 要求输出标准完成报告 |
| **不用 MCP Server** | ✅ | 全程通过 PowerShell 执行，无额外服务 |
| **通过 PowerShell 执行命令** | ✅ | 所有 action_type=shell 的步骤都是 PS |
| **迁移无需额外配置** | ✅ | 只改 `agent_workbench.yaml`，无 MCP/服务 |
| **用户不用写 task YAML** | ✅ | `plan` 完全从自然语言自动生成 |
| **现有手动命令保留** | ✅ | 所有 `agent_workbench.bat xxx` 继续可用 |
| **支持自动化调试** | ✅ | plan 识别 debug 类需求走 debug 流程 |
| **支持自动化功能开发** | ✅ | plan 识别 feature 类需求走 feature 流程 |
| **支持自动化测试验证** | ✅ | plan 中自动包含 uart_exec 验证步骤 |
| **弱模型稳定工作** | ✅ | Rules + 模板 + `ps-exec` 三层保护 |

---

## 九、附录：参考 Claude Code 的借鉴点

Claude Code 是 Anthropic 开源的优秀代码 Agent 产品，有以下能力值得借鉴：

| Claude Code 能力 | 本方案对应实现 |
|-----------------|--------------|
| 自然语言直接输入 | Continue 聊天窗口输入 |
| 自动任务拆解 | `plan` 命令 + 模板库 |
| Tool Use 循环（read/write/bash） | Continue 内置工具 + PowerShell |
| 结构化输出便于模型解析 | 所有命令的 `--json` 选项 |
| 错误自修复循环 | 编译错误 `suggested_fix` + 3 次重试 |
| Plan → Execute → Observe → Adjust | rules 文件强制的执行模式 |
| 清晰的 STOP 条件 | plan 的 `max_total_steps` + `success_criteria` |
| 上下文智能管理 | 保留现有 context_service.py 分阶段裁剪 |
| 对弱模型友好 | rules + 模板 + ps-exec 三层防护 |

**关键差异：**

- Claude Code 是通用代码 Agent，本方案专注 STM32 嵌入式开发
- Claude Code 需要自己提供 LLM API，本方案复用 Continue 已配置的模型
- Claude Code 有完整 UI，本方案全部在 Continue 聊天窗口内

---

## 十、根本设计思想

把当前系统的"**人搬运 Continue**"改为"**Continue 自主搬运 workbench**"：

```
改造前:
  人 → context → paste.md → 人复制 → Continue → 文本建议 → 人执行 PS → 结果 → 人复制 → Continue → ...
  （全是人力搬运）

改造后:
  人说一句话 → Continue 自动调 plan → Plan JSON → Continue 自动调 PowerShell → 结果 → Continue 判断 → 下一步
  （人只在关键节点审批）
```

### 核心改变点只有 3 个

1. **`plan` 命令**: 把人工拆解变成自动拆解
2. **`rules` 文件**: 告诉 Continue 如何自主执行 plan
3. **`ps-exec` + `--json`**: 让 PowerShell 交互对弱模型友好

### 本方案不涉及的

- 不加 MCP Server
- 不加新 UI / 进度条
- 不改 Continue 本身
- 不删任何现有命令
- 不让用户写 YAML

---

## 十一、变更文件清单（预估）

### 新增文件

```
agent_workbench/core/planner.py                    # 任务拆解器
agent_workbench/core/build_errors.py               # 编译错误解析
agent_workbench/core/project_scanner.py            # 项目扫描器
agent_workbench/core/ps_exec.py                    # PowerShell 容错包装
agent_workbench/templates/task_templates/*.yaml    # 任务模板库（10+ 个）
.continue/rules/stm32_auto_workflow.md             # 主规则
.continue/rules/stm32_weak_model_guard.md          # 弱模型约束
.continue/rules/stm32_powershell_syntax.md         # PS 语法速查
.continue/rules/stm32_error_recovery.md            # 错误修复指引
.continue/rules/stm32_hardware_safety.md           # 硬件安全规则
agent_workbench/CONTINUE_AUTO_MODE_GUIDE_ZH.md     # 自动模式使用教程
```

### 修改文件

```
agent_workbench/workbench.py                       # 所有命令添加 --json，新增 plan/ps-exec/parse-errors/scan-project/init-continue-rules
agent_workbench/core/task_spec.py                  # 放宽强制字段，支持 plan 生成的临时 spec
agent_workbench/core/vscode_service.py             # 新增 init-continue-rules 功能
agent_workbench/core/build_service.py              # 支持结构化错误输出
agent_workbench/core/uart_service.py               # 支持结构化诊断输出
agent_workbench/core/doctor.py                     # 检查 rules 文件完整性
agent_workbench/agent_workbench.yaml               # 新增 planner/templates 相关配置段
agent_workbench/MIGRATION_GUIDE_ZH.md              # 更新迁移说明
agent_workbench/README.md                          # 更新主流程介绍
```

### 不删任何文件

- 所有现有命令保留
- 所有现有文档保留（标注"老流程，仍然可用"）
- 所有现有 `tasks/*.yaml` 示例保留作为参考

---

## 十二、下一步

本计划文档为**规划阶段产物**，尚未修改任何代码。

如需开始实施：

1. 按第一阶段路线图从"所有命令添加 --json"开始
2. 每完成一个子模块先做单元测试
3. 每完成一个阶段做端到端联调
4. 出现任何阻塞问题及时停下来讨论

---

**文档结束**

> 生成时间: 2026-04-18
> 版本: v3 (最终版)
> 作者: AI Assistant (基于用户需求反复修正)
