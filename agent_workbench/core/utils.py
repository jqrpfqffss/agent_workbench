from __future__ import annotations

import csv
import json
import os
import shlex
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional


WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = WORKBENCH_ROOT.parent


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def local_now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, data: Any) -> Path:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(obj, ensure_ascii=False) + "\n")


def command_head(command: str) -> str:
    parts = split_command(command)
    return parts[0] if parts else ""


def split_command(command: str) -> list[str]:
    parts = shlex.split(command, posix=False)
    normalized: list[str] = []
    for part in parts:
        if len(part) >= 2 and part[0] == part[-1] and part[0] in {"'", '"'}:
            normalized.append(part[1:-1])
        else:
            normalized.append(part)
    return normalized


def command_exists(command: str) -> bool:
    head = command_head(command)
    if not head:
        return False
    if Path(head).exists():
        return True
    return any(
        (Path(folder) / head).exists() or (Path(folder) / f"{head}.exe").exists()
        for folder in os.environ.get("PATH", "").split(os.pathsep)
        if folder
    )


def render_template(template: str, values: dict[str, Any]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{" + key + "}", str(value))
    return rendered


def run_command(
    command: str,
    cwd: Path,
    log_path: Optional[Path] = None,
    env: Optional[dict[str, str]] = None,
) -> int:
    ensure_dir(cwd)
    merged_env = dict(os.environ)
    if env:
        merged_env.update(env)

    if log_path is not None:
        ensure_dir(log_path.parent)
        with log_path.open("a", encoding="utf-8") as fp:
            fp.write(f"\n[{utc_now_iso()}] $ {command}\n")
            fp.flush()
            proc = subprocess.Popen(
                command,
                cwd=str(cwd),
                shell=True,
                stdout=fp,
                stderr=subprocess.STDOUT,
                env=merged_env,
            )
            proc.wait()
            fp.write(f"[{utc_now_iso()}] exit={proc.returncode}\n")
            return int(proc.returncode)

    proc = subprocess.run(command, cwd=str(cwd), shell=True, env=merged_env)
    return int(proc.returncode)


def write_pid(pid_file: Path, pid: int) -> None:
    ensure_dir(pid_file.parent)
    pid_file.write_text(str(pid), encoding="utf-8")


def read_pid(pid_file: Path) -> Optional[int]:
    if not pid_file.exists():
        return None
    text = pid_file.read_text(encoding="utf-8").strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def clear_pid_file(pid_file: Path) -> None:
    try:
        pid_file.unlink(missing_ok=True)
        return
    except TypeError:
        pass
    except FileNotFoundError:
        return
    except OSError:
        pass

    try:
        pid_file.write_text("", encoding="utf-8")
    except OSError:
        pass


def is_process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            proc = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return False
        for line in proc.stdout.splitlines():
            if not line.startswith('"'):
                continue
            try:
                row = next(csv.reader([line]))
            except Exception:
                continue
            if len(row) >= 2 and row[1].isdigit() and int(row[1]) == pid:
                return True
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def terminate_process(pid: int) -> None:
    if pid <= 0:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(20):
            if not is_process_alive(pid):
                return
            time.sleep(0.1)
        return

    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return
    for _ in range(20):
        if not is_process_alive(pid):
            return
        time.sleep(0.1)
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass


def spawn_detached_python(args: Iterable[str], cwd: Path, env: Optional[dict[str, str]] = None) -> int:
    argv = [sys.executable, *args]
    kwargs: dict[str, Any] = {
        "cwd": str(cwd),
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if env:
        merged_env = dict(os.environ)
        merged_env.update(env)
        kwargs["env"] = merged_env
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    proc = subprocess.Popen(argv, **kwargs)
    return int(proc.pid)


def spawn_detached_command(
    command: str,
    cwd: Path,
    log_path: Optional[Path] = None,
    env: Optional[dict[str, str]] = None,
) -> int:
    ensure_dir(cwd)
    argv = split_command(command)
    if not argv:
        raise RuntimeError("cannot spawn empty command")
    log_fp = None
    if log_path is not None:
        ensure_dir(log_path.parent)
        log_fp = log_path.open("a", encoding="utf-8")
        log_fp.write(f"[{utc_now_iso()}] spawn: {command}\n")
        log_fp.flush()

    kwargs: dict[str, Any] = {
        "cwd": str(cwd),
        "stdin": subprocess.DEVNULL,
        "close_fds": True,
    }
    if env:
        merged_env = dict(os.environ)
        merged_env.update(env)
        kwargs["env"] = merged_env
    if log_fp is not None:
        kwargs["stdout"] = log_fp
        kwargs["stderr"] = subprocess.STDOUT
    else:
        kwargs["stdout"] = subprocess.DEVNULL
        kwargs["stderr"] = subprocess.DEVNULL
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

    try:
        proc = subprocess.Popen(argv, **kwargs)
        return int(proc.pid)
    finally:
        if log_fp is not None:
            log_fp.close()


def spawn_detached_command_with_stdin_keeper(
    command: str,
    cwd: Path,
    log_path: Optional[Path] = None,
    env: Optional[dict[str, str]] = None,
) -> int:
    helper = WORKBENCH_ROOT / "core" / "process_keeper.py"
    argv = [str(helper), "--cwd", str(cwd)]
    if log_path is not None:
        argv.extend(["--log", str(log_path)])
    argv.append("--")
    argv.extend(split_command(command))
    if os.name != "nt":
        return spawn_detached_python(argv, cwd=WORKBENCH_ROOT, env=env)

    helper_argv = [sys.executable, *argv]
    kwargs: dict[str, Any] = {
        "cwd": str(WORKBENCH_ROOT),
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if env:
        merged_env = dict(os.environ)
        merged_env.update(env)
        kwargs["env"] = merged_env
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
    kwargs["startupinfo"] = startupinfo
    proc = subprocess.Popen(helper_argv, **kwargs)
    return int(proc.pid)


def can_write_directory(path: Path) -> tuple[bool, str]:
    try:
        ensure_dir(path)
        probe = path / ".awb_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True, "ok"
    except Exception as exc:  # pragma: no cover - defensive
        return False, str(exc)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore").replace("\ufeff", "") if path.exists() else ""
