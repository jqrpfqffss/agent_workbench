from __future__ import annotations

import json
import os
from pathlib import Path

from .integrations_service import discover_integrations
from .utils import ensure_dir


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


def write_vscode_tasks(cfg: dict) -> Path:
    tasks_path = Path(cfg["vscode"]["tasks_file_path"])
    ensure_dir(tasks_path.parent)
    paths = _command_paths(cfg)
    write_project_wrappers(cfg)
    wrapper = paths["wrapper"]
    example_task = paths["example_task"]
    cli_task = paths["cli_task"]
    cli_regression_task = paths["cli_regression_task"]
    integration_tasks = [
        {
            "label": f"Agent Workbench: Install Integration ({manifest.display_name})",
            "type": "shell",
            "command": _ps_safe(f"{wrapper} integration install {manifest.id}"),
            "problemMatcher": [],
        }
        for manifest in discover_integrations(Path(cfg["agent_workbench_root_path"]))
    ]
    payload = {
        "version": "2.0.0",
        "tasks": [
            {"label": "Agent Workbench: Setup", "type": "shell", "command": _ps_safe("setup_workbench.bat"), "problemMatcher": []},
            {"label": "Agent Workbench: Doctor", "type": "shell", "command": _ps_safe(f"{wrapper} doctor"), "problemMatcher": []},
            {"label": "Agent Workbench: Build", "type": "shell", "command": _ps_safe(f"{wrapper} build"), "group": {"kind": "build", "isDefault": True}, "problemMatcher": []},
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
            {"label": "Agent Workbench: Verify CLI Task", "type": "shell", "command": _ps_safe(f"{wrapper} verify current --task {cli_task}"), "problemMatcher": []},
            *integration_tasks,
        ],
    }
    tasks_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return tasks_path
