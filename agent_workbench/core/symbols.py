from __future__ import annotations

import subprocess
from pathlib import Path


def symbol_image_path(cfg: dict, *, monitor: bool = False) -> Path:
    if monitor:
        return Path(str(cfg["monitor"]["symbols"]["path"]))
    return Path(str(cfg["project"]["artifact_file_path"]))


def load_symbols(cfg: dict, *, monitor: bool = False) -> dict[str, int]:
    image_path = symbol_image_path(cfg, monitor=monitor)
    nm_command = cfg["tools"].get("symbols_nm", "arm-none-eabi-nm")
    if not image_path.exists():
        return {}
    try:
        output = subprocess.check_output([nm_command, "-n", str(image_path)], stderr=subprocess.STDOUT, text=True)
    except Exception:
        return {}
    symbols: dict[str, int] = {}
    for line in output.splitlines():
        parts = line.strip().split()
        if len(parts) < 3:
            continue
        try:
            symbols[parts[2]] = int(parts[0], 16)
        except ValueError:
            continue
    return symbols


def probe_symbols(cfg: dict, *, monitor: bool = False) -> tuple[bool, str]:
    image_path = symbol_image_path(cfg, monitor=monitor)
    nm_command = cfg["tools"].get("symbols_nm", "arm-none-eabi-nm")
    if not image_path.exists():
        return False, f"missing {image_path}"
    try:
        subprocess.check_output([nm_command, "-n", str(image_path)], stderr=subprocess.STDOUT, text=True)
    except Exception as exc:
        return False, str(exc)
    return True, str(image_path)
