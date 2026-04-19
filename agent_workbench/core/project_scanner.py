from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from .task_spec import load_task_spec


_INIT_PATTERN = re.compile(r"\b(MX_[A-Za-z0-9_]+_Init)\s*\(")
_HANDLE_PATTERN = re.compile(r"\b([A-Za-z0-9_]+_HandleTypeDef)\s+([A-Za-z0-9_]+)\s*;")
_USER_CODE_BEGIN_RE = re.compile(r"/\*\s*USER CODE BEGIN (?P<name>.+?)\s*\*/")
_USER_CODE_END_RE = re.compile(r"/\*\s*USER CODE END (?P<name>.+?)\s*\*/")
_CLI_COMMAND_ENTRY_RE = re.compile(
    r'\{\s*"(?P<command>[A-Za-z_][A-Za-z0-9_]*)"\s*,\s*"(?P<summary>[^"]*)"\s*,\s*"(?P<usage>[^"]*)"\s*,\s*(?P<handler>[A-Za-z_][A-Za-z0-9_]*)\s*\}'
)


def _safe_absolute(path: Path) -> Path:
    try:
        return path.resolve()
    except Exception:
        return Path(os.path.abspath(str(path)))


def _relative_posix(path: Path, root: Path) -> str:
    absolute = _safe_absolute(path)
    try:
        return absolute.relative_to(_safe_absolute(root)).as_posix()
    except ValueError:
        return absolute.as_posix()


def _source_dirs(cfg: dict) -> list[Path]:
    project_root = Path(cfg["project_root_path"])
    raw_items = cfg.get("project", {}).get("source_dirs", [])
    dirs: list[Path] = []
    for item in raw_items:
        path = project_root / str(item)
        if path.exists():
            dirs.append(path)
    return dirs


def _excluded_roots(cfg: dict) -> list[Path]:
    roots: list[Path] = []
    outputs = cfg.get("outputs", {})
    for key in ("runtime_root_path", "evidence_root_path", "generated_root_path"):
        raw = outputs.get(key)
        if raw:
            roots.append(_safe_absolute(Path(raw)))
    return roots


def _is_excluded_path(path: Path, excluded_roots: list[Path]) -> bool:
    absolute = _safe_absolute(path)
    if "__pycache__" in absolute.parts:
        return True
    return any(root == absolute or root in absolute.parents for root in excluded_roots)


def _iter_source_paths(cfg: dict) -> list[Path]:
    excluded = _excluded_roots(cfg)
    files: list[Path] = []
    for directory in _source_dirs(cfg):
        for current_root, dirnames, filenames in os.walk(directory, topdown=True, onerror=lambda _: None):
            current_root_path = Path(current_root)
            dirnames[:] = sorted(
                name for name in dirnames if not _is_excluded_path(current_root_path / name, excluded)
            )
            for filename in sorted(filenames):
                path = current_root_path / filename
                if _is_excluded_path(path, excluded):
                    continue
                if path.suffix.lower() in {".c", ".h", ".cpp", ".hpp", ".s", ".ld"}:
                    files.append(path)
    return files


def _scan_source_files(cfg: dict) -> list[str]:
    project_root = Path(cfg["project_root_path"])
    return [_relative_posix(path, project_root) for path in _iter_source_paths(cfg)]


def _scan_init_functions(cfg: dict) -> list[str]:
    project_root = Path(cfg["project_root_path"])
    main_path = project_root / "Core" / "Src" / "main.c"
    if not main_path.exists():
        return []
    text = main_path.read_text(encoding="utf-8", errors="ignore")
    values: list[str] = []
    seen: set[str] = set()
    for match in _INIT_PATTERN.finditer(text):
        name = match.group(1)
        if name not in seen:
            seen.add(name)
            values.append(name)
    return values


def _scan_existing_handles(cfg: dict) -> list[dict[str, Any]]:
    project_root = Path(cfg["project_root_path"])
    preferred = [
        project_root / "Core" / "Src" / "main.c",
        project_root / "Core" / "Inc" / "main.h",
    ]
    candidates = [path for path in preferred if path.exists()]
    for path in _iter_source_paths(cfg):
        if path not in candidates:
            candidates.append(path)

    results: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for path in candidates:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(text.splitlines(), start=1):
            match = _HANDLE_PATTERN.search(line)
            if not match:
                continue
            handle_type = match.group(1)
            name = match.group(2)
            key = (handle_type, name)
            if key in seen:
                continue
            seen.add(key)
            results.append(
                {
                    "type": handle_type,
                    "name": name,
                    "file": _relative_posix(path, project_root),
                    "line": lineno,
                }
            )
    return results


def _scan_user_code_regions(cfg: dict) -> list[dict[str, Any]]:
    project_root = Path(cfg["project_root_path"])
    results: list[dict[str, Any]] = []
    for relative in ("Core/Src/main.c", "Core/Inc/main.h"):
        path = project_root / Path(relative)
        if not path.exists():
            continue
        begin_markers: dict[str, int] = {}
        for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            begin = _USER_CODE_BEGIN_RE.search(line)
            if begin:
                begin_markers[begin.group("name").strip()] = lineno
                continue
            end = _USER_CODE_END_RE.search(line)
            if not end:
                continue
            name = end.group("name").strip()
            start_line = begin_markers.get(name)
            if start_line is None:
                continue
            results.append(
                {
                    "name": f"USER CODE BEGIN {name}",
                    "file": relative,
                    "start_line": start_line,
                    "end_line": lineno,
                    "begin_marker": f"/* USER CODE BEGIN {name} */",
                    "end_marker": f"/* USER CODE END {name} */",
                }
            )
    return results


def _scan_cli_commands_from_sources(cfg: dict) -> list[dict[str, Any]]:
    project_root = Path(cfg["project_root_path"])
    candidates = [
        path
        for path in _iter_source_paths(cfg)
        if path.suffix.lower() == ".c" and "cli" in path.name.lower()
    ]
    commands: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in candidates:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(text.splitlines(), start=1):
            match = _CLI_COMMAND_ENTRY_RE.search(line)
            if not match:
                continue
            command = match.group("command").strip()
            if command in seen:
                continue
            seen.add(command)
            commands.append(
                {
                    "command": command,
                    "summary": match.group("summary").strip(),
                    "usage": match.group("usage").strip(),
                    "handler": match.group("handler").strip(),
                    "file": _relative_posix(path, project_root),
                    "line": lineno,
                }
            )
    return commands


def _scan_tasks(cfg: dict) -> list[dict[str, Any]]:
    project_root = Path(cfg["project_root_path"])
    task_root = Path(cfg["agent_workbench_root_path"]) / "tasks"
    items: list[dict[str, Any]] = []
    if not task_root.exists():
        return items
    for path in sorted(task_root.glob("*.yaml")):
        try:
            spec = load_task_spec(path, strict=False)
        except Exception:
            spec = {}
        items.append(
            {
                "path": _relative_posix(path, project_root),
                "id": str(spec.get("id", path.stem)),
                "mode": str(spec.get("mode", "")),
                "goal": str(spec.get("goal", "")),
            }
        )
    return items


def _scan_planner_templates(cfg: dict) -> list[str]:
    template_root = Path(cfg.get("planner", {}).get("templates_dir_path", ""))
    if not template_root.exists():
        return []
    return [path.name for path in sorted(template_root.glob("*.yaml"))]


def scan_project(cfg: dict) -> dict[str, Any]:
    project_root = Path(cfg["project_root_path"])
    source_files = _scan_source_files(cfg)
    planner_templates = _scan_planner_templates(cfg)
    parsed_cli_commands = _scan_cli_commands_from_sources(cfg)

    cli_commands = [item["command"] for item in parsed_cli_commands]
    for item in cfg.get("uart", {}).get("help_rows", []):
        command = str(item.get("command", "")).strip()
        if command and command not in cli_commands:
            cli_commands.append(command)
    for probe in cfg.get("uart", {}).get("probe_commands", []):
        command = str(probe).strip()
        if command and command not in cli_commands:
            cli_commands.append(command)

    payload = {
        "project": {
            "name": cfg.get("project", {}).get("name", ""),
            "root": str(project_root),
            "build_dir": str(cfg.get("project", {}).get("build_dir_path", "")),
        },
        "source_dirs": [path.name for path in _source_dirs(cfg)],
        "source_files": source_files,
        "source_file_count": len(source_files),
        "detected_init_functions": _scan_init_functions(cfg),
        "existing_handles": _scan_existing_handles(cfg),
        "user_code_regions": _scan_user_code_regions(cfg),
        "cli_commands": parsed_cli_commands,
        "uart": {
            "enabled": bool(cfg.get("uart", {}).get("enabled", True)),
            "ready_banner": str(cfg.get("uart", {}).get("ready_banner", "")),
            "prompt": str(cfg.get("uart", {}).get("prompt", "")),
            "probe_commands": [
                str(item).strip()
                for item in cfg.get("uart", {}).get("probe_commands", [])
                if str(item).strip()
            ],
            "help_commands": cli_commands,
        },
        "tasks": _scan_tasks(cfg),
        "planner_templates": planner_templates,
        "planner_template_count": len(planner_templates),
        "opencode_agents_file": str(cfg.get("opencode", {}).get("agents_file_path", "")),
        "opencode_agents_dir": str(cfg.get("opencode", {}).get("agents_dir_path", "")),
        "opencode_commands_dir": str(cfg.get("opencode", {}).get("commands_dir_path", "")),
    }
    compile_commands_path = Path(cfg.get("project", {}).get("compile_commands_path", ""))
    if compile_commands_path.exists():
        try:
            payload["compile_commands_entries"] = len(json.loads(compile_commands_path.read_text(encoding="utf-8")))
        except Exception:
            payload["compile_commands_entries"] = 0
    else:
        payload["compile_commands_entries"] = 0
    return payload
