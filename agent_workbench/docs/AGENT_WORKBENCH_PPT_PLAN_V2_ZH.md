# agent_workbench 使用介绍 PPT 内容规划 V2

> 面向对象：研发同事（嵌入式开发、测试、技术管理）  
> 建议时长：10–15 分钟  
> 总页数：13 页  
> 主叙事线：**痛点 → 使用场景 → 整体介绍 → 真实案例 → 征集新场景**  
> 核心目标：让听众理解 agent_workbench 解决什么问题、怎么用、为什么值得信任，并鼓励大家提出新的使用场景

---

## 页面速览

| # | 标题 | 作用 | 建议时长 |
|---|------|------|----------|
| 1 | 封面 | 主题 + 一句话定位 | 30s |
| 2 | 目录 | 让听众知道今天的节奏 | 30s |
| 3 | 背景：为什么需要 agent_workbench | 引出痛点，建立共鸣 | 1.5min |
| 4 | 使用场景全景图 | 让人快速对号入座 | 1.5min |
| 5 | 它到底是什么 | 定位：STM32 项目的自动化控制平面 | 1min |
| 6 | 整体架构：四层结构 | 配置 / CLI / 集成 / 证据 | 1.5min |
| 7 | 核心能力地图 | 命令分组速查 | 1min |
| 8 | 日常最小使用路径 | 5 步上手 | 1min |
| 9 | 案例 1：CLI 自动化回归闭环 | 已跑通的验证案例 | 1.5min |
| 10 | 案例 2：TIM3 LED 闪烁需求落地 | "加功能"类需求的全链路 | 1.5min |
| 11 | 案例 3：换 AI 前端只装一个包 | 体现"前端中立" | 1min |
| 12 | 征集使用场景 | 已知场景 + 投稿模板 + 号召 | 1.5min |
| 13 | 结尾 / Q&A | 总结 + 联系方式 | 1min |

---

## Slide 1 · 封面

### 标题

`agent_workbench：让 STM32 + AI 的研发流程可复用、可验证、可复盘`

### 副标题

`面向研发同事的使用介绍`

### 页面要点

- 一句话定位：**面向 STM32 项目的自动化控制平面**
- 不是某个 AI 前端的附属脚本，而是一个可插拔、可验证的工程底座

### 讲稿口播

> 大家好，今天给大家介绍一个我们在 STM32 开发流程中正在使用的工具——agent_workbench。
> 一句话概括：它是 STM32 项目的自动化控制平面，把构建、烧录、串口验证、AI 协作、结果留痕这些事情收敛到一个统一入口。
> 今天重点讲 4 件事：它解决什么问题、它能用在哪些场景、它内部怎么工作、以及真实跑通的案例长什么样。

### 视觉建议

- 深色背景 + 白色大标题
- 右下角放一个极简的"终端 + 芯片 + 文件"图标组合，暗示它连接的是完整工程链，不是单个工具
- 不需要复杂截图

---

## Slide 2 · 目录

### 标题

`今天聊什么`

### 页面要点

```
1. 背景：为什么需要 agent_workbench
2. 使用场景全景图
3. 整体介绍
   - 它到底是什么
   - 整体架构
   - 核心能力地图
   - 日常最小使用路径
4. 使用案例
   - CLI 自动化回归闭环
   - TIM3 LED 闪烁需求落地
   - 换 AI 前端只装一个包
5. 征集使用场景
```

### 讲稿口播

> 目录很直白：先说痛点，再看场景，然后从定位到架构到命令做一个整体介绍，接着通过 3 个真实案例看它是怎么跑的。
> 最后一页是今天最重要的——征集大家的使用场景，因为目前已知的场景还太少，没有发挥 agent_workbench 的能力。

### 视觉建议

- 左侧竖排目录列表，当前页对应序号高亮
- 右侧留白或放一个流程箭头示意

---

## Slide 3 · 背景：为什么需要 agent_workbench

### 标题

`日常研发，这些场景你一定遇到过`

### 页面要点（4 个痛点）

| 痛点 | 现场原话 | 后果 |
|------|----------|------|
| ① 命令入口分散 | "构建用 CMake、烧录用 OpenOCD、串口用 PuTTY，每次换机器都要重新记一遍" | 迁移机器和换人协作时命令容易失真 |
| ② 硬件参数靠口口相传 | "TIM1 的 Prescaler 是多少来着？上次谁改的？" | AI 凭记忆填硬件参数，错了很难发现 |
| ③ 验证停留在"看起来好了" | "我跑了一下感觉没问题" —— 但没有断言、没有 transcript、没有 evidence | 回头复盘时什么都对不上 |
| ④ 换 AI 前端要重新适配 | "我之前配的是 OpenCode，现在想试 Continue / Cursor / Cline，又得重写 prompt 和配置" | 同一套流程在不同前端重复维护 |

### 讲稿口播

> STM32 的研发场景和纯软件项目不一样。纯软件项目改完代码跑个 CI 就行了，但我们还得构建、烧录、连串口、看 CLI 反馈、判断结果。
>
> 先看第一个问题：命令入口太分散。构建用 CMake、烧录用 OpenOCD 或 STM32_Programmer_CLI、串口用 PuTTY 或 pyserial，每个人本地记一套命令，换机器的时候就得重来。
>
> 第二个问题：硬件参数。TIM1 的 Prescaler 是多少、PA8 对应哪个 Channel，这些东西经常是"口口相传"。如果你让 AI 帮你写代码，它更容易凭记忆猜——猜错了你还不一定马上发现。
>
> 第三个问题：验证太模糊。很多时候验证的结论是"我看了一下串口输出，感觉没问题"。但到底有没有看到 ready banner？help 命令输出了什么？这些都没有留痕。
>
> 第四个问题：你今天配好了 OpenCode 的 AGENTS.md 和 slash 命令，明天想换 Continue 或 Cursor，又得从头写一遍 prompt 和配置。
>
> agent_workbench 要解决的，就是这四个问题。

### 视觉建议

- 4 个痛点做成 2×2 卡片布局
- 每张卡片用 ❌ 图标 + 痛点标题 + 一句"现场原话"（带引号，像是研发说的话）
- 颜色偏暖色调（橙/红），暗示"问题"

---

## Slide 4 · 使用场景全景图

### 标题

`agent_workbench 能帮你做什么`

### 页面要点（6 个使用场景卡片）

| # | 场景名 | 一句话描述 | 典型触发方式 |
|---|--------|-----------|-------------|
| 1 | 新需求落地 | 把自然语言需求变成可执行的 plan → 编辑代码 → 构建 → UART 验证 | `plan "在 PA8 上加 1kHz PWM"` → `build` → `verify` |
| 2 | CLI 回归测试 | 用黑盒断言 + transcript 确保 CLI 命令未被破坏 | `verify current --task cli_automation_regression.yaml` |
| 3 | 硬件烟测 | 烧录后自动跑 UART 烟测，判断 ready banner / prompt / 命令响应 | `uart exec --reset-first --expect-ready --command help` |
| 4 | 接入新 AI 前端 | 一条命令给 OpenCode / Continue / Cursor 生成所有适配文件 | `integration install opencode` |
| 5 | 小上下文模型协作 | 为 7B/16k 本地模型切分阶段、生成 context pack、自动 resume | `context --profile qwen7b --stage analyze` |
| 6 | 失败复盘与 session 比较 | 用 evidence 回看这次 vs 上次的差异，不靠回忆 | `report --latest` / `compare` |

### 补充说明

> **以上只是目前已知的 6 个场景，第 12 页留给大家补充。**
> agent_workbench 的架构设计支持更多场景，但我们目前用得还不够多，很多能力还没发挥出来。

### 讲稿口播

> 先看全景图。目前我们已经在用的场景大概有 6 类。
>
> 第一类，"新需求落地"。比如老板说"给 PA8 加一个 1kHz PWM"，你可以用 `plan` 命令把自然语言变成可执行步骤，然后 `build`、`verify` 走一遍。
>
> 第二类，"CLI 回归测试"。我们的 STM32 上跑着一个文本 CLI，每次改代码后需要确认 help、status、LED 控制命令都还好使。agent_workbench 可以自动跑 10 条断言，输出 pass/fail。
>
> 第三类，"硬件烟测"。烧录完了，自动打开串口看 ready banner 和 prompt 是否出现。
>
> 第四类，"接入新 AI 前端"。你只需要 `integration install opencode` 一条命令，就能把 AGENTS.md、slash 命令、agent 配置全部生成好。想换 Continue 也是一条命令。
>
> 第五类，"小上下文模型协作"。如果你用的是 Qwen 7B 或 DeepSeek 16k 这种窗口不大的模型，agent_workbench 会把信息切分成 brief、facts、constraints、paste 这些紧凑产物，让模型一次只处理一个阶段。
>
> 第六类，"失败复盘"。跑完一轮后 evidence 目录里有 build.log、cli_transcript.log、session_summary.md，方便你回头看这次和上次有什么不同。
>
> 但是——这只是目前已知的 6 个场景。最后一页我会请大家补充，因为现在用到的场景确实还太少。

### 视觉建议

- 6 张卡片做成 3×2 网格
- 每张卡片用一个图标 + 场景名 + 一句话描述
- 底部加一行灰色小字："这只是已知场景，更多可能性等你来提"
- 颜色偏蓝/绿色调，暗示"我们能做什么"

---

## Slide 5 · 它到底是什么

### 标题

`agent_workbench = STM32 项目的自动化控制平面`

### 页面要点

- **单一事实来源**：`agent_workbench.yaml` —— 项目名、构建目录、串口、烧录方式、输出目录、模型 profile，全部集中描述
- **统一命令入口**：`agent_workbench.bat` —— 不管你要 doctor、plan、build、verify 还是接前端，都走同一个入口
- **核心能力与前端解耦**：`workbench.py` + `core/` 提供底层能力；OpenCode / Continue 只是装在上面的 integration
- **输出的不只是命令结果，还有可复盘的 evidence**：runtime/ 存当前产物，evidence/sessions/ 存会话证据

### 一句话口号

> **前端可替换，流程可复用，结论可验证。**

### 讲稿口播

> 那它到底是什么？一句话：**STM32 项目的自动化控制平面**。
>
> 首先，它把所有配置集中到一个文件——`agent_workbench.yaml`。项目名叫什么、构建目录在哪、串口是 COM 几、用哪种方式烧录、输出放哪个目录、AI 模型用什么 profile，全在一个地方。这意味着换机器、换人、换前端的时候，不需要到处找配置。
>
> 其次，它提供了统一命令入口。不管你要检查环境还是规划需求还是构建烧录还是验证，都是 `agent_workbench.bat xxx` 这一个入口。
>
> 第三，核心能力和前端是解耦的。`workbench.py` 和 `core/` 目录是底层引擎；OpenCode 只是一个 integration 包，Continue 也是一个 integration 包。以后支持 Cursor、Cline 也只需要加一个新包，不改核心代码。
>
> 最后，它输出的不只是命令返回值。每次跑过的 build.log、cli_transcript.log、session_summary.md、assertions.jsonl 都会留在 evidence 目录里。所以结论不是"我觉得好了"，而是"日志和断言证明了当前状态"。
>
> 用一句话总结：**前端可替换，流程可复用，结论可验证。**

### 视觉建议

- 页面上方：大字口号"前端可替换，流程可复用，结论可验证"
- 页面中部：左侧放 `agent_workbench.yaml` 截图（高亮 `project.name`、`build_dir`、`uart.port`、`uart.ready_banner`）
- 右侧放一个简图：一个 YAML 图标 → 一个 CLI 图标 → 多个前端图标分叉
- 底部：一行关键词 "单一配置源 | 统一 CLI 入口 | 前端中立 | evidence 驱动"

---

## Slide 6 · 整体架构：配置、CLI、集成、证据四层

### 标题

`四层架构：从配置到证据`

### 架构图

```
┌─────────────────────────────────────────────┐
│         agent_workbench.yaml                │
│         单一事实来源                         │
│  (项目 / 构建 / 串口 / 烧录 / 模型 profile)  │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│     workbench.py + core/                    │
│     统一 CLI 能力层                          │
│  doctor │ plan │ build │ flash │ uart │     │
│  verify │ context │ report │ test │ ...     │
└────┬──────────┬──────────────┬──────────────┘
     │          │              │
     ▼          ▼              ▼
┌─────────┐ ┌──────────┐ ┌──────────────────┐
│integra- │ │ runtime/ │ │evidence/sessions/│
│tions/   │ │当前运行   │ │会话证据          │
│opencode │ │产物       │ │可复盘记录        │
│continue │ │           │ │                  │
│cursor…  │ │           │ │                  │
└─────────┘ └──────────┘ └──────────────────┘
```

### 页面要点

- **第一层 · 配置层**：`agent_workbench.yaml` 是整个系统的"中央数据库"，所有能力都从这里取值
- **第二层 · CLI 能力层**：`workbench.py` + `core/` 提供 doctor / plan / build / flash / uart / verify / context / report 等命令
- **第三层 · 集成层**：`integrations/` 目录下每个前端一个包，自描述（manifest.yaml + 模板文件）
- **第四层 · 产物层**：
  - `runtime/`：当前运行临时产物（build.log、cli_transcript.log、direct_verify_summary.md…）
  - `evidence/sessions/`：每次会话的持久化证据（session_summary.md、assertions.jsonl、compare 报告…）

### 讲稿口播

> 这张图把 agent_workbench 分成四层。
>
> 最上面是配置层，就一个文件 `agent_workbench.yaml`，所有能力的参数都从这里来。你换机器只需要带走这个文件；换项目只需要改这个文件。
>
> 第二层是 CLI 能力层。`workbench.py` 和 `core/` 目录里是所有的核心逻辑：doctor 做环境自检，plan 做需求规划，build 做构建，flash 做烧录，uart 做串口交互，verify 做端到端验证，context 做上下文打包，report 做证据汇总。
>
> 第三层是集成层。OpenCode 是一个包，Continue 是一个包，将来 Cursor、Cline 各自也是一个包。每个包只需要一个 `manifest.yaml` 描述自己需要哪些模板文件，`install` 命令就能把它们渲染到项目里。
>
> 最下面是产物层。`runtime/` 放的是"这一次"的运行产物，跑完就会被下一次覆盖。`evidence/sessions/` 放的是"每一次"的持久化证据，可以回头翻。这就是为什么它的结论比"口头判断"更可信——因为有东西可以回放。

### 视觉建议

- 四层用垂直堆叠的方框表示，从上到下
- 每层用不同底色（配置层蓝色、CLI 层灰色、集成层绿色、产物层橙色）
- 箭头从上往下指
- 右侧可以放一个小表格，列出每层包含的关键文件/目录

---

## Slide 7 · 核心能力地图

### 标题

`4 类命令，覆盖从环境到证据`

### 页面要点

| 类别 | 命令 | 做什么 |
|------|------|--------|
| **环境与接入** | `doctor` | 检查工具链、配置、串口是否就绪 |
| | `integration install <name>` | 给 AI 前端生成项目级适配文件 |
| | `init-vscode` | 给 VS Code 生成 tasks.json |
| **开发与规划** | `scan-project` | 扫描项目结构，输出 JSON 摘要 |
| | `plan "<需求>"` | 自然语言需求 → 可执行步骤 + 硬件参数 |
| | `build` | 统一构建入口（CMake + 工具链） |
| **硬件与验证** | `flash` | 烧录 ELF（OpenOCD / STM32_Programmer_CLI） |
| | `reset` | 复位 MCU |
| | `uart exec` | 打开串口执行命令，检查 ready + prompt |
| | `verify current` | 端到端验证：doctor → build → test → uart |
| **证据与复盘** | `report --latest` | 输出本次运行的证据摘要 |
| | `context` | 为本地模型生成 brief / facts / paste / resume |
| | `test run` | 运行单元测试 |

### 讲稿口播

> 这张表把命令分成四类，方便你记忆。
>
> 第一类"环境与接入"——先确认环境能用，再把前端接进来。
> 第二类"开发与规划"——拿到需求后，扫描项目、生成 plan、然后构建。
> 第三类"硬件与验证"——烧录、复位、串口交互、端到端验证。
> 第四类"证据与复盘"——跑完后看报告、看证据、给模型打上下文包。
>
> 你不需要一次记住所有命令。先记住"先 doctor、再 plan、再 build、再 verify"这四步就够日常使用了。

### 视觉建议

- 四列表格，每列用不同颜色标识类别
- 或者做成 4 个卡片，每个卡片里列 3 条核心命令
- 命令名用等宽字体

---

## Slide 8 · 日常最小使用路径

### 标题

`第一次上手？记住这 5 步`

### 页面要点（流程图）

```
  ① doctor           ② integration install       ③ plan
  环境自检               前端接入                  需求规划
  ──────── ──→ ──────────────── ──→ ──────────── 
                                                    │
                                                    ▼
  ⑤ verify current                            ④ build
  端到端验证                                    统一构建
  ──────────────── ←── ──────────────────────────
```

### 5 步的命令和目的

| 步骤 | 命令 | 目的 |
|------|------|------|
| ① | `agent_workbench.bat doctor --json` | 确认工具链、配置、串口都 OK |
| ② | `agent_workbench.bat integration install opencode --json` | 给你常用的 AI 前端生成适配文件 |
| ③ | `agent_workbench.bat plan "add PWM on PA8, 1kHz, 50%" --json` | 把自然语言需求转成可执行 playbook |
| ④ | `agent_workbench.bat build --json` | 走统一构建入口 |
| ⑤ | `agent_workbench.bat verify current --task xxx.yaml --json` | 一条命令做完整验证闭环 |

### 讲稿口播

> 如果只记一个上手路径，就是这 5 步：
>
> 第一步 `doctor`——确认环境能用。工具链有没有装、YAML 配置对不对、串口能不能连，一条命令检查完。
>
> 第二步 `integration install`——把你的 AI 前端接进来。OpenCode 也好、Continue 也好，一条命令生成所有适配文件。
>
> 第三步 `plan`——拿到需求后不要直接写代码，先让 plan 帮你把需求拆成步骤、查硬件参数、列出要改哪些文件。
>
> 第四步 `build`——统一构建。不需要手动记 CMake 命令。
>
> 第五步 `verify current`——一条命令跑完 doctor + build + test + uart 烟测，输出 evidence。
>
> 对新人来说，先跑 ① 和 ⑤ 就能感受到它的价值。

### 视觉建议

- 做成水平箭头流程图，5 个圆角方框依次排列
- 每个方框内：步骤编号 + 命令名 + 一句话
- 底部加一行小字："对新人建议：先 ① doctor + ⑤ verify 就能感受到价值"

---

## Slide 9 · 案例 1：CLI 自动化回归闭环

### 标题

`案例 1：10 条断言、一条命令、一份 evidence`

### 场景描述

> 我们的 STM32 上跑着一个文本 CLI（USART2 @ 115200）。每次改动代码后，需要确认 CLI 的核心功能没被破坏：ready banner 正常输出、help 命令能列出所有命令、status 能报告 UART 和 LED 状态、LED 控制命令有正确的 ack 响应。

### 任务定义（来自 `tasks/cli_automation_regression.yaml`）

```yaml
id: cli_automation_regression
mode: feature
goal: Keep the USART2 text CLI command-driven, automation-friendly,
      and safe for repeated debug sessions.

acceptance:
  blackbox:
    - name: cli_ready_banner_seen        # 看到 "STM32 UART CLI ready."
    - name: cli_prompt_seen              # 看到 "cli>"
    - name: cli_has_no_timeout           # 没有超时
    - name: cli_help_lists_commands      # help 输出 "Available commands:"
    - name: cli_status_reports_uart      # status 报告 UART 信息
    - name: cli_status_reports_led       # status 报告 LED 状态
    - name: cli_red_ack                  # "red on"  → "[ok] red -> on"
    - name: cli_green_ack               # "green off" → "[ok] green -> off"
    - name: cli_blue_ack                # "blue toggle" → "[ok] blue -> toggle"
    - name: cli_all_off_ack             # "all off"  → "[ok] all -> off"

verify:
  sequence: [doctor, build, test, debug]
  cli_commands: [help, status, red on, green off, blue toggle, all off]
```

### 执行只需一条命令

```powershell
cmd /c ".\agent_workbench.bat verify current --task agent_workbench/tasks/cli_automation_regression.yaml --json"
```

### 输出的 evidence

- `session_summary.md`：verdict = **pass**，assertions = **pass=10, fail=0, skip=0**
- `cli_transcript.log`：完整的串口交互记录
- `assertions.jsonl`：每条断言的详细判定（name / type / needle / result）
- `build.log`：构建过程

### 讲稿口播

> 第一个案例是"CLI 自动化回归"。
>
> 我们的 STM32 上有一个文本 CLI，支持 help、status、红绿蓝 LED 控制等命令。每次改代码后要确认这些命令没被破坏。
>
> 以前怎么验？打开 PuTTY，手动输几条命令，看输出"像是对的"就算过了。问题是——没有留痕，没有标准，换个人就得重来。
>
> 现在怎么验？写一份 YAML 任务文件，定义 10 条黑盒断言：banner 出不出现、prompt 出不出现、help 输出里有没有 "Available commands"、red on 之后有没有 "[ok] red -> on"……
>
> 然后一条命令：`verify current --task cli_automation_regression.yaml`。它会自动跑 doctor → build → test → uart，最后输出 session_summary.md。
>
> 结果是：assertions = pass=10, fail=0, skip=0。这个结论不是 AI 说的，是 10 条断言在串口 transcript 里逐条匹配出来的。

### 视觉建议

- 左侧：YAML 任务定义截图（高亮 `acceptance.blackbox` 区块）
- 右侧：session_summary.md 截图（高亮 `verdict: pass`、`assertions: pass=10 fail=0 skip=0`）
- 中间一个箭头，标注"一条命令"
- 底部一行关键词："任务定义 → 自动执行 → 结构化 evidence"

---

## Slide 10 · 案例 2：TIM3 LED 闪烁需求落地

### 标题

`案例 2：从"加个 LED 闪烁"到 build + uart 验证`

### 场景描述

> 需求来了一句话："用 TIM3 让红色 LED 以 1Hz 频率闪烁"。以前你得自己查数据手册算 Prescaler 和 ARR，然后手动改 main.c 和中断文件，最后手动验证。

### 任务定义（来自 `tasks/timer_led_blink.yaml`）

```yaml
id: timer_led_blink
mode: feature
goal: Add a hardware timer (TIM3) that blinks the RED LED (PB0)
      at approximately 1 Hz using interrupt-driven toggling.

notes:
  - Use HSI clock (8 MHz) as timer source
  - Prescaler = 7999 (gives 1 kHz timer clock)
  - Auto-reload = 499 (gives 500ms period)
  # → 硬件参数不是靠记忆，是 plan 帮你查和算的

implementation:
  allowed_edits:
    - file: Core/Src/main.c
      changes: ["Add MX_TIM3_Init()", "Add HAL_TIM_Base_Start_IT()"]
    - file: Core/Src/stm32f1xx_it.c
      changes: ["Add TIM3_IRQHandler()", "Add HAL_TIM_PeriodElapsedCallback()"]
    - file: Core/Inc/main.h
      changes: ["Add extern htim3 declaration"]

verify:
  sequence: [doctor, build, uart_smoke]
  cli_commands: [help, status]
```

### 全链路

```
自然语言需求
  "用 TIM3 让红色 LED 以 1Hz 闪烁"
      │
      ▼
plan 命令解析
  → Prescaler = 7999, ARR = 499, Clock = HSI 8MHz
  → 需要编辑 main.c + stm32f1xx_it.c + main.h
      │
      ▼
按 plan 编辑代码（3 个文件）
      │
      ▼
build → 编译通过
      │
      ▼
verify → doctor ✓ / build ✓ / uart_smoke ✓
```

### 讲稿口播

> 第二个案例是"加功能"类需求。
>
> 需求就一句话："用 TIM3 让红色 LED 以 1Hz 频率闪烁"。以前你得自己去查手册：HSI 时钟 8MHz、Prescaler 设 7999 就得到 1kHz 的 timer clock、ARR 设 499 就得到 500ms 的中断周期。这些数字对不对？万一记错了呢？
>
> 现在 `plan` 命令会帮你做这件事。它从硬件知识库里查，输出 Prescaler=7999、ARR=499，并且告诉你需要改 main.c 里加 MX_TIM3_Init()、stm32f1xx_it.c 里加中断处理、main.h 里加 extern 声明。
>
> 改完之后 `build` 编译通过，`verify` 的 uart_smoke 确认 CLI 仍然响应——说明加功能没破坏已有功能。
>
> 这个案例的重点是：**硬件参数不靠记忆，plan 帮你查和算。**

### 视觉建议

- 纵向流程图：需求 → plan 解析（highlight Prescaler/ARR/Clock） → 代码编辑 → build → verify
- 右侧边栏：放 YAML 任务定义的 `notes` 部分截图
- 用绿色 ✓ 标记每个通过的步骤

---

## Slide 11 · 案例 3：换 AI 前端只装一个包

### 标题

`案例 3：前端可替换，一条命令搞定`

### 场景描述

> 你之前一直用 OpenCode 做 AI 辅助开发，现在想试试 Continue。以前要重新写 prompt、适配配置文件。现在？

### 对比演示

| 操作 | OpenCode | Continue |
|------|----------|----------|
| 安装 | `integration install opencode --json` | `integration install continue --json` |
| 检查 | `integration check opencode --json` | `integration check continue --json` |
| 卸载 | `integration remove opencode --json` | `integration remove continue --json` |
| 配置来源 | 同一个 `agent_workbench.yaml` | 同一个 `agent_workbench.yaml` |
| 模板变量 | `{project_name}`, `{ready_banner}`, `{prompt}`… | 同一套变量 |
| 核心 CLI | 完全不变 | 完全不变 |

### Integration 包的目录结构

```
agent_workbench/integrations/
├── opencode/
│   ├── manifest.yaml      # 声明需要生成哪些文件
│   ├── README_ZH.md       # 使用说明
│   └── files/             # 模板文件（AGENTS.md.tpl, slash commands…）
│
├── continue/
│   ├── manifest.yaml
│   ├── README_ZH.md
│   └── files/
│
└── cursor/                # 将来：只需要新建这个目录
    ├── manifest.yaml
    ├── README_ZH.md
    └── files/
```

### 讲稿口播

> 第三个案例讲"前端中立"。
>
> 假设你一直用 OpenCode，今天想试 Continue。以前你得重新写 prompt 模板、适配规则文件，可能花半天。现在只需要一条命令：`integration install continue`。它会用同一个 `agent_workbench.yaml` 里的变量，渲染 Continue 自己的模板，生成对应的配置文件。
>
> 回到 OpenCode？再 `integration install opencode`。想两个都留着？也可以。
>
> 那如果将来要支持 Cursor 或 Cline 怎么办？在 `integrations/` 下面新建一个目录，写一个 `manifest.yaml`，放几个模板文件。核心代码不需要动一行 Python。
>
> 这就是"前端可替换"的意义：**你在选 AI 工具的时候不用担心 agent_workbench 层面要重头适配。**

### 视觉建议

- 上半部分：两栏对比表（OpenCode vs Continue），关键信息一模一样
- 下半部分：目录树结构图，highlight `manifest.yaml`
- 底部：一句话"新增前端 = 新增一个目录，不改核心代码"

---

## Slide 12 · 征集使用场景（重点页）

### 标题

`你的场景是什么？`

### 上半部分：已知场景回顾（缩略版）

```
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ ① 新需求落地│ │ ② CLI 回归  │ │ ③ 硬件烟测  │
│   plan→     │ │   verify→   │ │   uart exec→│
│   build→    │ │   evidence  │ │   ready     │
│   verify    │ │             │ │   banner    │
└─────────────┘ └─────────────┘ └─────────────┘
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ ④ 接入新    │ │ ⑤ 小模型    │ │ ⑥ 失败复盘  │
│   AI 前端   │ │   协作      │ │   session   │
│   integration│ │   context   │ │   compare   │
│   install   │ │   pack      │ │             │
└─────────────┘ └─────────────┘ └─────────────┘
```

### 下半部分：投稿模板（3 张空白卡片）

> **我们目前用到的场景还是太少了，agent_workbench 有很多能力还没发挥出来。**
> 希望大家根据自己日常研发中的实际痛点，提出新的使用场景。

**投稿模板：**

```
场景名称：________________________
我现在的痛点是：________________________
我希望 agent_workbench 能：________________________
我可以提供的输入：
  □ 任务 YAML      □ 期望产物      □ 已有脚本      □ 需求描述
我对验收的判断标准：________________________
```

### 一些灵感方向

| 方向 | 可能的场景 |
|------|-----------|
| ADC 采集 | 自动配置 ADC Channel + DMA，plan 查引脚映射和采样率参数 |
| PWM 控制 | 自动推算 Prescaler / ARR / CCR，验证波形频率 |
| 多 UART 管理 | 一个口做 CLI 调试，一个口做协议通信，agent_workbench 管两路 |
| OTA 升级流程 | 构建 → 烧录 → 验证 → 推送固件版本号 |
| 功耗测试 | 进入低功耗模式 → 用 monitor 采集电流 → 输出功耗报告 |
| 自定义协议解析 | 用 diag_uart 发原始 hex → 解析应答帧 → 断言字段值 |
| CI/CD 集成 | 把 verify 接入 Jenkins / GitHub Actions，自动触发硬件验证 |

### 投稿方式

> 选择你最方便的方式：
> - **GitHub Issue**：到仓库 Issues 页面，使用"新场景投稿"模板提交
> - **仓库 PR**：在 `agent_workbench/docs/scenario_inbox.md` 里追加你的场景
> - **内部群接龙**：直接在群里按上面的模板格式发消息
> - **找我聊**：直接找我当面说也行，我帮你写成任务 YAML

### Call-to-Action

> **现在用得最少的不是 agent_workbench 的能力，而是我们的想象力。**
> **你的下一个需求，也许就是 agent_workbench 的下一个最佳实践。**

### 讲稿口播

> 这是今天最重要的一页。
>
> 上面 6 个场景是我们目前已知的、已经在用的。但说实话，它们只用到了 agent_workbench 能力的一小部分。
>
> 比如 ADC 采集——能不能用 plan 自动查引脚映射和采样率，然后 verify 去验证采集结果？
> 比如 OTA 升级——能不能把"构建 → 烧录 → 验证 → 推版本号"做成一条 verify 流水线？
> 比如自定义协议——能不能用 diag_uart 发原始 hex 帧，然后断言应答帧的特定字段？
>
> 这些是我想到的一些方向，但我最期待的是你们的方向。因为你们每天面对的项目和场景比我了解的多得多。
>
> 投稿方式很灵活：GitHub Issue、PR、群里接龙、或者直接找我聊都行。只需要告诉我：场景名是什么、你的痛点是什么、你希望 agent_workbench 帮你做什么、你觉得验收标准是什么。
>
> 一句话总结：**现在用得最少的不是 agent_workbench 的能力，而是我们的想象力。**

### 视觉建议

- 上半：6 张已知场景缩略卡片（小字，半透明，表示"这些已有"）
- 下半：3 张空白卡片 + 投稿模板文字（大字，高亮，表示"这些等你来填"）
- 最底部：call-to-action 一句话，加粗居中
- 整体色调偏暖（橙/黄），表示"邀请"和"开放"

---

## Slide 13 · 结尾 / Q&A

### 标题

`三句话总结`

### 页面要点

1. **如果只记一件事**：`agent_workbench` 不是某个 AI 前端的附属脚本，而是 STM32 项目的自动化控制平面。
2. **如果只记一个上手动作**：先跑 `doctor`，再通过统一 CLI 去接入、规划、构建和验证。
3. **如果只记一个判断标准**：最终结论要看 evidence，而不是看模型说了什么。

### 附加信息

- 仓库地址：`https://github.com/jqrpfqffss/agent_workbench.git`
- 文档入口：`agent_workbench/README.md`
- 配置文件：`agent_workbench/agent_workbench.yaml`
- 投稿入口：`GitHub Issues` / `agent_workbench/docs/scenario_inbox.md` / 群接龙

### 讲稿口播

> 最后三句话收尾。
>
> 第一，记住它的定位：自动化控制平面，不是某个前端的私有脚本。
> 第二，第一次上手就从 `doctor` 开始。
> 第三，结论要看 evidence——build.log、cli_transcript.log、session_summary.md——而不是看 AI 的口头判断。
>
> 谢谢大家，有问题随时问。也欢迎大家把自己的使用场景投稿进来，让 agent_workbench 变得更有用。

### 视觉建议

- 上方三个大数字 1 / 2 / 3，每个配一句话
- 下方放仓库/文档/投稿链接
- 背景延续封面色调
- 最底部：**Q&A** 大字

---

## 附录 A：版式与字体建议

| 元素 | 建议 |
|------|------|
| 封面 / 结尾 / 架构页 | 深色背景（深蓝/深灰） + 白色文字 |
| 案例页 / 命令页 / 证据页 | 浅底深字，方便投屏阅读 |
| 命令、路径、文件名 | 等宽字体（Consolas / Fira Code） |
| 每页正文 | 最多 3–4 个关键点，详细信息留给讲稿 |
| 截图 | 尽量只截关键区块，不截全文件；用高亮框标注重点行 |

## 附录 B：讲解时间分配建议

| 重要度 | 页面 | 累计 |
|--------|------|------|
| ★★★ | Slide 3（背景）+ Slide 4（场景）| 3 min |
| ★★★ | Slide 5–6（定位 + 架构）| 2.5 min |
| ★★ | Slide 7–8（能力 + 路径）| 2 min |
| ★★★ | Slide 9–11（3 个案例）| 4 min |
| ★★★ | Slide 12（征集场景）| 1.5 min |
| ★ | 其他（封面/目录/结尾）| 2 min |
| | **合计** | **~15 min** |

如果时间只有 10 分钟，优先讲 Slide 3、4、5、9、12。

## 附录 C：与 V1 讲稿的主要差异

| 维度 | V1（`AGENT_WORKBENCH_PPT_SCRIPT_ZH.md`）| V2（本文档） |
|------|----------------------------------------|-------------|
| 叙事起点 | 直接讲架构 | 先讲痛点和场景 |
| 使用场景 | 没有单独列出 | 第 4 页专门做全景图 |
| 案例数量 | 1 个（CLI 回归） | 3 个（CLI 回归 / TIM3 闪烁 / 换前端） |
| 征集场景 | 无 | 第 12 页专题页 + 投稿模板 + 灵感方向 |
| AI 友好性讲解 | 占 1 页（context 产物） | 并入"场景⑤小模型协作"展开讲 |
| 总页数 | 8 页 | 13 页 |
| 目标时长 | 5–10 min | 10–15 min |
