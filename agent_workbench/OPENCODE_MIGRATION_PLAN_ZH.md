# Agent Workbench 迁移 / 兼容 OpenCode 方案

> 本文档分析"如何把 agent_workbench 从 Continue 切换到 OpenCode"，以及"如何让两者共存/兼容"。
>
> **本文档只给方案，不做任何修改。**

---

## 目录

1. [背景：OpenCode 与 Continue 的本质差异](#一背景opencode-与-continue-的本质差异)
2. [当前项目里所有 Continue 相关代码清单](#二当前项目里所有-continue-相关代码清单)
3. [迁移策略选择（3 种路线对比）](#三迁移策略选择3-种路线对比)
4. [推荐方案：双平台共存 + 平台适配层](#四推荐方案双平台共存--平台适配层)
5. [详细改造清单（每个文件要改什么）](#五详细改造清单每个文件要改什么)
6. [配置文件升级设计](#六配置文件升级设计)
7. [OpenCode 侧的 AGENTS.md / 命令 / 代理设计](#七opencode-侧的-agentsmd--命令--代理设计)
8. [Rules 内容翻译规则](#八rules-内容翻译规则)
9. [测试与验收策略](#九测试与验收策略)
10. [分阶段实施路线图](#十分阶段实施路线图)
11. [用户侧操作手册（迁移后）](#十一用户侧操作手册迁移后)
12. [风险与兼容性保障](#十二风险与兼容性保障)

---

## 一、背景：OpenCode 与 Continue 的本质差异

### 1.1 两者定位

| 维度 | Continue | OpenCode |
|------|----------|----------|
| 产品形态 | VS Code 插件（侧边栏聊天） | 终端 TUI + VS Code 集成终端 |
| 默认运行方式 | VS Code 里手动打开聊天 | 在工程根目录跑 `opencode` 命令 |
| Agent 开启方式 | 聊天框切换 Chat/Agent 模式 | 终端默认就是 Agent 模式 |
| 指令文件 | `.continue/rules/*.md` + `.continue/prompts/*.md` | `AGENTS.md`（项目根）+ `.opencode/agent/*.md` + `.opencode/command/*.md` |
| 配置文件 | `.continue/config.yaml`（用户级） | `opencode.json` / `opencode.jsonc`（项目级 + 用户级） |
| 模型集成 | 每个模型显式声明 `capabilities: [tool_use]` | 用 providers 注册，默认全量 tool use |
| 工具调用 | 受模型能力限制 | 内置 shell / read / write / edit / grep 等丰富工具 |
| MCP 支持 | 较新版本支持 | 原生一等公民 |
| 自定义 Agent | 不支持或弱 | 通过 `.opencode/agent/*.md` 原生支持多 sub-agent |
| 自定义斜杠命令 | 通过 prompts，需要复制粘贴 | 原生支持 `/plan`、`/build` 等自定义斜杠命令 |

### 1.2 对 agent_workbench 的影响

**核心好消息：** `agent_workbench.bat` 的**所有命令**（`plan`, `build`, `flash`, `uart exec`, `parse-errors`, `fix-build`, `ps-exec` 等）都是**平台无关**的 PowerShell 子命令，输出都是 JSON，对 Continue 和 OpenCode 都能直接复用。

**需要调整的是"外壳层"：**

- 规则/指令文件格式（MD 内容需要调整）
- 生成规则的命令（`init-continue-rules` 要有对应的 `init-opencode-agents`）
- 配置段（`agent_workbench.yaml` 需要分支）
- 文档和使用手册
- doctor 检查项

**不需要改的（关键保留）：**

- `core/planner.py`
- `core/param_extractor.py`（如果未来做的话）
- `core/hardware_knowledge.py`（如果未来做的话）
- `core/build_errors.py`
- `core/build_service.py`
- `core/flash_service.py`
- `core/uart_service.py`
- `core/ps_exec.py`
- `core/cli_output.py`
- `templates/task_templates/*.yaml`
- `templates/hardware_knowledge/*.yaml`（如果未来做的话）
- `templates/build_error_rules.json`
- `core/project_scanner.py` 的扫描能力（只读一个字段需要改）

---

## 二、当前项目里所有 Continue 相关代码清单

经过 `grep [Cc]ontinue` 和代码审查，共 147 处引用。分类如下：

### 2.1 Python 核心代码（需要改造）

| 文件 | Continue 相关内容 | 改造思路 |
|------|-----------------|---------|
| `workbench.py` | `_cmd_init_continue_rules`（命令实现）、`init-continue-rules`（subparser） | 新增 `_cmd_init_opencode_agents` 和 `init-opencode-agents` 命令；保留原命令 |
| `core/config.py` | `"continue": {...}` 配置段、`rules_dir_path` 等字段解析 | 重构成 `agents:` 顶层段，内含 `continue:` 和 `opencode:` 两个并列子段，保持向后兼容 |
| `core/vscode_service.py` | `write_continue_rules()`、`_write_runtime_continue_prompts()`、`write_vscode_tasks()` 里 Init Continue Rules 任务 | 抽象为 `agents_service.py`；新增 `write_opencode_agents()`；保留 `write_continue_rules` 调用 |
| `core/doctor.py` | `_check_continue_rules()` 检查 rules_dir 和必需文件 | 抽象为 `_check_agent_platform(platform_name)`；循环检查当前启用的所有平台 |
| `core/project_scanner.py` | `"rules_dir": cfg["continue"]["rules_dir_path"]` | 改为读 `cfg["agents"]["<active_platform>"]["rules_dir_path"]` |
| `core/ps_exec.py` | `_KNOWN_COMMANDS` 里的 `init-continue-rules` | 保留 `init-continue-rules`，新增 `init-opencode-agents` |

### 2.2 模板文件（需要复制并改写）

| 源 | 目标 |
|----|------|
| `templates/continue_rules/stm32_auto_workflow.md` | `templates/opencode_agents/AGENTS.md.tpl`（主说明）+ `templates/opencode_agents/workflow_core.md.tpl`（可选子代理） |
| `templates/continue_rules/stm32_weak_model_guard.md` | `templates/opencode_agents/weak_model_guard.md.tpl`（作为辅助指令文件） |
| `templates/continue_rules/stm32_powershell_syntax.md` | `templates/opencode_agents/shell_syntax.md.tpl`（同时保留 PowerShell 段和 bash 段） |
| `templates/continue_rules/stm32_error_recovery.md` | `templates/opencode_agents/error_recovery.md.tpl` |
| `templates/continue_rules/stm32_hardware_safety.md` | `templates/opencode_agents/hardware_safety.md.tpl` |
| `templates/continue_rules/stm32_task_cookbook.md` | `templates/opencode_agents/task_cookbook.md.tpl` + 转换为 `.opencode/command/*.md` 里的多个 slash 命令 |
| `templates/continue_rules/stm32_model_deepseek_r1.md` | `templates/opencode_agents/model_profiles/deepseek_r1.md.tpl` |
| `templates/continue_rules/stm32_model_glm.md` | `templates/opencode_agents/model_profiles/glm.md.tpl` |
| `templates/continue_rules/stm32_model_qwen7b.md` | `templates/opencode_agents/model_profiles/qwen7b.md.tpl` |

### 2.3 运行时产物目录（需要新增）

| 当前 Continue 产出 | OpenCode 对应产出 |
|-------------------|------------------|
| `.continue/rules/stm32_auto_workflow.md` | `AGENTS.md`（项目根）+ `.opencode/agent/stm32_auto.md` |
| `.continue/rules/stm32_weak_model_guard.md` | `.opencode/agent/weak_model.md`（作为 sub-agent） |
| `.continue/rules/stm32_task_cookbook.md` | 转换为 `.opencode/command/plan-stm32.md` / `.opencode/command/verify.md` / `.opencode/command/fix-build.md` 等 5 个 slash 命令 |
| `.continue/prompts/local_model_*.md` | `.opencode/command/*.md`（slash 命令） |

### 2.4 文档（需要更新/新增）

| 文件 | 动作 |
|------|------|
| `README.md` | 新增"支持的 AI 平台"章节，并列 Continue + OpenCode 两条使用路径 |
| `MIGRATION_GUIDE_ZH.md` | 加入"从 Continue 切换到 OpenCode"的迁移步骤 |
| `CONTINUE_AUTO_MODE_GUIDE_ZH.md` | 保留（作为 Continue 用户指南） |
| `CONTINUE_AGENT_SETUP_ZH.md` | 保留 |
| `OPENCODE_AGENT_SETUP_ZH.md` | **【新增】** OpenCode 侧启用指南 |
| `OPENCODE_AUTO_MODE_GUIDE_ZH.md` | **【新增】** OpenCode 自动模式使用指南（对应 CONTINUE_AUTO_MODE_GUIDE_ZH.md） |
| `AGENT_PLATFORMS_COMPARISON_ZH.md` | **【新增】** 解释 Continue vs OpenCode 选哪个的决策指南 |

### 2.5 测试文件（需要更新）

| 文件 | 动作 |
|------|------|
| `tests/test_vscode_service.py` | 加 `test_write_opencode_agents()` 等 4-6 个测试 |
| `tests/test_doctor.py` | 加 `opencode_agents` 检查项测试 |
| `tests/test_project_scanner.py` | 参数化（对 continue / opencode 两套配置分别测） |
| `tests/test_planner.py` | 配置字段改为 `agents.continue`，也测 `agents.opencode` |
| `tests/test_planner_e2e.py` | 同上 |
| 新增 `tests/test_opencode_migration.py` | 专门测 AGENTS.md 生成、slash 命令生成、内容转换 |

---

## 三、迁移策略选择（3 种路线对比）

### 路线 A：硬切换（弃用 Continue，只保留 OpenCode）

**做法：** 删除所有 `continue_*` 文件，改名 `init-continue-rules` → `init-agent-rules`，删除 `.continue/` 生成逻辑。

**优点：**
- 代码库精简
- 没有分支维护成本

**缺点：**
- 已经在用 Continue 的用户被强制迁移
- 破坏向后兼容

**推荐度：** ❌ 不推荐（对已有用户破坏性太强）

---

### 路线 B：双平台并存（两套代码并行）

**做法：** 保留 Continue 所有现有代码和命令，另外增加一套完全独立的 OpenCode 实现。

**优点：**
- 实现简单
- 用户可以自由选择

**缺点：**
- 大量代码重复（两套 rules 生成逻辑、两套 doctor 检查、两套测试）
- 长期维护难度大
- rules 内容修改需要同步两份

**推荐度：** 🟡 可行但不最佳

---

### 路线 C（推荐）：平台适配层 + 双实现

**做法：**

1. 提取出"agent 平台适配器"概念（`core/agents_service.py`）
2. 定义统一接口：`generate_rules(cfg)` / `check_rules(cfg)` / `required_outputs(cfg)`
3. Continue 和 OpenCode 各自实现这个接口
4. 配置里用 `agents.active_platform` 指定当前激活哪个
5. 同时支持 `agents.active_platform: both` 同时生成两套

**优点：**
- 代码共享率高（模板渲染逻辑、配置解析等通用）
- 长期扩展性好（未来要接 Cursor / Windsurf / Claude Code 容易）
- 向后兼容（Continue 用户不受影响）
- 用户可以切换平台

**缺点：**
- 首次改造工作量略大（需要做适配层）

**推荐度：** ✅ **强烈推荐**

---

## 四、推荐方案：双平台共存 + 平台适配层

### 4.1 整体架构

```
agent_workbench/
├── core/
│   ├── agents/                           【新增目录】
│   │   ├── __init__.py
│   │   ├── base.py                       # 抽象基类 AgentPlatform
│   │   ├── continue_platform.py          # Continue 实现
│   │   ├── opencode_platform.py          # OpenCode 实现【新增】
│   │   └── registry.py                   # 平台注册 + 加载
│   ├── vscode_service.py                 # 保留，但 write_continue_rules 改为调 agents
│   ├── config.py                         # 配置段重构
│   ├── doctor.py                         # _check_continue_rules → _check_agent_platforms
│   └── ...
│
├── templates/
│   ├── continue_rules/                   【保留现有】
│   │   └── *.md
│   ├── opencode_agents/                  【新增目录】
│   │   ├── AGENTS.md.tpl
│   │   ├── agent/
│   │   │   ├── stm32_auto.md.tpl
│   │   │   ├── weak_model.md.tpl
│   │   │   └── ...
│   │   ├── command/
│   │   │   ├── plan-stm32.md.tpl
│   │   │   ├── verify.md.tpl
│   │   │   ├── fix-build.md.tpl
│   │   │   └── ...
│   │   └── model_profiles/
│   │       ├── deepseek_r1.md.tpl
│   │       └── ...
│   └── task_templates/                   【保留不动】
│
└── agent_workbench.yaml                  # 配置段改造见 §6
```

### 4.2 抽象基类设计

```python
# agent_workbench/core/agents/base.py

from abc import ABC, abstractmethod
from pathlib import Path

class AgentPlatform(ABC):
    """AI 代理平台抽象基类"""
    
    name: str  # 如 "continue" / "opencode"
    
    @abstractmethod
    def required_outputs(self, cfg: dict) -> list[Path]:
        """返回本平台需要生成的文件清单，用于 doctor 检查"""
        ...
    
    @abstractmethod
    def generate(self, cfg: dict) -> list[Path]:
        """根据 agent_workbench.yaml 的配置和模板，生成实际的规则/指令文件"""
        ...
    
    @abstractmethod
    def check_installed(self, cfg: dict) -> list[dict]:
        """返回 doctor 检查结果（每个检查项是 {name, level, detail} 字典）"""
        ...
    
    @abstractmethod
    def describe_setup_steps(self, cfg: dict) -> str:
        """返回给用户的启用步骤说明（markdown 文本）"""
        ...
```

### 4.3 平台注册和分发

```python
# agent_workbench/core/agents/registry.py

from .continue_platform import ContinuePlatform
from .opencode_platform import OpenCodePlatform

_REGISTRY = {
    "continue": ContinuePlatform(),
    "opencode": OpenCodePlatform(),
}

def get_platforms(cfg: dict) -> list[AgentPlatform]:
    """根据配置 agents.active_platform 返回激活的平台列表"""
    active = cfg.get("agents", {}).get("active_platform", "continue")
    if active == "both":
        return list(_REGISTRY.values())
    return [_REGISTRY[active]]

def generate_all(cfg: dict) -> dict[str, list[Path]]:
    """为所有激活平台生成文件"""
    return {
        platform.name: platform.generate(cfg)
        for platform in get_platforms(cfg)
    }
```

### 4.4 workbench.py 新增命令

```python
def _cmd_init_agents(args):
    """新增通用命令：根据 agents.active_platform 生成所有激活平台的文件"""
    from core.agents.registry import generate_all
    
    cfg = _cfg(args.config)
    results = generate_all(cfg)
    
    payload = build_result_payload(
        "init-agents",
        0,
        summary=f"generated rules for {len(results)} platform(s)",
        details={
            platform: [str(p) for p in paths]
            for platform, paths in results.items()
        },
    )
    return _emit(args, payload, [payload["summary"]])


def _cmd_init_opencode_agents(args):
    """专用命令：只生成 OpenCode 的 AGENTS.md 和子 agent 文件"""
    from core.agents.registry import _REGISTRY
    
    cfg = _cfg(args.config)
    paths = _REGISTRY["opencode"].generate(cfg)
    payload = build_result_payload(
        "init-opencode-agents",
        0,
        summary=f"generated {len(paths)} opencode files",
        artifacts={"files": [str(p) for p in paths]},
    )
    return _emit(args, payload, [payload["summary"]])


# 保留原 _cmd_init_continue_rules（完全不变），作为"专用命令"
# 新增一条 init-agents 作为"通用命令"
# 新增一条 init-opencode-agents 作为"OpenCode 专用命令"
```

---

## 五、详细改造清单（每个文件要改什么）

### 5.1 新增文件

| 文件 | 用途 |
|------|------|
| `agent_workbench/core/agents/__init__.py` | 包初始化 |
| `agent_workbench/core/agents/base.py` | 抽象基类 `AgentPlatform` |
| `agent_workbench/core/agents/continue_platform.py` | Continue 适配器（把现有 `write_continue_rules` 包起来） |
| `agent_workbench/core/agents/opencode_platform.py` | **OpenCode 适配器【核心】** |
| `agent_workbench/core/agents/registry.py` | 平台注册和分发 |
| `agent_workbench/templates/opencode_agents/AGENTS.md.tpl` | OpenCode 主指令文件模板 |
| `agent_workbench/templates/opencode_agents/agent/stm32_auto.md.tpl` | OpenCode 主 agent |
| `agent_workbench/templates/opencode_agents/agent/weak_model.md.tpl` | 弱模型约束 sub-agent |
| `agent_workbench/templates/opencode_agents/agent/code_planner.md.tpl` | 代码规划 sub-agent |
| `agent_workbench/templates/opencode_agents/agent/hardware_verifier.md.tpl` | 硬件验证 sub-agent |
| `agent_workbench/templates/opencode_agents/command/plan-stm32.md.tpl` | slash 命令：生成 plan |
| `agent_workbench/templates/opencode_agents/command/verify.md.tpl` | slash 命令：完整验证流程 |
| `agent_workbench/templates/opencode_agents/command/fix-build.md.tpl` | slash 命令：修复编译错误 |
| `agent_workbench/templates/opencode_agents/command/uart-smoke.md.tpl` | slash 命令：UART CLI 烟测 |
| `agent_workbench/templates/opencode_agents/command/flash-reset.md.tpl` | slash 命令：烧录复位 |
| `agent_workbench/templates/opencode_agents/shell_syntax.md.tpl` | shell 语法指南（PS + bash 并存） |
| `agent_workbench/templates/opencode_agents/error_recovery.md.tpl` | 错误恢复规则 |
| `agent_workbench/templates/opencode_agents/hardware_safety.md.tpl` | 硬件安全规则 |
| `agent_workbench/templates/opencode_agents/task_cookbook.md.tpl` | 任务速查 |
| `agent_workbench/templates/opencode_agents/model_profiles/deepseek_r1.md.tpl` | DeepSeek-R1 专用 |
| `agent_workbench/templates/opencode_agents/model_profiles/glm.md.tpl` | GLM 专用 |
| `agent_workbench/templates/opencode_agents/model_profiles/qwen7b.md.tpl` | Qwen7B 专用 |
| `agent_workbench/templates/opencode_agents/opencode.json.tpl` | OpenCode 项目配置模板 |
| `agent_workbench/OPENCODE_AGENT_SETUP_ZH.md` | OpenCode 启用指南（用户手册） |
| `agent_workbench/OPENCODE_AUTO_MODE_GUIDE_ZH.md` | OpenCode 自动模式使用指南 |
| `agent_workbench/AGENT_PLATFORMS_COMPARISON_ZH.md` | 平台对比和选型指南 |
| `agent_workbench/tests/test_opencode_migration.py` | OpenCode 生成测试 |
| `agent_workbench/tests/test_agents_registry.py` | 平台注册表测试 |

### 5.2 需要修改的文件

| 文件 | 修改内容 |
|------|---------|
| `agent_workbench.yaml` | 新增 `agents:` 顶层段（含 `active_platform` 和两个子段，详见 §6） |
| `core/config.py` | 解析新的 `agents:` 段；保留旧 `continue:` 段作为向后兼容 fallback |
| `core/vscode_service.py` | `write_continue_rules` 改为内部调用 `ContinuePlatform.generate()`；`write_vscode_tasks` 里新增 OpenCode 相关的 task 项 |
| `core/doctor.py` | `_check_continue_rules` 重构为 `_check_agent_platform(platform)` 并循环检查所有激活平台 |
| `core/project_scanner.py` | `"rules_dir": cfg["continue"]["rules_dir_path"]` 改为读激活平台的 rules_dir |
| `core/ps_exec.py` | `_KNOWN_COMMANDS` 新增 `init-opencode-agents` 和 `init-agents` |
| `workbench.py` | 新增 `_cmd_init_opencode_agents` 和 `_cmd_init_agents`；对应的 subparser |
| `MIGRATION_GUIDE_ZH.md` | 新增"平台迁移"章节 |
| `README.md` | 加"支持的 AI 平台"章节 |
| `CONTINUE_AUTO_MODE_GUIDE_ZH.md` | 首页加一条横幅："如果想用 OpenCode，请看 OPENCODE_AUTO_MODE_GUIDE_ZH.md" |
| `tests/test_vscode_service.py` | 新增 OpenCode 生成的几个测试 |
| `tests/test_doctor.py` | 新增 OpenCode rules 检查项测试 |
| `tests/test_project_scanner.py` | 参数化 |
| `tests/test_planner.py` | 配置用新的 `agents.continue` 段 |
| `tests/test_planner_e2e.py` | 同上 |

### 5.3 不需要改的文件（保留）

- `core/planner.py` ✅
- `core/param_extractor.py`（未来做） ✅
- `core/hardware_knowledge.py`（未来做） ✅
- `core/build_errors.py` ✅
- `core/build_service.py` ✅
- `core/flash_service.py` ✅
- `core/uart_service.py` ✅
- `core/cli_output.py` ✅
- `core/session_service.py` ✅
- `core/compare_service.py` ✅
- `core/context_service.py` ✅（输出的 paste.md 对 OpenCode 也有用）
- `core/reporting.py` ✅
- `core/assertions.py` ✅
- `core/cli_diag_service.py` ✅
- `core/diag_uart_service.py` ✅
- `core/monitor_service.py` ✅
- `core/openocd_client.py` ✅
- `core/openocd_service.py` ✅
- `core/session_service.py` ✅
- `core/task_spec.py` ✅
- `core/test_service.py` ✅
- `core/utils.py` ✅
- `templates/task_templates/*.yaml` ✅
- `templates/hardware_knowledge/*.yaml`（未来做） ✅
- `templates/build_error_rules.json` ✅
- `templates/continue_rules/*.md` ✅（继续作为 Continue 模板）
- 所有 `tasks/*.yaml` ✅

**关键：核心业务代码（plan / build / flash / uart / parse-errors / fix-build）零修改，完全平台无关。**

---

## 六、配置文件升级设计

### 6.1 `agent_workbench.yaml` 新增 / 调整的段

**当前结构（旧）：**
```yaml
continue:
  rules_dir: .continue/rules
  rules_template_dir: templates/continue_rules
  required_rules:
    - stm32_auto_workflow.md
    - stm32_weak_model_guard.md
    ...
  model_rules:
    deepseek_r1: ...
    glm: ...
    qwen7b: ...
```

**新结构（改造后）：**
```yaml
# AI 代理平台配置
agents:
  # 当前激活的平台。可选值:
  #   - continue: 只生成 Continue 规则（默认，向后兼容）
  #   - opencode: 只生成 OpenCode 代理文件
  #   - both:     同时生成两者（迁移过渡期用）
  active_platform: continue

  # Continue 平台配置（原 continue: 段完整搬迁过来）
  continue:
    rules_dir: .continue/rules
    rules_template_dir: templates/continue_rules
    required_rules:
      - stm32_auto_workflow.md
      - stm32_weak_model_guard.md
      - stm32_powershell_syntax.md
      - stm32_error_recovery.md
      - stm32_hardware_safety.md
      - stm32_task_cookbook.md
    model_rules:
      deepseek_r1:
        rule_file: stm32_model_deepseek_r1.md
        min_lines: 20
      glm:
        rule_file: stm32_model_glm.md
        min_lines: 20
      qwen7b:
        rule_file: stm32_model_qwen7b.md
        min_lines: 20

  # OpenCode 平台配置（【新增】）
  opencode:
    # AGENTS.md 生成的目标位置（项目根）
    agents_file: AGENTS.md
    
    # 自定义 agent 目录（可包含多个 sub-agent）
    agents_dir: .opencode/agent
    
    # 自定义 slash 命令目录
    commands_dir: .opencode/command
    
    # 【可选】OpenCode 项目级配置
    project_config_file: opencode.json
    
    # 模板源目录
    agents_template_dir: templates/opencode_agents
    
    # 必须生成的核心指令文件
    required_agents:
      - stm32_auto.md        # 主 agent
      - weak_model.md        # 弱模型约束
      - code_planner.md      # 代码规划 sub-agent
      - hardware_verifier.md # 硬件验证 sub-agent
    
    # 必须生成的 slash 命令文件
    required_commands:
      - plan-stm32.md
      - verify.md
      - fix-build.md
      - uart-smoke.md
      - flash-reset.md
    
    # 针对不同模型的 profile（内容基本同 Continue 的 model_rules）
    model_profiles:
      deepseek_r1:
        profile_file: model_profiles/deepseek_r1.md
        min_lines: 20
      glm:
        profile_file: model_profiles/glm.md
        min_lines: 20
      qwen7b:
        profile_file: model_profiles/qwen7b.md
        min_lines: 20
    
    # 是否把 AGENTS.md 强制同步到 ~/.config/opencode/AGENTS.md（全局）
    # 默认 false，只放在项目根
    also_install_global: false
```

### 6.2 `config.py` 的解析改造

```python
def _normalize_agents_section(raw: dict) -> dict:
    """
    兼容新老两种配置格式:
    - 新版本: raw["agents"]["continue"]
    - 老版本: raw["continue"]（没有顶层 agents 段）
    
    保证解析后始终有 raw["agents"]["continue"] 和 raw["agents"]["opencode"]
    """
    # 如果用户还是老版本，自动迁移
    if "agents" not in raw and "continue" in raw:
        raw["agents"] = {
            "active_platform": "continue",
            "continue": raw["continue"],
            "opencode": _default_opencode_config(),
        }
        # 不删除 raw["continue"]，保持老代码能读
    
    raw.setdefault("agents", {})
    raw["agents"].setdefault("active_platform", "continue")
    raw["agents"].setdefault("continue", raw.get("continue", {}))
    raw["agents"].setdefault("opencode", _default_opencode_config())
    
    # 解析两个平台的路径
    _resolve_continue_paths(raw)
    _resolve_opencode_paths(raw)
    return raw

def _default_opencode_config() -> dict:
    return {
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
        "model_profiles": {},
        "also_install_global": False,
    }
```

---

## 七、OpenCode 侧的 AGENTS.md / 命令 / 代理设计

### 7.1 项目根 `AGENTS.md`（主指令，OpenCode 自动加载）

**模板位置：** `templates/opencode_agents/AGENTS.md.tpl`

**内容结构：**

```markdown
# STM32 Agent Workbench — OpenCode 主指令

本文件由 `agent_workbench.bat init-opencode-agents` 自动生成。

## 项目绑定信息
- 项目: {project_name}
- 构建目录: {build_dir}
- UART CLI 串口: {uart_port} (baud {uart_baud})
- 诊断串口: {diag_uart_port}
- Ready banner: "{ready_banner}"
- Prompt: "{prompt}"

## 核心职责
你是这个 STM32 工程的开发助手。用户通常会给你一句自然语言需求，你必须：

1. 通过 shell 工具调用 `agent_workbench.bat plan "<需求>" --json` 生成执行计划
2. 按 plan 的 steps 数组依次执行（read / edit / shell）
3. 编译失败时调 `agent_workbench.bat fix-build --json` 获取结构化修复方案
4. 烧录前必须向用户确认
5. 最后输出完整验证报告

## 核心原则
1. 不要臆测硬件参数（Prescaler/Period/CCR 一律从 `plan.hardware_context` 取）
2. 所有 shell 命令都必须通过 OpenCode 的 shell 工具执行，禁止编造执行结果
3. Windows 下使用 `cmd /c ".\agent_workbench.bat xxx --json"`
4. 一次只运行一条命令，禁止用 `;` 或 `&&` 串联
5. 所有命令都加 `--json` 获取结构化输出

## 可用 sub-agent（见 .opencode/agent/）
- `@code_planner`: 专门负责从 plan 生成具体代码
- `@hardware_verifier`: 专门负责 UART / 烧录后验证
- `@weak_model`: 在检测到小上下文模型时启用的防护 agent

## 可用 slash 命令（见 .opencode/command/）
- `/plan-stm32 <需求>`: 快速生成执行计划
- `/verify`: 运行完整验证流程（doctor + build + flash + uart 烟测）
- `/fix-build`: 读取最新 build.log 并生成修复方案
- `/uart-smoke`: 发送 help/status 命令做 CLI 烟测
- `/flash-reset`: 烧录并复位硬件

## 工作流详细步骤
（此处内容基本等同于 Continue 侧的 stm32_auto_workflow.md，只是把"Continue" 换成"你"或"OpenCode"）

...（300+ 行完整指令）
```

### 7.2 `.opencode/agent/stm32_auto.md`（主 agent）

这个文件可以是 AGENTS.md 的一部分抽出来，或者独立。OpenCode 会把 `AGENTS.md` 和 `.opencode/agent/*.md` 都加载作为系统指令。

### 7.3 `.opencode/agent/weak_model.md`（弱模型约束 sub-agent）

内容和 Continue 的 `stm32_weak_model_guard.md` 一一对应，做如下调整：

```markdown
---
description: 弱模型安全约束（DeepSeek-R1 / 小上下文 Qwen 等）
model: 
  - deepseek-r1
  - qwen3.5-9b
  - glm-4-flash
---

# 弱模型安全约束

当你检测到自己是弱模型或上下文受限，严格遵守以下 20 条反例规则：

## 反例 1: ...
...
```

**关键：** OpenCode 支持在 agent 文件头部用 YAML frontmatter 声明 `model:` 列表，只对指定模型激活，这是比 Continue 更精细的控制。

### 7.4 `.opencode/command/plan-stm32.md`（slash 命令）

```markdown
---
description: 从自然语言需求生成 STM32 执行计划
argument-hint: <用户需求>
---

# /plan-stm32 命令

当用户输入 `/plan-stm32 <需求>` 时，执行：

1. 运行 shell:
   cmd /c ".\agent_workbench.bat plan ""{{ARG}}"" --json"

2. 解析返回的 JSON，检查：
   - parameter_extractions 是否完整
   - hardware_context 是否包含所需的硬件参数

3. 把 plan 的摘要展示给用户（不要全文输出 JSON）：
   - 识别到的参数
   - 硬件方案
   - 计划步骤数

4. 询问用户是否开始执行
```

### 7.5 `.opencode/command/verify.md`（完整验证流程）

```markdown
---
description: 运行完整 STM32 验证流程（doctor + build + uart-smoke）
---

# /verify 命令

顺序执行：

1. cmd /c ".\agent_workbench.bat doctor --json"
   → 如果 fail_count > 0, 报告并停止
2. cmd /c ".\agent_workbench.bat build --json"
   → 如果 exit_code != 0, 用 /fix-build 修复
3. cmd /c ".\agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --json"
   → 检查 transcript 里 ready banner 和 cli> prompt

最后输出合并报告。
```

### 7.6 `opencode.json` 项目配置（可选）

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "{recommended_model}",
  "theme": "opencode",
  "autoshare": false,
  "autoupdate": true,
  "provider": {
    "dashscope": {
      "npm": "@ai-sdk/openai-compatible",
      "options": {
        "baseURL": "https://dashscope.aliyuncs.com/compatible-mode/v1"
      },
      "models": {
        "qwen3-coder-plus": {},
        "deepseek-r1": {}
      }
    }
  },
  "instructions": [
    "AGENTS.md"
  ]
}
```

---

## 八、Rules 内容翻译规则

把 `templates/continue_rules/*.md` 翻译到 `templates/opencode_agents/*.md.tpl` 时，遵循这些**确定性替换规则**：

### 8.1 术语映射表

| Continue 用语 | OpenCode 用语 |
|-------------|--------------|
| Continue Agent | 你 / OpenCode |
| Continue 聊天窗口 | OpenCode 终端 / OpenCode 会话 |
| Continue 的 read_file 工具 | OpenCode 的 read 工具 |
| Continue 的 edit_file 工具 | OpenCode 的 edit 工具 |
| 在 Continue 里 | 在 OpenCode 里 |
| `.continue/rules/` | `.opencode/agent/` |
| `.continue/prompts/` | `.opencode/command/` |
| 用户手动切换 Agent 模式 | 直接在终端交互 |

### 8.2 工具调用语法

Continue 的内置工具（tool_use 模型用）：
- `read_file(path)`
- `edit_file(path, changes)`
- `search_code(pattern)`
- `list_files(dir)`

OpenCode 的内置工具：
- `read(path)` 或 `read(path, offset, limit)`
- `edit(path, old_string, new_string)` 或 `write(path, content)`
- `grep(pattern, path)`
- `list(path)`
- `bash(command)` 或 `shell(command)`

**翻译规则：**
- `read_file` → `read`
- `edit_file` → `edit` 或 `write`（新建文件时）
- `search_code` / `search_files` → `grep`
- `list_files` → `list`
- 执行 shell 的部分保持不变（都是 `cmd /c "..."`）

### 8.3 模型 profile 的前置声明

Continue 的模型 profile 只能在 rules 内容里写"如果你是 DeepSeek-R1..."。

OpenCode 支持 agent 文件用 YAML frontmatter 声明触发条件：

```markdown
---
description: DeepSeek-R1 专用约束
model:
  - deepseek-r1
  - deepseek-reasoner
---
```

**翻译规则：** Continue 的 `stm32_model_<name>.md` → OpenCode 的 `.opencode/agent/model_<name>.md`（带 frontmatter）。

### 8.4 slash 命令拆分

Continue 的 `stm32_task_cookbook.md` 里包含 5 个任务类型的示例，在 OpenCode 里拆成 5 个独立 slash 命令：

- `stm32_task_cookbook.md` 的"任务类型 1：PWM 输出" → `.opencode/command/plan-pwm.md`
- 任务类型 2：GPIO 闪烁 → `.opencode/command/plan-gpio-blink.md`
- 任务类型 3：添加 CLI 命令 → `.opencode/command/plan-cli-command.md`
- 任务类型 4：ADC 采样 → `.opencode/command/plan-adc.md`
- 任务类型 5：定时中断 → `.opencode/command/plan-timer-interrupt.md`

用户可以直接在 OpenCode 里输入 `/plan-pwm 1kHz PA8 50%` 触发。

### 8.5 shell 语法规则的平台差异

`templates/continue_rules/stm32_powershell_syntax.md` 只讲 PowerShell。

`templates/opencode_agents/shell_syntax.md.tpl` 应该包含：
- PowerShell 段（Windows 用户）
- bash 段（macOS/Linux 用户）
- 自动识别：通过 `$OS` 或 shell 检测

---

## 九、测试与验收策略

### 9.1 新增测试清单

| 测试文件 | 覆盖内容 |
|---------|---------|
| `tests/test_agents_registry.py` | `get_platforms(cfg)` 按 active_platform 返回正确平台列表；`both` 模式返回 2 个 |
| `tests/test_opencode_migration.py` | `OpenCodePlatform.generate(cfg)` 生成 AGENTS.md、至少 4 个 agent、至少 5 个 command |
| `tests/test_opencode_migration.py::test_agents_md_content` | AGENTS.md 内容里包含 `{project_name}` 渲染后的项目名 |
| `tests/test_opencode_migration.py::test_slash_command_format` | slash 命令文件必须有 `---\ndescription: ...\n---\n` frontmatter |
| `tests/test_opencode_migration.py::test_model_frontmatter` | model_<name>.md 文件必须有 `model:` frontmatter 数组 |
| `tests/test_doctor.py` (扩展) | 测 active_platform=opencode 时 doctor 只检查 OpenCode；active_platform=both 时检查两者 |
| `tests/test_config.py` (新增) | 老版本 `continue:` 段自动迁移到 `agents.continue:`（向后兼容） |

### 9.2 端到端验收脚本

**位置：** `agent_workbench/tests/e2e/test_opencode_e2e.py`（新增）

```python
class OpenCodeE2ETests(unittest.TestCase):
    """端到端验证 OpenCode 生成产物的有效性"""
    
    def test_full_opencode_generation(self):
        # 1. 设置 active_platform=opencode
        # 2. 运行 init-opencode-agents
        # 3. 验证项目根有 AGENTS.md
        # 4. 验证 .opencode/agent/ 下有 4 个文件
        # 5. 验证 .opencode/command/ 下有 5 个文件
        # 6. 验证每个文件都包含项目专属的 ready_banner
        ...
    
    def test_both_platform_generation(self):
        # active_platform=both 时同时生成两套
        ...
    
    def test_agents_md_references_valid_commands(self):
        # AGENTS.md 里引用的 agent_workbench.bat 命令都真实存在
        ...
    
    def test_slash_commands_reference_valid_tools(self):
        # slash 命令里引用的 shell 命令都通过 ps-exec 合法化
        ...
```

### 9.3 兼容性回归测试

确保现有 Continue 路径完全不受影响：

- `tests/test_vscode_service.py` 现有测试继续通过
- `tests/test_doctor.py` 对 active_platform=continue 的情况和老版本一致
- 运行 `agent_workbench.bat init-continue-rules` 的结果和改造前完全一致（字节级比对）

### 9.4 验收标准

**阶段 1 验收：**
- [ ] `agent_workbench.bat init-opencode-agents --json` 能成功运行
- [ ] 生成的 `AGENTS.md` 包含项目绑定信息（project_name、ready_banner 等变量渲染）
- [ ] `.opencode/agent/` 下至少有 4 个 markdown 文件
- [ ] `.opencode/command/` 下至少有 5 个 slash 命令
- [ ] 所有新增测试通过

**阶段 2 验收：**
- [ ] `agent_workbench.bat init-agents --json` 能根据 `active_platform=both` 同时生成 Continue 和 OpenCode
- [ ] `doctor --json` 对 OpenCode 资产做检查，给出对应 ok/warn

**阶段 3 验收：**
- [ ] 在真实 OpenCode CLI 里打开项目，能看到 AGENTS.md 被加载
- [ ] 输入 `/plan-stm32 给 STM32 加 1kHz PWM PA8`，OpenCode 自动运行 plan 命令并返回结构化结果
- [ ] OpenCode 按 AGENTS.md 指引完成 build / flash / uart 验证全流程

---

## 十、分阶段实施路线图

### 阶段 1：适配层基础 + OpenCode 最小可用（1–2 周）

| 天数 | 任务 | 产出 |
|------|------|------|
| 2 | 抽象基类 + 注册表 | `core/agents/base.py`, `core/agents/registry.py` |
| 1 | Continue 适配器（把现有代码包装进类） | `core/agents/continue_platform.py` |
| 3 | OpenCode 适配器 | `core/agents/opencode_platform.py` |
| 2 | OpenCode 模板（AGENTS.md + 4 agents + 5 commands） | `templates/opencode_agents/*.tpl` |
| 1 | 配置段升级 + 向后兼容 | `core/config.py` |
| 1 | 新增 `init-opencode-agents` 和 `init-agents` 命令 | `workbench.py` |
| 2 | 测试套件 | `tests/test_agents_registry.py`, `tests/test_opencode_migration.py` |

**阶段 1 验收：** 用户把 `agent_workbench.yaml` 的 `agents.active_platform` 改为 `opencode`，运行 `init-opencode-agents` 后能看到完整 `AGENTS.md` + `.opencode/` 目录。

### 阶段 2：doctor 检查 + VS Code Tasks 适配（1 周）

| 天数 | 任务 | 产出 |
|------|------|------|
| 2 | doctor 重构为多平台检查 | `core/doctor.py` |
| 1 | `vscode_service.py` 里新增 OpenCode 相关 task | `core/vscode_service.py` |
| 1 | `project_scanner.py` 调整 | `core/project_scanner.py` |
| 1 | 用户文档 | `OPENCODE_AGENT_SETUP_ZH.md` |
| 2 | 完整回归测试 | 确保老流程 bit-level 一致 |

**阶段 2 验收：** `active_platform=both` 时 doctor 检查两套资产，VS Code 任务列表里多出"Init OpenCode Agents"等任务。

### 阶段 3：端到端验证 + 文档（1 周）

| 天数 | 任务 | 产出 |
|------|------|------|
| 2 | OpenCode 端到端测试 | `tests/e2e/test_opencode_e2e.py` |
| 2 | 文档完善 | `OPENCODE_AUTO_MODE_GUIDE_ZH.md`, `AGENT_PLATFORMS_COMPARISON_ZH.md` |
| 1 | MIGRATION_GUIDE_ZH.md 增加迁移章节 | 文档 |
| 2 | 实际在 OpenCode CLI 里跑一次 PWM 需求做人工验证 | 视频/截图证据 |

**阶段 3 验收：** 用户能按 OPENCODE_AUTO_MODE_GUIDE 从零配置 OpenCode，输入自然语言需求自动完成 STM32 功能开发。

### 阶段 4：迁移推广 + 废弃提示（按需）

如果项目决定长期只维护 OpenCode：

- 给 Continue 路径加 deprecation warning
- README 里把 OpenCode 标为"推荐"
- 保留 Continue 一个版本周期后再删除

---

## 十一、用户侧操作手册（迁移后）

### 11.1 新用户（全新项目 + OpenCode）

```powershell
# 1. 把 agent_workbench 拷贝到新项目
# 2. 修改配置
vim agent_workbench/agent_workbench.yaml
#   agents.active_platform: opencode
#   agents.opencode.required_agents: [...]

# 3. 一次性初始化
setup_workbench.bat
agent_workbench.bat doctor
agent_workbench.bat init-vscode
agent_workbench.bat init-opencode-agents    # 【新】生成 AGENTS.md 和 .opencode/
agent_workbench.bat build

# 4. 在 VS Code 集成终端里启动 OpenCode
opencode

# 5. 直接对话
> 给 STM32 加一个 CLI 命令 'echo hello'
```

### 11.2 已有 Continue 用户迁移到 OpenCode

```powershell
# 1. 修改配置
vim agent_workbench/agent_workbench.yaml
#   agents.active_platform: both    # 先双跑一段时间

# 2. 初始化两套资产
agent_workbench.bat init-agents

# 3. 测试 OpenCode 是否工作
opencode
> /plan-stm32 给 STM32 加 LED 闪烁

# 4. 确认 OK 后切换到纯 OpenCode
vim agent_workbench/agent_workbench.yaml
#   agents.active_platform: opencode

# 5. 可选：删除 Continue 生成物
rm -rf .continue/rules .continue/prompts
# agent_workbench.yaml 里的 continue: 段可以保留（作为 fallback）
```

### 11.3 在两个平台间切换

```powershell
# 切换到 Continue
sed -i 's/active_platform: opencode/active_platform: continue/' agent_workbench/agent_workbench.yaml

# 切换到 OpenCode
sed -i 's/active_platform: continue/active_platform: opencode/' agent_workbench/agent_workbench.yaml

# 同时跑
sed -i 's/active_platform:.*/active_platform: both/' agent_workbench/agent_workbench.yaml
```

---

## 十二、风险与兼容性保障

### 12.1 向后兼容性保障

**原则：老版本配置文件（只有顶层 `continue:` 段）必须继续能跑。**

`config.py` 里的适配逻辑：

```python
def _normalize_agents_section(raw):
    if "agents" not in raw:
        # 老版本自动迁移
        raw["agents"] = {
            "active_platform": "continue",
            "continue": raw.get("continue", {}),
            "opencode": _default_opencode_config(),
        }
    # 双向同步: 保留 raw["continue"] 指向同一份数据，老代码能继续读
    raw["continue"] = raw["agents"]["continue"]
```

所有现有用户的 `agent_workbench.bat init-continue-rules` 命令行为完全不变。

### 12.2 OpenCode 版本兼容性

OpenCode 在快速迭代，不同版本对 `AGENTS.md` / `.opencode/agent/` / `.opencode/command/` 的支持可能有差异。

**缓解措施：**

- 在 `opencode.json` 里声明 `"$schema"` 以便 OpenCode 做版本校验
- 在 `doctor` 检查里加 OpenCode 版本探测（通过 `opencode --version`）
- `OPENCODE_AGENT_SETUP_ZH.md` 里写明已验证的 OpenCode 版本范围（如 `>= 0.5.0`）

### 12.3 模板维护成本风险

双平台意味着 9 个 Continue 规则文件 + 10+ 个 OpenCode 文件需要同步维护。

**缓解措施：**

- 把"核心内容"抽出成**共享片段**（如 `templates/shared/core_workflow.md.inc`），两个平台的模板都 `include` 这个片段
- 规则：**确定性内容放共享，差异化内容放平台专属**
- 模板渲染时用 `{{include "core_workflow.md.inc"}}` 语法

**示例：**

```
templates/
├── shared/
│   ├── core_workflow.md.inc         # 两个平台共用的工作流
│   ├── hardware_safety.md.inc       # 两个平台共用的硬件安全规则
│   ├── shell_syntax.md.inc          # PowerShell/bash 两套语法
│   └── weak_model_guard.md.inc      # 弱模型通用约束
├── continue_rules/
│   ├── stm32_auto_workflow.md.tpl   # 只引用 shared/core_workflow.md.inc
│   └── ...
└── opencode_agents/
    ├── AGENTS.md.tpl                # 也引用 shared/core_workflow.md.inc
    └── ...
```

### 12.4 测试失败风险

现有 147 处 Continue 引用改动后可能破坏测试。

**缓解措施：**

- 严格按阶段实施，每阶段结束跑全量测试
- 先写 `test_agents_registry.py`（适配层测试），确保适配层行为符合预期，再改业务代码
- CI 里同时跑 `active_platform=continue` / `opencode` / `both` 三种配置

### 12.5 文档一致性风险

多份文档（CONTINUE_*, OPENCODE_*, README, MIGRATION_GUIDE）容易出现内容漂移。

**缓解措施：**

- 所有平台相关的"使用步骤"放到一处单一真源：`AGENT_PLATFORMS_COMPARISON_ZH.md`
- 其它文档只引用，不重复
- CI 加一个 lint 脚本：检查 README 里的命令示例和实际 `agent_workbench.bat --help` 输出一致

---

## 十三、给实施者的交底

### 13.1 严禁做的事

1. ❌ **不要删除 `core/vscode_service.py::write_continue_rules()`** —— 这是向后兼容的关键
2. ❌ **不要删除 `templates/continue_rules/` 目录** —— Continue 用户依然在用
3. ❌ **不要修改 `core/planner.py` / `core/build_errors.py` / `core/ps_exec.py` 等核心业务代码**（平台无关）
4. ❌ **不要修改 `agent_workbench.bat` 本身的任何子命令**（除 init-xxx 命令外）
5. ❌ **不要删除 `agent_workbench.yaml` 里的 `continue:` 段** —— 老用户需要

### 13.2 必做的事

1. ✅ **把 Continue 现有实现包装成 `ContinuePlatform` 适配器**（不破坏现有行为）
2. ✅ **新增 `OpenCodePlatform` 作为并列实现**
3. ✅ **引入 `agents.active_platform` 开关**
4. ✅ **所有新增文件都加单元测试**
5. ✅ **更新文档，但保留所有 Continue 相关文档**

### 13.3 工作流程

1. 先实现 `core/agents/base.py` + `registry.py`（约 200 行）
2. 把现有 `write_continue_rules` 改造成 `ContinuePlatform.generate()`（重构，不加功能）
3. 跑一遍测试确认 Continue 路径没坏
4. 实现 `OpenCodePlatform.generate()`
5. 写 OpenCode 模板（AGENTS.md + agents + commands）
6. 加测试
7. 实际在 OpenCode CLI 里跑一次做人工验收
8. 最后写用户文档

### 13.4 不确定点的处理策略

- **OpenCode 的 slash 命令语法有变动时** → 参考 OpenCode 当前版本官方文档（https://opencode.ai/docs），把版本号记在 `opencode.json.tpl` 顶部注释里
- **某些 Continue 规则在 OpenCode 里不必要时** → 不强求 1:1 翻译，可以合并/删除，但要在 `AGENT_PLATFORMS_COMPARISON_ZH.md` 里说明差异原因
- **遇到 OpenCode 不支持的特性** → 降级成"shell 命令调用方式"，不要尝试黑魔法

---

## 十四、总结

### 14.1 一句话方案

**保留 Continue 的一切，新增一个并列的 OpenCode 平台适配器，通过 `agents.active_platform` 开关切换。**

### 14.2 核心工作量

- 新增 ~25 个文件（主要是模板和测试）
- 修改 ~10 个文件（核心业务代码零修改，只改外壳层）
- 核心业务代码（plan / build / flash / uart / parse-errors）**零修改**

### 14.3 用户价值

- **Continue 用户零影响**（`active_platform=continue` 是默认值）
- **OpenCode 用户开箱即用**（修改一行配置 + 一条命令）
- **迁移过渡期可以双跑**（`active_platform=both`）
- **未来扩展容易**（按同样模式接 Cursor / Windsurf / Claude Code 等）

### 14.4 预计耗时

- 阶段 1（适配层 + OpenCode 最小可用）：1–2 周
- 阶段 2（doctor + VS Code tasks 适配）：1 周
- 阶段 3（端到端验证 + 文档）：1 周
- **总计：3–4 周（含人工验收和文档完善）**

---

**文档结束**

> 生成时间: 2026-04-19
> 版本: v1（OpenCode 兼容方案）
> 作者: AI Assistant
> 注：本文档只做方案规划，未做任何代码修改。
