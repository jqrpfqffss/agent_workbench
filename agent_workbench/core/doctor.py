from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from .diag_uart_service import SERIAL_IMPORT_ERROR as DIAG_SERIAL_IMPORT_ERROR
from .diag_uart_service import diag_exec_supported, serial as diag_serial
from .serial_settings import powershell_serial_params, pyserial_open_kwargs, serial_format_code
from .symbols import probe_symbols
from .uart_service import SERIAL_IMPORT_ERROR, serial, uart_exec_supported
from .utils import can_write_directory, command_exists, command_head, render_template, write_json


def _append(results: list[dict], name: str, level: str, detail: str) -> None:
    results.append({"name": name, "level": level, "detail": detail})


def _required_hardware(cfg: dict) -> bool:
    return cfg.get("hardware", {}).get("mode", "prefer").lower() == "required"


def _needs_explicit_target_selection(config_files: list[str], connect_commands: list[str]) -> bool:
    if connect_commands:
        return False
    markers = ("h7x", "dual", "cpu1", "wlx")
    return any(any(marker in item.lower() for marker in markers) for item in config_files)


def _probe_serial_port_with_powershell(section: dict, *, timeout_sec: float) -> tuple[bool, str]:
    if os.name != "nt":
        return False, "PowerShell serial probe is only available on Windows"
    params = powershell_serial_params(section)
    script = r"""
$ErrorActionPreference = 'Stop'
$parity = [System.Enum]::Parse([System.IO.Ports.Parity], $env:AWB_PARITY, $true)
$stopBits = [System.Enum]::Parse([System.IO.Ports.StopBits], $env:AWB_STOP_BITS, $true)
$serial = [System.IO.Ports.SerialPort]::new($env:AWB_PORT, [int]$env:AWB_BAUD, $parity, [int]$env:AWB_DATA_BITS, $stopBits)
try {
  $serial.ReadTimeout = [int]$env:AWB_TIMEOUT_MS
  $serial.Open()
  Write-Output "ok"
}
finally {
  if ($serial -and $serial.IsOpen) {
    $serial.Close()
  }
}
"""
    env = dict(os.environ)
    env.update(
        {
            "AWB_PORT": str(params["port"]),
            "AWB_BAUD": str(params["baudrate"]),
            "AWB_DATA_BITS": str(params["data_bits"]),
            "AWB_PARITY": str(params["parity_name"]),
            "AWB_STOP_BITS": str(params["stop_bits_name"]),
            "AWB_TIMEOUT_MS": str(max(1, int(timeout_sec * 1000))),
        }
    )
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            timeout=max(2.0, timeout_sec + 2.0),
            env=env,
            check=False,
        )
    except Exception as exc:
        return False, str(exc)
    if proc.returncode == 0:
        return True, str(section.get("port", ""))
    detail = (proc.stderr or proc.stdout or f"PowerShell serial probe failed rc={proc.returncode}").strip()
    return False, detail


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

    artifact = Path(cfg["project"]["artifact_file_path"])
    _append(results, "artifact_file", "ok" if artifact.exists() else "warn", str(artifact))

    compile_commands = Path(cfg["project"]["compile_commands_path"])
    _append(results, "compile_commands", "ok" if compile_commands.exists() else "warn", str(compile_commands))

    symbols_ok, symbols_detail = probe_symbols(cfg)
    _append(results, "artifact_symbols", "ok" if symbols_ok else "warn", symbols_detail)

    monitor_symbols_ok, monitor_symbols_detail = probe_symbols(cfg, monitor=True)
    _append(results, "monitor_symbol_image", "ok" if monitor_symbols_ok else "warn", monitor_symbols_detail)

    openocd_command = render_template(cfg["tools"]["openocd"].get("daemon_cmd", ""), cfg["template_values"])
    openocd_level = "ok" if command_exists(openocd_command) else ("fail" if required_hardware else "warn")
    _append(results, "openocd", openocd_level, command_head(openocd_command) or "missing")

    flash_method = cfg["tools"]["flash"].get("default_method", "stlink_cli")
    flash_cfg = cfg["tools"]["flash"].get("methods", {}).get(flash_method, {})
    flash_command = render_template(flash_cfg.get("flash", ""), cfg["template_values"])
    flash_level = "ok" if command_exists(flash_command) else ("fail" if required_hardware else "warn")
    _append(results, "flash_method", flash_level, f"{flash_method}: {command_head(flash_command) or 'missing'}")

    monitor_cfg = cfg.get("monitor", {})
    monitor_items = monitor_cfg.get("items", [])
    if monitor_cfg.get("enabled", True):
        _append(results, "monitor_items", "ok" if monitor_items else "warn", f"count={len(monitor_items)}")
        symbol_items = [item for item in monitor_items if str(item.get("source", "")).lower() == "symbol"]
        if symbol_items and not monitor_symbols_ok:
            _append(results, "monitor_symbol_items", "warn", f"symbol items={len(symbol_items)} but symbol image is not readable")
        else:
            _append(results, "monitor_symbol_items", "ok", f"symbol items={len(symbol_items)}")
        config_files = [str(item) for item in cfg["tools"]["openocd"].get("config_files", [])]
        connect_commands = [str(item) for item in monitor_cfg.get("openocd", {}).get("connect_commands", [])]
        if _needs_explicit_target_selection(config_files, connect_commands):
            _append(results, "monitor_target_selection", "warn", "monitor.openocd.connect_commands is empty; target selection may be required")
        else:
            _append(
                results,
                "monitor_target_selection",
                "ok",
                ",".join(connect_commands) if connect_commands else "not required by current config",
            )
    else:
        _append(results, "monitor_items", "warn", "monitor disabled by config")

    if cfg["uart"].get("enabled", True):
        _append(
            results,
            "uart_protocol",
            "ok",
            f"ready_banner={cfg['uart'].get('ready_banner', 'cli ready')} "
            f"prompt={cfg['uart'].get('prompt', 'cli>')} format={serial_format_code(cfg['uart'])}",
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
            _append(results, "uart_backend", level, detail)
            ok, port_detail = _probe_serial_port_with_powershell(
                cfg["uart"],
                timeout_sec=float(cfg["uart"].get("line_timeout_sec", 0.2)),
            )
            _append(results, "uart_port", "ok" if ok else ("fail" if required_hardware else "warn"), port_detail)
        else:
            _append(results, "uart_backend", "ok", "pyserial available")
            try:
                with serial.Serial(
                    **pyserial_open_kwargs(
                        cfg["uart"],
                        serial,
                        timeout=float(cfg["uart"].get("line_timeout_sec", 0.2)),
                    )
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
            f"count={len(default_requests)} port={diag_cfg.get('port', '')} format={serial_format_code(diag_cfg)}",
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
            ok, port_detail = _probe_serial_port_with_powershell(
                diag_cfg,
                timeout_sec=float(diag_cfg.get("read_timeout_sec", 0.05)),
            )
            _append(results, "diag_uart_port", "ok" if ok else ("fail" if required_hardware else "warn"), port_detail)
        else:
            _append(results, "diag_uart_backend", "ok", "pyserial available")
            try:
                with diag_serial.Serial(
                    **pyserial_open_kwargs(
                        diag_cfg,
                        diag_serial,
                        timeout=float(diag_cfg.get("read_timeout_sec", 0.05)),
                    )
                ):
                    _append(results, "diag_uart_port", "ok", str(diag_cfg["port"]))
            except Exception as exc:
                level = "fail" if required_hardware else "warn"
                _append(results, "diag_uart_port", level, str(exc))
    else:
        _append(results, "diag_uart_backend", "warn", "diag_uart disabled by config")

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
