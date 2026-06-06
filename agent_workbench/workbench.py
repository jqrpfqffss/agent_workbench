from __future__ import annotations

import argparse
from pathlib import Path

from core.cli_output import build_result_payload, print_result_payload, status_from_exit_code
from core.config import load_config


DEFAULT_CONFIG = Path(__file__).resolve().parent / "agent_workbench.yaml"


def _cfg(path_text: str) -> dict:
    return load_config(Path(path_text).resolve())


def _emit(args: argparse.Namespace, payload: dict, text_lines: list[str]) -> int:
    if getattr(args, "json", False):
        print_result_payload(payload)
    else:
        for line in text_lines:
            if line:
                print(line)
    return int(payload["exit_code"])


def _add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true")


def _cmd_doctor(args: argparse.Namespace) -> int:
    from core.doctor import run_doctor

    cfg = _cfg(args.config)
    code, summary = run_doctor(cfg, cfg["outputs"]["runtime_root_path"])
    payload = build_result_payload(
        "doctor",
        code,
        summary=f"doctor fail={summary['fail_count']} warn={summary['warn_count']}",
        details={
            "fail_count": summary["fail_count"],
            "warn_count": summary["warn_count"],
            "results": summary["results"],
        },
        artifacts={
            "report_json": str(cfg["outputs"]["runtime_root_path"] / "doctor_report.json"),
            "report_md": str(cfg["outputs"]["runtime_root_path"] / "doctor_report.md"),
        },
    )
    return _emit(args, payload, [payload["summary"]])


def _cmd_build(args: argparse.Namespace) -> int:
    from core.build_errors import parse_build_log
    from core.build_service import run_build

    cfg = _cfg(args.config)
    log_path = cfg["outputs"]["runtime_root_path"] / "build.log"
    code = run_build(cfg, log_path)
    parsed = parse_build_log(log_path, Path(cfg["project_root_path"]))
    errors = [item.to_dict() for item in parsed if item.level == "error"]
    warnings = [item.to_dict() for item in parsed if item.level == "warning"]
    payload = build_result_payload(
        "build",
        code,
        summary=f"build exit={code} errors={len(errors)} warnings={len(warnings)}",
        details={
            "error_count": len(errors),
            "warning_count": len(warnings),
        },
        artifacts={"log_path": str(log_path)},
        errors=errors,
        warnings=warnings,
    )
    return _emit(args, payload, [payload["summary"]])


def _cmd_remote_dt(args: argparse.Namespace) -> int:
    from core.remote_dt_service import RemoteDtService

    cfg = _cfg(args.config)
    payload = RemoteDtService(cfg).run(args.action)
    if args.action == "push-files":
        return _emit(args, payload, _remote_dt_push_files_text_lines(payload))
    return _emit(args, payload, [payload["summary"]])


def _remote_dt_push_files_text_lines(payload: dict) -> list[str]:
    details = payload.get("details", {}) if isinstance(payload.get("details", {}), dict) else {}
    lines = [payload.get("summary", "")]
    lines.extend(str(item) for item in details.get("diagnostics", []) if item)
    if payload.get("status") == "fail":
        for error in payload.get("errors", []):
            message = error.get("message") if isinstance(error, dict) else str(error)
            if message:
                lines.append(f"REMOTE_DT_PUSH_FILES_ERROR: {message}")
    return lines


def _cmd_opencode_auto(args: argparse.Namespace) -> int:
    from core.opencode_auto_service import OpencodeAutoService

    cfg = _cfg(args.config)
    max_retries = args.max_retries if args.max_retries is not None else None
    payload = OpencodeAutoService(cfg).run(
        args.task,
        plan_file=args.plan_file,
        max_retries=max_retries,
        dry_run=bool(args.dry_run),
    )
    return _emit(args, payload, [payload["summary"]])


def _cmd_flash(args: argparse.Namespace) -> int:
    from core.flash_service import run_flash

    cfg = _cfg(args.config)
    method = args.method.strip() if args.method else None
    log_path = cfg["outputs"]["runtime_root_path"] / "flash.log"
    code = run_flash(cfg, method=method, log_path=log_path)
    selected = method or cfg["tools"]["flash"].get("default_method", "stlink_cli")
    payload = build_result_payload(
        "flash",
        code,
        summary=f"flash exit={code} method={selected}",
        details={"method": selected},
        artifacts={"log_path": str(log_path)},
    )
    return _emit(args, payload, [payload["summary"]])


def _cmd_reset(args: argparse.Namespace) -> int:
    from core.flash_service import run_reset

    cfg = _cfg(args.config)
    method = args.method.strip() if args.method else None
    log_path = cfg["outputs"]["runtime_root_path"] / "reset.log"
    code = run_reset(cfg, method=method, log_path=log_path)
    selected = method or cfg["tools"]["flash"].get("default_method", "stlink_cli")
    payload = build_result_payload(
        "reset",
        code,
        summary=f"reset exit={code} method={selected}",
        details={"method": selected},
        artifacts={"log_path": str(log_path)},
    )
    return _emit(args, payload, [payload["summary"]])


def _cmd_uart(args: argparse.Namespace) -> int:
    from core.uart_service import execute_uart_commands

    cfg = _cfg(args.config)
    runtime_root = cfg["outputs"]["runtime_root_path"]
    if args.action == "exec":
        commands = list(args.command or [])
        if args.script:
            script_path = Path(args.script)
            commands.extend(
                line.strip()
                for line in script_path.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.strip().startswith("#")
            )
        if not commands:
            payload = build_result_payload(
                "uart exec",
                2,
                summary="uart exec requires --command or --script",
            )
            return _emit(args, payload, [payload["summary"]])
        transcript_path = Path(args.transcript) if args.transcript else runtime_root / "cli_transcript.log"
        diag_path = Path(args.diag_path) if args.diag_path else transcript_path.with_name("cli_diag.json")
        result = execute_uart_commands(
            cfg,
            commands,
            transcript_path,
            reset_first=bool(args.reset_first),
            expect_ready=(True if args.expect_ready else None),
            diag_path=diag_path,
        )
        diagnosis = None
        if result.diag and isinstance(result.diag.get("classification"), dict):
            diagnosis = result.diag.get("classification")
        status = status_from_exit_code(result.exit_code, blocked=result.exit_code in {35, 36})
        payload = build_result_payload(
            "uart exec",
            result.exit_code,
            status=status,
            summary=f"uart exec exit={result.exit_code} commands={len(commands)}",
            details={
                "saw_ready": result.saw_ready,
                "saw_prompt": result.saw_prompt,
                "timeout_commands": result.timeout_commands,
                "command_count": len(commands),
            },
            artifacts={
                "transcript_path": str(transcript_path),
                "diag_path": str(result.diag_path or diag_path),
            },
            transcript=result.transcript_lines,
            diagnosis=diagnosis,
        )
        lines = [payload["summary"]]
        if diagnosis:
            lines.append(f"uart exec diagnosis: {diagnosis.get('summary', '')} | {diagnosis.get('detail', '')}")
        return _emit(args, payload, lines)
    raise ValueError(f"unknown uart action: {args.action}")


def _cmd_diag(args: argparse.Namespace) -> int:
    from core.diag_uart_service import execute_diag_requests

    cfg = _cfg(args.config)
    script_path = Path(args.script) if args.script else None
    log_path = Path(args.log_path) if args.log_path else cfg["outputs"]["runtime_root_path"] / "diag_exchange.log"
    result_path = Path(args.result_path) if args.result_path else cfg["outputs"]["runtime_root_path"] / "diag_exec_result.json"
    result = execute_diag_requests(
        cfg,
        list(args.hex or []),
        log_path,
        result_path,
        script_path=script_path,
    )
    status = status_from_exit_code(result.exit_code, blocked=result.exit_code in {40, 42})
    payload = build_result_payload(
        "diag exec",
        result.exit_code,
        status=status,
        summary=f"diag exec exit={result.exit_code} exchanges={result.payload.get('exchange_count', 0)}",
        details=result.payload,
        artifacts={"log_path": str(result.log_path), "result_path": str(result.result_path)},
    )
    lines = [payload["summary"]]
    if result.payload.get("error"):
        lines.append(f"diag exec error: {result.payload['error']}")
    return _emit(args, payload, lines)


def _cmd_monitor(args: argparse.Namespace) -> int:
    from core.monitor_service import (
        start_monitor_daemon,
        stop_monitor_daemon,
        summarize_monitor_samples,
    )

    cfg = _cfg(args.config)
    live_dir = cfg["outputs"]["runtime_root_path"] / "monitor_live"
    if args.action == "start":
        message = start_monitor_daemon(cfg, Path(args.config), Path(__file__).resolve(), reset_first=bool(args.reset_first))
        code = 2 if "monitor not started" in message else 0
        payload = build_result_payload("monitor start", code, summary=message, details={"action": "start", "reset_first": bool(args.reset_first)})
        return _emit(args, payload, [message])
    if args.action == "stop":
        message = stop_monitor_daemon(cfg)
        payload = build_result_payload("monitor stop", 0, summary=message, details={"action": "stop"})
        return _emit(args, payload, [message])
    if args.action == "stats":
        source = Path(args.source) if args.source else live_dir / "monitor_samples.csv"
        details = summarize_monitor_samples(source)
        code = 0 if details.get("ok") else 2
        payload = build_result_payload(
            "monitor stats",
            code,
            summary=(
                f"monitor stats hz={details.get('actual_sample_hz', 0)} samples={details.get('sample_count', 0)}"
                if details.get("ok")
                else f"monitor stats failed: {details.get('error', 'unknown error')}"
            ),
            details=details,
            artifacts={"source": str(source)},
        )
        return _emit(args, payload, [payload["summary"]])
    raise ValueError(f"unknown monitor action: {args.action}")


def _cmd_monitor_run_internal(args: argparse.Namespace) -> int:
    from core.monitor_service import MonitorEngine

    cfg = _cfg(args.config)
    live_dir = cfg["outputs"]["runtime_root_path"] / "monitor_live"
    out_dir = Path(args.out_dir) if args.out_dir else live_dir
    code = MonitorEngine(cfg, out_dir).run(reset_first=bool(args.reset_first))
    payload = build_result_payload(
        "__monitor-run",
        code,
        summary=f"monitor internal run exit={code}",
        details={"out_dir": str(out_dir), "reset_first": bool(args.reset_first)},
        artifacts={"out_dir": str(out_dir)},
    )
    return _emit(args, payload, [payload["summary"]])


def _cmd_fix_build(args: argparse.Namespace) -> int:
    from core.build_errors import parse_build_log

    cfg = _cfg(args.config)
    log_path = Path(args.log) if args.log else cfg["outputs"]["runtime_root_path"] / "build.log"
    if not log_path.exists():
        payload = build_result_payload(
            "fix-build",
            2,
            summary=f"build log not found: {log_path}",
            artifacts={"log_path": str(log_path)},
            suggested_fixes=[],
        )
        return _emit(args, payload, [payload["summary"]])

    parsed = [item for item in parse_build_log(log_path, Path(cfg["project_root_path"])) if item.level == "error"]
    suggested_fixes = [
        {
            "file": item.file,
            "line": item.line,
            "message": item.message,
            "error_code": item.error_code,
            "fix": item.suggested_fix,
        }
        for item in parsed
    ]
    payload = build_result_payload(
        "fix-build",
        0,
        summary=f"structured fixes ready: count={len(suggested_fixes)}",
        artifacts={"log_path": str(log_path)},
        suggested_fixes=suggested_fixes,
    )
    lines = [payload["summary"]]
    if suggested_fixes:
        first = suggested_fixes[0]
        lines.append(f"first fix: {first['error_code']} -> {first['fix'].get('action_type', '')}")
    return _emit(args, payload, lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Portable STM32 Agent Workbench")
    public_commands = "{doctor,build,remote-dt,opencode-auto,flash,reset,uart,diag,monitor,fix-build}"
    sub = parser.add_subparsers(dest="command", required=True, metavar=public_commands)

    p_doctor = sub.add_parser("doctor", help="run environment and configuration checks")
    p_doctor.add_argument("--config", default=str(DEFAULT_CONFIG))
    _add_json_flag(p_doctor)
    p_doctor.set_defaults(func=_cmd_doctor)

    p_build = sub.add_parser("build", help="configure and build the project")
    p_build.add_argument("--config", default=str(DEFAULT_CONFIG))
    _add_json_flag(p_build)
    p_build.set_defaults(func=_cmd_build)

    p_remote_dt = sub.add_parser("remote-dt", help="run remote DT build, execute, coverage, and artifact pull")
    p_remote_dt.add_argument("action", choices=["build", "execute", "coverage", "pipeline", "pull-logs", "push-files"])
    p_remote_dt.add_argument("--config", default=str(DEFAULT_CONFIG))
    _add_json_flag(p_remote_dt)
    p_remote_dt.set_defaults(func=_cmd_remote_dt)

    p_opencode_auto = sub.add_parser("opencode-auto", help="run OpenCode task planning and subtask execution")
    p_opencode_auto.add_argument("action", choices=["run"])
    p_opencode_auto.add_argument("--config", default=str(DEFAULT_CONFIG))
    p_opencode_auto.add_argument("--task", required=True)
    p_opencode_auto.add_argument("--plan-file", default="")
    p_opencode_auto.add_argument("--max-retries", type=int, default=None)
    p_opencode_auto.add_argument("--dry-run", action="store_true")
    _add_json_flag(p_opencode_auto)
    p_opencode_auto.set_defaults(func=_cmd_opencode_auto)

    p_flash = sub.add_parser("flash", help="flash firmware")
    p_flash.add_argument("--config", default=str(DEFAULT_CONFIG))
    p_flash.add_argument("--method", default="")
    _add_json_flag(p_flash)
    p_flash.set_defaults(func=_cmd_flash)

    p_reset = sub.add_parser("reset", help="reset target")
    p_reset.add_argument("--config", default=str(DEFAULT_CONFIG))
    p_reset.add_argument("--method", default="")
    _add_json_flag(p_reset)
    p_reset.set_defaults(func=_cmd_reset)

    p_uart = sub.add_parser("uart", help="run UART CLI command batches")
    p_uart.add_argument("action", choices=["exec"])
    p_uart.add_argument("--config", default=str(DEFAULT_CONFIG))
    p_uart.add_argument("--command", action="append", default=[])
    p_uart.add_argument("--script", default="")
    p_uart.add_argument("--transcript", default="")
    p_uart.add_argument("--diag-path", default="")
    p_uart.add_argument("--reset-first", action="store_true")
    p_uart.add_argument("--expect-ready", action="store_true")
    _add_json_flag(p_uart)
    p_uart.set_defaults(func=_cmd_uart)

    p_diag = sub.add_parser("diag", help="run raw hex request/reply exchanges on the diagnostic UART")
    p_diag.add_argument("action", choices=["exec"])
    p_diag.add_argument("--config", default=str(DEFAULT_CONFIG))
    p_diag.add_argument("--hex", action="append", default=[])
    p_diag.add_argument("--script", default="")
    p_diag.add_argument("--log-path", default="")
    p_diag.add_argument("--result-path", default="")
    _add_json_flag(p_diag)
    p_diag.set_defaults(func=_cmd_diag)

    p_monitor = sub.add_parser("monitor", help="start/stop monitor capture or summarize captured samples")
    p_monitor.add_argument("action", choices=["start", "stop", "stats"])
    p_monitor.add_argument("--config", default=str(DEFAULT_CONFIG))
    p_monitor.add_argument("--source", "--src", default="")
    p_monitor.add_argument("--reset-first", action="store_true")
    _add_json_flag(p_monitor)
    p_monitor.set_defaults(func=_cmd_monitor)

    p_monitor_run = sub.add_parser("__monitor-run", help=argparse.SUPPRESS)
    p_monitor_run.add_argument("--config", default=str(DEFAULT_CONFIG))
    p_monitor_run.add_argument("--out-dir", default="")
    p_monitor_run.add_argument("--reset-first", action="store_true")
    _add_json_flag(p_monitor_run)
    p_monitor_run.set_defaults(func=_cmd_monitor_run_internal)
    sub._choices_actions = [action for action in sub._choices_actions if action.dest != "__monitor-run"]

    p_fix_build = sub.add_parser("fix-build", help="turn the latest build log into structured suggested fixes")
    p_fix_build.add_argument("--config", default=str(DEFAULT_CONFIG))
    p_fix_build.add_argument("--log", default="")
    _add_json_flag(p_fix_build)
    p_fix_build.set_defaults(func=_cmd_fix_build)

    return parser


def _validate_args(args: argparse.Namespace) -> int | None:
    return None


def dispatch_args(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    validation = _validate_args(args)
    if validation is not None:
        return int(validation)
    return int(args.func(args))


def main() -> int:
    return dispatch_args()


if __name__ == "__main__":
    raise SystemExit(main())
