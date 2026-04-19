# agent_workbench 集成包作者指南

`agent_workbench` 的设计目标是让核心 CLI 保持前端中立，而把 OpenCode、Continue、Cursor、Cline 一类的前端适配放进独立 integration 包。

## 为什么要有 integration 包

好处有三点：

1. 核心能力和前端配置解耦。
2. 新增一个前端时，不需要修改 `core/`。
3. `doctor`、`scan-project`、`integration list/install/check/remove` 可以统一处理所有前端。

## 目录约定

每个 integration 放在：

```text
agent_workbench/integrations/<name>/
├─ manifest.yaml
├─ README_ZH.md
└─ files/
   └─ ...
```

其中：

- `manifest.yaml` 定义要生成的文件清单和 doctor 检查规则
- `files/` 存放模板文件
- `README_ZH.md` 说明这个前端怎么安装和使用

## manifest.yaml 规范

最小结构：

```yaml
id: opencode
display_name: OpenCode
description: OpenCode agent + slash commands for STM32 workflow

files:
  - src: AGENTS.md.tpl
    dst: AGENTS.md
    render: true

uses_values:
  - project_name
  - ready_banner
  - prompt

doctor:
  required_files:
    - AGENTS.md
  markers:
    AGENTS.md:
      - "{project_name}"
```

规则说明：

- `src` 相对 `files/`
- `dst` 相对项目根目录
- `render` 缺省为 `true`
- 模板只支持 `{key}` 这种简单替换

## 可用模板变量

当前 integration 可以使用的变量包括：

- `project_name`
- `ready_banner`
- `prompt`
- `uart_port`
- `uart_baud`
- `diag_uart_port`
- `build_dir`
- `default_profile`
- `source_dirs_csv`

这些值由 `core/integrations_service.py` 从配置文件统一派生。

## 提交流程

新增一个 integration 的典型步骤：

1. 新建 `integrations/<name>/manifest.yaml`
2. 把模板放到 `integrations/<name>/files/`
3. 编写 `integrations/<name>/README_ZH.md`
4. 运行：

```powershell
cmd /c ".\agent_workbench.bat integration list --json"
cmd /c ".\agent_workbench.bat integration install <name> --json"
cmd /c ".\agent_workbench.bat integration check <name> --json"
cmd /c ".\agent_workbench.bat test run --json"
```

## 例子：新增一个 cursor integration

目录结构示意：

```text
agent_workbench/integrations/cursor/
├─ manifest.yaml
├─ README_ZH.md
└─ files/
   ├─ cursor-rules.md.tpl
   └─ settings.json.tpl
```

如果文件之间没有冲突，核心代码通常不需要任何 Python 改动。
