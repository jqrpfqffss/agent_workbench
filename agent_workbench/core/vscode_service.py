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


def _ps_safe(command_text: str) -> str:
    return f'cmd /c ".\\{command_text}"'


def _write_runtime_continue_prompts(cfg: dict) -> list[Path]:
    project_root = Path(cfg["project_root_path"])
    runtime_root = Path(cfg["outputs"]["continue_runtime_root_path"])
    default_profile = str(cfg.get("agent", {}).get("default_profile", "balanced_local")).strip() or "balanced_local"
    prompt_roots = [runtime_root]
    continue_root = project_root / ".continue" / "prompts"
    if continue_root.parent.parent.exists():
        prompt_roots.append(continue_root)

    payloads = {
        "local_model_debug_analyze.md": (
            "# Local Model Debug Analyze\n\n"
            "```text\n"
            "Run the VS Code task: Agent Workbench: Context Pack (Debug Analyze)\n"
            "Then open the newest *_paste.md file under agent_workbench/runtime and paste it into Continue Agent.\n"
            f"The selected local-model profile comes from agent_workbench.yaml: {default_profile}.\n"
            "This round is analyze-only. Do not change code.\n"
            "```\n"
        ),
        "local_model_feature_implement.md": (
            "# Local Model Feature Implement\n\n"
            "```text\n"
            "Run the VS Code task: Agent Workbench: Context Pack (Feature Implement)\n"
            "Then open the newest *_paste.md file under agent_workbench/runtime and paste it into Continue Agent.\n"
            f"The selected local-model profile comes from agent_workbench.yaml: {default_profile}.\n"
            "This round is implement-only. Edit only allowed files.\n"
            "```\n"
        ),
        "local_model_feature_verify.md": (
            "# Local Model Feature Verify\n\n"
            "```text\n"
            "Run the VS Code task: Agent Workbench: Context Pack (Feature Verify)\n"
            "Then open the newest *_paste.md file under agent_workbench/runtime and paste it into Continue Agent.\n"
            f"The selected local-model profile comes from agent_workbench.yaml: {default_profile}.\n"
            "This round is verify-only. Run workbench commands and summarize evidence.\n"
            "```\n"
        ),
        "local_model_resume.md": (
            "# Local Model Resume\n\n"
            "```text\n"
            "Run the VS Code task: Agent Workbench: Resume Latest Local-Model Task\n"
            "Then open the newest *_paste.md file under agent_workbench/runtime and paste it into Continue Agent.\n"
            f"The selected local-model profile comes from agent_workbench.yaml: {default_profile}.\n"
            "This round resumes from the saved agent_state.json.\n"
            "```\n"
        ),
        "local_model_direct_verify.md": (
            "# Local Model Direct Verify\n\n"
            "```text\n"
            "Run the VS Code task: Agent Workbench: Direct Verify (CLI Regression)\n"
            "Or run exactly this PowerShell-safe command from the workspace root:\n"
            "cmd /c \".\\agent_workbench.bat verify current --task agent_workbench/tasks/cli_automation_regression.yaml\"\n"
            "Then read agent_workbench/runtime/direct_verify_summary.md first.\n"
            f"The selected local-model profile comes from agent_workbench.yaml: {default_profile}.\n"
            "This path is for immediate validation with one workbench command.\n"
            "```\n"
        ),
    }

    generated: list[Path] = []
    for root in prompt_roots:
        ensure_dir(root)
        for name, text in payloads.items():
            path = root / name
            path.write_text(text, encoding="utf-8")
            generated.append(path)
    return generated


def write_vscode_tasks(cfg: dict) -> Path:
    tasks_path = Path(cfg["vscode"]["tasks_file_path"])
    ensure_dir(tasks_path.parent)
    paths = _command_paths(cfg)
    write_project_wrappers(cfg)
    _write_runtime_continue_prompts(cfg)
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
            {"label": "Agent Workbench: Context Pack (Debug Analyze)", "type": "shell", "command": _ps_safe(f"{wrapper} context --mode debug --stage analyze"), "problemMatcher": []},
            {"label": "Agent Workbench: Context Pack (Feature Implement)", "type": "shell", "command": _ps_safe(f"{wrapper} context --mode feature --stage implement --task {cli_regression_task}"), "problemMatcher": []},
            {"label": "Agent Workbench: Context Pack (Feature Verify)", "type": "shell", "command": _ps_safe(f"{wrapper} context --mode feature --stage verify --task {cli_regression_task}"), "problemMatcher": []},
            {"label": "Agent Workbench: Context Pack (Test Analyze)", "type": "shell", "command": _ps_safe(f"{wrapper} context --mode test --stage analyze --task {cli_regression_task}"), "problemMatcher": []},
            {"label": "Agent Workbench: Resume Latest Local-Model Task", "type": "shell", "command": _ps_safe(f"{wrapper} context --stage resume"), "problemMatcher": []},
            {"label": "Agent Workbench: Direct Verify (CLI Regression)", "type": "shell", "command": _ps_safe(f"{wrapper} verify current --task {cli_regression_task}"), "problemMatcher": []},
            {"label": "Agent Workbench: Report Latest Verdict", "type": "shell", "command": _ps_safe(f"{wrapper} report --latest"), "problemMatcher": []},
            {"label": "Agent Workbench: Debug Session", "type": "shell", "command": _ps_safe(f"{wrapper} session debug"), "problemMatcher": []},
            {"label": "Agent Workbench: Compare Latest", "type": "shell", "command": _ps_safe(f"{wrapper} compare --latest"), "problemMatcher": []},
            {"label": "Agent Workbench: Test Generate (Example)", "type": "shell", "command": _ps_safe(f"{wrapper} test generate --task {example_task}"), "problemMatcher": []},
            {"label": "Agent Workbench: Test Generate (CLI Regression)", "type": "shell", "command": _ps_safe(f"{wrapper} test generate --task {cli_regression_task}"), "problemMatcher": []},
            {"label": "Agent Workbench: Test Run", "type": "shell", "command": _ps_safe(f"{wrapper} test run"), "problemMatcher": []},
            {"label": "Agent Workbench: UART Console", "type": "shell", "command": _ps_safe(f"{wrapper} uart console"), "problemMatcher": []},
            {"label": "Agent Workbench: UART CLI Smoke", "type": "shell", "command": _ps_safe(f"{wrapper} uart exec --reset-first --expect-ready --command help --command status"), "problemMatcher": []},
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
