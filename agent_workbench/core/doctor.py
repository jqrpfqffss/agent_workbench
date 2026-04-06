from __future__ import annotations

import sys
from pathlib import Path

from .uart_service import SERIAL_IMPORT_ERROR, serial, uart_exec_supported
from .utils import can_write_directory, command_exists, command_head, render_template, write_json


def _append(results: list[dict], name: str, level: str, detail: str) -> None:
    results.append({"name": name, "level": level, "detail": detail})


def _required_hardware(cfg: dict) -> bool:
    return cfg.get("hardware", {}).get("mode", "prefer").lower() == "required"


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
