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
    - .opencode/agent/model_<name>.md (model profiles)
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
        tpl_source = template_dir / "agent" / f"{name}.tpl"
        if not tpl_source.exists():
            tpl_source = template_dir / "agent" / name
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
