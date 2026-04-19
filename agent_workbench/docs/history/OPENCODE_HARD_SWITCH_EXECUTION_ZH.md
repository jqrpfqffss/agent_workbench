# OpenCode 硬切换执行清单（路线 A）

> 本清单是给"新会话"一次性执行的精确操作手册。
> 目标：**删除所有 Continue 相关代码，全面切换到 OpenCode**。
> 执行原则：**严格按顺序，不要跳步骤**。

---

## 给新会话的开场白模板（请整份复制）

```
请严格按照 agent_workbench/OPENCODE_HARD_SWITCH_EXECUTION_ZH.md 文档执行硬切换，
路线 A（完全弃用 Continue，只保留 OpenCode）。执行原则：
1. 按阶段顺序执行，每完成一个阶段跑一次测试。
2. 遇到 SEARCH/REPLACE 对不上时，先 read_file 重新读取实际内容再做。
3. 执行到阶段 5 删除旧文件前，先把所有阶段 1-4 的改动提交 git 快照。
4. 最后阶段 6 用 opencode 在终端里做人工冒烟验证。
```

---

## 阶段总览（建议按顺序）

| 阶段 | 任务 | 风险 |
|------|------|------|
| 阶段 1 | 创建所有 OpenCode 模板文件（新增，不删东西） | 低 |
| 阶段 2 | 重构 Python 代码：continue → opencode | 中 |
| 阶段 3 | 更新 `agent_workbench.yaml` 配置 | 低 |
| 阶段 4 | 更新测试文件 | 中 |
| 阶段 5 | 删除 Continue 遗留（模板、文档、生成物） | 高（不可回滚） |
| 阶段 6 | 验收：doctor + init-opencode-agents + opencode 实跑 | 低 |

---

## 阶段 1：创建 OpenCode 模板文件

### 1.1 创建目录结构

需要创建这些目录（用 write_to_file 自动创建）：
- `agent_workbench/templates/opencode_agents/`
- `agent_workbench/templates/opencode_agents/agent/`
- `agent_workbench/templates/opencode_agents/command/`
- `agent_workbench/templates/opencode_agents/model_profiles/`

### 1.2 创建 `agent_workbench/templates/opencode_agents/AGENTS.md.tpl`

```markdown
# STM32 Agent Workbench — OpenCode 主指令

> 本文件由 `agent_workbench.bat init-opencode-agents` 自动生成。手改会在下次重新生成时被覆盖。

## 项目绑定信息
- 项目名称: {project_name}
- 构建目录: {build_dir}
- 主要源码目录: {source_dirs_csv}
- UART CLI 串口: {uart_port}
- 诊断串口: {diag_uart_port}
- Ready banner: `{ready_banner}`
- Prompt: `{prompt}`
- 默认本地模型 profile: {default_profile}

## 你是谁
你是这个 STM32 工程的自动化开发助手。用户会给你一句自然语言需求（如"给 PA8 加一个 1kHz PWM，占空比 50%"），你负责完成：
1. 需求拆解 → 生成执行计划
2. 代码编辑 / 新增
3. 编译 / 烧录
4. UART CLI 验证
5. 输出完整证据报告

## 绝对铁律（违反即失败）

1. **不要臆测硬件参数**：TIM Prescaler / Period / CCR、GPIO Mode、ADC Channel 一律**通过工具查询**，禁止凭记忆填值。
2. **不要捏造命令输出**：所有 shell 命令必须通过 OpenCode 的 shell 工具执行；禁止编造"执行完成"之类的假输出。
3. **Windows PowerShell 语法**：一次只运行一条命令，不要用 `;` 或 `&&` 串联。路径用反斜杠时外层要加双引号。
4. **所有 workbench 命令都加 `--json`**：输出 JSON 比纯文本更可靠。
5. **烧录前必须征得用户同意**：flash / reset 是硬件动作，不能自行触发。

## 核心工作流（对每一个需求都按这个顺序走）

### 第 1 步：环境自检

```
cmd /c ".\agent_workbench.bat doctor --json"
```

读取返回 JSON 的 `fail_count`：
- `fail_count > 0`：停下来，把具体 fail 项报告给用户，等用户修完再继续
- `fail_count == 0`：进入第 2 步

### 第 2 步：生成执行计划

```
cmd /c ".\agent_workbench.bat plan ""<用户原话>"" --json"
```

解析返回 JSON 的：
- `parameter_extractions`：识别到的参数（如 pin=PA8, freq=1kHz）
- `hardware_context`：对应的 TIM/GPIO 方案
- `steps`：按顺序列出的 read/edit/shell 步骤

把 plan 的**摘要**（不是全文 JSON）回报给用户：
```
识别到：PA8 引脚、1kHz 频率、50% 占空比
硬件方案：TIM1_CH1（主频 72MHz → Prescaler=71, Period=999, CCR=500）
计划步骤：6 步（read 2 / edit 3 / shell 1）
是否开始执行？
```

### 第 3 步：按 plan.steps 执行

用 OpenCode 的对应工具依次执行：
- `read` 步骤 → 用 OpenCode 的 `read` 工具
- `edit` 步骤 → 用 OpenCode 的 `edit` 或 `write` 工具
- `shell` 步骤 → 用 OpenCode 的 `bash` / `shell` 工具
  - Windows 下所有 shell 命令都用 `cmd /c ".\agent_workbench.bat xxx --json"`

### 第 4 步：编译

```
cmd /c ".\agent_workbench.bat build --json"
```

- `exit_code == 0`：进入第 5 步
- `exit_code != 0`：

```
cmd /c ".\agent_workbench.bat fix-build --json"
```

读取返回的 `fixes` 数组（每项含 file / line / suggested_change），按建议修正后重新 build。
连续 3 次 fix-build 仍失败 → 停下来汇报给用户。

### 第 5 步：烧录（征得用户同意后）

```
cmd /c ".\agent_workbench.bat flash --method openocd_cmd --json"
```

### 第 6 步：UART CLI 烟测

```
cmd /c ".\agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --json"
```

检查返回 JSON 的 `transcript`：
- 必须包含 ready banner: `{ready_banner}`
- 必须包含 prompt: `{prompt}`
- `help` 和 `status` 命令必须有合理响应

### 第 7 步：输出最终报告

把本次会话的以下证据汇总给用户：
- 修改的文件列表
- build 日志片段（成功/失败关键行）
- UART transcript 前 50 行
- 硬件参数（Prescaler / Period / CCR 等）的来源（用了哪个 plan.hardware_context 条目）

---

## 可用 sub-agent（见 `.opencode/agent/`）

- `@code_planner`: 把 plan 转成具体代码修改
- `@hardware_verifier`: 烧录和 UART 验证专用
- `@weak_model`: 检测到自己是小上下文模型时启用

## 可用 slash 命令（见 `.opencode/command/`）

- `/plan-stm32 <需求>`: 只生成 plan 不执行
- `/verify`: 运行完整 doctor + build + uart 烟测
- `/fix-build`: 只读 build.log 生成修复建议
- `/uart-smoke`: 单独做 UART CLI 烟测
- `/flash-reset`: 只做烧录 + 复位

## 工具使用速查

| 目的 | OpenCode 工具 | 示例 |
|-----|-------------|------|
| 读文件 | `read` | `read("Core/Src/main.c")` |
| 改文件 | `edit` | `edit("Core/Src/main.c", old, new)` |
| 新建文件 | `write` | `write("Core/Inc/new.h", content)` |
| 搜代码 | `grep` | `grep("HAL_TIM_Init", "Core")` |
| 列目录 | `list` | `list("Core/Src")` |
| 跑命令 | `bash` | `bash('cmd /c ".\\agent_workbench.bat doctor --json"')` |

## 失败时的优先级

1. 硬件动作失败（flash/reset/uart 烟测） → 立刻停下来汇报，不要自动重试超过 1 次
2. 编译失败 → 走 fix-build 流程，最多 3 轮
3. plan 解析失败 → 把用户原话更具体再调一次 plan
4. 文件读写失败 → 检查路径是否包含中文/空格，用绝对路径重试

---

(模板结束)
```

**注意：** 这个文件里的变量 `{project_name}`、`{ready_banner}` 等会在 `write_opencode_agents()` 函数里用 Python 渲染。

### 1.3 创建 `agent_workbench/templates/opencode_agents/agent/stm32_auto.md.tpl`

```markdown
---
description: STM32 主 agent，负责端到端需求落地
---

# STM32 主 Agent

这是默认的主 agent。行为定义全部在 `AGENTS.md` 里，本文件只做激活标记。

如果 OpenCode 需要在一个会话里显式切换到本 agent，用户输入：

```
@stm32_auto 给 PA8 加 1kHz PWM
```

即进入本 agent 上下文。
```

### 1.4 创建 `agent_workbench/templates/opencode_agents/agent/weak_model.md.tpl`

```markdown
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
```

### 1.5 创建 `agent_workbench/templates/opencode_agents/agent/code_planner.md.tpl`

```markdown
---
description: 专注把 plan 转成代码修改的 sub-agent
---

# 代码规划 Sub-Agent

当主 agent 调用 `@code_planner <plan JSON>` 时，你负责把 plan 的 steps 转成具体的 edit/write 操作。

## 输入
- 一份完整的 plan JSON（来自 `agent_workbench.bat plan`）

## 输出
- 一组精确的文件编辑动作（edit/write）
- 每个动作都要标注：`来源: plan.steps[N]`

## 规则
1. 不要编造 `plan.hardware_context` 之外的硬件参数
2. 每次 edit 前都要先 read 对应文件片段确认上下文
3. `User Code` 区域（STM32CubeMX 生成的 `/* USER CODE BEGIN ... */` 块）才是允许修改的地方
4. 禁止动 `Drivers/`、`build/`、`Debug/` 目录下任何文件

## 完成后把控制权交还主 agent：
```
已完成 N 处代码修改，交回主 agent 继续 build + flash + verify 流程。
```
```

### 1.6 创建 `agent_workbench/templates/opencode_agents/agent/hardware_verifier.md.tpl`

```markdown
---
description: 硬件验证 sub-agent（烧录、复位、UART 烟测）
---

# 硬件验证 Sub-Agent

当主 agent 调用 `@hardware_verifier` 时，你负责烧录、复位、UART CLI 验证。

## 执行顺序

1. 向用户确认"是否烧录"（除非用户已经预先授权）
2. `cmd /c ".\agent_workbench.bat flash --method openocd_cmd --json"`
3. 检查 flash 返回 JSON 的 `exit_code == 0`
4. `cmd /c ".\agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --json"`
5. 检查 transcript 包含 `{ready_banner}` 和 `{prompt}`
6. 对本次新增的功能命令做针对性烟测（如新加了 `pwm_on` 命令，就加上 `--command pwm_on`）

## 证据汇总

结束时输出：
```
flash: exit=0
reset: ok
ready banner: 首次出现于 transcript 第 N 行
prompt count: K 次
命令响应:
  - help: ok (Y 行响应)
  - status: ok (Y 行响应)
  - <新命令>: ok / fail
```

## 失败处理

- flash 失败 → 立刻停下来汇报，不要重试超过 1 次
- 未见 ready banner → 检查 startup_drain_sec 设置，汇报给用户
- UART CLI 超时 → `cmd /c ".\agent_workbench.bat uart console"` 让用户手动观察
```

### 1.7 创建 `agent_workbench/templates/opencode_agents/command/plan-stm32.md.tpl`

```markdown
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
```

### 1.8 创建 `agent_workbench/templates/opencode_agents/command/verify.md.tpl`

```markdown
---
description: 运行完整 STM32 验证流程（doctor + build + flash + uart 烟测）
---

# /verify 命令

顺序执行以下步骤，任意一步失败立即停下并汇报：

## Step 1: doctor
```
cmd /c ".\agent_workbench.bat doctor --json"
```
- `fail_count > 0` → 停下来列出所有 fail 项

## Step 2: build
```
cmd /c ".\agent_workbench.bat build --json"
```
- `exit_code != 0` → 调 `/fix-build`

## Step 3: 征询烧录
询问用户："是否烧录并做 UART 烟测？(yes/no)"

## Step 4: flash（用户同意后）
```
cmd /c ".\agent_workbench.bat flash --method openocd_cmd --json"
```

## Step 5: uart smoke
```
cmd /c ".\agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --json"
```
- transcript 必须含 `{ready_banner}` 和 `{prompt}`

## Step 6: 报告
输出合并摘要：
```
/verify 完成:
  doctor: ok (N 项检查通过)
  build: ok (elf size=KB)
  flash: ok
  uart: ok (ready banner 第 L 行出现, prompt K 次)
```
```

### 1.9 创建 `agent_workbench/templates/opencode_agents/command/fix-build.md.tpl`

```markdown
---
description: 读取最新 build.log 并生成修复建议
---

# /fix-build 命令

当用户输入 `/fix-build` 时：

1. 运行:
   ```
   cmd /c ".\agent_workbench.bat fix-build --json"
   ```

2. 读取返回 JSON 的 `fixes` 数组，每项含：
   - `file`: 错误文件路径
   - `line`: 错误行号
   - `message`: 原始错误信息
   - `suggested_change`: 建议修改

3. 按行把建议展示给用户：
   ```
   发现 3 处编译错误:

   [1] Core/Src/main.c:112
       错误: 'htim1' undeclared
       建议: 在 Core/Src/main.c 顶部加 `extern TIM_HandleTypeDef htim1;`

   [2] ...
   ```

4. 询问："是否自动应用所有建议？(yes/select/no)"

5. `yes`: 用 edit 工具依次应用；每次 edit 后立刻 `build --json` 看是否减少错误
   `select`: 让用户选择应用哪几项
   `no`: 停下来

6. 全部应用后重新 build，如果还有错误递归调用 /fix-build，最多 3 轮
```

### 1.10 创建 `agent_workbench/templates/opencode_agents/command/uart-smoke.md.tpl`

```markdown
---
description: 只做 UART CLI 烟测（不编译不烧录）
---

# /uart-smoke 命令

运行:
```
cmd /c ".\agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --json"
```

检查返回 JSON 的 `transcript` 字段：
- [必须] 包含 ready banner: `{ready_banner}`
- [必须] 包含 prompt: `{prompt}`
- [必须] 每条 `--command` 都有非空响应

把 transcript 的前 30 行 + 最后 10 行贴给用户，并给出一行结论：
```
UART CLI 烟测: ok / fail
```
```

### 1.11 创建 `agent_workbench/templates/opencode_agents/command/flash-reset.md.tpl`

```markdown
---
description: 烧录并复位硬件（不跑测试）
---

# /flash-reset 命令

1. 先确认 build 产物存在:
   ```
   cmd /c ".\agent_workbench.bat doctor --json"
   ```
   检查 `artifact_elf` 检查项是 ok。

2. 征询用户: "即将烧录 {project_name}，是否继续？(yes/no)"

3. 用户同意后:
   ```
   cmd /c ".\agent_workbench.bat flash --method openocd_cmd --json"
   ```

4. 检查返回 JSON 的 `exit_code`:
   - 0: 成功，输出"flash ok, reset 完成"
   - 非 0: 列出 stderr 末尾 20 行并停下
```

### 1.12 创建 `agent_workbench/templates/opencode_agents/opencode.json.tpl`

```json
{
  "$schema": "https://opencode.ai/config.json",
  "$generated": "by agent_workbench.bat init-opencode-agents",
  "theme": "opencode",
  "autoshare": false,
  "autoupdate": true,
  "instructions": [
    "AGENTS.md",
    ".opencode/agent/stm32_auto.md",
    ".opencode/agent/weak_model.md"
  ]
}
```

### 1.13 创建 `agent_workbench/templates/opencode_agents/model_profiles/deepseek_r1.md.tpl`

```markdown
---
description: DeepSeek-R1 专用约束
model:
  - deepseek-r1
  - deepseek-reasoner
---

# DeepSeek-R1 专用补丁

DeepSeek-R1 是推理模型，特点是慢但精确。针对性约束：

1. **一次一步**：不要一轮给多个步骤的推理，每完成一个 workbench 命令就停下来等结果
2. **不要贴大段思考**：推理过程保留在内部，输出只要结论 + 下一步命令
3. **JSON 解析优先级最高**：所有判断基于 workbench 命令返回的 JSON，不基于文本推理
4. **Period 长度限制**：一次最多执行 3 步 plan.steps，然后汇报给用户
```

### 1.14 创建 `agent_workbench/templates/opencode_agents/model_profiles/glm.md.tpl`

```markdown
---
description: GLM-4 系列专用约束
model:
  - glm-4
  - glm-4-flash
  - glm-4-plus
---

# GLM 专用补丁

GLM-4 在中文指令理解上很好，但对 shell 命令语法敏感，针对性约束：

1. **中文输出**：所有对用户的回复用中文
2. **PowerShell 语法**：Windows 下命令必须用 `cmd /c "..."` 包起来
3. **一次一条**：禁止 `;` 和 `&&` 串联
4. **JSON 字段引用**：谈到返回值时明确写 `返回 JSON 的 .exit_code == 0`，不要简称
```

### 1.15 创建 `agent_workbench/templates/opencode_agents/model_profiles/qwen7b.md.tpl`

```markdown
---
description: Qwen-7B 专用约束（小模型）
model:
  - qwen2.5-7b-instruct
  - qwen3-7b
---

# Qwen-7B 专用补丁

Qwen-7B 是小模型，上下文受限，针对性约束：

1. **启用 weak_model agent 所有 10 条反例**
2. **每个文件最多读 200 行**：用 `read(path, offset, limit)` 分段
3. **不做代码重构**：只做"添加新功能"，不动现有代码结构
4. **plan.steps 严格按顺序**：禁止跳步，禁止合并步骤
5. **遇到不确定立刻停**：宁可多问用户，不要臆测
```

---

## 阶段 2：重构 Python 代码（continue → opencode）

### 2.1 改 `agent_workbench/core/config.py`

**需要做的替换（按顺序）：**

1. 找到 `"continue": {` 开头的默认配置段，整段替换为 `"opencode": { ... }`（字段见下面）
2. 找到 `raw["continue"]["rules_dir_path"] = ...` 这行，替换为 OpenCode 的路径解析块
3. 删除 `raw["outputs"]["continue_runtime_root_path"] = ...` 这行
4. 删除 `raw["prompts"]` 里的 `continue_*` prompt 字段

**新的 opencode 默认配置块（加到 _defaults() 返回的 dict 里，替换原 "continue": {...}）：**

```python
"opencode": {
    "agents_file": "AGENTS.md",
    "agents_dir": ".opencode/agent",
    "commands_dir": ".opencode/command",
    "project_config_file": "opencode.json",
    "agents_template_dir": "templates/opencode_agents",
    "required_agents": [
        "stm32_auto.md",
        "weak_model.md",
        "code_planner.md",
        "hardware_verifier.md",
    ],
    "required_commands": [
        "plan-stm32.md",
        "verify.md",
        "fix-build.md",
        "uart-smoke.md",
        "flash-reset.md",
    ],
    "model_profiles": {
        "deepseek_r1": {
            "profile_file": "model_profiles/deepseek_r1.md",
            "min_lines": 5,
        },
        "glm": {
            "profile_file": "model_profiles/glm.md",
            "min_lines": 5,
        },
        "qwen7b": {
            "profile_file": "model_profiles/qwen7b.md",
            "min_lines": 5,
        },
    },
    "also_install_global": False,
},
```

**新的路径解析块（替换原 continue 路径解析，在 _normalize_config 或类似函数里）：**

```python
# OpenCode 相关路径解析
oc = raw.setdefault("opencode", {})
oc["agents_file_path"] = _resolve(oc.get("agents_file", "AGENTS.md"), project_root)
oc["agents_dir_path"] = _resolve(oc.get("agents_dir", ".opencode/agent"), project_root)
oc["commands_dir_path"] = _resolve(oc.get("commands_dir", ".opencode/command"), project_root)
oc["project_config_file_path"] = _resolve(oc.get("project_config_file", "opencode.json"), project_root)
oc["agents_template_dir_path"] = _resolve(oc.get("agents_template_dir", "templates/opencode_agents"), workbench_root)
oc["model_profile_names"] = list((oc.get("model_profiles") or {}).keys())
```

### 2.2 改 `agent_workbench/core/vscode_service.py`

**完整重写这个文件**。新内容：

```python
from __future__ import annotations

import json
import os
from pathlib import Path

from .utils import ensure_dir, render_template


def _command_paths(cfg: dict) -> dict[str, str]:
    project_root = Path(cfg["project_root_path"])
    workbench_root = Path(cfg["agent_workbench_root_path"])
    example_task = workbench_root / "tasks" / "example_feature.yaml"
    cli_task = workbench_root / "tasks" / "cli_hardware_smoke.yaml"
    cli_regression_task = workbench_root / "tasks" / "cli_automation_regression.yaml"
    return {
        "wrapper": "agent_workbench.bat",
        "setup_target": os.path.relpath(workbench_root / "bin" / "setup.bat", project_root).replace("/", "\\"),
        "launcher_target": os.path.relpath(workbench_root / "bin" / "agent_workbench.bat", project_root).replace("/", "\\"),
        "example_task": os.path.relpath(example_task, project_root).replace("\\", "/"),
        "cli_task": os.path.relpath(cli_task, project_root).replace("\\", "/"),
        "cli_regression_task": os.path.relpath(cli_regression_task, project_root).replace("\\", "/"),
    }


def write_project_wrappers(cfg: dict) -> list[Path]:
    paths = _command_paths(cfg)
    project_root = Path(cfg["project_root_path"])
    generated: list[Path] = []
    wrapper_specs = {
        project_root / "agent_workbench.bat": paths["launcher_target"],
        project_root / "setup_workbench.bat": paths["setup_target"],
    }
    for output_path, target in wrapper_specs.items():
        output_path.write_text(
            "@echo off\n"
            "setlocal\n"
            f"call \"%~dp0{target}\" %*\n"
            "exit /b %ERRORLEVEL%\n",
            encoding="utf-8",
        )
        generated.append(output_path)
    return generated


def _ps_safe(command_text: str) -> str:
    return f'cmd /c ".\\{command_text}"'


def _render_values(cfg: dict) -> dict:
    return {
        "project_name": str(cfg["project"]["name"]),
        "ready_banner": str(cfg["uart"].get("ready_banner", "")),
        "prompt": str(cfg["uart"].get("prompt", "")),
        "uart_port": str(cfg["uart"].get("port", "")),
        "uart_baud": str(cfg["uart"].get("baudrate", "")),
        "diag_uart_port": str(cfg.get("diag_uart", {}).get("port", "")),
        "build_dir": str(cfg["project"].get("build_dir_path", "")),
        "default_profile": str(cfg.get("agent", {}).get("default_profile", "")),
        "source_dirs_csv": ", ".join(str(item) for item in cfg.get("project", {}).get("source_dirs", [])),
    }


def write_opencode_agents(cfg: dict) -> list[Path]:
    """生成 OpenCode 所需全部文件:
    - AGENTS.md (项目根)
    - .opencode/agent/*.md (sub-agents)
    - .opencode/command/*.md (slash commands)
    - opencode.json (项目配置)
    """
    opencode_cfg = cfg.get("opencode") or {}
    agents_file = Path(opencode_cfg["agents_file_path"])
    agents_dir = Path(opencode_cfg["agents_dir_path"])
    commands_dir = Path(opencode_cfg["commands_dir_path"])
    project_config_file = Path(opencode_cfg["project_config_file_path"])
    template_dir = Path(opencode_cfg["agents_template_dir_path"])

    ensure_dir(agents_file.parent)
    ensure_dir(agents_dir)
    ensure_dir(commands_dir)

    values = _render_values(cfg)
    generated: list[Path] = []

    # 1. 渲染 AGENTS.md
    agents_tpl = template_dir / "AGENTS.md.tpl"
    if agents_tpl.exists():
        agents_file.write_text(
            render_template(agents_tpl.read_text(encoding="utf-8"), values),
            encoding="utf-8",
        )
        generated.append(agents_file)

    # 2. 渲染 sub-agents
    for name in [str(x).strip() for x in opencode_cfg.get("required_agents", []) if str(x).strip()]:
        tpl_path = template_dir / "agent" / f"{name}.tpl"
        if not tpl_path.exists():
            tpl_path = template_dir / "agent" / name
            tpl_source = tpl_path if tpl_path.exists() else template_dir / "agent" / f"{name}.tpl"
        if not tpl_source.exists():
            raise FileNotFoundError(f"opencode agent template not found: {tpl_source}")
        target = agents_dir / name
        target.write_text(
            render_template(tpl_source.read_text(encoding="utf-8"), values),
            encoding="utf-8",
        )
        generated.append(target)

    # 3. 渲染 slash commands
    for name in [str(x).strip() for x in opencode_cfg.get("required_commands", []) if str(x).strip()]:
        tpl_source = template_dir / "command" / f"{name}.tpl"
        if not tpl_source.exists():
            tpl_source = template_dir / "command" / name
        if not tpl_source.exists():
            raise FileNotFoundError(f"opencode command template not found: {tpl_source}")
        target = commands_dir / name
        target.write_text(
            render_template(tpl_source.read_text(encoding="utf-8"), values),
            encoding="utf-8",
        )
        generated.append(target)

    # 4. 渲染 opencode.json
    project_config_tpl = template_dir / "opencode.json.tpl"
    if project_config_tpl.exists():
        project_config_file.write_text(
            render_template(project_config_tpl.read_text(encoding="utf-8"), values),
            encoding="utf-8",
        )
        generated.append(project_config_file)

    # 5. 渲染 model profiles（作为额外的 agent 文件）
    model_profiles = opencode_cfg.get("model_profiles") or {}
    for profile_name, meta in model_profiles.items():
        if not isinstance(meta, dict):
            continue
        profile_file = meta.get("profile_file")
        if not profile_file:
            continue
        tpl_source = template_dir / f"{profile_file}.tpl"
        if not tpl_source.exists():
            tpl_source = template_dir / profile_file
        if not tpl_source.exists():
            continue
        target = agents_dir / f"model_{profile_name}.md"
        target.write_text(
            render_template(tpl_source.read_text(encoding="utf-8"), values),
            encoding="utf-8",
        )
        generated.append(target)

    return generated


def write_vscode_tasks(cfg: dict) -> Path:
    tasks_path = Path(cfg["vscode"]["tasks_file_path"])
    ensure_dir(tasks_path.parent)
    paths = _command_paths(cfg)
    write_project_wrappers(cfg)
    wrapper = paths["wrapper"]
    example_task = paths["example_task"]
    cli_task = paths["cli_task"]
    cli_regression_task = paths["cli_regression_task"]
    payload = {
        "version": "2.0.0",
        "tasks": [
            {"label": "Agent Workbench: Setup", "type": "shell", "command": _ps_safe("setup_workbench.bat"), "problemMatcher": []},
            {"label": "Agent Workbench: Doctor", "type": "shell", "command": _ps_safe(f"{wrapper} doctor"), "problemMatcher": []},
            {"label": "Agent Workbench: Build", "type": "shell", "command": _ps_safe(f"{wrapper} build"), "group": {"kind": "build", "isDefault": True}, "problemMatcher": []},
            {"label": "Agent Workbench: Init OpenCode Agents", "type": "shell", "command": _ps_safe(f"{wrapper} init-opencode-agents"), "problemMatcher": []},
            {"label": "Agent Workbench: Scan Project", "type": "shell", "command": _ps_safe(f"{wrapper} scan-project --json"), "problemMatcher": []},
            {"label": "Agent Workbench: Direct Verify (CLI Regression)", "type": "shell", "command": _ps_safe(f"{wrapper} verify current --task {cli_regression_task}"), "problemMatcher": []},
            {"label": "Agent Workbench: Report Latest Verdict", "type": "shell", "command": _ps_safe(f"{wrapper} report --latest"), "problemMatcher": []},
            {"label": "Agent Workbench: Debug Session", "type": "shell", "command": _ps_safe(f"{wrapper} session debug"), "problemMatcher": []},
            {"label": "Agent Workbench: Compare Latest", "type": "shell", "command": _ps_safe(f"{wrapper} compare --latest"), "problemMatcher": []},
            {"label": "Agent Workbench: Test Generate (Example)", "type": "shell", "command": _ps_safe(f"{wrapper} test generate --task {example_task}"), "problemMatcher": []},
            {"label": "Agent Workbench: Test Generate (CLI Regression)", "type": "shell", "command": _ps_safe(f"{wrapper} test generate --task {cli_regression_task}"), "problemMatcher": []},
            {"label": "Agent Workbench: Test Run", "type": "shell", "command": _ps_safe(f"{wrapper} test run"), "problemMatcher": []},
            {"label": "Agent Workbench: UART Console", "type": "shell", "command": _ps_safe(f"{wrapper} uart console"), "problemMatcher": []},
            {"label": "Agent Workbench: UART CLI Smoke", "type": "shell", "command": _ps_safe(f"{wrapper} uart exec --reset-first --expect-ready --command help --command status"), "problemMatcher": []},
            {"label": "Agent Workbench: DIAG Hex Smoke", "type": "shell", "command": _ps_safe(f"{wrapper} diag exec"), "problemMatcher": []},
            {"label": "Agent Workbench: Monitor Start", "type": "shell", "command": _ps_safe(f"{wrapper} monitor start"), "problemMatcher": []},
            {"label": "Agent Workbench: Monitor Stop", "type": "shell", "command": _ps_safe(f"{wrapper} monitor stop"), "problemMatcher": []},
            {"label": "Agent Workbench: OpenOCD Start", "type": "shell", "command": _ps_safe(f"{wrapper} openocd start"), "problemMatcher": []},
            {"label": "Agent Workbench: OpenOCD Stop", "type": "shell", "command": _ps_safe(f"{wrapper} openocd stop"), "problemMatcher": []},
            {"label": "Agent Workbench: Flash (ST-Link)", "type": "shell", "command": _ps_safe(f"{wrapper} flash --method stlink_cli"), "problemMatcher": []},
            {"label": "Agent Workbench: Flash (OpenOCD)", "type": "shell", "command": _ps_safe(f"{wrapper} flash --method openocd_cmd"), "problemMatcher": []},
            {"label": "Agent Workbench: Feature Session (Example)", "type": "shell", "command": _ps_safe(f"{wrapper} session feature --task {example_task}"), "problemMatcher": []},
            {"label": "Agent Workbench: Feature Session (CLI Regression)", "type": "shell", "command": _ps_safe(f"{wrapper} session feature --task {cli_regression_task}"), "problemMatcher": []},
        ],
    }
    tasks_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return tasks_path
```

### 2.3 改 `agent_workbench/core/doctor.py`

**关键替换：**

找到 `def _check_continue_rules(cfg, results):` 整个函数，替换为：

```python
def _check_opencode_agents(cfg: dict, results: list[dict]) -> None:
    oc_cfg = cfg.get("opencode", {})
    if not oc_cfg:
        _append(results, "opencode_agents", "warn", "opencode config missing")
        return

    agents_file = Path(oc_cfg.get("agents_file_path", ""))
    agents_dir = Path(oc_cfg.get("agents_dir_path", ""))
    commands_dir = Path(oc_cfg.get("commands_dir_path", ""))

    # 检查 AGENTS.md
    if not agents_file.exists():
        _append(results, "opencode_agents_file", "warn", f"missing {agents_file} (run init-opencode-agents)")
    else:
        _append(results, "opencode_agents_file", "ok", str(agents_file))

    # 检查 sub-agent 目录
    required_agents = [str(x).strip() for x in oc_cfg.get("required_agents", []) if str(x).strip()]
    if not agents_dir.exists():
        _append(results, "opencode_agents_dir", "warn", f"missing {agents_dir}")
    else:
        _append(results, "opencode_agents_dir", "ok", str(agents_dir))
        missing = [name for name in required_agents if not (agents_dir / name).exists()]
        level = "ok" if not missing else "warn"
        detail = "all required agents present" if not missing else f"missing={','.join(missing)}"
        _append(results, "opencode_agents", level, detail)

    # 检查 slash commands 目录
    required_commands = [str(x).strip() for x in oc_cfg.get("required_commands", []) if str(x).strip()]
    if not commands_dir.exists():
        _append(results, "opencode_commands_dir", "warn", f"missing {commands_dir}")
    else:
        _append(results, "opencode_commands_dir", "ok", str(commands_dir))
        missing = [name for name in required_commands if not (commands_dir / name).exists()]
        level = "ok" if not missing else "warn"
        detail = "all required commands present" if not missing else f"missing={','.join(missing)}"
        _append(results, "opencode_commands", level, detail)

    # 检查模板目录
    template_dir = Path(oc_cfg.get("agents_template_dir_path", ""))
    if not template_dir.exists():
        _append(results, "opencode_templates", "warn", f"missing {template_dir}")
    else:
        _append(results, "opencode_templates", "ok", str(template_dir))
```

**然后把函数调用处 `_check_continue_rules(cfg, results)` 全部改成 `_check_opencode_agents(cfg, results)`。**

**另外：** 把 `required_docs` 字典里的键改为 OpenCode 对应的文档（见阶段 6）：
- 删除 `root / "CONTINUE_AUTO_MODE_GUIDE_ZH.md"` 这行
- 加上 `root / "OPENCODE_AUTO_MODE_GUIDE_ZH.md": ["OpenCode", "init-opencode-agents"]`
- `MIGRATION_GUIDE_ZH.md` 的关键词改为 `["agent_workbench 迁移指南", "init-opencode-agents"]`
- `README.md` 的关键词改为 `["OpenCode Auto Mode", "Local-Model Workflow"]`

### 2.4 改 `agent_workbench/core/project_scanner.py`

找到：
```python
"rules_dir": str(cfg.get("continue", {}).get("rules_dir_path", "")),
```

替换为：
```python
"opencode_agents_file": str(cfg.get("opencode", {}).get("agents_file_path", "")),
"opencode_agents_dir": str(cfg.get("opencode", {}).get("agents_dir_path", "")),
"opencode_commands_dir": str(cfg.get("opencode", {}).get("commands_dir_path", "")),
```

### 2.5 改 `agent_workbench/core/ps_exec.py`

找到 `_KNOWN_COMMANDS` 列表里的：
```python
"init-continue-rules",
```

替换为：
```python
"init-opencode-agents",
```

### 2.6 改 `agent_workbench/workbench.py`

**删除**：`_cmd_init_continue_rules` 函数 + 它对应的 subparser 注册块。

**新增** `_cmd_init_opencode_agents` 函数：

```python
def _cmd_init_opencode_agents(args: argparse.Namespace) -> int:
    from core.vscode_service import write_opencode_agents

    cfg = _cfg(args.config)
    generated = write_opencode_agents(cfg)
    payload = build_result_payload(
        "init-opencode-agents",
        0,
        summary=f"opencode files written: {len(generated)}",
        artifacts={
            "agents_file": str(cfg["opencode"]["agents_file_path"]),
            "agents_dir": str(cfg["opencode"]["agents_dir_path"]),
            "commands_dir": str(cfg["opencode"]["commands_dir_path"]),
            "files": [str(path) for path in generated],
        },
    )
    return _emit(args, payload, [payload["summary"]])
```

**新增** 对应的 subparser 注册（替换原 `init-continue-rules` 那块）：

```python
p_agents = sub.add_parser("init-opencode-agents", help="generate OpenCode AGENTS.md / agent / command files")
p_agents.add_argument("--config", default=str(DEFAULT_CONFIG))
_add_json_flag(p_agents)
p_agents.set_defaults(func=_cmd_init_opencode_agents)
```

### 2.7 改 `agent_workbench/core/context_service.py`

全文检索 `Continue` / `continue_rules` 等字符串，把面向用户的提示文本从 "Continue Agent" 改为 "OpenCode"：

- `"# Paste To Continue"` → `"# Paste To OpenCode"`
- `"## Continue From"` → `"## Resume From"`（或保留但去掉 Continue）
- 注释里 "paste it into Continue Agent" → "paste it into OpenCode session"

**注意：** 这个文件里 `continue` 作为 Python 关键字的 `continue` 循环控制语句**不要动**，只改字符串字面量。

---

## 阶段 3：更新 `agent_workbench/agent_workbench.yaml`

找到 `continue:` 开头的整个配置段（约 20-40 行），整段替换为：

```yaml
opencode:
  # OpenCode 主 agent 指令文件（项目根 AGENTS.md）
  agents_file: AGENTS.md

  # sub-agent 目录（相对 project.root）
  agents_dir: .opencode/agent

  # 自定义 slash 命令目录
  commands_dir: .opencode/command

  # OpenCode 项目配置文件
  project_config_file: opencode.json

  # 模板源目录（相对 agent_workbench/ 根目录）
  agents_template_dir: templates/opencode_agents

  # 必须生成的 sub-agent 文件
  required_agents:
    - stm32_auto.md
    - weak_model.md
    - code_planner.md
    - hardware_verifier.md

  # 必须生成的 slash 命令
  required_commands:
    - plan-stm32.md
    - verify.md
    - fix-build.md
    - uart-smoke.md
    - flash-reset.md

  # 针对不同本地模型的专用 profile
  model_profiles:
    deepseek_r1:
      profile_file: model_profiles/deepseek_r1.md
      min_lines: 5
    glm:
      profile_file: model_profiles/glm.md
      min_lines: 5
    qwen7b:
      profile_file: model_profiles/qwen7b.md
      min_lines: 5

  # 是否也同步到全局 ~/.config/opencode/
  also_install_global: false
```

---

## 阶段 4：更新测试文件

### 4.1 `agent_workbench/tests/test_vscode_service.py`

全文把：
- `from agent_workbench.core.vscode_service import write_continue_rules, write_vscode_tasks`
  → `from agent_workbench.core.vscode_service import write_opencode_agents, write_vscode_tasks`
- `write_continue_rules(cfg)` → `write_opencode_agents(cfg)`
- 所有 `.continue/rules` 路径 → `.opencode/agent`
- 所有 `templates/continue_rules` → `templates/opencode_agents`
- 所有 `init-continue-rules` → `init-opencode-agents`
- 配置字典里 `"continue": {...}` → `"opencode": {...}`（字段按 §3 的 yaml 结构）
- 测试用的模板文件从 `continue_rules/stm32_xxx.md` 改为 `opencode_agents/AGENTS.md.tpl` 等

### 4.2 `agent_workbench/tests/test_doctor.py`

- `.continue/rules` 路径 → `.opencode/` 下各子目录
- `"continue": {"rules_dir_path": ..., ...}` → `"opencode": {"agents_file_path": ..., "agents_dir_path": ..., ...}`
- `names["continue_rules"]` → `names["opencode_agents"]`
- `names["continue_model_rules"]` → 删除或改为 `names["opencode_agents"]` 的检查

### 4.3 `agent_workbench/tests/test_project_scanner.py`

- `"continue": {"rules_dir_path": ...}` → `"opencode": {"agents_dir_path": ..., "commands_dir_path": ..., "agents_file_path": ...}`

### 4.4 `agent_workbench/tests/test_planner*.py`

所有 `"continue": {"rules_dir_path": ...}` 全部替换为 OpenCode 等效：
```python
"opencode": {
    "agents_file_path": self.temp_dir / "AGENTS.md",
    "agents_dir_path": self.temp_dir / ".opencode" / "agent",
    "commands_dir_path": self.temp_dir / ".opencode" / "command",
    "agents_template_dir_path": self.temp_dir / "agent_workbench" / "templates" / "opencode_agents",
    "required_agents": [],
    "required_commands": [],
    "model_profiles": {},
},
```

---

## 阶段 5：删除 Continue 遗留

**先 git commit 当前进度！** 因为阶段 5 的删除操作不可回滚。

### 5.1 删除目录

- `agent_workbench/templates/continue_rules/`（整个目录）
- `.continue/rules/`（整个目录，项目根）
- `.continue/prompts/`（整个目录，项目根）
- `agent_workbench/runtime/continue/`（如果存在）

### 5.2 删除文件

- `agent_workbench/CONTINUE_AUTO_MODE_GUIDE_ZH.md`
- `agent_workbench/CONTINUE_AGENT_SETUP_ZH.md`
- `agent_workbench/VS_CODE_CONTINUE_FUNTUIN_GUIDE.txt`
- `agent_workbench/VS_CODE_CONTINUE_GUIDE_ZH.md`
- `agent_workbench/VS_CODE_CONTINUE_GUIDE.md`
- `agent_workbench/prompts/continue_debug.md`（如果存在）
- `agent_workbench/prompts/continue_feature.md`（如果存在）
- `agent_workbench/prompts/continue_test_author.md`（如果存在）
- `agent_workbench/prompts/continue_report.md`（如果存在）
- `agent_workbench/prompts/continue_low_context_zh.md`
- `.continue/prompts/local_model_*.md`（项目根下的）

### 5.3 保留但改写的文件

- `agent_workbench/MIGRATION_GUIDE_ZH.md`：整个改成"Continue → OpenCode 硬切换迁移指南"
- `agent_workbench/LOW_CONTEXT_MODELS_GUIDE_ZH.md`：内容里 "Continue" 字样改成 "OpenCode"
- `agent_workbench/IMPROVEMENT_PLAN_ZH.md`：保留（不含大量 Continue 字样）
- `agent_workbench/ACCEPTANCE_REPORT_AND_GAP_PLAN_ZH.md`：保留
- `agent_workbench/README.md`：更新主页章节，把 Continue 相关说明改成 OpenCode

---

## 阶段 6：新增 OpenCode 用户文档

### 6.1 新增 `agent_workbench/OPENCODE_AUTO_MODE_GUIDE_ZH.md`

```markdown
# OpenCode 自动模式使用指南

## 前置条件
- 安装 OpenCode: `npm i -g @opencode/cli` 或参考 https://opencode.ai/docs
- 项目已经跑过 `setup_workbench.bat` 和 `agent_workbench.bat doctor`

## 启用步骤

1. 生成 OpenCode 指令集:
   ```powershell
   agent_workbench.bat init-opencode-agents
   ```
   会生成:
   - `AGENTS.md`（项目根，OpenCode 自动加载）
   - `.opencode/agent/*.md`（4 个 sub-agent）
   - `.opencode/command/*.md`（5 个 slash 命令）
   - `opencode.json`（项目配置）

2. 进入项目目录，启动 OpenCode:
   ```powershell
   cd h:\stm32_RAG\code\serial
   opencode
   ```

3. 直接对话（OpenCode 自动加载 AGENTS.md）:
   ```
   > 给 STM32 加一个 CLI 命令 'echo hello'
   ```

4. 或者用 slash 命令精细控制:
   ```
   > /plan-stm32 给 PA8 加 1kHz PWM 50%占空比
   > /verify
   > /fix-build
   > /uart-smoke
   ```

## 工作流程

OpenCode 会自动按 `AGENTS.md` 的 7 步流程执行：
1. doctor
2. plan
3. 按 steps 执行 read/edit/shell
4. build
5. flash（征询）
6. uart 烟测
7. 最终报告

## 常见问题

- **问：OpenCode 没有自动加载 AGENTS.md？**
  答：确认 OpenCode 版本 >= 0.5.0；手动 `cat AGENTS.md | head -5` 确认文件存在。

- **问：模型是 DeepSeek-R1，执行很慢？**
  答：`.opencode/agent/model_deepseek_r1.md` 已经启用了针对性约束，慢是正常的（推理模型特性）。

- **问：想切回 Continue？**
  答：本项目已硬切换到 OpenCode，不再支持 Continue。
```

### 6.2 更新 `agent_workbench/MIGRATION_GUIDE_ZH.md`

改为：

```markdown
# agent_workbench Continue → OpenCode 迁移指南

## 背景
从 v<VERSION> 起，agent_workbench 硬切换到 OpenCode，不再支持 Continue。

## 迁移步骤

1. 安装 OpenCode: `npm i -g @opencode/cli`
2. 拉取最新 agent_workbench 代码
3. 删除旧的 `.continue/` 目录（如果有）:
   ```powershell
   Remove-Item -Recurse -Force .continue
   ```
4. 跑:
   ```powershell
   agent_workbench.bat doctor
   agent_workbench.bat init-opencode-agents
   ```
5. 启动 opencode 实跑:
   ```powershell
   opencode
   > /verify
   ```

## 如果你仍想用 Continue

本项目已不再维护 Continue 路径，建议 fork 一份老版本分支（git tag `continue-last`）自行维护。
```

### 6.3 更新 `agent_workbench/README.md`

- 所有 "Continue Auto Mode" 字样 → "OpenCode Auto Mode"
- 所有 `init-continue-rules` 命令示例 → `init-opencode-agents`
- `.continue/rules/` → `.opencode/agent/`
- "Continue Agent 模式" → "OpenCode Agent 模式"

---

## 阶段 7：最终验收

### 7.1 单元测试

```powershell
cd h:\stm32_RAG\code\serial
agent_workbench\bin\agent_workbench.bat
python -m unittest discover -s agent_workbench\tests -p "test_*.py"
```

预期：全绿。

### 7.2 doctor 自检

```powershell
agent_workbench.bat doctor --json
```

预期：`fail_count == 0`；检查项里有 `opencode_agents_file`、`opencode_agents`、`opencode_commands` 等。

### 7.3 init-opencode-agents 冒烟

```powershell
agent_workbench.bat init-opencode-agents --json
```

预期：生成的文件列表里至少含：
- `AGENTS.md`
- `.opencode/agent/stm32_auto.md`
- `.opencode/agent/weak_model.md`
- `.opencode/agent/code_planner.md`
- `.opencode/agent/hardware_verifier.md`
- `.opencode/command/plan-stm32.md`
- `.opencode/command/verify.md`
- `.opencode/command/fix-build.md`
- `.opencode/command/uart-smoke.md`
- `.opencode/command/flash-reset.md`
- `opencode.json`

### 7.4 AGENTS.md 内容校验

```powershell
Get-Content AGENTS.md | Select-String "serial"
```

预期：包含项目名 `serial`、ready banner `cli ready` 等。

### 7.5 OpenCode 实跑（最终验收）

```powershell
opencode
```

在 opencode 提示符下输入：
```
/plan-stm32 给 PA8 加 1kHz PWM 50% 占空比
```

预期：
- OpenCode 自动跑 `cmd /c ".\agent_workbench.bat plan ..."`
- 返回 JSON 后摘要展示给用户
- 询问是否继续

如果 OpenCode 没有识别 slash 命令，检查：
1. `.opencode/command/plan-stm32.md` 文件存在
2. 文件头部有 YAML frontmatter `---\ndescription: ...\n---`
3. OpenCode 版本足够新（>= 0.5.0）

---

## 附录 A：SEARCH/REPLACE 快速索引

按文件整理的精确替换块（新会话可直接用 `replace_in_file` 工具执行）：

### A.1 `core/config.py`

```
------- SEARCH
        "continue": {
            "rules_dir": ".continue/rules",
            "rules_template_dir": "templates/continue_rules",
=======
        "opencode": {
            "agents_file": "AGENTS.md",
            "agents_dir": ".opencode/agent",
            "commands_dir": ".opencode/command",
            "project_config_file": "opencode.json",
            "agents_template_dir": "templates/opencode_agents",
+++++++ REPLACE
```

（后面 required_rules / model_rules 字段继续按 §2.1 替换）

### A.2 `core/config.py` 路径解析段

```
------- SEARCH
    raw["continue"]["rules_dir_path"] = _resolve(raw["continue"]["rules_dir"], project_root)
    raw["continue"]["rules_template_dir_path"] = _resolve(raw["continue"]["rules_template_dir"], workbench_root)
=======
    oc = raw.setdefault("opencode", {})
    oc["agents_file_path"] = _resolve(oc.get("agents_file", "AGENTS.md"), project_root)
    oc["agents_dir_path"] = _resolve(oc.get("agents_dir", ".opencode/agent"), project_root)
    oc["commands_dir_path"] = _resolve(oc.get("commands_dir", ".opencode/command"), project_root)
    oc["project_config_file_path"] = _resolve(oc.get("project_config_file", "opencode.json"), project_root)
    oc["agents_template_dir_path"] = _resolve(oc.get("agents_template_dir", "templates/opencode_agents"), workbench_root)
    oc["model_profile_names"] = list((oc.get("model_profiles") or {}).keys())
+++++++ REPLACE
```

### A.3 `core/config.py` 删除 continue_runtime_root_path

```
------- SEARCH
    raw["outputs"]["continue_runtime_root_path"] = raw["outputs"]["runtime_root_path"] / "continue"
=======
+++++++ REPLACE
```

### A.4 `core/config.py` 删除 raw["continue"]["model_rule_names"]

```
------- SEARCH
    raw["continue"]["model_rule_names"] = list((raw["continue"].get("model_rules") or {}).keys())
=======
+++++++ REPLACE
```

### A.5 `core/project_scanner.py`

```
------- SEARCH
        "rules_dir": str(cfg.get("continue", {}).get("rules_dir_path", "")),
=======
        "opencode_agents_file": str(cfg.get("opencode", {}).get("agents_file_path", "")),
        "opencode_agents_dir": str(cfg.get("opencode", {}).get("agents_dir_path", "")),
        "opencode_commands_dir": str(cfg.get("opencode", {}).get("commands_dir_path", "")),
+++++++ REPLACE
```

### A.6 `core/ps_exec.py`

```
------- SEARCH
    "init-continue-rules",
=======
    "init-opencode-agents",
+++++++ REPLACE
```

### A.7 `workbench.py`

（函数整段替换 + subparser 整段替换，按 §2.6 的代码）

---

## 附录 B：调试技巧

- 如果 `agent_workbench.bat init-opencode-agents --json` 报 `FileNotFoundError: opencode agent template not found`：
  → 检查 `agent_workbench/templates/opencode_agents/agent/` 下是否有对应的 `.md.tpl` 文件
  → 注意代码里 `tpl_path = template_dir / "agent" / f"{name}.tpl"`，name 已经是 `stm32_auto.md`，所以实际找的是 `stm32_auto.md.tpl`

- 如果 OpenCode 启动后没加载 AGENTS.md：
  → 确认 `opencode.json` 里的 `instructions` 数组包含 `"AGENTS.md"`
  → 确认 opencode 版本：`opencode --version`

- 如果测试 `test_vscode_service` 失败：
  → 先读 `tests/test_vscode_service.py` 完整内容，把所有 `continue` 字串一次性替换完
  → 临时文件系统用 mock，所以要在 setUp 里创建所有模板占位文件

---

## 附录 C：Git 分支建议

```powershell
# 执行前打 tag
git tag continue-last
git checkout -b feature/hard-switch-opencode

# 每阶段完成一次提交
git add -A && git commit -m "phase 1: add opencode templates"
git add -A && git commit -m "phase 2: refactor python to opencode"
git add -A && git commit -m "phase 3: update yaml"
git add -A && git commit -m "phase 4: update tests"
git add -A && git commit -m "phase 5: remove continue remnants"
git add -A && git commit -m "phase 6: add opencode docs"

# 最终验收通过后合并
git checkout main
git merge feature/hard-switch-opencode
```

---

**清单结束。按这份文档执行即可完成硬切换到 OpenCode 的全流程。**
