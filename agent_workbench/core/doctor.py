from __future__ import annotations

import sys
from pathlib import Path

from .diag_uart_service import SERIAL_IMPORT_ERROR as DIAG_SERIAL_IMPORT_ERROR
from .diag_uart_service import diag_exec_supported, serial as diag_serial
from .task_spec import load_task_spec
from .uart_service import SERIAL_IMPORT_ERROR, serial, uart_exec_supported
from .utils import can_write_directory, command_exists, command_head, render_template, write_json


def _append(results: list[dict], name: str, level: str, detail: str) -> None:
    results.append({"name": name, "level": level, "detail": detail})


def _required_hardware(cfg: dict) -> bool:
    return cfg.get("hardware", {}).get("mode", "prefer").lower() == "required"


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        import json

        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _word_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for item in path.read_text(encoding="utf-8", errors="ignore").split() if item.strip())


def _line_count(path: Path) -> int:
    if not path.exists():
        return 0
    return len(path.read_text(encoding="utf-8", errors="ignore").splitlines())


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
        text = agents_file.read_text(encoding="utf-8", errors="ignore")
        markers = [
            str(cfg.get("project", {}).get("name", "")).strip(),
            str(cfg.get("uart", {}).get("ready_banner", "")).strip(),
            str(cfg.get("uart", {}).get("prompt", "")).strip(),
        ]
        markers = [marker for marker in markers if marker]
        bound = bool(markers) and all(marker in text for marker in markers)
        _append(
            results,
            "opencode_agents_binding",
            "ok" if bound else "warn",
            "project name and UART markers injected into AGENTS.md" if bound else "generated AGENTS.md does not appear to contain current project markers",
        )

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

    # 检查模型 profile 文件
    model_profiles = oc_cfg.get("model_profiles") or {}
    missing_profiles: list[str] = []
    for profile_name, meta in model_profiles.items():
        if not isinstance(meta, dict):
            continue
        target = agents_dir / f"model_{profile_name}.md"
        if not target.exists():
            missing_profiles.append(profile_name)
    if model_profiles:
        level = "ok" if not missing_profiles else "warn"
        detail = "all model profile files present" if not missing_profiles else f"missing={','.join(missing_profiles)}"
        _append(results, "opencode_model_profiles", level, detail)


def _check_planner_templates(cfg: dict, results: list[dict]) -> None:
    planner_cfg = cfg.get("planner", {})
    if not planner_cfg:
        _append(results, "planner_templates", "warn", "planner not configured")
        return
    template_dir = Path(planner_cfg.get("templates_dir_path", ""))
    if not template_dir.exists():
        _append(results, "planner_templates", "fail", f"missing {template_dir}")
        return
    templates = sorted(template_dir.glob("*.yaml"))
    minimum = int(planner_cfg.get("minimum_template_count", 15))
    level = "ok" if len(templates) >= minimum else "warn"
    _append(results, "planner_templates", level, f"count={len(templates)} minimum={minimum}")


def _check_migration_docs(cfg: dict, results: list[dict]) -> None:
    if "agent_workbench_root_path" not in cfg:
        _append(results, "migration_docs", "warn", "agent_workbench_root_path not configured")
        return
    root = Path(cfg.get("agent_workbench_root_path", ""))
    required_docs = {
        root / "README.md": ["OpenCode Auto Mode", "Local-Model Workflow"],
        root / "MIGRATION_GUIDE_ZH.md": ["agent_workbench 迁移指南", "init-opencode-agents"],
        root / "OPENCODE_AUTO_MODE_GUIDE_ZH.md": ["OpenCode", "init-opencode-agents"],
    }
    missing = [path.name for path in required_docs if not path.exists()]
    unreadable: list[str] = []
    for path, markers in required_docs.items():
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if not all(marker in text for marker in markers):
            unreadable.append(path.name)
    if missing:
        level = "warn"
        detail = f"missing={','.join(missing)}"
    elif unreadable:
        level = "warn"
        detail = f"missing key sections in {','.join(unreadable)}"
    else:
        level = "ok"
        detail = "migration docs ready"
    _append(results, "migration_docs", level, detail)


def run_doctor(cfg: dict, output_dir: Path) -> tuple[int, dict]:
    results: list[dict] = []
    required_hardware = _required_hardware(cfg)

    _append(results, "python", "ok", sys.executable)

    try:
        import yaml  # type: ignore  # noqa: F401
        _append(results, "yaml", "ok", "PyYAML available")
    except Exception as exc:
        _append(results, "yaml", "fail", str(exc))

    for name, path in (
        ("runtime_root", cfg["outputs"]["runtime_root_path"]),
        ("evidence_root", cfg["outputs"]["evidence_root_path"]),
        ("generated_root", cfg["outputs"]["generated_root_path"]),
    ):
        ok, detail = can_write_directory(path)
        _append(results, name, "ok" if ok else "fail", detail)

    _append(results, "cmake", "ok" if command_exists("cmake") else "fail", "cmake")

    toolchain = Path(cfg["tools"]["cmake"]["toolchain_file_path"])
    _append(results, "toolchain_file", "ok" if toolchain.exists() else "fail", str(toolchain))

    artifact = Path(cfg["project"]["artifact_elf_path"])
    _append(results, "artifact_elf", "ok" if artifact.exists() else "warn", str(artifact))

    compile_commands = Path(cfg["project"]["compile_commands_path"])
    _append(results, "compile_commands", "ok" if compile_commands.exists() else "warn", str(compile_commands))

    openocd_command = render_template(cfg["tools"]["openocd"].get("daemon_cmd", ""), cfg["template_values"])
    openocd_level = "ok" if command_exists(openocd_command) else ("fail" if required_hardware else "warn")
    _append(results, "openocd", openocd_level, command_head(openocd_command) or "missing")

    flash_method = cfg["tools"]["flash"].get("default_method", "stlink_cli")
    flash_cfg = cfg["tools"]["flash"].get("methods", {}).get(flash_method, {})
    flash_command = render_template(flash_cfg.get("flash", ""), cfg["template_values"])
    flash_level = "ok" if command_exists(flash_command) else ("fail" if required_hardware else "warn")
    _append(results, "flash_method", flash_level, f"{flash_method}: {command_head(flash_command) or 'missing'}")

    if cfg["uart"].get("enabled", True):
        _append(
            results,
            "uart_protocol",
            "ok",
            f"ready_banner={cfg['uart'].get('ready_banner', 'cli ready')} prompt={cfg['uart'].get('prompt', 'cli>')}",
        )
        if serial is None:
            if uart_exec_supported():
                level = "warn"
                detail = (
                    f"pyserial unavailable: {SERIAL_IMPORT_ERROR}. "
                    "PowerShell UART fallback is available for CLI exec and logging, but interactive console still prefers pyserial."
                )
            else:
                level = "fail" if required_hardware else "warn"
                detail = (
                    f"pyserial unavailable: {SERIAL_IMPORT_ERROR}. "
                    "Re-run setup or set SMARTFARM_PYTHON to a Python with PyYAML and pyserial."
                )
            _append(
                results,
                "uart_backend",
                level,
                detail,
            )
        else:
            _append(results, "uart_backend", "ok", "pyserial available")
            try:
                with serial.Serial(
                    cfg["uart"]["port"],
                    int(cfg["uart"]["baudrate"]),
                    timeout=float(cfg["uart"].get("line_timeout_sec", 0.2)),
                ):
                    _append(results, "uart_port", "ok", cfg["uart"]["port"])
            except Exception as exc:
                level = "fail" if required_hardware else "warn"
                _append(results, "uart_port", level, str(exc))
    else:
        _append(results, "uart_backend", "warn", "UART disabled by config")

    diag_cfg = cfg.get("diag_uart", {})
    if diag_cfg.get("enabled", True):
        default_requests = [str(item).strip() for item in diag_cfg.get("default_hex_requests", []) if str(item).strip()]
        _append(
            results,
            "diag_uart_requests",
            "ok" if default_requests else "warn",
            f"count={len(default_requests)} port={diag_cfg.get('port', '')}",
        )
        if diag_serial is None:
            if diag_exec_supported():
                level = "warn"
                detail = (
                    f"pyserial unavailable: {DIAG_SERIAL_IMPORT_ERROR}. "
                    "PowerShell fallback is available for diag exec."
                )
            else:
                level = "fail" if required_hardware else "warn"
                detail = (
                    f"pyserial unavailable: {DIAG_SERIAL_IMPORT_ERROR}. "
                    "Re-run setup or use a Python with PyYAML and pyserial."
                )
            _append(results, "diag_uart_backend", level, detail)
            _append(results, "diag_uart_port", "warn", "port availability not checked without pyserial")
        else:
            _append(results, "diag_uart_backend", "ok", "pyserial available")
            try:
                with diag_serial.Serial(
                    diag_cfg["port"],
                    int(diag_cfg["baudrate"]),
                    timeout=float(diag_cfg.get("read_timeout_sec", 0.05)),
                ):
                    _append(results, "diag_uart_port", "ok", str(diag_cfg["port"]))
            except Exception as exc:
                level = "fail" if required_hardware else "warn"
                _append(results, "diag_uart_port", level, str(exc))
    else:
        _append(results, "diag_uart_backend", "warn", "diag_uart disabled by config")

    agent_cfg = cfg.get("agent", {})
    profiles = agent_cfg.get("profiles", {})
    default_profile = str(agent_cfg.get("default_profile", "balanced_local")).strip() or "balanced_local"
    profile = profiles.get(default_profile)
    if not profile:
        _append(results, "agent_profile", "fail", f"missing agent profile: {default_profile}")
    else:
        required_keys = [
            "max_pack_words",
            "max_fact_items",
            "max_cli_tail_lines",
            "max_failed_assertions_shown",
            "max_extra_reads",
            "max_edit_files",
            "require_fact_citations",
            "prefer_ascii_runtime_artifacts",
            "session_pick_strategy",
        ]
        missing_keys = [key for key in required_keys if key not in profile]
        _append(results, "agent_profile", "ok" if not missing_keys else "fail", f"{default_profile} missing={','.join(missing_keys) or 'none'}")

    ready_banner = str(cfg["uart"].get("ready_banner", "")).strip()
    prompt = str(cfg["uart"].get("prompt", "")).strip()
    probe_commands = [str(item).strip() for item in cfg["uart"].get("probe_commands", []) if str(item).strip()]
    markers_ok = bool(ready_banner and prompt and probe_commands)
    _append(
        results,
        "uart_markers",
        "ok" if markers_ok else "warn",
        f"ready={ready_banner or 'missing'} prompt={prompt or 'missing'} probe_count={len(probe_commands)}",
    )

    state_path = Path(cfg["agent"]["state_path"])
    state = _read_json(state_path)
    if state:
        _append(results, "agent_state", "ok", str(state_path))
        brief_path = Path(str((state.get("generated_files") or {}).get("brief", ""))) if (state.get("generated_files") or {}).get("brief") else None
        paste_path = Path(str((state.get("generated_files") or {}).get("paste", ""))) if (state.get("generated_files") or {}).get("paste") else None
        if brief_path and brief_path.exists() and profile:
            words = _word_count(brief_path)
            budget = int(profile.get("max_pack_words", 550))
            level = "ok" if words <= budget else "warn"
            _append(results, "context_budget", level, f"{brief_path.name} words={words} budget={budget}")
        else:
            _append(results, "context_budget", "warn", "no generated brief found in agent_state")
        if paste_path and paste_path.exists():
            _append(results, "paste_card", "ok", str(paste_path))
        else:
            _append(results, "paste_card", "warn", "no generated paste card found in agent_state")

        task_text = str(state.get("task_path", "")).strip()
        if task_text:
            task_path = Path(task_text)
            try:
                task = load_task_spec(task_path)
            except Exception as exc:
                _append(results, "task_spec", "warn", str(exc))
            else:
                include_count = len(task.get("scope", {}).get("include", []))
                impl = task.get("implementation", {})
                read_candidates = impl.get("read_candidates", [])
                edit_candidates = impl.get("edit_candidates", [])
                max_edit_files = int(impl.get("max_edit_files", profile.get("max_edit_files", 2) if profile else 2))
                scope_level = "ok" if include_count <= max(max_edit_files * 3, 6) else "warn"
                _append(results, "task_scope", scope_level, f"include={include_count} max_edit_files={max_edit_files}")
                candidate_level = "ok" if read_candidates and edit_candidates else "warn"
                _append(
                    results,
                    "task_candidates",
                    candidate_level,
                    f"read_candidates={len(read_candidates)} edit_candidates={len(edit_candidates)}",
                )
    else:
        _append(results, "agent_state", "warn", f"missing {state_path}")
        _append(results, "context_budget", "warn", "no active local-model context has been generated yet")
        _append(results, "paste_card", "warn", "no paste card available until `agent_workbench.bat context ...` runs")

    _check_opencode_agents(cfg, results)
    _check_planner_templates(cfg, results)
    _check_migration_docs(cfg, results)

    unit_cfg = cfg["checks"].get("unit", {})
    if unit_cfg.get("enabled", False):
        unit_command = render_template(unit_cfg.get("command", ""), cfg["template_values"])
        _append(results, "unit_command", "ok", unit_command)
    else:
        _append(results, "unit_command", "warn", "unit checks disabled")

    summary = {
        "results": results,
        "fail_count": sum(1 for item in results if item["level"] == "fail"),
        "warn_count": sum(1 for item in results if item["level"] == "warn"),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "doctor_report.json", summary)
    with (output_dir / "doctor_report.md").open("w", encoding="utf-8") as fp:
        fp.write("# Doctor Report\n\n")
        fp.write("| check | level | detail |\n")
        fp.write("|---|---|---|\n")
        for item in results:
            fp.write(f"| {item['name']} | {item['level']} | {item['detail']} |\n")

    return (1 if summary["fail_count"] else 0), summary
