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
   - `.opencode/agent/*.md`（4 个 sub-agent + 3 个模型 profile）
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
   > /flash-reset
   ```

## 工作流程

OpenCode 会自动按 `AGENTS.md` 的 7 步流程执行：
1. `doctor` - 环境自检
2. `plan` - 把自然语言需求转成执行计划
3. 按 steps 执行 read/edit/shell
4. `build` - 编译
5. `flash` - 烧录（会征询用户同意）
6. `uart exec` - UART CLI 烟测
7. 输出最终证据报告

## 可用 Sub-Agent

- `@stm32_auto`: 默认主 agent（对应 AGENTS.md 全部行为）
- `@code_planner`: 把 plan JSON 转成具体 edit/write
- `@hardware_verifier`: 烧录 + UART 验证专用
- `@weak_model`: 弱模型 10 条反例（自动按模型名启用）

## 可用 Slash 命令

| 命令 | 作用 |
|------|------|
| `/plan-stm32 <需求>` | 只生成 plan，不执行 |
| `/verify` | 完整 doctor + build + flash + uart 烟测 |
| `/fix-build` | 读取 build.log 生成修复建议 |
| `/uart-smoke` | 只做 UART CLI 烟测 |
| `/flash-reset` | 只做烧录 + 复位 |

## 本地模型 Profile

每个 profile 对应不同本地模型的专用约束，生成在 `.opencode/agent/model_<name>.md`：
- `model_deepseek_r1.md`: DeepSeek-R1 推理模型
- `model_glm.md`: GLM-4 系列
- `model_qwen7b.md`: Qwen-7B 小模型

OpenCode 会根据当前选用的模型名自动匹配对应的 profile（依赖 YAML frontmatter 的 `model:` 字段）。

## 常见问题

- **问：OpenCode 没有自动加载 AGENTS.md？**
  答：确认 OpenCode 版本 >= 0.5.0；手动 `Get-Content AGENTS.md | Select-Object -First 5` 确认文件存在，且 `opencode.json` 里 `instructions` 数组包含 `"AGENTS.md"`。

- **问：slash 命令没识别？**
  答：确认 `.opencode/command/*.md` 文件头部有 YAML frontmatter `---\ndescription: ...\n---`。

- **问：模型是 DeepSeek-R1，执行很慢？**
  答：`.opencode/agent/model_deepseek_r1.md` 已经启用了针对性约束，慢是正常的（推理模型特性）。

- **问：想切回 Continue？**
  答：本项目已硬切换到 OpenCode，不再支持 Continue。若需使用旧版本，请 `git checkout continue-last` 回到硬切换之前的 tag。
