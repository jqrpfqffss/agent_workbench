# agent_workbench 使用介绍 PPT 改进规划 V3

> **本文档是对 V2 版 PPT（AGENT_WORKBENCH_OVERVIEW_EDITABLE_V2_ZH.pptx）的全面改进规划。**  
> 面向对象：研发同事（嵌入式开发、测试、技术管理）  
> 建议时长：10–15 分钟  
> 总页数：12 页  
> 核心叙事：**日常开发效率痛点 → OpenCode + agent_workbench 如何提效 → 整体架构 → 实战案例 → 征集场景**

---

## V2 → V3 主要改进点

| 维度 | V2 的问题 | V3 的改进 |
|------|----------|----------|
| 背景页 | 抽象痛点（命令分散/参数口传/验证模糊/前端适配），没有和日常开发效率挂钩 | **以"日常开发效率瓶颈"为核心，列出 10 个具体场景**，每个都说清"以前怎么做→现在怎么做→快了多少" |
| 架构页 | 四层架构图不专业，文字堆叠，看不懂层与层之间的关系 | **重新设计为"三圈一流"架构图**：外圈（AI 前端）→ 中圈（agent_workbench CLI）→ 内圈（硬件/项目），贯穿一条数据流。配合清晰的表格说明 |
| 整体组织 | 内容零散，定位页/架构页/能力页/路径页各讲各的 | **合并为"3 页完成整体介绍"**：What → How → Quick Start，逻辑连贯 |
| 案例页 | 案例只展示任务 YAML 和结果，没有讲"以前多痛苦、现在多快" | **每个案例都用"Before → After"对比**，突出效率提升 |
| 征集页 | 缺少和"效率提升"的呼应 | **征集模板增加"预期节省时间"字段**，引导大家从效率角度思考 |

---

## 页面速览

| # | 标题 | 核心信息 | 建议时长 |
|---|------|---------|----------|
| 1 | 封面 | OpenCode + agent_workbench：让 STM32 开发提速 | 30s |
| 2 | 目录 | 今天的节奏 | 20s |
| 3 | **背景：日常开发的 10 个效率瓶颈** | 具体场景 + "以前→现在"对比 | 2.5min |
| 4 | **一句话理解 agent_workbench** | 定位 + 核心价值 | 1min |
| 5 | **架构全景：AI 前端 → 工作台 → 硬件** | 三圈架构图 + 数据流 | 1.5min |
| 6 | **5 步快速上手** | 从零到跑通的最短路径 | 1min |
| 7 | **案例 1：一句话需求到板上验证** | TIM3 LED 闪烁全链路 | 1.5min |
| 8 | **案例 2：代码有 bug，AI 帮你定位** | debug 模式 + evidence 定位 | 1.5min |
| 9 | **案例 3：测试验收自动化** | CLI 回归 10 条断言 + 报告 | 1.5min |
| 10 | **案例 4：换 AI 前端零成本** | OpenCode ↔ Continue 一键切换 | 1min |
| 11 | **征集使用场景** | 已知 + 征集 + 模板 | 1.5min |
| 12 | 总结 / Q&A | 三句话 + 联系方式 | 1min |

---

## Slide 1 · 封面

### 标题

**OpenCode + agent_workbench**  
**让 STM32 的开发、调试、验证都快起来**

### 副标题

面向研发同事的使用介绍

### 页面要点

- 不是介绍一个工具的功能列表
- 而是展示：**同样的开发任务，怎么做得更快、更准、更可追溯**

### 讲稿口播

> 今天介绍的不是一个抽象的框架，而是一套已经在我们项目里跑通的提效方案。
> 核心组合是 OpenCode（AI 编程助手）+ agent_workbench（STM32 自动化工作台）。
> 它能把你日常开发中最费时间的环节——写代码、编译、调试、烧录、验证——串成一条自动化流水线。
> 今天的目标很简单：让大家看到"以前要 30 分钟的事情，现在 5 分钟能做完"的真实案例。

### 视觉建议

- 深色背景，大字标题
- 左侧放 OpenCode logo / AI 图标，右侧放 STM32 芯片图标，中间用 agent_workbench 连接
- 底部一行小字："从需求到板上验证，一条流水线"

---

## Slide 2 · 目录

### 标题

`今天聊什么`

### 页面要点

```
1. 背景：日常开发的 10 个效率瓶颈
2. 整体介绍
   - 一句话理解 agent_workbench
   - 架构全景
   - 5 步快速上手
3. 实战案例（×4）
4. 征集使用场景
```

### 讲稿口播

> 先从大家每天遇到的效率瓶颈说起，然后看 agent_workbench 怎么解决这些瓶颈。
> 中间用 4 个真实案例演示，最后征集大家的新场景。

---

## Slide 3 · 背景：日常开发的 10 个效率瓶颈

### 标题

`这些场景，你每天花了多少时间？`

### 核心理念

> **这一页是整个 PPT 最重要的页面。** 不讲抽象痛点，只讲具体开发场景，每个都要让听众感同身受。重点是把"以前手动怎么做"和"现在用 OpenCode + agent_workbench 怎么做"形成鲜明对比。

### 10 个效率瓶颈与提效方案

| # | 效率瓶颈 | 以前怎么做（手动） | 现在怎么做（OpenCode + agent_workbench） |
|---|---------|-------------------|----------------------------------------|
| ❶ | **AI 生成的代码编译不过** | 从 ChatGPT/通义 复制代码到项目 → 编译报错 → 手动改 → 再编译 → 又报错 → 循环多次 | OpenCode 直接在项目里改代码 → `build` 自动编译 → 报错了 `fix-build` 自动分析错误并修复 → 循环直到编译通过，**全程不用手动复制粘贴** |
| ❷ | **代码有 bug 但定位不出来** | 加 printf → 编译 → 烧录 → 看串口 → 猜 → 再改 → 循环好几轮 | 告诉 OpenCode "帮我找这个 bug" → 它读代码 + 读 evidence（build.log / cli_transcript / assertions）→ **精准定位问题文件和行号** → 一次修复 |
| ❸ | **新功能从需求到板上验证** | 查手册算参数 → 手写代码 → 编译 → 烧录 → 连串口手动测 → 记录结果 | 说一句"给 PA8 加 1kHz PWM" → `plan` 自动查参数 → OpenCode 改代码 → `build` → `flash` → `uart exec` 自动验证 → **evidence 自动留痕** |
| ❹ | **硬件参数经常算错查错** | 翻数据手册 → 手算 Prescaler / ARR / CCR → 写错了编译能过但功能不对 | `plan` 从硬件知识库自动查询 → **Prescaler=7999, ARR=499 这些值不靠记忆**，plan 帮你查和算 |
| ❺ | **每次改完代码要手动验证** | 打开 PuTTY → 手动输 help / status / led on → 目测输出"像是对的" | `verify current --task xxx.yaml` → **10 条黑盒断言自动跑完** → pass=10, fail=0 → session_summary.md 自动生成 |
| ❻ | **测试想验收模块功能** | 测试人员写测试用例文档 → 手动逐条执行 → 截图记录 → 汇总报告 | 把验收标准写成任务 YAML → `verify current` 一条命令 → **CLI 自动执行所有断言** → 生成 assertions.jsonl + session_summary.md 作为测试报告 |
| ❼ | **烧录验证流程太慢** | 手动 `openocd -c "program ..."` → 等烧录完 → 手动打开串口 → 手动输命令 → 手动看结果 | `flash` → `uart exec --reset-first --expect-ready --command help --command status` → **一条命令完成烧录 + 串口验证** |
| ❽ | **换机器后环境全乱了** | 重新装工具链 → 找构建命令 → 找串口号 → 重新配 AI 前端 | `doctor` 一键自检所有环境 → `agent_workbench.yaml` 里所有配置集中 → **换机器只带走一个 YAML 文件** |
| ❾ | **多人协作各记各的命令** | 你用 `cmake -G "..."` 我用 `make -j4`，构建命令不统一，经常互相的编译结果不一样 | **统一 CLI 入口** `agent_workbench.bat build/flash/verify` → 所有人用同一套命令 → 结果可复现 |
| ❿ | **切换 AI 工具要重新配置** | 从 OpenCode 换到 Continue → 重写 prompt → 重配规则文件 → 花半天 | `integration install continue` **一条命令** → 自动从同一个 YAML 渲染所有配置 → 5 秒搞定 |

### 讲稿口播

> 这一页列了 10 个场景，我相信在座的每个人至少中了 5 个以上。
>
> 先看第一个：你有没有从 ChatGPT 或通义千问复制代码到项目里，然后编译报错，改了又报错，来回好几轮？OpenCode + agent_workbench 的做法是让 AI 直接在你的项目里改代码，`build` 自动编译，编译报错就 `fix-build` 自动修复，全程不用手动复制粘贴。
>
> 第二个：代码有 bug，你加了一堆 printf，编译烧录看串口，猜半天，经常几个小时才定位出来。现在你可以告诉 OpenCode "帮我找这个 bug"，它会读源码、读 build 日志、读串口 transcript，精准定位到具体文件和行号。
>
> 第三个：新功能落地需要查手册、写代码、编译、烧录、手动验证。现在你说一句"给 PA8 加 1kHz PWM"，`plan` 帮你查参数，OpenCode 帮你改代码，`build`、`flash`、`verify` 一路走到底。
>
> 后面的我就不一一展开了，核心结论只有一个：**以前需要手动做 30 分钟的事情，现在 5 分钟做完，而且每一步都有 evidence 留痕。**

### 视觉建议

- **分两页展示**（如果空间不够）：❶–❺ 一页，❻–❿ 一页
- 每行用三列：序号 + 以前 + 现在
- "以前"列用灰色/红色调，"现在"列用绿色/蓝色调
- 关键词加粗高亮
- 底部一行总结："同样的任务，从 30 分钟 → 5 分钟，每一步自动留痕"

---

## Slide 4 · 一句话理解 agent_workbench

### 标题

`agent_workbench 是什么？`

### 一句话定义

> **agent_workbench 是 STM32 项目的自动化工作台。**  
> 它把 AI 编程助手（OpenCode / Continue / Cursor）和 STM32 硬件开发流程（编译 → 烧录 → 串口验证）连接起来，让 AI 不只是"帮你写代码"，而是**帮你写代码 + 编译 + 烧录 + 验证 + 出报告**。

### 页面要点（3 个核心价值，简洁明确）

| 核心价值 | 一句话解释 |
|---------|-----------|
| 🔗 **连接 AI 和硬件** | AI 助手产出代码后，agent_workbench 帮你自动完成编译 → 烧录 → 串口验证的后半程 |
| 📋 **结论靠 evidence，不靠猜** | 每次运行都产出 build.log、cli_transcript.log、session_summary.md，结果可追溯 |
| 🔌 **AI 前端随意换** | 今天用 OpenCode，明天换 Continue，后天换 Cursor——核心工作台不变 |

### OpenCode + agent_workbench 的协作关系

```
┌──────────────────────────────────────────────────────────┐
│                     你（开发者）                          │
│            "给 PA8 加一个 1kHz PWM"                       │
└─────────────────────┬────────────────────────────────────┘
                      │ 自然语言需求
                      ▼
┌──────────────────────────────────────────────────────────┐
│                   OpenCode（AI 前端）                     │
│  · 理解需求，调用 agent_workbench 的命令                   │
│  · 读/写项目源码                                          │
│  · 执行 plan → build → flash → verify 流程                │
└─────────────────────┬────────────────────────────────────┘
                      │ 调用 CLI 命令
                      ▼
┌──────────────────────────────────────────────────────────┐
│              agent_workbench（自动化工作台）                │
│  · doctor：环境自检                                       │
│  · plan：需求 → 硬件参数 + 执行步骤                        │
│  · build：统一编译                                        │
│  · flash：统一烧录                                        │
│  · uart exec：串口自动验证                                 │
│  · verify：端到端验证闭环                                  │
│  · report：evidence 汇总                                  │
└─────────────────────┬────────────────────────────────────┘
                      │ 控制硬件
                      ▼
┌──────────────────────────────────────────────────────────┐
│                STM32 开发板 + 串口                         │
│  · 编译产物烧录到芯片                                      │
│  · CLI 通过 UART 响应命令                                  │
│  · 运行结果回传给 agent_workbench                          │
└──────────────────────────────────────────────────────────┘
```

### 讲稿口播

> agent_workbench 不是 AI，它是 AI 和硬件之间的桥梁。
>
> 你跟 OpenCode 说需求，OpenCode 帮你写代码并调用 agent_workbench 的命令去编译、烧录、验证。agent_workbench 把结果从硬件收回来，形成 evidence。
>
> 所以它的价值不是"又一个命令行工具"，而是**让 AI 能真正走完从代码到板上验证的全程**。
>
> 记住三个关键词：**连接 AI 和硬件、结论靠 evidence、前端随意换。**

### 视觉建议

- 上方：一句话定义，大字，加粗
- 中间：三个核心价值用三张卡片横排
- 下方：协作关系图（三层纵向箭头：开发者 → OpenCode → agent_workbench → 开发板）
- 配色清爽，信息层次分明

---

## Slide 5 · 架构全景：AI 前端 → 工作台 → 硬件

### 标题

`它内部怎么工作？`

### 设计理念

> **V2 的架构页把四层平铺，信息密度过高且层次不清。V3 改为"三圈一流"设计：** 用三个同心圈（外/中/内）+ 一条从上到下的数据流，让听众 10 秒看懂整体结构。

### 架构图（三圈一流）

```
╔═══════════════════════════════════════════════════╗
║                  外圈：AI 前端层                    ║
║      OpenCode  │  Continue  │  Cursor  │  Cline    ║
║      （通过 integration 包接入，可随时替换）         ║
╠═══════════════════════════════════════════════════╣
║                                                     ║
║    ┌─────────────────────────────────────────┐      ║
║    │         中圈：agent_workbench 工作台      │      ║
║    │                                           │      ║
║    │  ┌─────────┐  ┌─────────┐  ┌─────────┐  │      ║
║    │  │ 配置中心 │  │ CLI引擎 │  │ 证据系统 │  │      ║
║    │  │  .yaml   │  │ doctor  │  │ runtime/ │  │      ║
║    │  │ 单一事实 │  │ plan    │  │ evidence │  │      ║
║    │  │ 来源     │  │ build   │  │ /sessions│  │      ║
║    │  │          │  │ flash   │  │          │  │      ║
║    │  │          │  │ verify  │  │ build.log│  │      ║
║    │  │          │  │ uart    │  │ transcript│ │      ║
║    │  │          │  │ report  │  │ summary  │  │      ║
║    │  └─────────┘  └─────────┘  └─────────┘  │      ║
║    └─────────────────────────────────────────┘      ║
║                                                     ║
╠═══════════════════════════════════════════════════╣
║                  内圈：硬件层                        ║
║    STM32 MCU  │  UART CLI  │  OpenOCD / ST-Link    ║
╚═══════════════════════════════════════════════════╝
```

### 三圈说明表（简洁版，替代 V2 的长文字）

| 圈层 | 包含什么 | 职责 | 你需要关心什么 |
|------|---------|------|---------------|
| **外圈：AI 前端** | OpenCode / Continue / Cursor / Cline | 理解自然语言需求，读写代码，调用工作台命令 | 选你顺手的那个，`integration install` 一键接入 |
| **中圈：工作台** | `agent_workbench.yaml` + CLI 引擎 + 证据系统 | 统一编译/烧录/验证/报告，所有结果留 evidence | 核心配置在 YAML 里，命令都走 `agent_workbench.bat` |
| **内圈：硬件** | STM32 芯片 + UART 串口 + 调试器 | 运行固件，通过串口响应 CLI 命令 | 确保串口连通、调试器可用 |

### 数据流（一条线讲清楚）

```
需求（自然语言）
    ↓  OpenCode 理解需求
plan（硬件参数 + 执行步骤）
    ↓  OpenCode 按 plan 改代码
build（编译产物 .elf）
    ↓  
flash（烧录到 MCU）
    ↓  
uart exec（串口发命令、收响应）
    ↓  
verify（断言判定 pass/fail）
    ↓  
evidence（build.log + transcript + summary）
```

### 讲稿口播

> 看这张图，从外到内三层。
>
> 最外层是 AI 前端——OpenCode、Continue、Cursor 这些。它们负责理解你的需求、帮你改代码。但它们自己不会编译、不会烧录、不会验证。
>
> 中间层是 agent_workbench 工作台。它有三个核心模块：
> - **配置中心**：一个 YAML 文件管所有配置
> - **CLI 引擎**：doctor / plan / build / flash / uart / verify 这些命令
> - **证据系统**：每次运行的 build.log、cli_transcript.log、session_summary.md
>
> 最内层是硬件——STM32 芯片和串口。
>
> 数据流很简单：需求进来 → plan 出参数 → 改代码 → 编译 → 烧录 → 串口验证 → 输出 evidence。
>
> **AI 前端可以换，工作台不变；硬件项目可以换，只需要改 YAML。**

### 视觉建议

- 三层同心圆或三个横向色带（外蓝/中灰/内绿）
- 右侧竖向箭头展示数据流，每步标注对应的命令
- 底部三圈说明表用三列卡片
- **不要用 V2 那种密密麻麻的文字堆叠**，每个区域最多 3-4 个关键词

---

## Slide 6 · 5 步快速上手

### 标题

`第一次用？5 步跑通全流程`

### 流程图

```
① doctor          ② integration       ③ plan             ④ build          ⑤ verify
环境自检            install             需求规划             统一编译          端到端验证
检查工具链         接入 AI 前端          自然语言→步骤        一键编译          断言+evidence
配置、串口          一条命令搞定         +硬件参数            自动修错         

──── ➤ ──── ➤ ──── ➤ ──── ➤ ────
```

### 5 步详细说明

| 步骤 | 命令 | 做什么 | 耗时 |
|------|------|--------|------|
| ① | `agent_workbench.bat doctor --json` | 自检工具链、YAML、串口、build 目录 | 5 秒 |
| ② | `agent_workbench.bat integration install opencode --json` | 给 OpenCode 生成 AGENTS.md、slash 命令、agent 配置 | 3 秒 |
| ③ | `agent_workbench.bat plan "给 PA8 加 1kHz PWM" --json` | 输出：Prescaler=71, ARR=999, 需要改的文件和步骤 | 2 秒 |
| ④ | `agent_workbench.bat build --json` | CMake 配置 + 编译，失败自动走 fix-build | 10-30 秒 |
| ⑤ | `agent_workbench.bat verify current --task xxx.yaml --json` | doctor → build → uart 烟测 → 断言判定 → 输出 summary | 30-60 秒 |

### 讲稿口播

> 第一次上手就 5 步：
>
> 第一步 `doctor`——5 秒钟检查完你的环境能不能用。
> 第二步 `integration install`——3 秒钟给 AI 前端生成所有配置。
> 第三步 `plan`——你说一句中文需求，它 2 秒钟告诉你硬件参数和执行步骤。
> 第四步 `build`——一键编译，编译报错会自动修。
> 第五步 `verify`——一条命令跑完整个验证闭环，输出 evidence。
>
> 全程加起来不到 2 分钟。以前同样的事情你得打开 5 个工具、查 3 份手册、手动输 10 条命令。

### 视觉建议

- 5 个圆角方框水平排列，箭头连接
- 每个方框内：编号 + 命令名 + 一句话 + 耗时
- 底部："全程 < 2 分钟，以前至少 30 分钟"

---

## Slide 7 · 案例 1：一句话需求到板上验证

### 标题

`案例 1：说一句"加个 LED 闪烁"，5 分钟后板子上在闪`

### Before vs After

| | Before（手动） | After（OpenCode + agent_workbench） |
|---|---------------|-------------------------------------|
| 查参数 | 翻数据手册，手算 Prescaler / ARR | `plan` 自动查 → Prescaler=7999, ARR=499 |
| 写代码 | 手动改 main.c、中断文件、头文件 | OpenCode 按 plan 自动改 3 个文件 |
| 编译 | 手动跑 cmake + make，报错手动查 | `build` 一键编译，报错 `fix-build` 自动修 |
| 烧录 | 手动输 openocd 命令 | `flash` 一条命令 |
| 验证 | 打开 PuTTY 手动看 | `verify` 自动断言 CLI 正常 |
| 记录 | 截图或不记录 | session_summary.md 自动生成 |
| **总耗时** | **30-60 分钟** | **< 5 分钟** |

### 具体流程

```
你说："用 TIM3 让红色 LED 以 1Hz 频率闪烁"

    ↓ OpenCode 调用 plan

plan 输出：
  · Clock: HSI 8MHz
  · Prescaler: 7999 → 1kHz timer clock
  · ARR: 499 → 500ms 中断周期
  · 需要改: main.c + stm32f1xx_it.c + main.h

    ↓ OpenCode 按 plan 改代码

build → 编译通过 ✓

    ↓ 用户确认后

flash → 烧录成功 ✓
verify → uart_smoke：CLI 仍正常 ✓

    ↓

evidence 输出：
  · build.log（编译过程）
  · cli_transcript.log（串口验证记录）
  · 板子上红色 LED 在以 1Hz 频率闪烁 ✓
```

### 讲稿口播

> 第一个案例：你跟 OpenCode 说"用 TIM3 让红色 LED 以 1Hz 频率闪烁"。
>
> 以前你得翻数据手册查时钟频率、算 Prescaler 和 ARR、手动改三个文件、编译、烧录、打开串口看。整套下来少说 30 分钟。
>
> 现在 `plan` 帮你查参数——HSI 8MHz、Prescaler=7999、ARR=499。OpenCode 按照 plan 自动改 main.c 里加初始化、中断文件里加 callback、头文件里加声明。`build` 编译通过，`flash` 烧录，`verify` 确认 CLI 还能正常响应。
>
> **从需求到板上验证，5 分钟以内。硬件参数不是你查的，是 plan 查的。代码不是你手写的，是 OpenCode 写的。验证不是你看的，是断言判的。**

### 视觉建议

- 左半：Before（灰色调，手动步骤列表，配❌或😫表情）
- 右半：After（绿色调，自动化流程图，配✓）
- 底部大字：30 分钟 → 5 分钟

---

## Slide 8 · 案例 2：代码有 bug，AI 帮你定位

### 标题

`案例 2：找了 2 小时的 bug，AI 5 分钟定位出来`

### Before vs After

| | Before（手动调试） | After（OpenCode + agent_workbench） |
|---|-------------------|-------------------------------------|
| 定位方式 | 加 printf → 编译 → 烧录 → 看串口 → 猜 → 再改 | 告诉 AI "串口收不到 ready banner" |
| 信息来源 | 全靠自己读代码 + 经验猜测 | AI 读代码 + build.log + cli_transcript + assertions |
| 迭代次数 | 可能 5-10 轮 | 通常 1-2 轮 |
| **总耗时** | **1-3 小时** | **5-15 分钟** |

### 工作流

```
你说："UART CLI 没有输出 ready banner，帮我查一下"

    ↓ OpenCode 执行 debug 流程

第 1 步：读 evidence
  · 读 cli_transcript.log → 确认没有 "STM32 UART CLI ready."
  · 读 build.log → 编译有没有 warning
  · 读 assertions.jsonl → 哪些断言 fail 了

第 2 步：读相关代码
  · 根据 task YAML 的 scope，只读 cli.c / main.c / app_cli_commands.c
  · 不会漫无目的通读整个仓库

第 3 步：定位问题
  · 发现 main.c 里 UART 初始化顺序错了
  · 给出修复建议：把 MX_USART2_UART_Init() 移到 CLI_Init() 之前

第 4 步：修复 + 验证
  · OpenCode 修改 main.c
  · build → flash → verify → pass ✓
```

### 讲稿口播

> 第二个案例：代码有 bug，串口收不到 ready banner。
>
> 以前你怎么调？加 printf、编译、烧录、看串口、猜、再改。一轮下来至少 10 分钟，经常要 5-10 轮才能定位。
>
> 现在你告诉 OpenCode "UART CLI 没有输出 ready banner，帮我查一下"。它会先读 evidence——cli_transcript.log 里确认没有 banner，build.log 里看有没有 warning，assertions.jsonl 里看哪些断言 fail 了。然后它只读任务 YAML 里 scope 定义的那几个文件，不会漫无目的通读整个仓库。
>
> 最终它发现 main.c 里 UART 初始化顺序错了，改一行代码，重新 build → flash → verify → pass。
>
> **2 小时的事情变成 5 分钟，而且修复过程有完整的 evidence 记录。**

### 视觉建议

- 上方：Before vs After 对比表
- 下方：4 步流程图（读 evidence → 读代码 → 定位 → 修复验证）
- 关键信息：cli_transcript.log 截图片段，标注"没有 ready banner"

---

## Slide 9 · 案例 3：测试验收自动化

### 标题

`案例 3：10 条断言、一条命令、一份测试报告`

### Before vs After

| | Before（手动测试） | After（agent_workbench 自动化） |
|---|-------------------|-------------------------------|
| 写用例 | Word/Excel 写文字用例 | 任务 YAML 定义黑盒断言 |
| 执行 | 手动打开串口逐条输命令 | `verify current` 一条命令 |
| 判定 | 目测"输出像是对的" | 机器逐条匹配 needle in transcript |
| 报告 | 截图 + 手写 | session_summary.md + assertions.jsonl |
| **总耗时** | **30-60 分钟** | **< 1 分钟** |

### 任务 YAML 示例（来自 `cli_automation_regression.yaml` ）

```yaml
acceptance:
  blackbox:
    - name: cli_ready_banner_seen     # "STM32 UART CLI ready."
    - name: cli_prompt_seen           # "cli>"
    - name: cli_help_lists_commands   # "Available commands:"
    - name: cli_status_reports_uart   # "UART: USART2 @ 115200 8N1"
    - name: cli_red_ack              # "[ok] red -> on"
    - name: cli_green_ack            # "[ok] green -> off"
    - name: cli_blue_ack             # "[ok] blue -> toggle"
    - name: cli_all_off_ack          # "[ok] all -> off"
    # ... 共 10 条断言

verify:
  sequence: [doctor, build, test, debug]
  cli_commands: [help, status, red on, green off, blue toggle, all off]
```

### 执行与输出

```
执行：
  agent_workbench.bat verify current --task cli_automation_regression.yaml --json

输出：
  session_summary.md
    verdict: pass
    assertions: pass=10, fail=0, skip=0
    strongest_evidence: saw_ready=True, saw_prompt=True

  cli_transcript.log
    > help
    < Available commands: help status led red green blue all
    > red on
    < [ok] red -> on
    ...

  assertions.jsonl
    {"name":"cli_ready_banner_seen","result":"pass","needle":"STM32 UART CLI ready."}
    {"name":"cli_red_ack","result":"pass","needle":"[ok] red -> on"}
    ...
```

### 讲稿口播

> 第三个案例面向测试验收。
>
> 测试同事要验收 CLI 模块功能，以前怎么做？打开 PuTTY，手动输 help、status、red on、blue toggle，目测输出"好像对了"，截几张图，写一份测试报告。整套下来至少 30 分钟。
>
> 现在测试同事只需要定义一份任务 YAML——把验收标准写成黑盒断言。然后一条命令 `verify current`，agent_workbench 自动打开串口、逐条执行命令、逐条匹配断言。
>
> 结果直接出 session_summary.md：verdict=pass，assertions=pass=10 fail=0 skip=0。每条断言的详细判定在 assertions.jsonl 里。完整的串口交互记录在 cli_transcript.log 里。
>
> **这就是测试报告。机器判的，不是人看的。**

### 视觉建议

- 左上：任务 YAML 截图（高亮 acceptance.blackbox）
- 右上：session_summary.md 截图（高亮 verdict + assertions）
- 下方：cli_transcript.log 截图片段
- 大字总结："10 条断言、1 条命令、1 份 evidence"

---

## Slide 10 · 案例 4：换 AI 前端零成本

### 标题

`案例 4：从 OpenCode 换到 Continue，5 秒搞定`

### Before vs After

| | Before（手动配置） | After（integration 一条命令） |
|---|-------------------|-------------------------------|
| 换前端 | 重写 prompt、重配规则、可能半天 | `integration install continue` → 5 秒 |
| 配置来源 | 每个前端各记一份 | 统一从 `agent_workbench.yaml` 渲染 |
| 核心命令 | 可能要改 | 完全不变 |

### integration 机制

```
agent_workbench/integrations/
├── opencode/
│   ├── manifest.yaml          # 声明要生成哪些文件
│   ├── files/                 # 模板文件
│   │   ├── AGENTS.md.tpl      # → 渲染成项目根目录的 AGENTS.md
│   │   ├── agent/*.md.tpl     # → 渲染成 .opencode/agent/*.md
│   │   └── command/*.md.tpl   # → 渲染成 .opencode/command/*.md
│   └── README_ZH.md
│
├── continue/
│   ├── manifest.yaml
│   ├── files/
│   └── README_ZH.md
│
└── cursor/                    # 将来新增
    └── ...

所有 integration 共享同一套模板变量：
  {project_name}    → serial
  {ready_banner}    → STM32 UART CLI ready.
  {prompt}          → cli>
  {uart_port}       → COM3
  {build_dir}       → build/cmake-debug
  ...
  变量值统一来自 agent_workbench.yaml
```

### 讲稿口播

> 第四个案例很快讲完。
>
> 你一直用 OpenCode，有天想试试 Continue。以前你得研究 Continue 的配置格式，重写 prompt 模板，可能花半天。
>
> 现在：`integration install continue`，5 秒钟。它从同一个 YAML 里取值，渲染 Continue 自己的模板，所有配置自动生成。
>
> 想回 OpenCode？`integration install opencode`。想支持新前端？加一个目录、写一个 manifest.yaml。核心代码不需要改一行。
>
> **这就是"前端可替换"的意思：你的选择自由度变大了，迁移成本趋近于零。**

### 视觉建议

- 左侧：OpenCode 图标 + 对应文件列表
- 右侧：Continue 图标 + 对应文件列表
- 中间：`agent_workbench.yaml`（共享配置源）
- 箭头从 YAML 分别指向两侧
- 底部大字："新增前端 = 新增一个目录"

---

## Slide 11 · 征集使用场景

### 标题

`你的下一个提效场景是什么？`

### 上半部分：目前已知场景（小字回顾）

| 场景 | 效率提升 |
|------|---------|
| 新功能落地（需求→代码→板上验证） | 30min → 5min |
| Bug 定位（加 printf 循环 → AI 读 evidence） | 2h → 15min |
| 测试验收（手动逐条 → 自动断言+报告） | 30min → 1min |
| 换 AI 前端 | 半天 → 5 秒 |
| 硬件参数查询 | 翻手册 → plan 自动查 |
| 环境配置 | 到处找 → doctor 一键自检 |

### 下半部分：征集模板

> **以上 6 个场景只是起点。agent_workbench 的核心能力（plan / build / flash / uart / verify / context / report）还有很多组合方式没被发掘。**

**投稿模板：**

```
场景名称：________________________
我现在手动做要多久：__________ 分钟/小时
我现在的痛点是：________________________
我希望 OpenCode + agent_workbench 能帮我：
  ________________________
我可以提供的输入：
  □ 任务 YAML    □ 期望产物    □ 已有脚本    □ 需求描述
我对验收的标准：________________________
预期节省时间：__________ 分钟/小时
```

### 灵感方向

| 方向 | 可能的场景 | 预期提效 |
|------|-----------|---------|
| ADC 采集配置 | plan 查引脚映射 + 采样率 → 生成初始化代码 → verify 验证数据输出 | 参数查询从 20min → 2s |
| PWM 波形调参 | plan 推算 Prescaler/ARR/CCR → 生成代码 → 示波器或 CLI 验证 | 全链路从 40min → 5min |
| 多 UART 管理 | 一口调试 + 一口协议通信 → agent_workbench 管两路 | 串口切换不再手忙脚乱 |
| 自定义协议解析 | diag_uart 发 hex → 解析应答 → 断言字段值 | 协议调试从"猜"到"断言" |
| 功耗测试 | 低功耗模式切换 → monitor 采样 → 自动出功耗报告 | 测试报告自动化 |
| CI/CD 硬件验证 | verify 接入 Jenkins/Actions → 每次提交自动跑硬件验证 | 验证从"记得跑"到"自动跑" |
| 代码 review 辅助 | AI 读 diff + evidence → 判断改动是否破坏已有功能 | review 从"看感觉"到"看证据" |

### 投稿方式

- **GitHub Issue**：仓库 Issues 页面，"新场景投稿"模板
- **仓库 PR**：在 `agent_workbench/docs/scenario_inbox.md` 追加
- **内部群接龙**：按上面模板格式发消息
- **直接找我聊**：我帮你写成任务 YAML

### Call-to-Action

> **你每天重复最多的手动操作是什么？**  
> **那就是 agent_workbench 下一个要自动化的事情。**

### 讲稿口播

> 最后一页，也是今天最重要的一页。
>
> 上面这些都是已经跑通的场景。但我们目前用到的只是 agent_workbench 能力的一小部分。
>
> 你每天重复最多的手动操作是什么？查参数？改代码后反复编译？手动验证？写报告？
>
> 这些都有可能被自动化。我需要大家帮我一起想：你的下一个提效场景是什么？
>
> 投稿方式很灵活，关键是告诉我：你现在手动做要多久，你希望它帮你做什么，验收标准是什么。
>
> **你每天重复最多的手动操作，就是 agent_workbench 下一个要自动化的事情。**

### 视觉建议

- 上半：已知场景缩略表（小字，灰色调）
- 下半：投稿模板（大字，橙/黄高亮，3 张空白卡片）
- 最底部：call-to-action 大字加粗居中
- 整体色调偏暖，表示"邀请和开放"

---

## Slide 12 · 总结 / Q&A

### 标题

`三句话带走`

### 页面要点

| # | 一句话 |
|---|--------|
| 1 | **OpenCode 是大脑，agent_workbench 是手脚** —— AI 负责思考和写代码，工作台负责编译、烧录、验证、出报告 |
| 2 | **所有结论看 evidence** —— build.log、cli_transcript.log、session_summary.md 比口头判断靠谱 |
| 3 | **你的重复劳动就是它的自动化目标** —— 把你的场景投稿进来，让 agent_workbench 帮更多的人 |

### 附加信息

- 仓库：`https://github.com/jqrpfqffss/agent_workbench.git`
- 文档：`agent_workbench/README.md`
- 配置：`agent_workbench/agent_workbench.yaml`
- 投稿：GitHub Issues / `scenario_inbox.md` / 群接龙

### 讲稿口播

> 三句话收尾。
>
> 第一，OpenCode 是大脑，agent_workbench 是手脚。AI 帮你想和写，工作台帮你编译、烧录、验证、出报告。
> 第二，结论一定看 evidence。build.log、transcript、session_summary 比任何人的"我觉得没问题"都靠谱。
> 第三，你每天重复最多的手动操作，就是它下一个要帮你自动化的事情。把你的场景告诉我。
>
> 谢谢大家。

### 视觉建议

- 三个大数字 1/2/3，每个配一句话
- 下方仓库/文档/投稿链接
- 最底部：**Q&A** 大字
- 深色背景，和封面呼应

---

## 附录 A：版式与字体建议

| 元素 | 建议 |
|------|------|
| 封面/结尾 | 深色背景 + 白色大字 |
| 背景页（效率对比） | 左灰右绿双色调，"以前→现在"对比鲜明 |
| 架构页 | 浅底深字，三圈用不同底色区分 |
| 案例页 | 统一 Before/After 双栏布局 |
| 命令、路径、文件名 | 等宽字体（Consolas / Fira Code / Source Code Pro） |
| 每页正文 | 最多 3-4 个关键点 |
| 中文字体 | 思源黑体 / 微软雅黑 |

## 附录 B：时间分配

| 优先级 | 页面 | 时长 |
|--------|------|------|
| ★★★ | Slide 3（10 个效率瓶颈） | 2.5 min |
| ★★★ | Slide 4-5（定位 + 架构） | 2.5 min |
| ★★ | Slide 6（5 步上手） | 1 min |
| ★★★ | Slide 7-10（4 个案例） | 5.5 min |
| ★★★ | Slide 11（征集场景） | 1.5 min |
| ★ | 其他 | 2 min |
| | **合计** | **~15 min** |

如果只有 10 分钟，优先讲 Slide 3（挑 3-4 个瓶颈讲）、Slide 4、Slide 7、Slide 9、Slide 11。

## 附录 C：与 V2 的关键差异

| 维度 | V2 | V3 |
|------|----|----|
| 背景页 | 4 个抽象痛点 | **10 个具体效率瓶颈，每个有 Before/After 对比** |
| 架构页 | 四层平铺文字堆叠 | **三圈一流设计，10 秒看懂** |
| 定位页 | 说"控制平面" | **说"AI 的大脑 + 工作台的手脚"，更直观** |
| 案例页 | 只展示 YAML 和结果 | **每个案例都有 Before/After + 时间对比** |
| 征集页 | 无时间维度 | **模板增加"手动耗时"和"预期节省"字段** |
| 整体风格 | 技术文档感 | **以效率提升为核心叙事** |
| OpenCode 角色 | 只作为 integration 提及 | **明确为"大脑"角色，与 agent_workbench"手脚"角色配合讲** |
