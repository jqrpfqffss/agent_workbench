# agent_workbench 使用介绍 PPT 内容规划 V4

> **面向对象：** 研发同事（嵌入式开发、测试、技术管理）  
> **建议时长：** 10–15 分钟  
> **总页数：** 10 页  
> **核心叙事线：** 背景痛点 → 使用场景一览 → 整体介绍（是什么 + 怎么工作） → 实战案例 → 征集场景

---

## 页面总览

| # | 类型 | 标题 | 核心信息 | 建议时长 |
|---|------|------|---------|---------|
| 1 | 封面 | agent_workbench：STM32 自动化工作台 | 定位一句话 | 30s |
| 2 | 背景 | 为什么需要 agent_workbench | 4 个核心痛点，让听众感同身受 | 1.5min |
| 3 | 使用场景 | agent_workbench 能帮你做什么 | 6 大使用场景概览 | 2min |
| 4 | 整体介绍 | agent_workbench 是什么 | 一句话定位 + 三个核心特性 | 1.5min |
| 5 | 架构 | 它内部怎么工作 | 三层架构：AI前端 → 工作台 → 硬件 | 1.5min |
| 6 | 快速上手 | 5 步跑通全流程 | 从零到 verify 的最短路径 | 1min |
| 7 | 案例1 | 一句话需求到板上验证 | PWM 需求全链路闭环 | 2min |
| 8 | 案例2 | 测试验收自动化 | 10 条断言自动判定 + 报告 | 2min |
| 9 | 征集 | 你的下一个自动化场景是什么？ | 已知场景 + 征集模板 + 灵感方向 | 2min |
| 10 | 总结 | 三句话带走 + Q&A | 收束 + 联系方式 | 1min |

---

## Slide 1 · 封面

### 标题

**agent_workbench**  
**STM32 项目的自动化工作台**

### 副标题

面向研发同事的使用介绍

### 页面要点

- agent_workbench 不是一个 AI 工具
- 它是连接 AI 编程助手和 STM32 硬件开发流程的自动化控制平面
- 目标：让"从需求到板上验证"变成一条可复用的流水线

### 讲稿

> 今天给大家介绍的是 agent_workbench——我们 STM32 项目的自动化工作台。
> 它不是一个 AI，而是把 AI 编程助手（比如 OpenCode、Continue、Cursor）和我们日常的构建、烧录、串口验证串起来的一套流程工具。
> 听完今天的介绍，希望大家能回答三个问题：它解决什么问题、怎么上手、以及你自己的哪些重复劳动可以被它自动化。

### 视觉建议

- 深色背景，大字标题居中
- 底部一行小字："从需求到板上验证，一条流水线"

---

## Slide 2 · 背景：为什么需要 agent_workbench

### 标题

**这些问题，你遇到过几个？**

### 四大核心痛点

agent_workbench 的诞生不是为了解决一个抽象的技术问题，而是解决我们每天真实遇到的开发效率瓶颈：

| 痛点 | 具体表现 | 后果 |
|------|---------|------|
| **① 命令入口分散** | 构建用 cmake + make，烧录用 openocd，串口用 PuTTY，验证靠手动——每个环节各有各的命令和工具 | 换机器要重新找命令，换人协作要口头传授，出问题了不知道哪一步出错 |
| **② 硬件参数靠记忆** | TIM Prescaler / ARR / CCR、GPIO 模式、ADC Channel，经常翻手册手算，或者"上次算好了但忘记存在哪" | 参数算错了编译能过但功能不对，排查成本极高 |
| **③ 验证停留在"目测"** | 改完代码，编译烧录，打开串口手动输命令，看输出"好像对了"就算过了 | 没有记录、不可复现、回归测试靠人记性 |
| **④ AI 生成代码落不了地** | 从 ChatGPT/通义千问复制代码到项目，编译报错，手动改，又报错，来回好几轮 | AI 只帮你写了代码的"前半程"，后半程（编译→烧录→验证）还是手动 |

### 一句话总结

> **agent_workbench 解决的不是某一个命令，而是把"改代码→编译→烧录→串口验证→结果留痕"这条链路从头到尾统一起来。**

### 讲稿

> 在介绍 agent_workbench 之前，先看看我们每天遇到的问题。
>
> 第一个：命令入口分散。构建用 cmake，烧录用 openocd，串口用 PuTTY，换台机器全忘了。
> 第二个：硬件参数靠记忆。Prescaler 多少、ARR 多少，每次都要翻手册算，算错了编译能过但功能不对。
> 第三个：验证停在目测。改完代码打开串口看一眼"好像对了"就算过了，没有记录，不可复现。
> 第四个：AI 代码落不了地。从 ChatGPT 复制代码过来，编译报错改来改去，AI 只帮了前半程。
>
> 这四个问题不是偶尔发生，是天天发生。agent_workbench 就是为了把这些高频痛点一起解决。

### 视觉建议

- 四个痛点用四张卡片/图标横排或 2×2 网格
- 每张卡片：图标 + 标题 + 一句话描述
- 底部总结句加粗高亮
- 配色："痛点"部分用灰/红色调

---

## Slide 3 · 使用场景：agent_workbench 能帮你做什么

### 标题

**6 个已验证的使用场景**

### 核心理念

> 这一页不讲技术细节，只讲"它能帮你做什么事"。让听众快速建立"这个工具和我有关系"的认知。

### 场景列表

| # | 使用场景 | 以前怎么做 | 现在怎么做 | 预估提效 |
|---|---------|-----------|-----------|---------|
| ❶ | **新功能从需求到板上验证** | 查手册算参数 → 手写代码 → 手动编译 → 手动烧录 → 打开串口手动测 | 说一句需求 → `plan` 查参数 → AI 改代码 → `build` → `flash` → `verify` 自动验证 | 30min → 5min |
| ❷ | **AI 代码编译不过** | 从 ChatGPT 复制 → 报错 → 手动改 → 又报错 → 循环 | AI 直接在项目里改 → `build` 编译 → 报错自动 `fix-build` → 循环到通过 | 手动 5-10 轮 → 自动 1-2 轮 |
| ❸ | **测试验收自动化** | 手动逐条输命令 → 目测结果 → 截图写报告 | 定义任务 YAML → `verify current` 一条命令 → 自动断言 + 自动出报告 | 30min → 1min |
| ❹ | **环境换机器后全乱** | 重装工具链 → 找命令 → 找串口号 → 重配 AI 前端 | `doctor` 一键自检 → `agent_workbench.yaml` 集中配置 → 换机器只带一个 YAML | 半天 → 5 分钟 |
| ❺ | **切换 AI 前端** | 重写 prompt → 重配规则文件 → 花半天适配 | `integration install continue` 一条命令 → 5 秒自动渲染所有配置 | 半天 → 5 秒 |
| ❻ | **多人协作命令不统一** | 你用 `cmake -G "..."` 我用 `make -j4`，结果不一样 | 统一 CLI 入口 `agent_workbench.bat build/flash/verify` → 所有人同一套命令 | 结果可复现 |

### 一句话总结

> **以上只是已经跑通的场景。agent_workbench 的核心能力（plan / build / flash / uart / verify / report）还有很多组合方式等你发掘。**

### 讲稿

> 我们先看 agent_workbench 现在已经能帮你做什么。
>
> 第一个场景最直接：你说一句"给 PA8 加 1kHz PWM"，它帮你查参数、改代码、编译、烧录、验证，全程 5 分钟搞定。以前同样的事至少半小时。
>
> 第二个：AI 写的代码编译不过。以前你复制粘贴改来改去，现在 AI 直接在项目里改，编译失败自动走 fix-build 流程。
>
> 第三个：测试验收。以前手动逐条输命令目测结果，现在写一份 YAML、一条命令把 10 条断言跑完，自动出报告。
>
> 还有换机器、换 AI 前端、团队命令统一——这些都是每天都会遇到的场景。
>
> 但我要说的是：**以上只是起点**。等会儿最后一页，我要向大家征集更多场景。

### 视觉建议

- 6 个场景用 6 张小卡片，每张有序号图标、场景名、一句话对比
- "以前"用灰色小字，"现在"用蓝/绿色高亮
- 底部总结句
- 如果空间不够可以分两页（❶❷❸ + ❹❺❻）

---

## Slide 4 · 整体介绍：agent_workbench 是什么

### 标题

**一句话理解 agent_workbench**

### 一句话定位

> **agent_workbench 是 STM32 项目的自动化工作台。**  
> 它把 AI 编程助手和 STM32 硬件开发流程（编译 → 烧录 → 串口验证）连接起来，  
> 让 AI 不只是"帮你写代码"，而是 **帮你写代码 + 编译 + 烧录 + 验证 + 出报告**。

### 三个核心特性

| 特性 | 解释 | 对你的意义 |
|------|------|-----------|
| 🔗 **统一入口** | 所有命令走 `agent_workbench.bat`，所有配置在 `agent_workbench.yaml` | 不用再记各种零散命令，换机器只带一个 YAML |
| 📋 **结论靠 Evidence** | 每次运行产出 build.log、cli_transcript.log、session_summary.md | 验证结果可追溯、可复盘，不再"目测像是对的" |
| 🔌 **前端可替换** | AI 前端（OpenCode / Continue / Cursor）通过 integration 插件接入 | 核心工作台不变，换 AI 前端只需一条命令 |

### 关键概念：agent_workbench ≠ AI

```
┌──────────────────────────────────────────────┐
│            你（开发者）                        │
│      "给 PA8 加一个 1kHz PWM"                  │
└──────────────────┬───────────────────────────┘
                   │ 自然语言需求
                   ▼
┌──────────────────────────────────────────────┐
│         OpenCode / Continue / Cursor          │
│         （AI 前端 = "大脑"）                   │
│   · 理解需求、读写代码                         │
│   · 调用 agent_workbench 的命令                │
└──────────────────┬───────────────────────────┘
                   │ 调用 CLI 命令
                   ▼
┌──────────────────────────────────────────────┐
│          agent_workbench（"手脚"）             │
│   · doctor：环境自检                          │
│   · plan：需求 → 硬件参数 + 执行步骤          │
│   · build：统一编译（失败自动 fix-build）      │
│   · flash：统一烧录                           │
│   · uart exec：串口自动发命令收响应            │
│   · verify：端到端验证闭环                     │
│   · report：evidence 汇总                     │
└──────────────────┬───────────────────────────┘
                   │ 控制硬件
                   ▼
┌──────────────────────────────────────────────┐
│      STM32 开发板 + UART 串口 + 调试器        │
└──────────────────────────────────────────────┘
```

### 讲稿

> agent_workbench 不是 AI，它是 AI 和硬件之间的桥梁。
>
> 你跟 AI 说需求，AI 帮你写代码。但写完代码之后呢？编译、烧录、打开串口验证——这些"后半程"以前都是手动的。
>
> agent_workbench 就是做"后半程"的工具。AI 是大脑，agent_workbench 是手脚。它把编译、烧录、串口验证、结果留痕全部自动化。
>
> 记住三个关键词：**统一入口、结论靠 Evidence、前端可替换。**

### 视觉建议

- 上方：一句话定位，大字加粗居中
- 中间：三个特性用三张卡片横排
- 下方：三层协作图（开发者 → AI → agent_workbench → 硬件）
- 配色清爽简洁

---

## Slide 5 · 架构：它内部怎么工作

### 标题

**三层架构：AI 前端 → 工作台 → 硬件**

### 架构图

```
╔════════════════════════════════════════════════╗
║              外层：AI 前端                      ║
║    OpenCode  │  Continue  │  Cursor  │  ...    ║
║   （通过 integration 包接入，可随时替换）        ║
╠════════════════════════════════════════════════╣
║                                                  ║
║   ┌────────────┐  ┌────────────┐  ┌──────────┐  ║
║   │  配置中心   │  │  CLI 引擎  │  │ 证据系统 │  ║
║   │            │  │            │  │          │  ║
║   │ .yaml      │  │ doctor     │  │ runtime/ │  ║
║   │ 统一配置   │  │ plan       │  │ evidence/│  ║
║   │ 项目/串口  │  │ build      │  │          │  ║
║   │ /烧录/输出 │  │ flash      │  │ build.log│  ║
║   │            │  │ uart       │  │ transcript│ ║
║   │            │  │ verify     │  │ summary  │  ║
║   │            │  │ report     │  │ assertions│ ║
║   └────────────┘  └────────────┘  └──────────┘  ║
║                                                  ║
║         中层：agent_workbench 工作台              ║
╠════════════════════════════════════════════════╣
║              内层：硬件                          ║
║    STM32 MCU  │  UART CLI  │  OpenOCD/ST-Link  ║
╚════════════════════════════════════════════════╝
```

### 三层职责

| 层 | 包含什么 | 职责 | 你关心什么 |
|----|---------|------|-----------|
| **外层：AI 前端** | OpenCode / Continue / Cursor | 理解需求、读写代码、调用工作台命令 | 选你顺手的，`integration install` 一键接入 |
| **中层：工作台** | `agent_workbench.yaml` + CLI 引擎 + 证据系统 | 统一编译/烧录/验证/报告，所有结果留 evidence | 核心配置在 YAML，命令走 `agent_workbench.bat` |
| **内层：硬件** | STM32 芯片 + UART 串口 + 调试器 | 运行固件，通过串口响应 CLI 命令 | 确保串口连通、调试器可用 |

### 工作台核心三件套

| 模块 | 文件/目录 | 作用 |
|------|----------|------|
| **配置中心** | `agent_workbench.yaml` | 单一事实来源：项目名、构建目录、串口号、烧录方式、模型配置——一个文件管所有 |
| **CLI 引擎** | `workbench.py` + `core/` | 统一命令行：doctor / plan / build / flash / uart / verify / report |
| **证据系统** | `runtime/` + `evidence/sessions/` | 每次运行的 build.log、cli_transcript.log、session_summary.md、assertions.jsonl |

### 数据流

```
需求（自然语言）
  ↓  AI 理解需求
plan（硬件参数 + 执行步骤）
  ↓  AI 按 plan 改代码
build（编译产出 .elf）
  ↓
flash（烧录到 MCU）
  ↓
uart exec（串口发命令、收响应）
  ↓
verify（断言判定 pass/fail）
  ↓
evidence（build.log + transcript + summary）
```

### 讲稿

> 从外到内三层。
>
> 最外层是 AI 前端，OpenCode 也好、Continue 也好，它们负责理解你的需求、帮你改代码。但它们自己不会编译、不会烧录、不会验证。
>
> 中间层是 agent_workbench 工作台，它有三个核心模块：
> - 配置中心：一个 YAML 管所有配置
> - CLI 引擎：doctor / plan / build / flash / verify 这些命令
> - 证据系统：build.log、transcript、session_summary
>
> 最内层是硬件——STM32 和串口。
>
> 关键一点：**AI 前端可以换，工作台不变；硬件项目可以换，只需改 YAML。**

### 视觉建议

- 三层用不同底色：外层蓝色、中层灰色、内层绿色
- 右侧放数据流箭头
- 底部放三模块简表

---

## Slide 6 · 快速上手：5 步跑通全流程

### 标题

**第一次用？5 步跑通**

### 流程图

```
① doctor → ② integration install → ③ plan → ④ build → ⑤ verify
 环境自检     接入 AI 前端           需求规划    统一编译    端到端验证
   5 秒          3 秒                2 秒      10-30 秒    30-60 秒
```

### 5 步详解

| 步骤 | 命令 | 做什么 | 耗时 |
|------|------|--------|------|
| ① doctor | `agent_workbench.bat doctor --json` | 自检工具链、YAML 配置、串口连通、构建目录 | 5 秒 |
| ② integration install | `agent_workbench.bat integration install opencode --json` | 给 AI 前端生成 AGENTS.md、命令、agent 配置 | 3 秒 |
| ③ plan | `agent_workbench.bat plan "给 PA8 加 1kHz PWM" --json` | 从需求提取参数 → 查硬件方案 → 输出执行步骤 | 2 秒 |
| ④ build | `agent_workbench.bat build --json` | CMake + 编译，失败自动走 fix-build | 10-30 秒 |
| ⑤ verify | `agent_workbench.bat verify current --task xxx.yaml --json` | doctor → build → uart 烟测 → 断言 → 输出 summary | 30-60 秒 |

### 讲稿

> 第一次上手就记 5 个动作。
>
> 第一步 doctor，5 秒钟检查完环境。
> 第二步 integration install，3 秒钟把 AI 前端接上。
> 第三步 plan，你说一句中文需求，它告诉你参数和步骤。
> 第四步 build，一键编译，报错自动修。
> 第五步 verify，一条命令完成端到端验证。
>
> 全程不到 2 分钟。以前同样的事你得打开 5 个工具。

### 视觉建议

- 5 个圆角方框水平排列，箭头连接
- 每个方框：编号 + 命令名 + 一句话 + 耗时
- 底部："全程 < 2 分钟"

---

## Slide 7 · 案例 1：一句话需求到板上验证

### 标题

**案例 1：说"加个 LED 闪烁"，5 分钟后板子上在闪**

### Before vs After

| 环节 | 以前（手动） | 现在（agent_workbench） |
|------|------------|----------------------|
| 查参数 | 翻数据手册，手算 Prescaler / ARR | `plan` 自动查 → Prescaler=7999, ARR=499 |
| 写代码 | 手动改 main.c、中断文件、头文件 | AI 按 plan 自动改 3 个文件 |
| 编译 | 手动 cmake + make，报错手动查 | `build` 一键编译，报错 `fix-build` 自动修 |
| 烧录 | 手动输 openocd 命令 | `flash` 一条命令 |
| 验证 | 打开 PuTTY 手动看 | `verify` 自动断言 |
| 记录 | 截图或不记录 | session_summary.md 自动生成 |
| **总耗时** | **30-60 分钟** | **< 5 分钟** |

### 完整流程

```
你说："用 TIM3 让红色 LED 以 1Hz 频率闪烁"

    ↓ AI 调用 plan

plan 输出：
  · Clock: HSI 8MHz
  · Prescaler: 7999 → 1kHz timer clock
  · ARR: 499 → 500ms 中断周期
  · 需要改: main.c + stm32f1xx_it.c + main.h

    ↓ AI 按 plan 改代码

build → 编译通过 ✓

    ↓ 用户确认后

flash → 烧录成功 ✓
verify → CLI 仍正常响应 ✓

    ↓

evidence 输出：
  · build.log（编译全过程）
  · cli_transcript.log（串口验证记录）
  · 板子上 LED 在闪 ✓
```

### 讲稿

> 第一个案例：你说"用 TIM3 让红色 LED 以 1Hz 闪烁"。
>
> 以前你得翻手册查时钟、算 Prescaler、手动改三个文件、编译、烧录、打开串口看。少说半小时。
>
> 现在 plan 帮你查参数——HSI 8MHz、Prescaler=7999、ARR=499。AI 自动改好代码。build 编译通过，flash 烧录，verify 确认串口正常。
>
> **硬件参数是 plan 查的，代码是 AI 写的，验证是断言判的。每一步都有 evidence。**

### 视觉建议

- 左半：Before（灰色调，列出手动步骤）
- 右半：After（绿色调，自动化流程图）
- 底部大字："30 分钟 → 5 分钟"

---

## Slide 8 · 案例 2：测试验收自动化

### 标题

**案例 2：10 条断言、一条命令、一份测试报告**

### Before vs After

| 环节 | 以前（手动） | 现在（agent_workbench） |
|------|------------|----------------------|
| 写用例 | Word/Excel 写文字用例 | 任务 YAML 定义黑盒断言 |
| 执行 | 手动打开串口逐条输命令 | `verify current` 一条命令 |
| 判定 | 目测"输出像是对的" | 机器逐条匹配 needle in transcript |
| 报告 | 截图 + 手写 | session_summary.md + assertions.jsonl |
| **总耗时** | **30-60 分钟** | **< 1 分钟** |

### 任务 YAML 示例

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

verify:
  sequence: [doctor, build, test, debug]
  cli_commands: [help, status, red on, green off, blue toggle, all off]
```

### 输出结果

```
session_summary.md
  verdict: pass
  assertions: pass=10, fail=0, skip=0
  strongest_evidence: saw_ready=True, saw_prompt=True

assertions.jsonl
  {"name":"cli_ready_banner_seen","result":"pass","needle":"STM32 UART CLI ready."}
  {"name":"cli_red_ack","result":"pass","needle":"[ok] red -> on"}
  ...
```

### 讲稿

> 第二个案例面向测试验收。
>
> 以前测试怎么做？打开 PuTTY，手动输 help、status、red on，目测"好像对了"，截图写报告。30 分钟起。
>
> 现在你把验收标准写进 YAML——10 条黑盒断言。一条命令 verify current，agent_workbench 自动打开串口、逐条执行、逐条判定。
>
> 最终输出：verdict=pass, assertions=pass=10 fail=0。每条断言的详情在 assertions.jsonl，完整串口交互在 cli_transcript.log。
>
> **这就是测试报告：机器判的，不是人看的。**

### 视觉建议

- 左上：任务 YAML 截图（高亮 acceptance.blackbox）
- 右上：session_summary.md 截图（高亮 verdict + assertions）
- 下方：cli_transcript.log 片段
- 大字总结："10 条断言、1 条命令、1 份 evidence"

---

## Slide 9 · 征集：你的下一个自动化场景是什么？

### 标题

**你每天重复最多的手动操作是什么？**

### 已知场景回顾

| 场景 | 提效幅度 |
|------|---------|
| 新功能从需求到板上验证 | 30min → 5min |
| AI 代码编译不过自动修复 | 手动 5-10 轮 → 自动 1-2 轮 |
| 测试验收自动化 | 30min → 1min |
| 环境换机器 | 半天 → 5 分钟 |
| 切换 AI 前端 | 半天 → 5 秒 |
| 团队命令统一 | 各记一套 → 统一 CLI |

### 征集说明

> **以上 6 个场景只是起点。**  
> agent_workbench 的核心能力（plan / build / flash / uart / verify / context / report）还有很多组合方式没被发掘。  
> **你每天重复最多的手动操作，就是它下一个要自动化的事情。**

### 投稿模板

```
场景名称：________________________
我现在手动做要多久：__________ 分钟/小时
我现在的痛点是：________________________
我希望 agent_workbench 能帮我：________________________
验收标准：________________________
预期节省时间：________________________
```

### 灵感方向

| 方向 | 可能的场景 |
|------|-----------|
| ADC 采集配置 | plan 查引脚映射 + 采样率 → 生成代码 → verify 验证 |
| PWM 波形调参 | plan 推算参数 → 生成代码 → CLI 验证波形 |
| 自定义协议解析 | diag_uart 发 hex → 解析应答 → 断言字段值 |
| CI/CD 硬件验证 | verify 接入 Jenkins → 每次提交自动跑硬件验证 |
| 代码 review 辅助 | AI 读 diff + evidence → 判断改动是否破坏已有功能 |
| 功耗测试 | 低功耗模式切换 → 自动采样 → 出功耗报告 |

### 投稿方式

- **GitHub Issue**：仓库 Issues 页面
- **仓库 PR**：在 `agent_workbench/docs/scenario_inbox.md` 追加
- **群接龙**：按模板格式发消息
- **直接找我聊**：帮你写成任务 YAML

### 讲稿

> 这是今天最重要的一页。
>
> 上面列的都是已经跑通的。但说实话，agent_workbench 的能力我们只用了一小部分。
>
> 你每天重复最多的手动操作是什么？查参数？反复编译？手动串口验证？写测试报告？
>
> 这些都可能被自动化。我需要大家帮我想：下一个场景是什么？
>
> 投稿模板很简单：告诉我你现在做多久、痛点是什么、希望怎么帮你、验收标准是什么。
>
> **你每天重复最多的手动操作，就是 agent_workbench 下一个要自动化的事情。**

### 视觉建议

- 上半：已知场景缩略表（小字灰色调）
- 中间：投稿模板（大字高亮，留白卡片）
- 下半：灵感方向表
- 最底部：Call-to-Action 大字加粗

---

## Slide 10 · 总结 + Q&A

### 标题

**三句话带走**

### 三句话

| # | 一句话 |
|---|--------|
| 1 | **agent_workbench 是 STM32 的自动化工作台，AI 是大脑，它是手脚** — 编译、烧录、验证、出报告全自动 |
| 2 | **所有结论看 Evidence** — build.log / cli_transcript / session_summary 比口头判断靠谱 |
| 3 | **你的重复劳动就是它的自动化目标** — 把场景投稿进来，让更多人受益 |

### 附加信息

- 仓库：`https://github.com/jqrpfqffss/agent_workbench.git`
- 文档入口：`agent_workbench/README.md`
- 配置文件：`agent_workbench/agent_workbench.yaml`
- 场景投稿：GitHub Issues / `scenario_inbox.md` / 群接龙

### 讲稿

> 三句话收尾。
>
> 第一，agent_workbench 是手脚，AI 是大脑。它帮你完成代码之后的全部后半程。
> 第二，结论看 evidence。build.log、transcript、summary 比"我觉得没问题"靠谱。
> 第三，你每天重复最多的手动操作，就是它下一个要自动化的事情。
>
> 谢谢大家，欢迎提问。

### 视觉建议

- 三个大数字 1/2/3，每个配一句话
- 下方仓库/文档链接
- 深色背景，和封面呼应
- 最底部："Q&A"

---

## 附录：版式建议

| 元素 | 建议 |
|------|------|
| 封面/结尾 | 深色背景 + 白字 |
| 背景/场景页 | "以前"灰/红色调，"现在"蓝/绿色调 |
| 架构页 | 浅底深字，三层用不同色带区分 |
| 案例页 | Before/After 双栏 |
| 命令/路径/文件名 | 等宽字体 |
| 中文字体 | 微软雅黑 / 思源黑体 |
| 每页最多 | 3-4 个关键点 |

## 附录：时间分配

| 优先级 | 页面 | 时长 |
|--------|------|------|
| ★★★ | Slide 2（背景痛点） | 1.5 min |
| ★★★ | Slide 3（使用场景） | 2 min |
| ★★★ | Slide 4-5（整体介绍+架构） | 3 min |
| ★★ | Slide 6（5步上手） | 1 min |
| ★★★ | Slide 7-8（案例） | 4 min |
| ★★★ | Slide 9（征集场景） | 2 min |
| ★ | 其他 | 1.5 min |
| | **合计** | **~15 min** |

如果只有 10 分钟，优先讲 Slide 2、3、4、7、9。
