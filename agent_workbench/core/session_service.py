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
from .reporting import derive_session_verdict, write_feature_summary, write_session_summary
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
                    data_bits=int(cfg["uart"].get("data_bits", 8)),
                    stop_bits=float(cfg["uart"].get("stop_bits", 1.0)),
                    parity=str(cfg["uart"].get("parity", "none")),
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
    refreshed_summary = write_session_summary(session_dir)
    append_jsonl(session_dir / "events.jsonl", {"ts": utc_now_iso(), "event": "session_summary_refreshed", "path": str(refreshed_summary)})
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


def run_current_verify(cfg: dict, task_path: Path, session_name: str | None = None) -> tuple[int, Path]:
    task = load_task_spec(task_path)
    runtime_root = cfg["outputs"]["runtime_root_path"]
    ensure_dir(runtime_root)

    summary_json_path = runtime_root / "direct_verify_summary.json"
    summary_md_path = runtime_root / "direct_verify_summary.md"
    smoke_transcript = runtime_root / "cli_transcript.log"
    smoke_diag = runtime_root / "cli_diag.json"
    cli_commands = ["help", "status"]
    steps: list[dict[str, Any]] = []

    def _record(name: str, *, code: int, status: str, detail: str = "", artifact: str = "") -> None:
        steps.append({"name": name, "code": int(code), "status": status, "detail": detail, "artifact": artifact})

    doctor_code, doctor_summary = run_doctor(cfg, runtime_root)
    _record(
        "doctor",
        code=doctor_code,
        status="pass" if doctor_code == 0 else "fail",
        detail=f"fail={doctor_summary['fail_count']} warn={doctor_summary['warn_count']}",
        artifact=str(runtime_root / "doctor_report.md"),
    )

    build_code = run_build(cfg, runtime_root / "build.log")
    _record(
        "build",
        code=build_code,
        status="pass" if build_code == 0 else "fail",
        detail=f"exit={build_code}",
        artifact=str(runtime_root / "build.log"),
    )

    generated_dir = generate_tests(cfg, task_path)
    _record("test_generate", code=0, status="pass", detail="generated", artifact=str(generated_dir))

    unit_code, unit_log = run_tests(cfg)
    _record(
        "test_run",
        code=unit_code,
        status="pass" if unit_code == 0 else "fail",
        detail=f"exit={unit_code}",
        artifact=str(unit_log),
    )

    smoke_code = 0
    smoke_status = "skipped"
    smoke_detail = "UART smoke skipped."
    smoke_artifact = str(smoke_transcript)
    if cfg.get("uart", {}).get("enabled", True) and uart_exec_supported():
        smoke_result = execute_uart_commands(
            cfg,
            cli_commands,
            smoke_transcript,
            reset_first=True,
            expect_ready=True,
            diag_path=smoke_diag,
            reset_log_path=runtime_root / "uart_exec_reset.log",
        )
        smoke_code = smoke_result.exit_code
        if smoke_code == 0:
            smoke_status = "pass"
            smoke_detail = "ready banner, prompt, and help/status smoke all completed."
        elif smoke_code == 35:
            smoke_status = "blocked"
            smoke_detail = "PowerShell UART backend could not open the configured COM port."
        else:
            smoke_status = "fail"
            smoke_detail = f"exit={smoke_code}"
        smoke_artifact = str(smoke_result.diag_path or smoke_transcript)
    elif cfg.get("uart", {}).get("enabled", True):
        smoke_code = 36
        smoke_status = "blocked"
        smoke_detail = "No UART backend is available in the current Python/PowerShell environment."
    _record("uart_smoke", code=smoke_code, status=smoke_status, detail=smoke_detail, artifact=smoke_artifact)

    feature_session_dir: Path | None = None
    feature_code = 0
    feature_status = "skipped"
    feature_detail = "Feature session skipped because a host-side prerequisite failed."
    compare_path = ""
    report_path = ""
    if doctor_code == 0 and build_code == 0 and unit_code == 0 and smoke_status != "blocked":
        feature_session_name = session_name or f"{task['id']}_direct_verify_{local_now_tag()}"
        feature_session_dir = cfg["outputs"]["evidence_root_path"] / feature_session_name
        feature_code = run_feature_session(cfg, task_path, session_name=feature_session_name)
        report_path = str(rebuild_report(feature_session_dir))
        verdict = derive_session_verdict(feature_session_dir)
        feature_status = str(verdict.get("status", "needs_review"))
        feature_detail = str(verdict.get("summary", "feature session finished"))
        previous = find_previous_session(cfg["outputs"]["evidence_root_path"], feature_session_dir)
        if previous is not None:
            compare_target = feature_session_dir / f"compare_vs_{previous.name}.md"
            compare_path = str(compare_sessions(previous, feature_session_dir, compare_target))
    elif doctor_code == 0 and build_code == 0 and unit_code == 0 and smoke_status == "blocked":
        feature_status = "blocked"
        feature_detail = "Feature session skipped because UART smoke was blocked by the current environment."
    _record(
        "feature_session",
        code=feature_code,
        status=feature_status,
        detail=feature_detail,
        artifact=str(feature_session_dir) if feature_session_dir else "",
    )

    overall_status = "pass"
    if any(step["status"] == "fail" for step in steps):
        overall_status = "fail"
    elif any(step["status"] == "blocked" for step in steps):
        overall_status = "blocked"
    elif any(step["status"] == "needs_review" for step in steps):
        overall_status = "needs_review"

    exit_code = 0 if overall_status == "pass" else 1
    summary = {
        "generated_at": utc_now_iso(),
        "task_id": task["id"],
        "status": overall_status,
        "exit_code": exit_code,
        "steps": steps,
        "artifacts": {
            "runtime_cli_transcript": str(smoke_transcript),
            "runtime_cli_diag": str(smoke_diag),
            "feature_session_dir": str(feature_session_dir) if feature_session_dir else "",
            "report_path": report_path,
            "compare_path": compare_path,
        },
        "next_step": "Read direct_verify_summary.md first, then inspect the linked evidence files.",
    }
    write_json(summary_json_path, summary)

    with summary_md_path.open("w", encoding="utf-8") as fp:
        fp.write("# Direct Verify Summary\n\n")
        fp.write(f"- generated_at: {summary['generated_at']}\n")
        fp.write(f"- task_id: `{task['id']}`\n")
        fp.write(f"- status: `{overall_status}`\n")
        fp.write(f"- exit_code: `{exit_code}`\n")
        fp.write(f"- next_step: {summary['next_step']}\n\n")
        fp.write("## Steps\n")
        for step in steps:
            fp.write(
                f"- {step['name']}: status={step['status']} code={step['code']} detail={step['detail']}"
                + (f" artifact=`{step['artifact']}`" if step["artifact"] else "")
                + "\n"
            )
        fp.write("\n## Key Artifacts\n")
        fp.write(f"- runtime_cli_transcript: `{smoke_transcript}`\n")
        fp.write(f"- runtime_cli_diag: `{smoke_diag}`\n")
        if feature_session_dir is not None:
            fp.write(f"- feature_session_dir: `{feature_session_dir}`\n")
        if report_path:
            fp.write(f"- report_path: `{report_path}`\n")
        if compare_path:
            fp.write(f"- compare_path: `{compare_path}`\n")

    return exit_code, summary_md_path
