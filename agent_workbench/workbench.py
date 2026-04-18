from __future__ import annotations

import argparse
import sys
from pathlib import Path

from core.config import load_config


DEFAULT_CONFIG = Path(__file__).resolve().parent / "agent_workbench.yaml"
UART_ACTIONS = {"console", "exec", "start", "run", "stop", "status"}
UART_ALIAS_FLAGS = {
    "--console": "console",
    "--exec": "exec",
    "--start": "start",
    "--run": "run",
    "--stop": "stop",
    "--status": "status",
}


def _cfg(path_text: str) -> dict:
    return load_config(Path(path_text).resolve())


def _normalize_uart_argv(argv: list[str]) -> list[str]:
    if not argv or argv[0] != "uart":
        return argv
    if len(argv) > 1 and argv[1] in UART_ACTIONS:
        return argv
    if "--help" in argv or "-h" in argv:
        return argv

    rest = list(argv[1:])
    has_exec_payload = any(token in {"--command", "--script"} for token in rest) or ("--exec" in rest)
    action = "exec" if has_exec_payload else None
    normalized: list[str] = []
    index = 0
    while index < len(rest):
        token = rest[index]
        if token in UART_ALIAS_FLAGS:
            if token == "--exec":
                if index + 1 < len(rest) and not str(rest[index + 1]).startswith("-"):
                    normalized.extend(["--command", rest[index + 1]])
                    index += 2
                    continue
                index += 1
                continue
            if action is None:
                action = UART_ALIAS_FLAGS[token]
            index += 1
            continue
        normalized.append(token)
        index += 1

    if action is None and any(token in {"--command", "--script"} for token in normalized):
        action = "exec"
    if action is None:
        return argv
    return ["uart", action, *normalized]


def _normalize_argv(argv: list[str]) -> list[str]:
    if not argv:
        return argv
    if argv[0] == "uart":
        return _normalize_uart_argv(argv)
    return argv


def _cmd_doctor(args: argparse.Namespace) -> int:
    from core.doctor import run_doctor

    cfg = _cfg(args.config)
    code, summary = run_doctor(cfg, cfg["outputs"]["runtime_root_path"])
    print(f"doctor fail={summary['fail_count']} warn={summary['warn_count']}")
    return int(code)


def _cmd_build(args: argparse.Namespace) -> int:
    from core.build_service import run_build

    cfg = _cfg(args.config)
    code = run_build(cfg, cfg["outputs"]["runtime_root_path"] / "build.log")
    print(f"build exit={code}")
    return int(code)


def _cmd_flash(args: argparse.Namespace) -> int:
    from core.flash_service import run_flash

    cfg = _cfg(args.config)
    code = run_flash(cfg, method=args.method.strip() if args.method else None, log_path=cfg["outputs"]["runtime_root_path"] / "flash.log")
    print(f"flash exit={code}")
    return int(code)


def _cmd_reset(args: argparse.Namespace) -> int:
    from core.flash_service import run_reset

    cfg = _cfg(args.config)
    code = run_reset(cfg, method=args.method.strip() if args.method else None, log_path=cfg["outputs"]["runtime_root_path"] / "reset.log")
    print(f"reset exit={code}")
    return int(code)


def _cmd_uart(args: argparse.Namespace) -> int:
    from core.uart_service import UartLogger, execute_uart_commands, run_uart_console, start_uart_daemon, stop_uart_daemon, uart_status
    from core.utils import ensure_dir

    cfg = _cfg(args.config)
    if args.port:
        cfg["uart"]["port"] = str(args.port).strip()
    if args.baudrate:
        cfg["uart"]["baudrate"] = int(args.baudrate)
    if args.action == "console":
        return run_uart_console(cfg, cfg["outputs"]["runtime_root_path"] / "uart_console.log")
    if args.action == "start":
        print(start_uart_daemon(cfg, Path(args.config), Path(__file__).resolve()))
        return 0
    if args.action == "stop":
        print(stop_uart_daemon(cfg))
        return 0
    if args.action == "status":
        print(uart_status(cfg))
        return 0
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
            print("uart exec requires --command or --script", file=sys.stderr)
            return 2
        transcript_path = Path(args.transcript) if args.transcript else cfg["outputs"]["runtime_root_path"] / "cli_transcript.log"
        diag_path = Path(args.diag_path) if args.diag_path else transcript_path.with_name("cli_diag.json")
        result = execute_uart_commands(
            cfg,
            commands,
            transcript_path,
            reset_first=bool(args.reset_first),
            expect_ready=(True if args.expect_ready else None),
            diag_path=diag_path,
        )
        extra = f" diag={result.diag_path}" if result.diag_path else ""
        print(f"uart exec exit={result.exit_code} transcript={transcript_path}{extra}")
        if result.diag and result.diag.get("classification"):
            summary = result.diag["classification"].get("summary", "")
            detail = result.diag["classification"].get("detail", "")
            print(f"uart exec diagnosis: {summary} | {detail}")
        return int(result.exit_code)
    if args.action == "run":
        log_path = Path(args.log_path) if args.log_path else cfg["outputs"]["runtime_root_path"] / "uart_live" / "uart.log"
        ensure_dir(log_path.parent)
        logger = UartLogger(
            port=cfg["uart"]["port"],
            baudrate=int(cfg["uart"]["baudrate"]),
            encoding=cfg["uart"].get("encoding", "utf-8"),
            timeout_sec=float(cfg["uart"].get("line_timeout_sec", 0.2)),
            log_path=log_path,
        )
        return logger.run(echo_stdout=False)
    raise ValueError(f"unknown uart action: {args.action}")


def _cmd_diag(args: argparse.Namespace) -> int:
    from core.diag_uart_service import execute_diag_exchange

    cfg = _cfg(args.config)
    if args.port:
        cfg["diag_uart"]["port"] = str(args.port).strip()
    if args.baudrate:
        cfg["diag_uart"]["baudrate"] = int(args.baudrate)
    if args.action == "exchange":
        if not args.hex:
            print("diag exchange requires --hex \"01 03 00 10 ...\"", file=sys.stderr)
            return 2
        log_path = Path(args.log_path) if args.log_path else cfg["outputs"]["runtime_root_path"] / "diag_exchange.log"
        try:
            result = execute_diag_exchange(
                cfg,
                args.hex,
                log_path,
                append_crc=args.append_crc,
                response_timeout_sec=(float(args.timeout_sec) if args.timeout_sec > 0 else None),
                expected_length=max(0, int(args.rx_len)),
            )
        except (RuntimeError, ValueError) as exc:
            print(f"diag exchange failed: {exc}", file=sys.stderr)
            return 1
        print(
            f"diag exchange exit={result.exit_code} port={cfg['diag_uart']['port']} "
            f"tx=\"{result.request_hex}\" rx=\"{result.response_hex or '[timeout]'}\" log={result.log_path}"
        )
        return int(result.exit_code)
    raise ValueError(f"unknown diag action: {args.action}")


def _cmd_monitor(args: argparse.Namespace) -> int:
    from core.monitor_service import MonitorEngine, export_monitor_table, monitor_status, start_monitor_daemon, stop_monitor_daemon
    from core.utils import ensure_dir

    cfg = _cfg(args.config)
    if args.action == "start":
        print(start_monitor_daemon(cfg, Path(args.config), Path(__file__).resolve()))
        return 0
    if args.action == "stop":
        print(stop_monitor_daemon(cfg))
        return 0
    if args.action == "status":
        print(monitor_status(cfg))
        return 0
    if args.action == "run":
        out_dir = Path(args.out_dir) if args.out_dir else cfg["outputs"]["runtime_root_path"] / "monitor_live"
        ensure_dir(out_dir)
        return MonitorEngine(cfg, out_dir).run()
    if args.action == "export":
        print(export_monitor_table(Path(args.source), Path(args.dest)))
        return 0
    raise ValueError(f"unknown monitor action: {args.action}")


def _cmd_openocd(args: argparse.Namespace) -> int:
    from core.openocd_service import openocd_status, start_openocd_daemon, stop_openocd_daemon

    cfg = _cfg(args.config)
    if args.action == "start":
        print(start_openocd_daemon(cfg))
        return 0
    if args.action == "stop":
        print(stop_openocd_daemon(cfg))
        return 0
    if args.action == "status":
        print(openocd_status(cfg))
        return 0
    raise ValueError(f"unknown openocd action: {args.action}")


def _cmd_session(args: argparse.Namespace) -> int:
    from core.session_service import run_debug_session, run_feature_session

    cfg = _cfg(args.config)
    if args.mode == "debug":
        return run_debug_session(cfg, session_name=args.name)
    return run_feature_session(cfg, task_path=Path(args.task), session_name=args.name)


def _cmd_test(args: argparse.Namespace) -> int:
    from core.test_service import generate_tests, run_tests

    cfg = _cfg(args.config)
    if args.action == "generate":
        out_dir = generate_tests(cfg, Path(args.task))
        print(f"generated tests: {out_dir}")
        return 0
    code, log_path = run_tests(cfg)
    print(f"tests exit={code} log={log_path}")
    return int(code)


def _cmd_decompose(args: argparse.Namespace) -> int:
    from core.task_breakdown import write_task_breakdown

    cfg = _cfg(args.config)
    out_path = write_task_breakdown(cfg, Path(args.task))
    print(f"task breakdown: {out_path}")
    return 0


def _cmd_autoflow(args: argparse.Namespace) -> int:
    from core.autoflow_service import mark_autoflow_progress, resume_autoflow, run_autoflow, status_autoflow

    cfg = _cfg(args.config)
    task_path = Path(args.task).resolve() if args.task else None
    if args.status:
        start_path = status_autoflow(cfg, task_path=task_path)
        print(f"autoflow start: {start_path}")
        return 0
    if args.done:
        start_path = mark_autoflow_progress(
            cfg,
            status="done",
            subtask_ids=[item.strip() for item in str(args.done).split(",") if item.strip()],
            note=args.note,
            task_path=task_path,
        )
        print(f"autoflow start: {start_path}")
        return 0
    if args.blocked:
        start_path = mark_autoflow_progress(
            cfg,
            status="blocked",
            subtask_ids=[item.strip() for item in str(args.blocked).split(",") if item.strip()],
            note=args.note,
            task_path=task_path,
        )
        print(f"autoflow start: {start_path}")
        return 0
    if args.skip:
        start_path = mark_autoflow_progress(
            cfg,
            status="skipped",
            subtask_ids=[item.strip() for item in str(args.skip).split(",") if item.strip()],
            note=args.note,
            task_path=task_path,
        )
        print(f"autoflow start: {start_path}")
        return 0
    if args.resume:
        start_path = resume_autoflow(cfg)
        print(f"autoflow start: {start_path}")
        return 0
    start_path = run_autoflow(
        cfg,
        goal=args.goal,
        mode=args.mode,
        profile_name=args.profile,
        task_path=task_path,
    )
    print(f"autoflow start: {start_path}")
    return 0


def _cmd_compare(args: argparse.Namespace) -> int:
    from core.compare_service import compare_sessions
    from core.session_service import compare_latest

    cfg = _cfg(args.config)
    if args.latest:
        out_path = compare_latest(cfg)
        print(f"compare report: {out_path}")
        return 0
    if not args.old or not args.new:
        print("compare requires --latest or both --old and --new", file=sys.stderr)
        return 2
    out_path = Path(args.out) if args.out else Path(args.new) / f"compare_vs_{Path(args.old).name}.md"
    result = compare_sessions(Path(args.old), Path(args.new), out_path)
    print(f"compare report: {result}")
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    from core.compare_service import list_session_dirs
    from core.session_service import rebuild_report
    from core.utils import read_text

    if args.latest:
        cfg = _cfg(args.config)
        sessions = list_session_dirs(Path(cfg["outputs"]["evidence_root_path"]))
        if not sessions:
            print("report requires --session or an existing latest session", file=sys.stderr)
            return 2
        result = rebuild_report(sessions[-1])
        print(f"report generated: {result}")
        brief_path = sessions[-1] / "session_brief.md"
        if brief_path.exists():
            first_line = next((line for line in read_text(brief_path).splitlines() if line.startswith("- summary: ")), "")
            if first_line:
                print(first_line.replace("- summary: ", "report summary: ", 1))
        return 0
    result = rebuild_report(Path(args.session))
    print(f"report generated: {result}")
    return 0


def _cmd_init_vscode(args: argparse.Namespace) -> int:
    from core.vscode_service import write_vscode_tasks

    cfg = _cfg(args.config)
    tasks_path = write_vscode_tasks(cfg)
    print(f"vscode tasks written: {tasks_path}")
    return 0


def _cmd_context(args: argparse.Namespace) -> int:
    from core.context_service import write_context_pack

    cfg = _cfg(args.config)
    task_path = Path(args.task).resolve() if args.task else None
    session_path = Path(args.session).resolve() if args.session else None
    out_path = Path(args.out).resolve() if args.out else None
    result = write_context_pack(
        cfg,
        mode=args.mode,
        stage=args.stage,
        profile_name=args.profile,
        task_path=task_path,
        session_dir=session_path,
        out_path=out_path,
    )
    print(f"context pack: {result}")
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    from core.session_service import run_current_verify
    from core.utils import read_text

    cfg = _cfg(args.config)
    if args.mode == "current":
        code, summary_path = run_current_verify(cfg, Path(args.task))
        print(f"verify summary: {summary_path}")
        first_lines = read_text(summary_path).splitlines()[:8]
        for line in first_lines:
            print(line)
        return int(code)
    print(f"unknown verify mode: {args.mode}", file=sys.stderr)
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Portable STM32 Agent Workbench")
    sub = parser.add_subparsers(dest="command", required=True)

    p_doctor = sub.add_parser("doctor", help="run environment and configuration checks")
    p_doctor.add_argument("--config", default=str(DEFAULT_CONFIG))
    p_doctor.set_defaults(func=_cmd_doctor)

    p_build = sub.add_parser("build", help="configure and build the project")
    p_build.add_argument("--config", default=str(DEFAULT_CONFIG))
    p_build.set_defaults(func=_cmd_build)

    p_flash = sub.add_parser("flash", help="flash firmware")
    p_flash.add_argument("--config", default=str(DEFAULT_CONFIG))
    p_flash.add_argument("--method", default="")
    p_flash.set_defaults(func=_cmd_flash)

    p_reset = sub.add_parser("reset", help="reset target")
    p_reset.add_argument("--config", default=str(DEFAULT_CONFIG))
    p_reset.add_argument("--method", default="")
    p_reset.set_defaults(func=_cmd_reset)

    p_uart = sub.add_parser("uart", help="UART console, logger, and CLI execution")
    p_uart.add_argument("action", choices=["console", "exec", "start", "run", "stop", "status"])
    p_uart.add_argument("--config", default=str(DEFAULT_CONFIG))
    p_uart.add_argument("--log-path", default="")
    p_uart.add_argument("--command", action="append", default=[])
    p_uart.add_argument("--script", default="")
    p_uart.add_argument("--transcript", default="")
    p_uart.add_argument("--diag-path", default="")
    p_uart.add_argument("--reset-first", action="store_true")
    p_uart.add_argument("--expect-ready", action="store_true")
    p_uart.add_argument("--port", default="")
    p_uart.add_argument("--baudrate", type=int, default=0)
    p_uart.set_defaults(func=_cmd_uart)

    p_diag = sub.add_parser("diag", help="diagnostic UART hex exchange")
    p_diag.add_argument("action", choices=["exchange"])
    p_diag.add_argument("--config", default=str(DEFAULT_CONFIG))
    p_diag.add_argument("--hex", default="")
    p_diag.add_argument("--append-crc", choices=["none", "modbus"], default="")
    p_diag.add_argument("--timeout-sec", type=float, default=0.0)
    p_diag.add_argument("--rx-len", type=int, default=0)
    p_diag.add_argument("--log-path", default="")
    p_diag.add_argument("--port", default="")
    p_diag.add_argument("--baudrate", type=int, default=0)
    p_diag.set_defaults(func=_cmd_diag)

    p_monitor = sub.add_parser("monitor", help="monitor variables/registers/memory")
    p_monitor.add_argument("action", choices=["start", "run", "stop", "status", "export"])
    p_monitor.add_argument("--config", default=str(DEFAULT_CONFIG))
    p_monitor.add_argument("--out-dir", default="")
    p_monitor.add_argument("--source", default="")
    p_monitor.add_argument("--dest", default="")
    p_monitor.set_defaults(func=_cmd_monitor)

    p_openocd = sub.add_parser("openocd", help="manage openocd daemon")
    p_openocd.add_argument("action", choices=["start", "stop", "status"])
    p_openocd.add_argument("--config", default=str(DEFAULT_CONFIG))
    p_openocd.set_defaults(func=_cmd_openocd)

    p_session = sub.add_parser("session", help="run debug or feature session")
    p_session.add_argument("mode", choices=["debug", "feature"])
    p_session.add_argument("--config", default=str(DEFAULT_CONFIG))
    p_session.add_argument("--task", default="")
    p_session.add_argument("--name", default="")
    p_session.set_defaults(func=_cmd_session)

    p_test = sub.add_parser("test", help="generate or run tests")
    p_test.add_argument("action", choices=["generate", "run"])
    p_test.add_argument("--config", default=str(DEFAULT_CONFIG))
    p_test.add_argument("--task", default="")
    p_test.set_defaults(func=_cmd_test)

    p_decompose = sub.add_parser("decompose", help="generate a small-step breakdown for a task")
    p_decompose.add_argument("--config", default=str(DEFAULT_CONFIG))
    p_decompose.add_argument("--task", default="")
    p_decompose.set_defaults(func=_cmd_decompose)

    p_autoflow = sub.add_parser("autoflow", help="start or resume one-line staged automation from a natural-language goal")
    p_autoflow.add_argument("--config", default=str(DEFAULT_CONFIG))
    p_autoflow.add_argument("--goal", default="")
    p_autoflow.add_argument("--mode", choices=["debug", "feature", "test"], default="")
    p_autoflow.add_argument("--profile", default="")
    p_autoflow.add_argument("--task", default="")
    p_autoflow.add_argument("--resume", action="store_true")
    p_autoflow.add_argument("--status", action="store_true")
    p_autoflow.add_argument("--done", default="")
    p_autoflow.add_argument("--blocked", default="")
    p_autoflow.add_argument("--skip", default="")
    p_autoflow.add_argument("--note", default="")
    p_autoflow.set_defaults(func=_cmd_autoflow)

    p_compare = sub.add_parser("compare", help="compare session outputs")
    p_compare.add_argument("--config", default=str(DEFAULT_CONFIG))
    p_compare.add_argument("--latest", action="store_true")
    p_compare.add_argument("--old", default="")
    p_compare.add_argument("--new", default="")
    p_compare.add_argument("--out", default="")
    p_compare.set_defaults(func=_cmd_compare)

    p_report = sub.add_parser("report", help="rebuild session summary or the latest verdict set")
    p_report.add_argument("--config", default=str(DEFAULT_CONFIG))
    p_report.add_argument("--session", default="")
    p_report.add_argument("--latest", action="store_true")
    p_report.set_defaults(func=_cmd_report)

    p_vscode = sub.add_parser("init-vscode", help="generate VS Code tasks.json")
    p_vscode.add_argument("--config", default=str(DEFAULT_CONFIG))
    p_vscode.set_defaults(func=_cmd_init_vscode)

    p_context = sub.add_parser("context", help="generate a compact context pack for low-context models")
    p_context.add_argument("--config", default=str(DEFAULT_CONFIG))
    p_context.add_argument("--mode", choices=["debug", "feature", "test", "report"], default="debug")
    p_context.add_argument("--stage", choices=["analyze", "implement", "verify", "resume"], default="analyze")
    p_context.add_argument("--profile", default="")
    p_context.add_argument("--task", default="")
    p_context.add_argument("--session", default="")
    p_context.add_argument("--out", default="")
    p_context.set_defaults(func=_cmd_context)

    p_verify = sub.add_parser("verify", help="run a one-command verification flow")
    p_verify.add_argument("mode", choices=["current"])
    p_verify.add_argument("--config", default=str(DEFAULT_CONFIG))
    p_verify.add_argument("--task", default="")
    p_verify.set_defaults(func=_cmd_verify)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args(_normalize_argv(sys.argv[1:]))
    if getattr(args, "command", "") == "session" and getattr(args, "mode", "") == "feature" and not getattr(args, "task", ""):
        print("session feature requires --task <task.yaml>", file=sys.stderr)
        return 2
    if getattr(args, "command", "") == "test" and getattr(args, "action", "") == "generate" and not getattr(args, "task", ""):
        print("test generate requires --task <task.yaml>", file=sys.stderr)
        return 2
    if getattr(args, "command", "") == "decompose" and not getattr(args, "task", ""):
        print("decompose requires --task <task.yaml>", file=sys.stderr)
        return 2
    if getattr(args, "command", "") == "autoflow":
        action_flags = [
            bool(getattr(args, "resume", False)),
            bool(getattr(args, "status", False)),
            bool(getattr(args, "done", "")),
            bool(getattr(args, "blocked", "")),
            bool(getattr(args, "skip", "")),
        ]
        if sum(1 for item in action_flags if item) > 1:
            print("autoflow accepts only one of --resume, --status, --done, --blocked, or --skip", file=sys.stderr)
            return 2
        if not any(action_flags) and not getattr(args, "goal", "") and not getattr(args, "task", ""):
            print("autoflow requires --goal <natural language task>, --task <task.yaml>, or one of --resume/--status/--done/--blocked/--skip", file=sys.stderr)
            return 2
        if any(action_flags) and getattr(args, "goal", ""):
            print("autoflow status/update actions do not accept --goal", file=sys.stderr)
            return 2
    if getattr(args, "command", "") == "verify" and getattr(args, "mode", "") == "current" and not getattr(args, "task", ""):
        print("verify current requires --task <task.yaml>", file=sys.stderr)
        return 2
    if getattr(args, "command", "") == "report" and not getattr(args, "latest", False) and not getattr(args, "session", ""):
        print("report requires --session <session_dir> or --latest", file=sys.stderr)
        return 2
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
