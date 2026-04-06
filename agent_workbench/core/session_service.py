from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

from .assertions import evaluate_assertions
from .build_service import run_build
from .compare_service import compare_latest as compare_latest_sessions
from .compare_service import compare_sessions, find_previous_session
from .doctor import run_doctor
from .flash_service import run_flash, run_reset
from .monitor_service import MonitorEngine
from .openocd_service import start_openocd_daemon, stop_openocd_daemon
from .reporting import write_feature_summary, write_session_summary
from .task_spec import load_task_spec
from .test_service import generate_tests, run_tests
from .uart_service import UartLogger, execute_uart_commands, serial, uart_exec_supported, uart_logger_supported
from .utils import append_jsonl, command_exists, ensure_dir, local_now_tag, read_text, render_template, utc_now_iso, write_json


def create_session_dir(cfg: dict, mode: str, session_name: str | None = None) -> Path:
    root = cfg["outputs"]["evidence_root_path"]
    ensure_dir(root)
    tag = session_name or f"{mode}_{local_now_tag()}"
    return ensure_dir(root / tag)


def _record_manifest(session_dir: Path, mode: str, cfg: dict, task: dict[str, Any] | None = None) -> Path:
    return write_json(
        session_dir / "session_manifest.json",
        {
            "generated_at": utc_now_iso(),
            "mode": mode,
            "project": cfg["project"]["name"],
            "project_root": str(cfg["project_root_path"]),
            "config_path": cfg["config_path"],
            "task": task or None,
        },
    )


def _hardware_required(cfg: dict) -> bool:
    return cfg.get("hardware", {}).get("mode", "prefer").lower() == "required"


def _hardware_allowed(cfg: dict) -> bool:
    return cfg.get("hardware", {}).get("mode", "prefer").lower() in {"prefer", "required"}


def _cli_probe_commands(cfg: dict, task: dict[str, Any] | None) -> list[str]:
    commands: list[str] = []
    seen: set[str] = set()
    for command in cfg.get("uart", {}).get("probe_commands", []):
        text = str(command).strip()
        if text and text not in seen:
            commands.append(text)
            seen.add(text)
    if task is not None:
        for command in task.get("verify", {}).get("cli_commands", []):
            text = str(command).strip()
            if text and text not in seen:
                commands.append(text)
                seen.add(text)
    return commands


def _run_debug_steps(
    cfg: dict,
    session_dir: Path,
    task: dict[str, Any] | None = None,
    auto_compare: bool = True,
) -> int:
    events_path = session_dir / "events.jsonl"
    append_jsonl(events_path, {"ts": utc_now_iso(), "event": "session_start"})

    doctor_code, doctor_summary = run_doctor(cfg, session_dir)
    append_jsonl(events_path, {"ts": utc_now_iso(), "event": "doctor_done", "code": doctor_code, "summary": doctor_summary})
    if doctor_code != 0:
        write_session_summary(session_dir)
        return doctor_code

    build_code = run_build(cfg, session_dir / "commands.log")
    append_jsonl(events_path, {"ts": utc_now_iso(), "event": "build_done", "code": build_code})
    if build_code != 0:
        write_session_summary(session_dir)
        return build_code

    unit_code, unit_log = run_tests(cfg, session_dir)
    append_jsonl(events_path, {"ts": utc_now_iso(), "event": "unit_done", "code": unit_code, "log": str(unit_log)})
    if unit_code != 0:
        write_session_summary(session_dir)
        return unit_code

    openocd_started = False
    openocd_command = render_template(cfg["tools"]["openocd"].get("daemon_cmd", ""), cfg["template_values"])
    flash_method = cfg["tools"]["flash"].get("default_method", "stlink_cli")
    flash_cfg = cfg["tools"]["flash"].get("methods", {}).get(flash_method, {})
    flash_command = render_template(flash_cfg.get("flash", ""), cfg["template_values"])
    reset_command = render_template(flash_cfg.get("reset", ""), cfg["template_values"])
    cli_commands = _cli_probe_commands(cfg, task)

    results = {"flash": 0, "reset": 0, "uart": 0, "monitor": 0, "cli": 0}
    uart_logger = None
    monitor_engine = None
    uart_thread = None
    monitor_thread = None
    try:
        if _hardware_allowed(cfg):
            if command_exists(flash_command):
                results["flash"] = run_flash(cfg, method=None, log_path=session_dir / "commands.log")
                append_jsonl(events_path, {"ts": utc_now_iso(), "event": "flash_done", "code": results["flash"]})
            else:
                append_jsonl(events_path, {"ts": utc_now_iso(), "event": "flash_skipped", "reason": "command unavailable"})
            if results["flash"] != 0 and _hardware_required(cfg):
                return results["flash"]

            if cfg["uart"].get("enabled", True) and uart_exec_supported() and cli_commands:
                try:
                    cli_result = execute_uart_commands(
                        cfg,
                        cli_commands,
                        session_dir / "cli_transcript.log",
                        reset_first=True,
                        expect_ready=True,
                        diag_path=session_dir / "cli_diag.json",
                        reset_log_path=session_dir / "commands.log",
                    )
                    results["cli"] = cli_result.exit_code
                    results["reset"] = 0
                    append_jsonl(
                        events_path,
                        {
                            "ts": utc_now_iso(),
                            "event": "cli_probe_done",
                            "code": cli_result.exit_code,
                            "commands": cli_commands,
                            "transcript": str(session_dir / "cli_transcript.log"),
                            "diag": str(cli_result.diag_path) if cli_result.diag_path else "",
                            "saw_ready": cli_result.saw_ready,
                            "saw_prompt": cli_result.saw_prompt,
                            "timeout_commands": cli_result.timeout_commands,
                        },
                    )
                except Exception as exc:
                    results["cli"] = 12
                    append_jsonl(events_path, {"ts": utc_now_iso(), "event": "cli_probe_error", "error": str(exc)})
            elif cfg["uart"].get("enabled", True) and cli_commands:
                append_jsonl(events_path, {"ts": utc_now_iso(), "event": "cli_probe_skipped", "reason": "pyserial unavailable"})
                if command_exists(reset_command):
                    results["reset"] = run_reset(cfg, method=None, log_path=session_dir / "commands.log")
                    append_jsonl(events_path, {"ts": utc_now_iso(), "event": "reset_done", "code": results["reset"]})
                else:
                    append_jsonl(events_path, {"ts": utc_now_iso(), "event": "reset_skipped", "reason": "command unavailable"})
            else:
                if command_exists(reset_command):
                    results["reset"] = run_reset(cfg, method=None, log_path=session_dir / "commands.log")
                    append_jsonl(events_path, {"ts": utc_now_iso(), "event": "reset_done", "code": results["reset"]})
                else:
                    append_jsonl(events_path, {"ts": utc_now_iso(), "event": "reset_skipped", "reason": "command unavailable"})
            if results["reset"] != 0 and _hardware_required(cfg):
                return results["reset"]

            if cfg["workflow"].get("manage_openocd", True) and command_exists(openocd_command):
                message = start_openocd_daemon(cfg)
                append_jsonl(events_path, {"ts": utc_now_iso(), "event": "openocd_start", "message": message})
                openocd_started = "started pid=" in message or "already running pid=" in message
            elif cfg["workflow"].get("manage_openocd", True):
                append_jsonl(events_path, {"ts": utc_now_iso(), "event": "openocd_skipped", "reason": "command unavailable"})

            if cfg["uart"].get("enabled", True) and uart_logger_supported():
                uart_logger = UartLogger(
                    port=cfg["uart"]["port"],
                    baudrate=int(cfg["uart"]["baudrate"]),
                    encoding=cfg["uart"].get("encoding", "utf-8"),
                    timeout_sec=float(cfg["uart"].get("line_timeout_sec", 0.2)),
                    log_path=session_dir / "uart.log",
                )

                def _uart_run() -> None:
                    try:
                        results["uart"] = uart_logger.run(echo_stdout=False)
                    except Exception as exc:
                        append_jsonl(events_path, {"ts": utc_now_iso(), "event": "uart_error", "error": str(exc)})
                        results["uart"] = 10

                uart_thread = threading.Thread(target=_uart_run, daemon=True)
                uart_thread.start()
            elif cfg["uart"].get("enabled", True):
                append_jsonl(events_path, {"ts": utc_now_iso(), "event": "uart_skipped", "reason": "uart backend unavailable"})

            if cfg["monitor"].get("enabled", True) and (openocd_started or not cfg["workflow"].get("manage_openocd", True)):
                monitor_engine = MonitorEngine(cfg, session_dir)

                def _monitor_run() -> None:
                    try:
                        results["monitor"] = monitor_engine.run()
                    except Exception as exc:
                        append_jsonl(events_path, {"ts": utc_now_iso(), "event": "monitor_error", "error": str(exc)})
                        results["monitor"] = 11

                monitor_thread = threading.Thread(target=_monitor_run, daemon=True)
                monitor_thread.start()
            elif cfg["monitor"].get("enabled", True):
                append_jsonl(events_path, {"ts": utc_now_iso(), "event": "monitor_skipped", "reason": "openocd unavailable"})
        else:
            append_jsonl(events_path, {"ts": utc_now_iso(), "event": "hardware_skipped"})

        observe_seconds = int(cfg["workflow"].get("observe_seconds", 30))
        append_jsonl(events_path, {"ts": utc_now_iso(), "event": "observe_start", "seconds": observe_seconds})
        time.sleep(observe_seconds)
    finally:
        if uart_logger is not None:
            uart_logger.stop_event.set()
        if monitor_engine is not None:
            monitor_engine.stop_event.set()
        if uart_thread is not None:
            uart_thread.join(timeout=5.0)
        if monitor_thread is not None:
            monitor_thread.join(timeout=5.0)
        if openocd_started and cfg["workflow"].get("manage_openocd", True):
            append_jsonl(events_path, {"ts": utc_now_iso(), "event": "openocd_stop", "message": stop_openocd_daemon(cfg)})

    assertions = (task or {}).get("acceptance", {}).get("blackbox", [])
    passed, failed, skipped = evaluate_assertions(session_dir, assertions)
    append_jsonl(
        events_path,
        {"ts": utc_now_iso(), "event": "assertions_done", "passed": passed, "failed": failed, "skipped": skipped},
    )
    summary_path = write_session_summary(session_dir)
    append_jsonl(events_path, {"ts": utc_now_iso(), "event": "session_done", "summary": str(summary_path)})

    if auto_compare and cfg["workflow"].get("auto_compare_previous", True):
        previous = find_previous_session(cfg["outputs"]["evidence_root_path"], session_dir)
        if previous is not None:
            compare_path = session_dir / f"compare_vs_{previous.name}.md"
            compare_sessions(previous, session_dir, compare_path)
            append_jsonl(events_path, {"ts": utc_now_iso(), "event": "compare_done", "report": str(compare_path)})

    return max(build_code, unit_code, results["flash"], results["reset"], results["uart"], results["monitor"], results["cli"], failed)


def run_debug_session(cfg: dict, session_name: str | None = None) -> int:
    session_dir = create_session_dir(cfg, "debug", session_name)
    _record_manifest(session_dir, "debug", cfg)
    return _run_debug_steps(cfg, session_dir, task=None, auto_compare=True)


def run_feature_session(cfg: dict, task_path: Path, session_name: str | None = None) -> int:
    task = load_task_spec(task_path)
    session_dir = create_session_dir(cfg, "feature", session_name or task["id"])
    _record_manifest(session_dir, "feature", cfg, task)
    generated_dir = generate_tests(cfg, task_path)
    append_jsonl(session_dir / "events.jsonl", {"ts": utc_now_iso(), "event": "tests_generated", "path": str(generated_dir)})
    exit_code = _run_debug_steps(cfg, session_dir, task=task, auto_compare=False)
    feature_summary = write_feature_summary(session_dir, task)
    append_jsonl(session_dir / "events.jsonl", {"ts": utc_now_iso(), "event": "feature_summary_done", "path": str(feature_summary)})
    return exit_code


def compare_latest(cfg: dict) -> Path:
    return compare_latest_sessions(cfg["outputs"]["evidence_root_path"])


def rebuild_report(session_dir: Path) -> Path:
    manifest_text = read_text(session_dir / "session_manifest.json")
    if manifest_text:
        manifest = json.loads(manifest_text)
        if manifest.get("mode") == "feature" and manifest.get("task"):
            write_feature_summary(session_dir, manifest["task"])
    return write_session_summary(session_dir)
