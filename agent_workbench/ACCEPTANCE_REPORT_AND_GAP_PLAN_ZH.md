# Agent Workbench 改进计划实施验收报告 + 补充改进计划（v2 修正版）

> 本文档是对其他大模型依据 `IMPROVEMENT_PLAN_ZH.md` 所做实施的**验收结果**，以及**补足缺陷的改进计划**。
>
> **重要约束（v2 修正）：**
> - ❌ **不要把 LLM Client 接入 agent_workbench**（原 v1 的改进模块 A 作废）
> - ✅ **所有与大模型的交互都只在 Continue 聊天窗口进行**
> - ✅ **Continue 的 Agent 模式由用户自己开启**（不是我们改造的范围）
> - ✅ **agent_workbench 保持纯确定性工具层**（关键词匹配、regex、模板、静态知识库）
>
> 本文档**只给改进计划，不执行任何修改**。

---

## 核心架构（修正后的清晰分层）

```
┌────────────────────────────────────────────────────────────┐
│  第 1 层（用户层）                                          │
│  用户在 Continue 聊天窗口输入自然语言需求                   │
└──────────────────────┬─────────────────────────────────────┘
                       ↓
┌────────────────────────────────────────────────────────────┐
│  第 2 层（智能层 = Continue Agent）                         │
│  - 用户自己开启 Continue 的 Agent 模式                      │
│  - Continue 读取 .continue/rules/*.md 理解工作流            │
│  - Continue 用自己的 LLM 能力做代码决策                     │
│  - 通过 PowerShell 调用 agent_workbench.bat xxx             │
│  ★ 所有 LLM 交互都在这一层，不进入 agent_workbench 项目     │
└──────────────────────┬─────────────────────────────────────┘
                       ↓
┌────────────────────────────────────────────────────────────┐
│  第 3 层（确定性工具层 = agent_workbench）                  │
│  - plan: 关键词匹配 + 参数提取 + 硬件知识库 + 模板渲染      │
│  - build / flash / uart / parse-errors: 现有工具            │
│  - scan-project: 项目扫描                                   │
│  ★ 全部确定性，不调用任何 LLM API                          │
│  ★ 输出结构化 JSON，Continue 的 LLM 基于此做决策           │
└────────────────────────────────────────────────────────────┘
```

**关键设计：** agent_workbench 的职责是**给 Continue 提供"做决策所需的所有确定性信息"**，Continue 自己的 LLM 负责把信息转成具体代码。

---

## 目录

1. [验收总览（完成度打分）](#一验收总览完成度打分)
2. [实际验证过程和证据](#二实际验证过程和证据)
3. [严重缺陷清单（阻断自动化）](#三严重缺陷清单阻断自动化)
4. [次要缺陷清单](#四次要缺陷清单)
5. [补充改进计划（v2 修正版：纯确定性工具方案）](#五补充改进计划v2-修正版纯确定性工具方案)
6. [新的实施路线图](#六新的实施路线图)
7. [验收标准](#七验收标准)
8. [给实施者的交底](#八给实施者的交底)

---

## 一、验收总览（完成度打分）

| 计划项 | 实施状态 | 质量评分 | 备注 |
|--------|---------|---------|------|
| **`plan` 命令** | ✅ 已实现 | 🟡 40 / 100 | 只做关键词匹配 + 字符串模板替换，输出对 Continue 来说"信息量不足" |
| **`.continue/rules/`** | ✅ 已创建 | 🟡 50 / 100 | 8 个文件，主规则只有 57 行，弱模型规则只有 11 行，约束力不足 |
| **`--json` / `ps-exec` / `build_errors`** | ✅ 已实现 | 🟢 85 / 100 | 基础设施到位 |
| 项目扫描器 | ✅ 已实现 | 🟢 75 / 100 | 扫描基础信息可以，但没有扫描"硬件参数/引脚映射/已有函数体" |
| 任务模板库（16 个） | ✅ 已实现 | 🟡 55 / 100 | 数量达标，但每个模板只给出模糊指令，没有硬件参数表、参数提取规则 |
| 编译错误解析 | ✅ 已实现 | 🟡 60 / 100 | 能解析，但 `suggested_fix` 是通用静态字符串，信息量不足以让 Continue 精确修复 |
| 测试套件 | ✅ 已实现 | 🟢 80 / 100 | 30 个测试，29 通过（1 个因 COM3 不存在） |
| `init-continue-rules` | ✅ 已实现 | 🟢 75 / 100 | 基础完整 |
| 迁移简化 | ✅ 已实现 | 🟢 80 / 100 | 迁移步骤清晰 |
| **"用户一句话→自动完成"** | ❌ **未达成** | 🔴 **30 / 100** | **核心能力缺失（详见下文）** |

**整体：62 / 100**

---

## 二、实际验证过程和证据

### 2.1 实测 plan 命令（PWM 场景）

**输入：** `agent_workbench.bat plan "给STM32添加PWM蜂鸣器控制频率1kHz PA8引脚" --json`

**关键输出片段：**

```json
{
  "template_id": "timer_pwm",
  "matched_keywords": ["pwm", "蜂鸣器", "频率"],
  "steps": [
    {
      "id": 3,
      "action_type": "edit_file",
      "file": "Core/Src/main.c",
      "instructions": "依据 `给STM32添加PWM蜂鸣器控制频率1kHz PA8引脚` 在现有主流程中加入最小安全的 PWM/蜂鸣器控制逻辑，避免改坏串口 CLI 和启动提示。"
    }
  ]
}
```

**问题分析：**

Continue 的 LLM 拿到上面这个 instructions，**即使它有 tool_use 能力，也不知道**：

- 应该用哪个定时器？（TIM1 / TIM3 / ...?）
- 1kHz 对应什么 Prescaler/Period？
- PA8 该怎么配引脚复用？
- 在哪段 USER CODE 区插入？

**关键发现：用户的"1kHz"和"PA8"这两个关键参数根本没被 plan 提取出来，也没传给 Continue。**

### 2.2 实测 plan 命令（CLI 命令场景）

**输入：** `agent_workbench.bat plan "添加一个CLI命令uptime可以显示系统运行了多少秒" --json`

**输出观察：**
- ✅ 识别为 `uart_cli_command` 模板
- ❌ `instructions` 仍然只有模糊描述
- ❌ **"uptime" 这个命令名没被提取出来**，Continue 只能从用户原话里自己理解
- ❌ **"系统运行了多少秒"的功能描述没被提取**
- ❌ `stable_strings` 里出现乱码 `"{'Available commands': None}"`

### 2.3 实测其它命令

- ✅ `ps-exec "build"` 正常工作
- ✅ `parse-errors --json` 结构正确
- ✅ `scan-project --json` 能输出项目扫描结果
- ⚠️ 测试套件 30 个里 29 通过（1 个因 COM3 环境问题）

### 2.4 阅读代码的关键发现

查看 `core/planner.py::Planner.plan()`（第 126–233 行）：

```python
def plan(self, user_request: str) -> dict[str, Any]:
    snapshot = scan_project(self.cfg)
    template, matched_keywords = self._match_template(user_request)
    ...
    payload = _render_value(template.payload, values)  # ← 只做字符串替换
    ...
```

**`_render_value` 只把 `{user_request}`、`{ready_banner}`、`{prompt}`、`{uart_port}`、`{build_dir}` 这 5 个变量做字符串替换。**

- ❌ 没有提取用户需求里的关键参数（"1kHz"、"PA8"、"uptime"）
- ❌ 没有引入硬件知识库（引脚复用表、定时器频率公式）
- ❌ 没有基于 snapshot 做智能决策

这就是为什么输出对 Continue 来说"信息量不足"。

---

## 三、严重缺陷清单（阻断自动化）

### 缺陷 #1：Plan 输出的信息量不足以让 Continue 做出具体决策 🔴

**问题本质：** 用户需求里的关键参数没被提取出来并结构化返回给 Continue。

**影响：** Continue 的 LLM（即使在 Agent 模式下）也得"从原始自然语言里猜"，弱模型很容易猜错。

**具体案例：**

用户说 **"给 STM32 加 1kHz PWM PA8"**

**Continue 需要知道但 plan 没给的信息：**

| 关键参数 | Continue 应该知道 | Plan 当前是否提供 |
|---------|------------------|-----------------|
| 频率值 | 1000 Hz | ❌ 只在 user_request 字符串里 |
| 引脚 | PA8 | ❌ 只在 user_request 字符串里 |
| 可用定时器 | TIM1/TIM3 等在这个芯片上的列表 | ❌ 没有 |
| 定时器→引脚映射 | PA8 对应 TIM1_CH1 | ❌ 没有 |
| 计算公式 | f = 72MHz/((P+1)*(N+1)) | ❌ 没有 |
| USER CODE 块位置 | `/* USER CODE BEGIN 2 */` 的具体行号 | ❌ 没有 |
| 现有 TIM 句柄 | 是否已经有 htim1 | ❌ 没有 |

**结论：** agent_workbench 可以在**不调用 LLM** 的情况下，用纯确定性手段（regex 提取 + 静态知识库 + 项目扫描）把上面所有信息都补齐，这是下面改进计划的核心。

---

### 缺陷 #2：编译错误的 `suggested_fix` 信息量不足 🔴

**问题：** `suggested_fix` 是静态通用字符串，Continue 拿到后依然要自己推理。

**案例：**
```json
{
  "message": "'htim1' undeclared (first use in this function)",
  "suggested_fix": "查看日志上下文并从第一条 error 开始修复，避免被连锁报错干扰。"
}
```

Continue 的 LLM 看到这个，得自己推理：
1. 需要在哪个文件加声明？
2. 用 extern 还是 typedef？
3. 放在哪一行？

**应该改为：**
```json
{
  "message": "'htim1' undeclared",
  "suggested_fix": {
    "pattern_matched": "undeclared_timer_handle",
    "recommended_action": "add_extern_declaration",
    "target_files": ["Core/Inc/main.h"],
    "target_region": "/* USER CODE BEGIN PV */",
    "code_template": "extern TIM_HandleTypeDef htim{N};",
    "parameter_hints": {"N": "1"},
    "reasoning": "htim1 在使用但未声明。需要在全局声明区加 extern。"
  }
}
```

**关键：这全部可以用 regex + 静态规则库实现，不需要 LLM。**

---

### 缺陷 #3：Rules 文件不足以指导 Continue 按结构化 plan 工作 🔴

**问题：** 当前 rules 没告诉 Continue：

1. `plan.steps[i].instructions` 里可能包含 code_change_hints 数组，Continue 应该按这个数组展开为具体代码
2. `plan.hardware_context` 里的引脚映射、时钟公式是权威信息源
3. `plan.parameter_extractions` 里的提取结果是"用户真实意图"的翻译
4. build 失败时，要调 `parse-errors --json` 读结构化 `suggested_fix`，然后按 `recommended_action` + `code_template` + `parameter_hints` 组合生成具体修改

**需要把 rules 改成"Continue 消费结构化 plan 的完整操作手册"**。

---

### 缺陷 #4：Plan 没有消费 scan_project 的结果做智能决策 🟠

**现象：** scan_project 返回了 `detected_init_functions`、`help_commands` 等信息，但 Planner 只把它放在 `context` 字段里，没有基于这些信息调整 plan。

**应该做的（纯确定性）：**
- 如果 `detected_init_functions` 里已经有 `TIM1`，plan 应提示"TIM1 已存在，复用而不是新建"
- 如果 `help_commands` 里已经有 `uptime`，plan 应标记这是**修改**而不是**新增**
- 如果 `Core/Src/cli.c` 不存在，action_type 应改为 `create_file`

---

### 缺陷 #5：stable_strings 模板渲染 bug 🟠

**现象：** 输出出现 `"{'Available commands': None}"` 乱码。

**根因：** YAML 模板里写了 `{Available commands}` 这种占位符但 `values` 字典里没有这个 key，render_template 返回了默认的空 dict 被 str 化。

**解决：** render_template 未知变量时应保留原字符串或直接删除，而不是 fallback 成空 dict。

---

### 缺陷 #6：没有端到端自动化验收 🟠

**现象：** 30 个单元测试都是模块级，没有"用真 Continue 跑真需求看能否完成"的回归。

**注意：** 这个验收不需要在 CI 里调 LLM API（符合"不接 LLM 到 workbench"的约束），而是：
- 验证 plan 输出的 JSON 结构完整性
- 验证关键参数是否被提取出来
- 验证硬件知识库是否生效

---

### 缺陷 #7：Continue Agent 模式的集成使用文档缺失 🟠

**问题：** Rules 文件写了，但新用户不知道：
- Continue 里 Agent 模式在哪开启
- 如何确认 rules 被加载
- 如何测试 tool_use 已启用

**注意：** 这不需要改 Continue 配置，只需要**给用户一份操作手册**。

---

## 四、次要缺陷清单

### 4.1 文档滞后
- `MIGRATION_GUIDE_ZH.md` 没提 `init-continue-rules`
- `README.md` 主流程还是老 paste.md 流程
- `CONTINUE_AUTO_MODE_GUIDE_ZH.md` 内容未审查

### 4.2 模板粒度问题
- 模板之间可能关键词冲突（如 "led" 同时匹配 gpio_blink / gpio_output）
- 没有分类组织
- 没有继承/组合机制

### 4.3 fallback 模板太弱
- 用户说"为什么串口断连"时，fallback 只提供 3 步通用流程

### 4.4 verify 命令未整合
- 还依赖手写 task yaml，没有 `verify --request "自然语言"` 模式

---

## 五、补充改进计划（v2 修正版：纯确定性工具方案）

### 核心原则（反复强调）

🔴 **不要在 agent_workbench 项目中接入任何 LLM API**  
🔴 **不要创建 `core/llm_client.py` 或类似文件**  
🔴 **所有 LLM 调用都只在 Continue 聊天窗口完成**  
✅ agent_workbench 只做：关键词匹配、regex 参数提取、静态知识库查表、模板渲染、项目扫描、结构化 JSON 输出  

---

### 改进模块 A：参数提取器 + 硬件知识库（替代 v1 的 LLM 填充） 🔴【最高优先级】

**目标：** 让 Planner 在**不调用 LLM** 的前提下，把用户需求里的关键参数提取出来，并查静态硬件知识库补齐上下文，最终输出**信息量足够让 Continue 的 LLM 直接生成代码**的结构化 JSON。

#### A.1 新增参数提取器

**位置：** `agent_workbench/core/param_extractor.py`（新建）

**职责：** 纯 regex 从用户自然语言提取结构化参数。

```python
from dataclasses import dataclass, field
import re

@dataclass
class ExtractedParameters:
    """从自然语言提取的结构化参数（纯 regex，无 LLM）"""
    frequency_hz: int | None = None       # "1kHz" → 1000
    duty_percent: int | None = None       # "50%占空比" → 50
    period_ms: int | None = None          # "500ms" → 500
    pin: str | None = None                # "PA8" → "PA8"
    timer: str | None = None              # "TIM3" → "TIM3"
    gpio_port: str | None = None          # "GPIOA" → "GPIOA"
    cli_command_name: str | None = None   # 从"添加命令XXX"中提取
    baud_rate: int | None = None          # "115200" → 115200
    voltage: float | None = None          # "3.3V" → 3.3
    raw_keywords: list[str] = field(default_factory=list)

# 单位换算表（确定性）
FREQUENCY_UNITS = {
    "hz": 1,
    "khz": 1000,
    "mhz": 1_000_000,
    "千赫": 1000,
    "兆赫": 1_000_000,
}

# 正则模式库
FREQUENCY_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*(hz|khz|mhz|千赫|兆赫)",
    re.IGNORECASE
)

PIN_PATTERN = re.compile(r"\bP([A-H])(\d{1,2})\b", re.IGNORECASE)

TIMER_PATTERN = re.compile(r"\bTIM(\d{1,2})\b", re.IGNORECASE)

CLI_COMMAND_PATTERN = re.compile(
    r"(?:命令|command)[\s'\"]*([a-z_][a-z0-9_]*)",
    re.IGNORECASE
)

DUTY_PATTERN = re.compile(r"(\d+)\s*%\s*(?:占空比|duty)")

PERIOD_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*(ms|s|毫秒|秒)",
    re.IGNORECASE
)

def extract_parameters(user_request: str) -> ExtractedParameters:
    """从自然语言需求提取结构化参数（纯 regex）"""
    params = ExtractedParameters()
    lower = user_request.lower()

    # 频率
    if match := FREQUENCY_PATTERN.search(user_request):
        value = float(match.group(1))
        unit = match.group(2).lower()
        params.frequency_hz = int(value * FREQUENCY_UNITS[unit])

    # 引脚
    if match := PIN_PATTERN.search(user_request):
        params.pin = f"P{match.group(1).upper()}{match.group(2)}"
        params.gpio_port = f"GPIO{match.group(1).upper()}"

    # 定时器
    if match := TIMER_PATTERN.search(user_request):
        params.timer = f"TIM{match.group(1)}"

    # CLI 命令名（识别引号/空格后的英文单词作为命令名）
    if match := CLI_COMMAND_PATTERN.search(user_request):
        params.cli_command_name = match.group(1)

    # 占空比
    if match := DUTY_PATTERN.search(user_request):
        params.duty_percent = int(match.group(1))

    # 周期
    if match := PERIOD_PATTERN.search(user_request):
        value = float(match.group(1))
        unit = match.group(2).lower()
        if unit in ("ms", "毫秒"):
            params.period_ms = int(value)
        else:
            params.period_ms = int(value * 1000)

    return params
```

**关键：所有提取逻辑都是纯 Python + regex，不调用任何外部 API。**

#### A.2 新增硬件知识库

**位置：** `agent_workbench/templates/hardware_knowledge/`（新建目录）

**格式：** 静态 YAML 文件，包含 STM32 硬件参数和算法。

**A.2.1：** `templates/hardware_knowledge/stm32f1_clock.yaml`

```yaml
# STM32F1 时钟配置（静态数据，不会变）
mcu_family: stm32f1
system_clock_hz: 72000000
default_hsi_hz: 8000000
default_hse_hz: 8000000

# 各定时器使用的时钟源（都是 72MHz）
timer_clocks:
  TIM1: 72000000
  TIM2: 72000000
  TIM3: 72000000
  TIM4: 72000000

# 定时器频率计算公式说明
frequency_formula: "f = system_clock / ((Prescaler + 1) * (Period + 1))"
```

**A.2.2：** `templates/hardware_knowledge/stm32f1_timer_pin_map.yaml`

```yaml
# STM32F103 定时器通道 ↔ 引脚映射表（静态权威数据）
timer_channel_to_pin:
  TIM1_CH1: { pin: PA8,  af: AF_PP }
  TIM1_CH2: { pin: PA9,  af: AF_PP }
  TIM1_CH3: { pin: PA10, af: AF_PP }
  TIM1_CH4: { pin: PA11, af: AF_PP }
  TIM2_CH1: { pin: PA0,  af: AF_PP }
  TIM2_CH2: { pin: PA1,  af: AF_PP }
  TIM2_CH3: { pin: PA2,  af: AF_PP }   # 注意：与 USART2_TX 冲突！
  TIM2_CH4: { pin: PA3,  af: AF_PP }
  TIM3_CH1: { pin: PA6,  af: AF_PP }
  TIM3_CH2: { pin: PA7,  af: AF_PP }
  TIM3_CH3: { pin: PB0,  af: AF_PP }
  TIM3_CH4: { pin: PB1,  af: AF_PP }
  TIM4_CH1: { pin: PB6,  af: AF_PP }
  TIM4_CH2: { pin: PB7,  af: AF_PP }
  TIM4_CH3: { pin: PB8,  af: AF_PP }
  TIM4_CH4: { pin: PB9,  af: AF_PP }

# 反向映射：给定引脚找可用的定时器通道
pin_to_timer_channels:
  PA0: [TIM2_CH1]
  PA1: [TIM2_CH2]
  PA2: [TIM2_CH3]    # 已被 USART2_TX 占用
  PA3: [TIM2_CH4]    # 已被 USART2_RX 占用
  PA6: [TIM3_CH1]
  PA7: [TIM3_CH2]
  PA8: [TIM1_CH1]
  PA9: [TIM1_CH2]
  PA10: [TIM1_CH3]
  PA11: [TIM1_CH4]
  PB0: [TIM3_CH3]
  PB1: [TIM3_CH4]
  PB6: [TIM4_CH1]
  PB7: [TIM4_CH2]
  PB8: [TIM4_CH3]
  PB9: [TIM4_CH4]

# 常用预配置组合（给定频率，给出推荐配置）
preset_frequencies:
  - frequency_hz: 1000
    prescaler: 71
    period: 999
    description: "72MHz/72/1000 = 1kHz"
  - frequency_hz: 10000
    prescaler: 71
    period: 99
    description: "72MHz/72/100 = 10kHz"
  - frequency_hz: 100
    prescaler: 719
    period: 999
    description: "72MHz/720/1000 = 100Hz"
```

**A.2.3：** `templates/hardware_knowledge/stm32f1_user_code_regions.yaml`

```yaml
# main.c 里标准的 USER CODE 区域（来自 STM32CubeMX 生成规则）
user_code_regions:
  - name: "USER CODE BEGIN Includes"
    purpose: "添加 #include 语句"
    insert_after_regex: "/\\* USER CODE BEGIN Includes \\*/"
    insert_before_regex: "/\\* USER CODE END Includes \\*/"
  - name: "USER CODE BEGIN PV"
    purpose: "添加全局变量、句柄声明"
    insert_after_regex: "/\\* USER CODE BEGIN PV \\*/"
    insert_before_regex: "/\\* USER CODE END PV \\*/"
  - name: "USER CODE BEGIN PFP"
    purpose: "添加函数原型声明"
    insert_after_regex: "/\\* USER CODE BEGIN PFP \\*/"
    insert_before_regex: "/\\* USER CODE END PFP \\*/"
  - name: "USER CODE BEGIN 2"
    purpose: "main() 里在 HAL_Init 和 while(1) 之间，添加初始化调用"
    insert_after_regex: "/\\* USER CODE BEGIN 2 \\*/"
    insert_before_regex: "/\\* USER CODE END 2 \\*/"
  - name: "USER CODE BEGIN WHILE"
    purpose: "主循环开始"
    insert_after_regex: "/\\* USER CODE BEGIN WHILE \\*/"
    insert_before_regex: "/\\* USER CODE END WHILE \\*/"
  - name: "USER CODE BEGIN 3"
    purpose: "主循环内部"
    insert_after_regex: "/\\* USER CODE BEGIN 3 \\*/"
    insert_before_regex: "/\\* USER CODE END 3 \\*/"
  - name: "USER CODE BEGIN 4"
    purpose: "文件末尾，添加函数定义"
    insert_after_regex: "/\\* USER CODE BEGIN 4 \\*/"
    insert_before_regex: "/\\* USER CODE END 4 \\*/"
```

#### A.3 新增硬件知识库查询器

**位置：** `agent_workbench/core/hardware_knowledge.py`（新建）

```python
import math
from pathlib import Path
import yaml

class HardwareKnowledge:
    """静态硬件知识库查询器（纯计算，无 LLM）"""

    def __init__(self, knowledge_dir: Path):
        self.clock = self._load(knowledge_dir / "stm32f1_clock.yaml")
        self.pin_map = self._load(knowledge_dir / "stm32f1_timer_pin_map.yaml")
        self.regions = self._load(knowledge_dir / "stm32f1_user_code_regions.yaml")

    def _load(self, path: Path) -> dict:
        if path.exists():
            return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return {}

    def find_timer_for_pin(self, pin: str) -> list[str]:
        """查 PA8 对应哪些定时器通道"""
        return self.pin_map.get("pin_to_timer_channels", {}).get(pin.upper(), [])

    def compute_timer_params(self, frequency_hz: int, system_clock_hz: int = None) -> dict:
        """
        给定频率，计算 Prescaler 和 Period。
        算法：优先查预置表，未命中时用确定性公式计算。
        """
        sys_clock = system_clock_hz or self.clock.get("system_clock_hz", 72000000)

        # 先查预置表
        for preset in self.clock.get("preset_frequencies", []):
            if preset["frequency_hz"] == frequency_hz:
                return {
                    "prescaler": preset["prescaler"],
                    "period": preset["period"],
                    "description": preset["description"],
                    "source": "preset_table"
                }

        # 未命中预置表，用确定性算法
        # 策略：先让 TimerClock 变为 1MHz（Prescaler=71），再用 Period 控制频率
        if frequency_hz <= 1_000_000:
            prescaler = 71  # 72MHz / 72 = 1MHz
            period = (sys_clock // (prescaler + 1)) // frequency_hz - 1
        else:
            prescaler = 0
            period = sys_clock // frequency_hz - 1

        return {
            "prescaler": prescaler,
            "period": period,
            "description": f"{sys_clock}/{prescaler+1}/{period+1} = {frequency_hz}Hz",
            "source": "computed"
        }

    def compute_duty_ccr(self, period: int, duty_percent: int) -> int:
        """给定周期和占空比，计算 CCR 值"""
        return int((period + 1) * duty_percent / 100)

    def get_user_code_region(self, region_name: str) -> dict:
        """查某个 USER CODE 区域的正则"""
        for region in self.regions.get("user_code_regions", []):
            if region_name in region["name"]:
                return region
        return {}
```

#### A.4 改造 Planner 消费参数提取和硬件知识库

**不新增 LLM**，只在现有 `core/planner.py` 里加入确定性逻辑：

```python
from .param_extractor import extract_parameters
from .hardware_knowledge import HardwareKnowledge

class Planner:
    def __init__(self, cfg):
        self.cfg = cfg
        self.templates_dir = Path(cfg["planner"]["templates_dir_path"])
        # 【新增】加载硬件知识库
        self.hw = HardwareKnowledge(
            Path(cfg["planner"]["hardware_knowledge_dir_path"])
        )

    def plan(self, user_request: str) -> dict:
        snapshot = scan_project(self.cfg)
        
        # 【新增步骤 A】参数提取（纯 regex）
        params = extract_parameters(user_request)
        
        # 【新增步骤 B】基于硬件知识库补齐上下文
        hardware_context = self._build_hardware_context(params)
        
        # 原有模板匹配
        template, matched = self._match_template(user_request)
        if template is None:
            template = self._fallback_template(user_request)

        # 【修改】把提取的参数 + 硬件上下文喂给模板渲染
        values = {
            "user_request": user_request,
            "project_name": self.cfg["project"]["name"],
            "ready_banner": self.cfg["uart"].get("ready_banner", ""),
            "prompt": self.cfg["uart"].get("prompt", ""),
            # 【新增】
            "extracted_frequency_hz": params.frequency_hz,
            "extracted_pin": params.pin,
            "extracted_timer": params.timer,
            "extracted_cli_command": params.cli_command_name,
            "extracted_duty_percent": params.duty_percent,
        }
        payload = _render_value(template.payload, values)

        # 【新增步骤 C】基于 snapshot 动态调整（纯确定性）
        payload = self._adjust_by_snapshot(payload, snapshot, params)

        # 原有组装 JSON，但加入新字段
        result = {
            # ... 原有字段
            
            # 【新增】参数提取结果（让 Continue 知道我们读懂了什么）
            "parameter_extractions": asdict(params),
            
            # 【新增】硬件上下文（给 Continue 生成代码用的权威信息）
            "hardware_context": hardware_context,
            
            # ... 其它原有字段
        }
        return result

    def _build_hardware_context(self, params) -> dict:
        """基于提取的参数，查硬件知识库补齐上下文"""
        ctx = {"mcu": "stm32f1", "system_clock_hz": 72_000_000}
        
        # 如果提取到频率，计算 Prescaler/Period
        if params.frequency_hz:
            timer_params = self.hw.compute_timer_params(params.frequency_hz)
            ctx["timer_config"] = {
                "frequency_hz": params.frequency_hz,
                "prescaler": timer_params["prescaler"],
                "period": timer_params["period"],
                "description": timer_params["description"]
            }
            # 计算占空比对应的 CCR
            if params.duty_percent:
                ctx["timer_config"]["ccr"] = self.hw.compute_duty_ccr(
                    timer_params["period"], params.duty_percent
                )
            else:
                ctx["timer_config"]["ccr"] = self.hw.compute_duty_ccr(
                    timer_params["period"], 50  # 默认 50%
                )
        
        # 如果提取到引脚，查映射
        if params.pin:
            available_timers = self.hw.find_timer_for_pin(params.pin)
            ctx["pin_mapping"] = {
                "pin": params.pin,
                "gpio_port": params.gpio_port,
                "available_timer_channels": available_timers,
                "recommended": available_timers[0] if available_timers else None
            }
        
        # 添加 USER CODE 区域速查
        ctx["user_code_regions"] = self.hw.regions.get("user_code_regions", [])
        
        return ctx

    def _adjust_by_snapshot(self, payload, snapshot, params) -> dict:
        """基于 scan_project 的结果动态调整（纯确定性）"""
        existing_inits = snapshot.get("detected_init_functions", [])
        existing_cmds = snapshot.get("uart", {}).get("help_commands", [])
        
        # 如果要加 TIM1，但 TIM1 已存在，加个 note
        if params.timer:
            timer_num = params.timer.replace("TIM", "")
            if timer_num in existing_inits:
                payload["notes"] = payload.get("notes", [])
                payload["notes"].append(
                    f"⚠️ {params.timer} 已存在 MX_{params.timer}_Init，建议修改现有初始化而不是新建"
                )
        
        # 如果要加 CLI 命令，但命令已存在
        if params.cli_command_name and params.cli_command_name in existing_cmds:
            payload["notes"] = payload.get("notes", [])
            payload["notes"].append(
                f"⚠️ CLI 命令 '{params.cli_command_name}' 已存在，建议修改或升级而不是重复添加"
            )
        
        return payload
```

#### A.5 改造任务模板为"结构化代码提示"格式

**保持 YAML 格式，但 instructions 字段改为结构化数组：**

```yaml
# templates/task_templates/timer_pwm.yaml（改造后）
id: timer_pwm
mode: feature
description: 为 PWM、蜂鸣器、占空比和频率控制类需求生成执行计划。
keywords:
  - pwm
  - 蜂鸣器
  - buzzer
  - 频率
  - 方波
  - 占空比

read_files:
  - file: Core/Src/main.c
    why: 查看现有 USER CODE 区域和初始化顺序
  - file: Core/Inc/main.h
    why: 查看现有句柄声明和 include

edit_files:
  - file: Core/Src/main.c
    # 【新】结构化的 code_change_hints 数组
    # Continue 的 LLM 拿到这个 + hardware_context 就能生成完整代码
    code_change_hints:
      - type: add_declaration
        region: "USER CODE BEGIN PV"
        code_template: "TIM_HandleTypeDef htim{timer_num};"
        parameter_binding:
          timer_num: "from hardware_context.pin_mapping.recommended (取 TIM1_CH1 的 1)"
        why: 新定时器需要全局句柄
      
      - type: add_function
        region: "USER CODE BEGIN 4"
        code_template: |
          void MX_TIM{timer_num}_PWM_Init(void) {
            TIM_OC_InitTypeDef sConfigOC = {0};
            htim{timer_num}.Instance = {timer_instance};
            htim{timer_num}.Init.Prescaler = {prescaler};
            htim{timer_num}.Init.Period = {period};
            htim{timer_num}.Init.CounterMode = TIM_COUNTERMODE_UP;
            HAL_TIM_PWM_Init(&htim{timer_num});
            
            sConfigOC.OCMode = TIM_OCMODE_PWM1;
            sConfigOC.Pulse = {ccr};
            sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;
            HAL_TIM_PWM_ConfigChannel(&htim{timer_num}, &sConfigOC, TIM_CHANNEL_{channel});
            HAL_TIM_PWM_Start(&htim{timer_num}, TIM_CHANNEL_{channel});
          }
        parameter_binding:
          timer_num: "from hardware_context.pin_mapping.recommended"
          timer_instance: "from hardware_context.pin_mapping.recommended (TIM1)"
          channel: "from hardware_context.pin_mapping.recommended (_CH1 的 1)"
          prescaler: "from hardware_context.timer_config.prescaler"
          period: "from hardware_context.timer_config.period"
          ccr: "from hardware_context.timer_config.ccr"
        why: PWM 初始化函数
      
      - type: add_call
        region: "USER CODE BEGIN 2"
        code_template: "MX_TIM{timer_num}_PWM_Init();"
        parameter_binding:
          timer_num: "from hardware_context.pin_mapping.recommended"
        why: 在 main 里调用初始化
      
      - type: gpio_alternate_function_config
        code_template: |
          /* 在 MX_GPIO_Init() 或新增的 GPIO 配置中，配置 {pin} 为复用推挽 */
          GPIO_InitTypeDef GPIO_InitStruct = {0};
          __HAL_RCC_{gpio_port}_CLK_ENABLE();
          __HAL_RCC_{timer_instance}_CLK_ENABLE();
          GPIO_InitStruct.Pin = GPIO_PIN_{pin_num};
          GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
          GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
          HAL_GPIO_Init({gpio_port}, &GPIO_InitStruct);
        parameter_binding:
          pin: "from hardware_context.pin_mapping.pin"
          gpio_port: "from hardware_context.pin_mapping.gpio_port"
          pin_num: "from hardware_context.pin_mapping.pin (去掉 P<Letter>)"
          timer_instance: "from hardware_context.pin_mapping.recommended (TIM1)"

shell_steps:
  - name: 编译验证
    command: ./agent_workbench.bat build --json
    success_criteria: exit_code == 0
    on_failure:
      max_retries: 3
      retry_command: ./agent_workbench.bat parse-errors --json
      retry_strategy: >
        对每个 errors[i]，查看 suggested_fix 的 recommended_action 和 code_template，
        按 parameter_hints 替换后生成具体代码，用 edit_file 修复，然后重试 build。

  - name: 烧录到硬件
    command: ./agent_workbench.bat flash --json
    success_criteria: exit_code == 0
    requires_confirmation: true

  - name: UART CLI 回归验证
    command: ./agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --json
    success_criteria: transcript 包含 ready banner 和 cli> prompt

stable_strings:
  - "{ready_banner}"
  - "{prompt}"

forbidden_operations:
  - 删除已有 CLI 命令
  - 修改 ready banner 或 prompt 字符串
  - 改动 Drivers 目录
```

**关键设计：**
- Continue 的 LLM 拿到 `code_template` + `parameter_binding` + `hardware_context`，自己完成"变量替换生成代码"
- agent_workbench 只负责**提供原料**，不生成代码
- 不违反"不接 LLM"的约束

#### A.6 Plan 最终输出样例（改造后）

```json
{
  "plan_id": "plan_20260419_103000",
  "user_request": "给STM32添加PWM蜂鸣器控制，频率1kHz，PA8引脚",
  "template_id": "timer_pwm",
  
  "parameter_extractions": {
    "frequency_hz": 1000,
    "pin": "PA8",
    "gpio_port": "GPIOA",
    "timer": null,
    "cli_command_name": null,
    "duty_percent": null
  },
  
  "hardware_context": {
    "mcu": "stm32f1",
    "system_clock_hz": 72000000,
    "timer_config": {
      "frequency_hz": 1000,
      "prescaler": 71,
      "period": 999,
      "ccr": 500,
      "description": "72MHz/72/1000 = 1kHz"
    },
    "pin_mapping": {
      "pin": "PA8",
      "gpio_port": "GPIOA",
      "available_timer_channels": ["TIM1_CH1"],
      "recommended": "TIM1_CH1"
    },
    "user_code_regions": [ ... ]
  },
  
  "steps": [
    {
      "id": 1,
      "action_type": "read_file",
      "file": "Core/Src/main.c"
    },
    {
      "id": 3,
      "action_type": "edit_file",
      "file": "Core/Src/main.c",
      "code_change_hints": [
        {
          "type": "add_declaration",
          "region": "USER CODE BEGIN PV",
          "code_template": "TIM_HandleTypeDef htim{timer_num};",
          "parameter_binding": {
            "timer_num": "1 (from hardware_context.pin_mapping.recommended TIM1_CH1)"
          }
        },
        ...
      ]
    }
  ],
  
  "notes": [],
  
  "constraints": {
    "allowed_edit_files": ["Core/Src/main.c", "Core/Inc/main.h"],
    "forbidden_operations": [...]
  }
}
```

**Continue 的 LLM 拿到这个 JSON，完全有能力自己生成正确代码：**
- 知道频率 1000 → prescaler=71, period=999（已经算好了）
- 知道 PA8 → TIM1_CH1（已经查好了）
- 知道具体代码模板（已经给好了）
- 只需要做"变量替换 + 微调"

---

### 改进模块 B：静态错误修复规则库扩充（纯规则，不接 LLM） 🔴

**位置：** `agent_workbench/templates/build_error_rules.json`（扩充现有文件）

**目标：** 把静态规则库从"通用建议"升级为"结构化修复方案"。

#### B.1 扩充错误规则结构

当前规则：
```json
{
  "pattern": "undeclared",
  "category": "syntax",
  "suggested_fix": "查看日志上下文并从第一条 error 开始修复"
}
```

**改造为：**
```json
{
  "pattern": "'(\\w+)' undeclared",
  "capture_groups": ["symbol"],
  "category": "syntax",
  "error_code": "undeclared_identifier",
  "recommended_action": "add_declaration",
  "fix_template": {
    "action_type": "add_declaration",
    "target_files": ["Core/Inc/main.h", "Core/Src/main.c"],
    "target_region": "USER CODE BEGIN PV",
    "code_template_by_symbol_pattern": {
      "^htim\\d+$": "extern TIM_HandleTypeDef {symbol};",
      "^huart\\d+$": "extern UART_HandleTypeDef {symbol};",
      "^hspi\\d+$": "extern SPI_HandleTypeDef {symbol};",
      "^hi2c\\d+$": "extern I2C_HandleTypeDef {symbol};",
      "^hadc\\d*$": "extern ADC_HandleTypeDef {symbol};",
      "default": "/* TODO: declare {symbol} */"
    }
  },
  "reasoning": "符号未声明，通常需要在全局区加 extern 声明"
}
```

**改造后，parse-errors 的 JSON 输出：**

```json
{
  "errors": [{
    "file": "Core/Src/main.c",
    "line": 123,
    "message": "'htim1' undeclared",
    "captured": {"symbol": "htim1"},
    "suggested_fix": {
      "action_type": "add_declaration",
      "target_files": ["Core/Inc/main.h"],
      "target_region": "USER CODE BEGIN PV",
      "code": "extern TIM_HandleTypeDef htim1;",
      "reasoning": "htim1 匹配 TIM 句柄命名模式，应以 extern 形式声明"
    }
  }]
}
```

**关键：全部来自静态规则库的 regex 匹配 + 模板替换，不调用 LLM。**

#### B.2 扩充规则覆盖面

至少覆盖以下 15 种常见错误：

| 错误类型 | regex pattern | fix_action |
|---------|--------------|-----------|
| 未声明的定时器句柄 | `'htim(\d+)' undeclared` | 加 `extern TIM_HandleTypeDef htim{N};` |
| 未声明的串口句柄 | `'huart(\d+)' undeclared` | 加 `extern UART_HandleTypeDef huart{N};` |
| 缺失头文件 include | `fatal error: (\w+\.h): No such file` | 加 `#include "{header}"` |
| 未定义函数 | `undefined reference to `(\w+)'` | 提示检查是否漏包含源文件 |
| 函数声明缺失 | `implicit declaration of function '(\w+)'` | 加函数原型声明 |
| 类型不匹配 | `incompatible types .* assignment` | 提示检查强转 |
| 变量未初始化 | `may be used uninitialized` | 加默认初始化 = 0 |
| 多余分号 | `expected .* before ';' token` | 提示检查前一行 |
| 括号不匹配 | `expected .* before .*} token` | 提示检查括号 |
| 指针强转警告 | `cast from .* pointer` | 加显式 (void\*) 强转 |
| 未使用参数 | `unused parameter` | 加 `(void)arg_name;` |
| 符号冲突 | `redefinition of` | 提示函数名重复 |
| 超出范围 | `overflow in implicit conversion` | 提示类型范围 |
| 链接错误 | `section .*\.text.*overflowed` | 提示 Flash 不足 |
| main.h 缺失 define | `'([A-Z_][A-Z0-9_]+)' undeclared` | 提示在 main.h 加 #define |

#### B.3 新增 `fix-build` 命令（纯规则封装）

```python
def _cmd_fix_build(args):
    """
    基于静态规则库，把最新 build.log 的错误转成可执行的修复提示。
    注意：本命令不调用任何 LLM，全部基于 regex + 规则库。
    """
    from core.build_errors import parse_build_log_structured
    
    errors = parse_build_log_structured(log_path)
    
    fix_plan = {
        "command": "fix-build",
        "error_count": len(errors),
        "suggested_fixes": [
            {
                "step_id": i+1,
                "error": {
                    "file": e.file,
                    "line": e.line,
                    "message": e.message
                },
                "fix": e.suggested_fix  # 结构化 fix_action
            }
            for i, e in enumerate(errors)
        ]
    }
    return fix_plan
```

---

### 改进模块 C：Rules 文件大幅扩充（教 Continue 消费结构化 plan） 🔴

**核心：** 把 rules 写成"Continue 的 LLM 拿到 plan JSON 后，怎么一步步展开代码"的完整操作手册。

#### C.1 主规则文件重写（目标 300+ 行）

**位置：** `.continue/rules/stm32_auto_workflow.md`

**新增关键章节：**

```markdown
# STM32 Agent Workbench 自主执行规则（完整版）

## 你的身份和职责

你是 STM32 开发助手，在 Continue 的 Agent 模式下工作。
用户只会给你一句自然语言需求。你必须：
1. 调用 agent_workbench.bat 生成结构化 plan
2. 基于 plan 的 hardware_context 和 code_change_hints 生成具体代码
3. 按 steps 顺序执行，调用对应工具
4. 最后输出完整报告

## 核心原则（必须遵守）

1. **不要臆测硬件参数**。所有定时器参数、引脚映射都以 `plan.hardware_context` 为准
2. **不要跳过 plan**，每次都先运行 plan 生成结构化执行脚本
3. **命令必须用 cmd /c 包装**，路径用正斜杠
4. **一次只运行一条命令**，禁止用 `;` 或 `&&` 串联

## 执行流程

### 第 1 步：生成 plan

运行：
    cmd /c ".\agent_workbench.bat plan ""<用户原话>"" --json"

返回的 JSON 包含关键字段：
- `parameter_extractions`: 我们从用户需求里提取出来的结构化参数
- `hardware_context`: 硬件知识库给出的权威参数（定时器计算结果、引脚映射）
- `steps`: 需要按序执行的步骤数组
- `notes`: 项目当前状态的提醒（如"TIM1 已存在"）
- `constraints`: 必须遵守的约束（允许改哪些文件等）

### 第 2 步：检查 plan 是否需要人工确认

- 如果 `notes` 里有 "⚠️" 开头的提醒（如"TIM1 已存在"），先向用户汇报再继续
- 如果 `parameter_extractions` 里关键参数为 null（比如用户要 PWM 但没说引脚），向用户追问

### 第 3 步：按 steps 数组执行

对每个 step：

#### 如果 action_type == "read_file"
1. 用 read_file 工具读取 step.file
2. 回复一行："✅ Step N: 已读取 <file>，共 X 行"

#### 如果 action_type == "edit_file"
这是最关键的一步，你要做结构化代码生成：

1. 先确认 step.file 在 constraints.allowed_edit_files 里
2. 对 step.code_change_hints 数组里的每一项：
   a. 读 type 字段，决定操作类型
      - `add_declaration`: 在 region 之后插入
      - `add_function`: 在 region 之后插入完整函数
      - `add_call`: 在 region 之后插入函数调用
      - `add_include`: 在已有 include 之后插入
      - `gpio_alternate_function_config`: 补充 GPIO 配置
   b. 读 code_template 字段，里面有 `{占位符}`
   c. 读 parameter_binding 字段，按绑定规则解析占位符
      - 例如 `timer_num: "from hardware_context.pin_mapping.recommended TIM1_CH1"` 
        说明从 hardware_context 里取 TIM1_CH1，提取出数字 1
      - 例如 `prescaler: "from hardware_context.timer_config.prescaler"` 
        直接从 hardware_context.timer_config.prescaler 取值
   d. 把占位符替换成实际值，得到具体代码
3. 用 edit_file 工具把生成的代码插入到 step.file 的正确 region

#### 如果 action_type == "shell"
1. 运行 step.command（在 PowerShell 用 `cmd /c` 包装）
2. 解析返回 JSON 的 exit_code 和 status
3. 如果成功：继续下一步
4. 如果失败，且 step 有 on_failure.retry_command：
   a. 运行 retry_command 拿到 suggested_fixes
   b. 对每个 suggested_fixes[i]，用 edit_file 执行 fix.code
   c. 重新运行 step.command
   d. 达到 max_retries 后停止
5. 如果 requires_confirmation: 先让用户确认

## 关键技术细节

### 如何从 hardware_context 正确提取参数

假设 plan 有：
    "hardware_context": {
        "timer_config": {
            "prescaler": 71,
            "period": 999,
            "ccr": 500
        },
        "pin_mapping": {
            "pin": "PA8",
            "gpio_port": "GPIOA",
            "recommended": "TIM1_CH1"
        }
    }

当 code_template 是 `htim{timer_num}`，parameter_binding 是 `timer_num: "from hardware_context.pin_mapping.recommended TIM1_CH1"`：
1. 从 hardware_context.pin_mapping.recommended 取 "TIM1_CH1"
2. 从 "TIM1_CH1" 提取定时器号: "1"
3. 最终代码: `htim1`

当 code_template 是 `.Init.Prescaler = {prescaler}`：
1. 从 hardware_context.timer_config.prescaler 取 71
2. 最终代码: `.Init.Prescaler = 71`

### 如何处理 parse-errors 返回的 suggested_fix

假设收到：
    {
      "errors": [{
        "file": "Core/Src/main.c",
        "line": 123,
        "suggested_fix": {
          "action_type": "add_declaration",
          "target_files": ["Core/Inc/main.h"],
          "target_region": "USER CODE BEGIN PV",
          "code": "extern TIM_HandleTypeDef htim1;",
          "reasoning": "htim1 匹配 TIM 句柄命名模式"
        }
      }]
    }

你应该：
1. 读 target_files[0] = "Core/Inc/main.h"
2. 找到 USER CODE BEGIN PV 区域
3. 在这个区域插入 `extern TIM_HandleTypeDef htim1;`
4. 然后重新 build

## 禁止行为（列举 10 条）

1. ❌ 不要跳过 plan 直接改代码
2. ❌ 不要编造硬件参数（Prescaler、Period 都从 hardware_context 取）
3. ❌ 不要编造引脚复用（从 hardware_context.pin_mapping 取）
4. ❌ 不要在没看到 build exit_code=0 前声称完成
5. ❌ 不要超出 allowed_edit_files 范围
6. ❌ 不要删除 ready banner 或 cli> prompt
7. ❌ 不要用 `cd xxx; command` 串联命令
8. ❌ 不要把多条 shell 命令用 `;` 或 `&&` 拼起来
9. ❌ 不要在 JSON 解析失败时 continue 执行
10. ❌ 不要连续失败 3 次后还继续

## 最终报告模板（必须输出）

    ## 任务完成报告
    - 用户需求: <原始需求>
    - 理解参数: <parameter_extractions 摘要>
    - 硬件方案: <hardware_context 关键决策>
    - 修改的文件: <修改列表及变更行数>
    - 编译结果: <pass/fail + 最终 exit_code>
    - 烧录结果: <pass/fail/skipped>
    - CLI 验证结果: <pass/fail，引用 transcript 关键行>
    - 证据文件:
      - plan JSON: <保存到 runtime 的路径>
      - build log: agent_workbench/runtime/build.log
      - cli transcript: agent_workbench/runtime/cli_transcript.log
    - 备注: <遇到的问题和解决过程>
```

#### C.2 弱模型规则扩充（目标 150+ 行）

**位置：** `.continue/rules/stm32_weak_model_guard.md`

**新增内容：**

```markdown
# 弱模型安全约束（完整版）

## 针对 DeepSeek-R1 / 本地 Qwen / 小上下文模型

### 防止 PowerShell 语法错误（20 条反例）

#### 反例 1：混用路径分隔符
❌ `cmd /c ".\agent_workbench.bat build"` 里的 `.\` 可能在某些终端失败
✅ 始终用 `cmd /c ".\agent_workbench.bat build --json"`（最稳写法）

#### 反例 2：中文参数引号问题
❌ `cmd /c ".\agent_workbench.bat plan "给STM32加PWM" --json"` (双引号嵌套错误)
✅ `cmd /c ".\agent_workbench.bat plan ""给STM32加PWM"" --json"` (cmd 里用双引号转义)

#### 反例 3：忘记 --json
❌ `cmd /c ".\agent_workbench.bat build"` (返回人类可读文本，难以解析)
✅ `cmd /c ".\agent_workbench.bat build --json"` (返回结构化 JSON)

... (继续列出共 20 条)

### 防止"伪执行"（严禁编造结果）

规则 1：每次运行命令前，必须先在回复里写：
    下一步执行: cmd /c "..."

规则 2：命令返回后，必须写：
    返回: {"exit_code": 0, ...}

规则 3：严禁下面这些"偷懒话术"：
- "根据经验，应该..."（没有运行命令就不要推论）
- "通常来说..."（不要用通用知识代替具体验证）
- "我相信..."（工程上只信工具返回值）

### 防止代码幻觉（硬件参数必须来自 plan.hardware_context）

规则 1：看到"1kHz" 不要自己心算，必须从 hardware_context.timer_config.prescaler 取 71
规则 2：看到"PA8" 不要自己猜 TIM1_CH1，必须从 hardware_context.pin_mapping.recommended 取
规则 3：看到"50% 占空比" 不要自己算 500，必须从 hardware_context.timer_config.ccr 取

### 防止死循环和死锁

规则 1：同一步骤连续失败 3 次必须停止
规则 2：总步骤数超过 plan.constraints.max_total_steps 必须停止
规则 3：build 失败后，最多运行 3 次 parse-errors + edit_file + build 循环
规则 4：遇到无法理解的错误，直接向用户汇报
```

#### C.3 新增任务速查手册

**位置：** `.continue/rules/stm32_task_cookbook.md`（新建）

为 5 类常见需求分别给出"从自然语言到最终验证"的完整示例：

```markdown
# STM32 任务速查手册

本文档给出 5 类常见任务的完整 Continue Agent 对话示例。
每个示例都按照主规则的流程执行，展示"plan → 展开代码 → 构建 → 验证"全流程。

## 任务类型 1：PWM 输出

### 示例输入
用户: "给STM32加PWM蜂鸣器控制，频率1kHz，PA8引脚，占空比50%"

### 完整执行流程（示范）

步骤 1 - 生成 plan:
    下一步执行: cmd /c ".\agent_workbench.bat plan ""给STM32加PWM蜂鸣器控制，频率1kHz，PA8引脚，占空比50%"" --json"
    返回: {
      "parameter_extractions": {"frequency_hz": 1000, "pin": "PA8", "duty_percent": 50},
      "hardware_context": {
        "timer_config": {"prescaler": 71, "period": 999, "ccr": 500},
        "pin_mapping": {"recommended": "TIM1_CH1"}
      },
      ...
    }

步骤 2 - 读取文件:
    调用 read_file: Core/Src/main.c
    调用 read_file: Core/Inc/main.h

步骤 3 - 基于 code_change_hints 生成代码:
    (基于 hardware_context 和 code_template 生成具体代码，然后 edit_file)
    
    在 main.c 的 USER CODE BEGIN PV 后添加:
        TIM_HandleTypeDef htim1;
    
    在 main.c 的 USER CODE BEGIN 4 后添加:
        void MX_TIM1_PWM_Init(void) {
            TIM_OC_InitTypeDef sConfigOC = {0};
            htim1.Instance = TIM1;
            htim1.Init.Prescaler = 71;       // 从 hardware_context
            htim1.Init.Period = 999;         // 从 hardware_context
            htim1.Init.CounterMode = TIM_COUNTERMODE_UP;
            HAL_TIM_PWM_Init(&htim1);
            
            sConfigOC.OCMode = TIM_OCMODE_PWM1;
            sConfigOC.Pulse = 500;           // 从 hardware_context.ccr
            sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;
            HAL_TIM_PWM_ConfigChannel(&htim1, &sConfigOC, TIM_CHANNEL_1);
            HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);
        }
    
    在 main.c 的 USER CODE BEGIN 2 后添加:
        MX_TIM1_PWM_Init();
    
    在 MX_GPIO_Init 的合适位置添加 PA8 AF_PP 配置

步骤 4 - 编译验证:
    下一步执行: cmd /c ".\agent_workbench.bat build --json"
    返回: {"exit_code": 0}
    ✅ 编译成功

步骤 5 - 烧录 (需要用户确认):
    ⚠️ 即将烧录到硬件，继续吗？
    [用户确认]
    下一步执行: cmd /c ".\agent_workbench.bat flash --json"
    返回: {"exit_code": 0}

步骤 6 - UART 验证:
    下一步执行: cmd /c ".\agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --json"
    返回: {"exit_code": 0, "transcript": "...STM32 UART CLI ready...cli>..."}

步骤 7 - 最终报告:
    ## 任务完成报告
    - 用户需求: 给STM32加PWM蜂鸣器控制，频率1kHz，PA8引脚，占空比50%
    - 理解参数: frequency=1000Hz, pin=PA8, duty=50%
    - 硬件方案: TIM1_CH1, Prescaler=71, Period=999, CCR=500
    - 修改的文件: Core/Src/main.c (+38 行), Core/Inc/main.h (+1 行)
    - 编译结果: pass
    - 烧录结果: pass
    - CLI 验证结果: pass (ready banner + cli> prompt 均出现)
    ...

## 任务类型 2：GPIO 闪烁
...（类似完整示例）

## 任务类型 3：添加 CLI 命令
...

## 任务类型 4：ADC 采样
...

## 任务类型 5：定时中断
...
```

---

### 改进模块 D：Plan 动态化（消费 snapshot，纯确定性） 🟠

**位置：** `core/planner.py` 和 `core/project_scanner.py`

**目标：** 基于 `scan_project` 结果做确定性决策，不引入 LLM。

#### D.1 `project_scanner.py` 扩展

新增扫描能力（纯 regex 和文件解析）：

```python
def scan_existing_cli_commands(cfg) -> list[dict]:
    """
    解析 app_cli_commands.c，提取已有命令的函数名、help 文本。
    纯 regex，不调用 LLM。
    """
    pattern = re.compile(
        r'/\*\s*(\w+)_help\s*\*/\s*"([^"]+)"',  # 根据实际格式调整
        re.MULTILINE
    )
    ...

def scan_user_code_regions(main_c_path: Path) -> dict:
    """
    扫描 main.c，找出每个 USER CODE BEGIN/END 的行号。
    """
    regions = {}
    for i, line in enumerate(lines):
        if m := re.search(r"USER CODE BEGIN (\w+)", line):
            regions[m.group(1)] = {"begin_line": i + 1}
        if m := re.search(r"USER CODE END (\w+)", line):
            regions[m.group(1)]["end_line"] = i + 1
    return regions

def scan_existing_handles(main_c_path: Path, main_h_path: Path) -> list[dict]:
    """
    扫描所有 TIM_HandleTypeDef / UART_HandleTypeDef 等声明。
    """
    pattern = re.compile(r"(TIM|UART|SPI|I2C|ADC)_HandleTypeDef\s+(\w+);")
    ...
```

#### D.2 Planner 使用这些信息做决策

```python
def _adjust_by_snapshot(self, payload, snapshot, params) -> dict:
    existing_handles = snapshot.get("existing_handles", [])
    existing_cmds = snapshot.get("uart", {}).get("help_commands", [])
    
    # 决策 1：如果要新建 TIM1，但已存在 htim1，调整为"复用"
    if params.timer:
        handle_name = f"htim{params.timer.replace('TIM', '')}"
        if any(h["name"] == handle_name for h in existing_handles):
            payload["notes"] = payload.get("notes", [])
            payload["notes"].append(
                f"⚠️ {handle_name} 已存在，应修改现有初始化代码而不是新建"
            )
            # 可以进一步调整 code_change_hints
            for hint in payload.get("code_change_hints", []):
                if hint["type"] == "add_declaration" and "htim" in hint["code_template"]:
                    hint["type"] = "skip"  # 跳过已存在的声明
    
    # 决策 2：如果要加 CLI 命令但已存在
    if params.cli_command_name and params.cli_command_name in existing_cmds:
        payload["notes"] = payload.get("notes", [])
        payload["notes"].append(
            f"⚠️ CLI 命令 '{params.cli_command_name}' 已存在，建议修改或升级"
        )
    
    return payload
```

---

### 改进模块 E：端到端回归测试（离线，不调 LLM） 🟠

**关键：** 测试不调用真实 LLM，只验证 plan 输出的结构完整性和参数提取正确性。

#### E.1 新增测试

**位置：** `agent_workbench/tests/test_planner_e2e.py`（新建）

```python
class PlannerE2ETests(unittest.TestCase):
    """验证 plan 输出对 Continue 来说信息量充足（离线）"""
    
    def test_pwm_request_extracts_all_parameters(self):
        """PWM 场景：所有关键参数都必须被提取"""
        plan = Planner(cfg).plan("给STM32添加PWM蜂鸣器，1kHz，PA8，50%占空比")
        
        extracts = plan["parameter_extractions"]
        self.assertEqual(extracts["frequency_hz"], 1000)
        self.assertEqual(extracts["pin"], "PA8")
        self.assertEqual(extracts["duty_percent"], 50)
    
    def test_pwm_request_hardware_context_has_computed_values(self):
        """PWM 场景：hardware_context 必须包含计算好的 Prescaler/Period/CCR"""
        plan = Planner(cfg).plan("给STM32添加PWM蜂鸣器，1kHz，PA8，50%占空比")
        
        hw = plan["hardware_context"]
        self.assertEqual(hw["timer_config"]["prescaler"], 71)
        self.assertEqual(hw["timer_config"]["period"], 999)
        self.assertEqual(hw["timer_config"]["ccr"], 500)
        self.assertEqual(hw["pin_mapping"]["recommended"], "TIM1_CH1")
    
    def test_pwm_request_steps_have_code_change_hints(self):
        """PWM 场景：edit_file 步骤必须包含 code_change_hints 数组"""
        plan = Planner(cfg).plan("给STM32添加PWM蜂鸣器，1kHz，PA8")
        
        edit_steps = [s for s in plan["steps"] if s["action_type"] == "edit_file"]
        self.assertGreater(len(edit_steps), 0)
        
        for step in edit_steps:
            self.assertIn("code_change_hints", step)
            self.assertIsInstance(step["code_change_hints"], list)
            self.assertGreater(len(step["code_change_hints"]), 0)
    
    def test_cli_command_request_extracts_command_name(self):
        """CLI 命令场景：必须提取出命令名"""
        plan = Planner(cfg).plan("添加一个CLI命令uptime显示运行时间")
        
        self.assertEqual(plan["parameter_extractions"]["cli_command_name"], "uptime")
    
    def test_existing_timer_triggers_warning_note(self):
        """如果 TIM1 已存在，plan 里必须有警告 note"""
        # Mock snapshot 让 TIM1 已经存在
        ...
        plan = Planner(cfg).plan("加 TIM1 1kHz PWM")
        
        warning_notes = [n for n in plan.get("notes", []) if "⚠️" in n]
        self.assertTrue(any("TIM1 已存在" in n for n in warning_notes))
```

#### E.2 测试覆盖矩阵

至少覆盖 10 类需求：

| 需求类型 | 必须提取的参数 | 必须输出的 hardware_context |
|---------|--------------|--------------------------|
| PWM 蜂鸣器 | frequency, pin, duty | timer_config, pin_mapping |
| LED 闪烁 | period, pin | pin_mapping |
| 添加 CLI 命令 | cli_command_name | - |
| ADC 采样 | pin (ADC 通道) | adc_channel_mapping |
| 定时中断 | period | timer_config |
| UART 回显 | baud_rate | - |
| I2C 读写 | i2c_port, address | - |
| SPI 读写 | spi_port, speed | - |
| GPIO 输入 | pin | pin_mapping |
| 外部中断 | pin (EXTI line) | exti_mapping |

---

### 改进模块 F：修复 stable_strings 渲染 bug 🟡

**位置：** `core/planner.py`

**修复方式：**

```python
def _render_value(value, values):
    if isinstance(value, str):
        try:
            # 当变量不存在时，保留原字符串而不是 fallback 成空 dict
            rendered = render_template(value, values)
            # 保护性检查：如果结果是 dict 的 str 表示，说明渲染出错了，保留原文
            if rendered.startswith("{'") and rendered.endswith("}"):
                return value
            return rendered
        except KeyError:
            return value
    ...
```

同时清理 `templates/task_templates/uart_cli_command.yaml` 里的错误占位符。

---

### 改进模块 G：Continue Agent 模式使用文档 🟡

**位置：** `agent_workbench/CONTINUE_AGENT_SETUP_ZH.md`（新建）

**内容（只是用户操作手册，不改 Continue 配置）：**

```markdown
# Continue Agent 模式启用指南

本文档告诉你如何在 Continue 里开启 Agent 模式，让它按本项目的 rules 自动工作。

## 前提

- 已经装好 Continue VS Code 插件（最新版）
- 已经运行过 `agent_workbench.bat init-continue-rules`（生成 .continue/rules）
- `.continue/config.yaml` 里有至少一个支持 tool_use 的模型

## 步骤 1：开启 Agent 模式

1. 在 VS Code 打开 Continue 侧边栏
2. 在聊天输入框右侧，点击模式切换按钮
3. 选择 "Agent" 模式（而不是默认的 "Chat" 模式）

## 步骤 2：确认 rules 已加载

在聊天窗口输入：
    列出当前加载的 rules 文件

Continue 应该回复你 .continue/rules/ 下的所有 md 文件列表。
如果它不知道，说明 rules 没加载。

## 步骤 3：测试 Agent 能否自主调用 PowerShell

输入测试需求：
    请运行 scan-project 命令看看当前项目结构

预期行为：
- Continue 应该自动运行 `cmd /c ".\agent_workbench.bat scan-project --json"`
- 返回项目文件清单
- 在聊天窗口汇报

如果它只是说"你应该运行..."但不实际执行，说明 Agent 模式或 tool_use 没正确启用。

## 步骤 4：小需求全流程测试

输入：
    给板子加一个 CLI 命令 'echo hello'

观察 Continue 是否按 rules 执行：
1. 运行 plan 命令
2. 按 steps 顺序执行
3. 遇到编译失败自动 fix-build
4. 最后输出完成报告

## 故障排查

### 问题 1：Continue 不运行 PowerShell 命令
- 检查 Continue 侧边栏是否切换到 Agent 模式
- 检查模型是否支持 tool_use（见 .continue/config.yaml 的 capabilities 字段）

### 问题 2：Continue 编代码不按 hardware_context
- 检查 .continue/rules/ 里文件是否完整
- 检查主规则文件行数是否 >= 300（参考 init-continue-rules 最新输出）

### 问题 3：弱模型（DeepSeek-R1）经常出错
- 确保加载了 stm32_weak_model_guard.md
- 在需求前加 "严格按 rules 执行" 做提示
```

---

## 六、新的实施路线图（v2 修正版）

### 阶段 1：参数提取 + 硬件知识库（2 周）🔴

| 天数 | 任务 | 产出 |
|------|------|------|
| 3 | 参数提取器 | `core/param_extractor.py` + 完整 regex 库 + 单元测试 |
| 3 | 硬件知识库 | `templates/hardware_knowledge/*.yaml` + `core/hardware_knowledge.py` |
| 3 | Planner 集成 extract + hw_ctx | `core/planner.py` 改造 |
| 3 | 改造所有 16 个任务模板 | `templates/task_templates/*.yaml` 改为 code_change_hints 格式 |
| 2 | 端到端测试套件 | `tests/test_planner_e2e.py` |

**阶段 1 验收：** `plan "给STM32加1kHz PWM PA8"` 的 JSON 输出里，`parameter_extractions.frequency_hz == 1000`，`hardware_context.timer_config.prescaler == 71`，`hardware_context.pin_mapping.recommended == "TIM1_CH1"`。

### 阶段 2：编译错误规则库扩充（1 周）🔴

| 天数 | 任务 | 产出 |
|------|------|------|
| 2 | 扩充 build_error_rules.json 到 15 种模式 | `templates/build_error_rules.json` |
| 2 | `BuildError.suggested_fix` 改为结构化 dict | `core/build_errors.py` 改造 |
| 2 | 新增 `fix-build` 命令 | `workbench.py` 增加 subparser + `_cmd_fix_build` |
| 1 | 测试覆盖 15 种错误 | `tests/test_build_errors.py` 扩充 |

**阶段 2 验收：** 故意在 main.c 删掉 htim1 声明，运行 `fix-build --json`，输出里 `suggested_fixes[0].fix.code == "extern TIM_HandleTypeDef htim1;"`。

### 阶段 3：Rules 文件大幅扩充（1 周）🔴

| 天数 | 任务 | 产出 |
|------|------|------|
| 2 | 主规则改写（300+ 行） | `.continue/rules/stm32_auto_workflow.md` + 模板 |
| 1 | 弱模型规则（150+ 行） | `.continue/rules/stm32_weak_model_guard.md` + 模板 |
| 2 | 任务速查手册（5 类任务完整示例） | `.continue/rules/stm32_task_cookbook.md` + 模板 |
| 1 | 改造 `init-continue-rules` 从模板生成 | `core/vscode_service.py` 调整 |
| 1 | 审查所有 rules 文件的一致性 | - |

**阶段 3 验收：** 主规则 wc >= 300，弱模型规则 wc >= 150，cookbook 包含 5 个完整任务示例。

### 阶段 4：Plan 动态化 + bug 修复（1 周）🟠

| 天数 | 任务 | 产出 |
|------|------|------|
| 2 | `project_scanner.py` 增强（扫描 USER CODE 区域、已有句柄、CLI 命令实现） | `core/project_scanner.py` |
| 2 | `Planner._adjust_by_snapshot()` | `core/planner.py` |
| 1 | 修复 stable_strings bug | `core/planner.py`, `templates/` |
| 2 | 文档更新 | `MIGRATION_GUIDE_ZH.md`, `README.md`, `CONTINUE_AGENT_SETUP_ZH.md` |

---

## 七、验收标准

### 7.1 阶段 1 验收（参数提取 + 硬件知识库）

运行命令：
```
cmd /c ".\agent_workbench.bat plan ""给STM32添加PWM蜂鸣器控制，频率1kHz，PA8引脚，占空比50%"" --json"
```

**必须满足的断言：**

1. `plan.parameter_extractions.frequency_hz == 1000`
2. `plan.parameter_extractions.pin == "PA8"`
3. `plan.parameter_extractions.duty_percent == 50`
4. `plan.hardware_context.timer_config.prescaler == 71`
5. `plan.hardware_context.timer_config.period == 999`
6. `plan.hardware_context.timer_config.ccr == 500`
7. `plan.hardware_context.pin_mapping.recommended == "TIM1_CH1"`
8. `plan.steps` 数组里至少有一个 `action_type == "edit_file"` 的 step
9. 该 step 里有 `code_change_hints` 数组
10. 数组里至少有 1 项 `type == "add_function"`

### 7.2 阶段 2 验收（编译错误结构化修复）

手动在 `Core/Src/main.c` 添加一行 `htim999.Instance = TIM1;`（制造未定义句柄错误）。

运行：
```
cmd /c ".\agent_workbench.bat build --json"
cmd /c ".\agent_workbench.bat fix-build --json"
```

**必须满足的断言：**

1. `build` 输出里 `errors[0].message` 包含 "'htim999' undeclared"
2. `fix-build` 输出里 `suggested_fixes[0].fix.action_type == "add_declaration"`
3. `suggested_fixes[0].fix.target_files == ["Core/Inc/main.h"]`
4. `suggested_fixes[0].fix.code == "extern TIM_HandleTypeDef htim999;"`

### 7.3 阶段 3 验收（Rules 扩充）

文件行数检查：

```
wc -l .continue/rules/stm32_auto_workflow.md       # >= 300
wc -l .continue/rules/stm32_weak_model_guard.md    # >= 150
wc -l .continue/rules/stm32_task_cookbook.md       # >= 200
```

**cookbook 内容检查：**
- 至少包含 5 个任务类型：PWM / GPIO / CLI / ADC / 定时中断
- 每个任务有完整的"用户输入 → plan → 代码展开 → 编译 → 验证 → 报告"流程

### 7.4 最终验收（端到端）

用户在 Continue Agent 模式下输入：
> 给 STM32 添加 PWM 蜂鸣器控制，频率 1kHz，PA8 引脚

**期望 Continue 的行为（全程自主，只需烧录前一次确认）：**

```
下一步执行: cmd /c ".\agent_workbench.bat plan ""给STM32添加PWM蜂鸣器控制，频率1kHz，PA8引脚"" --json"
返回: 结构化 plan JSON (包含 frequency=1000, prescaler=71, period=999, pin=PA8, timer=TIM1_CH1)

✅ Step 1: 已读取 Core/Src/main.c
✅ Step 2: 已读取 Core/Inc/main.h

✅ Step 3: 已修改 Core/Src/main.c
  - 在 USER CODE BEGIN PV 后添加: TIM_HandleTypeDef htim1;
  - 在 USER CODE BEGIN 4 后添加 MX_TIM1_PWM_Init (Prescaler=71, Period=999, CCR=500)
  - 在 USER CODE BEGIN 2 后添加调用 MX_TIM1_PWM_Init();
  - 在 MX_GPIO_Init 里配置 PA8 为 AF_PP

✅ Step 4: 已修改 Core/Inc/main.h (添加 extern TIM_HandleTypeDef htim1;)

下一步执行: cmd /c ".\agent_workbench.bat build --json"
返回: {"exit_code": 0, "errors": []}
✅ Step 5: 编译成功

⚠️ Step 6 需要确认: 即将烧录到硬件
[用户点"继续"]

下一步执行: cmd /c ".\agent_workbench.bat flash --json"
返回: {"exit_code": 0}
✅ Step 6: 烧录成功

下一步执行: cmd /c ".\agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --json"
返回: {"exit_code": 0, "transcript": "...STM32 UART CLI ready...cli>..."}
✅ Step 7: CLI 验证通过

## 任务完成报告
- 用户需求: 给STM32添加PWM蜂鸣器控制，频率1kHz，PA8引脚
- 理解参数: frequency=1000Hz, pin=PA8, duty=50%(default)
- 硬件方案: TIM1_CH1, Prescaler=71, Period=999, CCR=500
- 修改的文件: Core/Src/main.c (+38 行), Core/Inc/main.h (+1 行)
- 编译结果: pass (0 errors, 0 warnings)
- 烧录结果: pass
- CLI 验证结果: pass
- 证据文件:
  - build.log, cli_transcript.log
```

**且硬件上 PA8 真的输出 1kHz PWM 方波。** 验收通过。

---

## 八、给实施者的交底

### 实施者需要了解的项目现状

1. 已实施文件清单（不要重复创建）：
   - `agent_workbench/core/planner.py`（已有，需改造）
   - `agent_workbench/core/ps_exec.py`（已有，OK）
   - `agent_workbench/core/build_errors.py`（已有，需改造）
   - `agent_workbench/core/project_scanner.py`（已有，需扩展）
   - `agent_workbench/core/cli_output.py`（已有，OK）
   - `agent_workbench/templates/task_templates/*.yaml`（已有 16 个，需全部改造）
   - `agent_workbench/templates/build_error_rules.json`（已有，需扩充）
   - `agent_workbench/templates/continue_rules/*.md`（已有，需重写）
   - `.continue/rules/*.md`（已有，由 init-continue-rules 生成）

2. 新增文件清单（必须创建）：
   - `agent_workbench/core/param_extractor.py`
   - `agent_workbench/core/hardware_knowledge.py`
   - `agent_workbench/templates/hardware_knowledge/stm32f1_clock.yaml`
   - `agent_workbench/templates/hardware_knowledge/stm32f1_timer_pin_map.yaml`
   - `agent_workbench/templates/hardware_knowledge/stm32f1_user_code_regions.yaml`
   - `agent_workbench/tests/test_planner_e2e.py`
   - `agent_workbench/tests/test_param_extractor.py`
   - `agent_workbench/tests/test_hardware_knowledge.py`
   - `agent_workbench/CONTINUE_AGENT_SETUP_ZH.md`

3. 必须修改的文件：
   - `agent_workbench/core/planner.py`（接入 param_extractor、hardware_knowledge、adjust_by_snapshot）
   - `agent_workbench/core/build_errors.py`（suggested_fix 改为结构化）
   - `agent_workbench/core/project_scanner.py`（扩展扫描能力）
   - `agent_workbench/workbench.py`（新增 `_cmd_fix_build`）
   - `agent_workbench/agent_workbench.yaml`（新增 `planner.hardware_knowledge_dir_path` 配置）
   - `agent_workbench/templates/task_templates/*.yaml`（全部改造为 code_change_hints）
   - `agent_workbench/templates/build_error_rules.json`（扩充到 15+ 条规则）
   - `agent_workbench/templates/continue_rules/stm32_auto_workflow.md`（扩充到 300+ 行）
   - `agent_workbench/templates/continue_rules/stm32_weak_model_guard.md`（扩充到 150+ 行）
   - 新增 `agent_workbench/templates/continue_rules/stm32_task_cookbook.md`（200+ 行）

### 严格禁止做的事（反复强调）

1. ❌ **绝对不要**创建 `core/llm_client.py` 或任何调用 OpenAI / DashScope / DeepSeek / LMStudio API 的代码
2. ❌ **绝对不要**在 `agent_workbench.yaml` 里加任何 API key / api_base / model 字段（这些应该只在 `.continue/config.yaml` 里）
3. ❌ **绝对不要**修改 `.continue/config.yaml`（这是用户自己的 Continue 配置）
4. ❌ **绝对不要**改变 agent_workbench 为"同步调用 LLM 的服务"
5. ❌ 不要删除任何现有命令（保留所有向后兼容）

### 必须遵守的设计原则

1. ✅ agent_workbench 全程**离线可用**（没有网络连接也能跑 plan、build、parse-errors）
2. ✅ 所有"智能"都在 Continue 的 LLM 那边（我们只提供原料）
3. ✅ 测试必须可以在 CI 上跑过（不依赖 LLM API）
4. ✅ 确定性至上（相同输入必须产出相同输出，不能有"LLM 随机性"）

### 工作流程建议

1. 从阶段 1 开始，严格按顺序
2. 每个子任务完成后，先跑对应单元测试
3. 完成一个阶段后，跑一次完整端到端验收（按本文件第 7 节的断言）
4. 有不确定的地方，先停下来，不要自己加 LLM 调用"解决问题"

---

## 九、最后总结（给实施者的三段话）

### 第 1 段：清楚职责分工

**agent_workbench 是"工具库"，Continue Agent 是"大脑"。**

agent_workbench 负责：提取参数、查硬件知识库、渲染模板、跑 build/flash/uart、解析错误、输出结构化 JSON。全部离线确定性。

Continue Agent 负责：读用户需求、调 agent_workbench 工具、用 LLM 能力把结构化提示转成具体代码、做失败重试决策。全部在 Continue 聊天窗口。

### 第 2 段：清楚输出质量标准

Plan 输出必须让 Continue 的 LLM 拿到后**不需要再猜任何硬件参数**：
- 频率 → Prescaler/Period 已经算好了
- 引脚 → 对应定时器通道已经查好了
- 占空比 → CCR 值已经算好了
- 代码模板 → 已经给好骨架了

Continue 的 LLM 只需要做"变量替换 + 少量微调"，不需要原创硬件知识。

### 第 3 段：清楚验收标准

**最终目标：** 用户在 Continue Agent 里说"给 STM32 加 1kHz PWM PA8"，板子上 PA8 真的输出 1kHz PWM 方波，全程用户只点一次"确认烧录"。

**阶段性目标：**
- 阶段 1 结束：plan 输出里能看到 prescaler=71、period=999、recommended=TIM1_CH1
- 阶段 2 结束：故意制造的 undeclared 错误能被 fix-build 精确修复
- 阶段 3 结束：rules 总行数超过 700，包含 5 个完整任务示例
- 阶段 4 结束：新项目迁移 15 分钟内跑通第一个自动化需求

**文档结束**

> 生成时间: 2026-04-19
> 版本: v2 (修正版 - 纯确定性工具方案，不接 LLM)
> 作者: AI Assistant
> 修正说明: 严格遵守用户约束"不要把 LLM 接入 agent_workbench"，改为用参数提取器 + 静态硬件知识库实现确定性 plan 生成
