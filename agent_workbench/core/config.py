from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - env specific
    raise RuntimeError(
        "PyYAML is required. Run agent_workbench\\bin\\setup.bat first."
    ) from exc

from .utils import WORKBENCH_ROOT


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"config not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data or {}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(merged.get(key), dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _resolve(path_text: str, root: Path) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else (root / path).resolve()


def _defaults() -> dict[str, Any]:
    return {
        "project": {
            "name": "STM32Project",
            "root": "..",
            "build_dir": "build",
            "artifact_elf": "build/SmartFarm.elf",
            "compile_commands": "build/compile_commands.json",
            "source_dirs": ["Core", "Drivers", "Middlewares", "cmake"],
        },
        "outputs": {
            "runtime_root": "agent_workbench/runtime",
            "evidence_root": "agent_workbench/evidence/sessions",
            "generated_root": "agent_workbench/generated",
        },
        "hardware": {
            "mode": "prefer",
        },
        "tools": {
            "cmake": {
                "generator": "MinGW Makefiles",
                "build_type": "Debug",
                "toolchain_file": "cmake/gcc-arm-none-eabi.cmake",
                "configure_args": [],
                "build_args": ["-j"],
            },
            "openocd": {
                "host": "127.0.0.1",
                "telnet_port": 4444,
                "startup_wait_sec": 3.0,
                "daemon_cmd": 'openocd -l "{openocd_live_log_posix}" -f interface/stlink.cfg -f target/stm32f1x.cfg -c "gdb_port 3333; tcl_port 6666; telnet_port 4444"',
            },
            "flash": {
                "default_method": "openocd_cmd",
                "methods": {
                    "stlink_cli": {
                        "flash": 'STM32_Programmer_CLI -c port=SWD -w "{artifact_elf}" -v -rst',
                        "reset": "STM32_Programmer_CLI -c port=SWD -rst",
                    },
                    "openocd_cmd": {
                        "flash": 'openocd -f interface/stlink.cfg -f target/stm32f1x.cfg -c "program {artifact_elf_posix} verify reset exit"',
                        "reset": 'openocd -f interface/stlink.cfg -f target/stm32f1x.cfg -c "init; reset run; shutdown"',
                    },
                },
            },
            "symbols_nm": "arm-none-eabi-nm",
        },
        "uart": {
            "enabled": True,
            "port": "COM5",
            "baudrate": 9600,
            "encoding": "utf-8",
            "line_timeout_sec": 0.2,
            "startup_drain_sec": 1.0,
            "ready_banner": "cli ready",
            "prompt": "cli>",
            "ready_timeout_sec": 5.0,
            "command_timeout_sec": 2.0,
            "exec_require_ready": True,
            "exec_fail_on_timeout": True,
            "probe_commands": ["help", "version", "state", "range", "alerts"],
            "help_rows": [],
        },
        "monitor": {
            "enabled": True,
            "sample_hz": 10,
            "ring_size": 2000,
            "export_interval_sec": 3,
            "openocd": {
                "host": "127.0.0.1",
                "port": 4444,
                "timeout_sec": 2.0,
            },
            "symbols": {
                "elf_path": "build/SmartFarm.elf",
            },
            "items": [],
        },
        "checks": {
            "unit": {
                "enabled": True,
                "command": '{python} -m unittest discover -s agent_workbench/tests -p "test_*.py"',
            },
        },
        "workflow": {
            "manage_openocd": True,
            "observe_seconds": 30,
            "auto_compare_previous": True,
            "verify_sequence": ["doctor", "build", "flash", "reset", "observe", "report"],
        },
        "vscode": {
            "tasks_file": ".vscode/tasks.json",
        },
        "prompts": {
            "debug": "prompts/continue_debug.md",
            "feature": "prompts/continue_feature.md",
            "test_author": "prompts/continue_test_author.md",
            "report": "prompts/continue_report.md",
        },
    }


def load_config(config_path: Path) -> dict[str, Any]:
    raw = _deep_merge(_defaults(), _load_yaml(config_path))
    workbench_root = config_path.parent.resolve()
    project_root = _resolve(raw["project"]["root"], workbench_root)

    raw["config_path"] = str(config_path.resolve())
    raw["agent_workbench_root_path"] = workbench_root
    raw["project_root_path"] = project_root
    raw["project"]["build_dir_path"] = _resolve(raw["project"]["build_dir"], project_root)
    raw["project"]["artifact_elf_path"] = _resolve(raw["project"]["artifact_elf"], project_root)
    raw["project"]["compile_commands_path"] = _resolve(raw["project"]["compile_commands"], project_root)
    raw["outputs"]["runtime_root_path"] = _resolve(raw["outputs"]["runtime_root"], project_root)
    raw["outputs"]["evidence_root_path"] = _resolve(raw["outputs"]["evidence_root"], project_root)
    raw["outputs"]["generated_root_path"] = _resolve(raw["outputs"]["generated_root"], project_root)
    raw["monitor"]["symbols"]["elf_path"] = str(_resolve(raw["monitor"]["symbols"]["elf_path"], project_root))
    raw["tools"]["cmake"]["toolchain_file_path"] = str(
        _resolve(raw["tools"]["cmake"]["toolchain_file"], project_root)
    )
    raw["vscode"]["tasks_file_path"] = _resolve(raw["vscode"]["tasks_file"], project_root)
    raw["prompts"]["debug_path"] = _resolve(raw["prompts"]["debug"], workbench_root)
    raw["prompts"]["feature_path"] = _resolve(raw["prompts"]["feature"], workbench_root)
    raw["prompts"]["test_author_path"] = _resolve(raw["prompts"]["test_author"], workbench_root)
    raw["prompts"]["report_path"] = _resolve(raw["prompts"]["report"], workbench_root)
    raw["template_values"] = {
        "python": sys.executable,
        "project_root": str(project_root),
        "workbench_root": str(workbench_root),
        "build_dir": str(raw["project"]["build_dir_path"]),
        "build_dir_posix": str(raw["project"]["build_dir_path"]).replace("\\", "/"),
        "artifact_elf": str(raw["project"]["artifact_elf_path"]),
        "artifact_elf_posix": str(raw["project"]["artifact_elf_path"]).replace("\\", "/"),
        "toolchain_file": str(raw["tools"]["cmake"]["toolchain_file_path"]),
        "toolchain_file_posix": str(raw["tools"]["cmake"]["toolchain_file_path"]).replace("\\", "/"),
        "openocd_live_log": str(raw["outputs"]["runtime_root_path"] / "openocd_live" / "openocd.log"),
        "openocd_live_log_posix": str(raw["outputs"]["runtime_root_path"] / "openocd_live" / "openocd.log").replace("\\", "/"),
    }
    return raw
