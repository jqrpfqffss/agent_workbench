from __future__ import annotations

import json
import os
from pathlib import Path

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
            {"label": "Agent Workbench: Setup", "type": "shell", "command": "setup_workbench.bat", "problemMatcher": []},
            {"label": "Agent Workbench: Doctor", "type": "shell", "command": f"{wrapper} doctor", "problemMatcher": []},
            {"label": "Agent Workbench: Build", "type": "shell", "command": f"{wrapper} build", "group": {"kind": "build", "isDefault": True}, "problemMatcher": []},
            {"label": "Agent Workbench: Debug Session", "type": "shell", "command": f"{wrapper} session debug", "problemMatcher": []},
            {"label": "Agent Workbench: Compare Latest", "type": "shell", "command": f"{wrapper} compare --latest", "problemMatcher": []},
            {"label": "Agent Workbench: Test Generate (Example)", "type": "shell", "command": f"{wrapper} test generate --task {example_task}", "problemMatcher": []},
            {"label": "Agent Workbench: Test Generate (CLI Regression)", "type": "shell", "command": f"{wrapper} test generate --task {cli_regression_task}", "problemMatcher": []},
            {"label": "Agent Workbench: Test Run", "type": "shell", "command": f"{wrapper} test run", "problemMatcher": []},
            {"label": "Agent Workbench: UART Console", "type": "shell", "command": f"{wrapper} uart console", "problemMatcher": []},
            {"label": "Agent Workbench: UART CLI Smoke", "type": "shell", "command": f"{wrapper} uart exec --reset-first --expect-ready --command help --command status --command red on --command green on --command blue on --command all off", "problemMatcher": []},
            {"label": "Agent Workbench: Monitor Start", "type": "shell", "command": f"{wrapper} monitor start", "problemMatcher": []},
            {"label": "Agent Workbench: Monitor Stop", "type": "shell", "command": f"{wrapper} monitor stop", "problemMatcher": []},
            {"label": "Agent Workbench: OpenOCD Start", "type": "shell", "command": f"{wrapper} openocd start", "problemMatcher": []},
            {"label": "Agent Workbench: OpenOCD Stop", "type": "shell", "command": f"{wrapper} openocd stop", "problemMatcher": []},
            {"label": "Agent Workbench: Flash (ST-Link)", "type": "shell", "command": f"{wrapper} flash --method stlink_cli", "problemMatcher": []},
            {"label": "Agent Workbench: Flash (OpenOCD)", "type": "shell", "command": f"{wrapper} flash --method openocd_cmd", "problemMatcher": []},
            {"label": "Agent Workbench: Feature Session (Example)", "type": "shell", "command": f"{wrapper} session feature --task {example_task}", "problemMatcher": []},
            {"label": "Agent Workbench: Feature Session (CLI Regression)", "type": "shell", "command": f"{wrapper} session feature --task {cli_regression_task}", "problemMatcher": []},
        ],
    }
    tasks_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return tasks_path
