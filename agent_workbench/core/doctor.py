from __future__ import annotations

import sys
from pathlib import Path

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
    autoflow_state_path = Path(cfg["agent"].get("autoflow_state_path", output_dir / "autoflow_state.json"))
    autoflow_start_path = Path(cfg["outputs"]["runtime_root_path"]) / "autoflow_start.md"
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

    autoflow_state = _read_json(autoflow_state_path)
    if autoflow_state:
        _append(results, "autoflow_state", "ok", str(autoflow_state_path))
    else:
        _append(results, "autoflow_state", "warn", f"missing {autoflow_state_path}")
    _append(
        results,
        "autoflow_start",
        "ok" if autoflow_start_path.exists() else "warn",
        str(autoflow_start_path),
    )

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
