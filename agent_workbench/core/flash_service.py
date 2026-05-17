from __future__ import annotations

from pathlib import Path
from typing import Optional

from .openocd_service import stop_openocd_daemon
from .utils import render_template, run_command


def _resolve_method(cfg: dict, method: Optional[str]) -> dict:
    flash_cfg = cfg["tools"]["flash"]
    selected = method or flash_cfg.get("default_method", "stlink_cli")
    method_cfg = flash_cfg.get("methods", {}).get(selected)
    if not method_cfg:
        raise RuntimeError(f"unknown flash method: {selected}")
    return method_cfg


def run_flash(cfg: dict, method: Optional[str], log_path: Path) -> int:
    method_cfg = _resolve_method(cfg, method)
    command = render_template(method_cfg.get("flash", ""), cfg["template_values"])
    if not command:
        return 2
    stop_openocd_daemon(cfg)
    return run_command(command, cwd=cfg["project_root_path"], log_path=log_path)


def run_reset(cfg: dict, method: Optional[str], log_path: Path) -> int:
    method_cfg = _resolve_method(cfg, method)
    command = render_template(method_cfg.get("reset", ""), cfg["template_values"])
    if not command:
        return 2
    stop_openocd_daemon(cfg)
    return run_command(command, cwd=cfg["project_root_path"], log_path=log_path)
