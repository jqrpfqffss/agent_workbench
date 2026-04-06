from __future__ import annotations

from pathlib import Path

from .utils import render_template, run_command


def _configure_command(cfg: dict) -> str:
    cmake_cfg = cfg["tools"]["cmake"]
    parts = ["cmake", "-S", ".", "-B", str(cfg["project"]["build_dir_path"])]
    generator = cmake_cfg.get("generator", "")
    if generator:
        parts.extend(["-G", f'"{generator}"'])
    build_type = cmake_cfg.get("build_type", "Debug")
    parts.append(f"-DCMAKE_BUILD_TYPE={build_type}")
    parts.append(f"-DCMAKE_TOOLCHAIN_FILE={cfg['tools']['cmake']['toolchain_file_path']}")
    for arg in cmake_cfg.get("configure_args", []):
        parts.append(render_template(str(arg), cfg["template_values"]))
    return " ".join(parts)


def _build_command(cfg: dict) -> str:
    cmake_cfg = cfg["tools"]["cmake"]
    parts = ["cmake", "--build", str(cfg["project"]["build_dir_path"])]
    for arg in cmake_cfg.get("build_args", []):
        parts.append(render_template(str(arg), cfg["template_values"]))
    return " ".join(parts)


def run_build(cfg: dict, log_path: Path) -> int:
    for command in (_configure_command(cfg), _build_command(cfg)):
        code = run_command(command, cwd=cfg["project_root_path"], log_path=log_path)
        if code != 0:
            return code
    return 0
