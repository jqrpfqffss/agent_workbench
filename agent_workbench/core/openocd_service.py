from __future__ import annotations

import time
from pathlib import Path

from .openocd_client import OpenOcdClient, OpenOcdConfig
from .utils import (
    clear_pid_file,
    command_exists,
    command_head,
    ensure_dir,
    is_process_alive,
    read_pid,
    render_template,
    spawn_detached_command_with_stdin_keeper,
    terminate_process,
    write_pid,
)


def _pid_path(cfg: dict) -> Path:
    return ensure_dir(cfg["outputs"]["runtime_root_path"] / "pids") / "openocd.pid"


def _log_path(cfg: dict) -> Path:
    return ensure_dir(cfg["outputs"]["runtime_root_path"] / "openocd_live") / "openocd.log"


def _client(cfg: dict) -> OpenOcdClient:
    openocd_cfg = cfg["tools"]["openocd"]
    return OpenOcdClient(
        OpenOcdConfig(
            host=openocd_cfg.get("host", "127.0.0.1"),
            port=int(openocd_cfg.get("telnet_port", 4444)),
            timeout_sec=0.5,
        )
    )


def _wait_ready(cfg: dict, timeout_sec: float) -> bool:
    end_time = time.time() + timeout_sec
    while time.time() < end_time:
        client = _client(cfg)
        try:
            client.connect()
            return True
        except Exception:
            time.sleep(0.2)
        finally:
            client.close()
    return False


def _shutdown_via_telnet(cfg: dict) -> bool:
    client = _client(cfg)
    try:
        client.connect()
        client.command("shutdown")
        return True
    except Exception:
        return False
    finally:
        client.close()

def start_openocd_daemon(cfg: dict) -> str:
    pid_file = _pid_path(cfg)
    old_pid = read_pid(pid_file)
    if old_pid and is_process_alive(old_pid):
        return f"openocd already running pid={old_pid}"
    if old_pid:
        clear_pid_file(pid_file)

    openocd_cfg = cfg["tools"]["openocd"]
    command = render_template(openocd_cfg.get("daemon_cmd", ""), cfg["template_values"])
    if not command:
        return "openocd daemon_cmd is empty"
    if not command_exists(command):
        clear_pid_file(pid_file)
        return f"openocd command unavailable: {command_head(command) or 'missing'}"
    ensure_dir(_log_path(cfg).parent)
    pid = spawn_detached_command_with_stdin_keeper(command, cwd=cfg["project_root_path"], log_path=None)
    write_pid(pid_file, pid)
    host = openocd_cfg.get("host", "127.0.0.1")
    port = int(openocd_cfg.get("telnet_port", 4444))
    wait_sec = float(openocd_cfg.get("startup_wait_sec", 3.0))
    time.sleep(wait_sec)
    if _wait_ready(cfg, max(wait_sec, 0.6)):
        return f"openocd started pid={pid} ({host}:{port})"
    if is_process_alive(pid):
        terminate_process(pid)
    clear_pid_file(pid_file)
    return f"openocd startup timeout pid={pid} ({host}:{port})"


def stop_openocd_daemon(cfg: dict) -> str:
    pid_file = _pid_path(cfg)
    pid = read_pid(pid_file)
    if _shutdown_via_telnet(cfg):
        clear_pid_file(pid_file)
        return f"openocd stopped via telnet pid={pid or 'unknown'}"
    if not pid:
        return "openocd not running"
    if not is_process_alive(pid):
        clear_pid_file(pid_file)
        return f"openocd stale pid cleaned pid={pid}"
    terminate_process(pid)
    clear_pid_file(pid_file)
    return f"openocd stopped pid={pid}"


def openocd_status(cfg: dict) -> str:
    pid = read_pid(_pid_path(cfg))
    telnet_ok = _wait_ready(cfg, 0.6)
    if not pid and not telnet_ok:
        return "openocd status: stopped"
    openocd_cfg = cfg["tools"]["openocd"]
    host = openocd_cfg.get("host", "127.0.0.1")
    port = int(openocd_cfg.get("telnet_port", 4444))
    state = "running" if telnet_ok else ("running" if pid and is_process_alive(pid) else "stale")
    return f"openocd status: {state} pid={pid or 'unknown'} telnet={host}:{port} ready={int(telnet_ok)}"
