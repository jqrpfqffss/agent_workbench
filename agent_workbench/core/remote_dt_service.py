from __future__ import annotations

import re
import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

from .remote_dt_errors import RemoteDtConfigError, error_to_dict
from .utils import ensure_dir, read_text, split_command, utc_now_iso, write_json


DT_LOG_FILES = {
    "build": "dt_build.log",
    "execute": "dt_execute.log",
    "coverage": "dt_coverage.log",
}

DT_RESULT_FILES = {
    "build": "dt_build_result.json",
    "execute": "dt_execute_result.json",
    "coverage": "dt_coverage_result.json",
}

STEP_SCRIPTS = {
    "build": "build",
    "execute": "execute",
    "coverage": "coverage",
}

STEP_TIMEOUTS = {
    "build": "build_sec",
    "execute": "execute_sec",
    "coverage": "coverage_sec",
}

ERROR_PATTERNS = [
    "error:",
    "fatal error:",
    "undefined reference",
    "multiple definition",
    "no such file or directory",
    "command not found",
    "permission denied",
    "make: ***",
    "ninja: build stopped",
    "cmake error",
    "gcov error",
    "lcov error",
    "genhtml error",
    "cannot open",
    "no coverage data found",
]

WARNING_PATTERNS = [
    "warning:",
    "deprecated",
    "unused variable",
    "implicit declaration",
]

TEST_FAILURE_PATTERNS = [
    "fail",
    "failed",
    "assertion",
    "assert",
    "expected",
    "actual",
    "error count",
    "test failed",
]


@dataclass
class CommandResult:
    argv: list[str]
    returncode: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False


Runner = Callable[[Sequence[str], int], CommandResult]


class RemoteDtService:
    def __init__(self, cfg: dict[str, Any], runner: Runner | None = None):
        self.cfg = cfg
        self.remote_cfg = cfg.get("remote_dt", {}) if isinstance(cfg.get("remote_dt", {}), dict) else {}
        self.project_root = Path(cfg.get("project_root_path", Path.cwd())).resolve()
        self.runner = runner or self._subprocess_runner

    def run(self, action: str) -> dict[str, Any]:
        try:
            self._validate_config()
            if action == "pipeline":
                payload = self._run_pipeline()
            elif action == "pull-logs":
                payload = self._pull_logs_action()
            elif action in STEP_SCRIPTS:
                payload = self._run_single_step(action)
            else:
                raise RemoteDtConfigError(f"unsupported remote-dt action: {action}")
        except RemoteDtConfigError as exc:
            payload = self._base_payload(
                action=action,
                status="fail",
                exit_code=2,
                summary=str(exc),
                errors=[error_to_dict(exc, kind="config")],
            )
            self._write_outputs(payload)
        return payload

    def _validate_config(self) -> None:
        if not bool(self.remote_cfg.get("enabled", False)):
            raise RemoteDtConfigError("remote_dt is not enabled")
        missing = [
            name
            for name in ("host", "user", "remote_project_dir")
            if not str(self.remote_cfg.get(name, "")).strip()
        ]
        if missing:
            raise RemoteDtConfigError("remote_dt missing required fields: " + ", ".join(missing))

    def _run_single_step(self, step: str) -> dict[str, Any]:
        step_result = self._run_remote_step(step)
        status = "pass" if step_result["status"] == "pass" else "fail"
        exit_code = 0 if status == "pass" else 1
        payload = self._base_payload(
            action=step,
            status=status,
            exit_code=exit_code,
            summary=f"remote DT {step} {'passed' if status == 'pass' else 'failed'}",
            steps=[step_result],
        )
        self._merge_step_findings(payload, [step_result])
        self._write_outputs(payload)
        return payload

    def _run_pipeline(self) -> dict[str, Any]:
        steps: list[dict[str, Any]] = []
        failed_step = ""
        for step in ("build", "execute", "coverage"):
            if failed_step:
                steps.append({"name": step, "status": "skipped", "reason": f"{failed_step} failed"})
                continue
            result = self._run_remote_step(step)
            steps.append(result)
            if result["status"] != "pass":
                failed_step = step

        if failed_step:
            skipped_text = ""
            if failed_step == "build":
                skipped_text = ", execute and coverage skipped"
            elif failed_step == "execute":
                skipped_text = ", coverage skipped"
            summary = f"remote DT {failed_step} failed{skipped_text}"
            status = "fail"
            exit_code = 1
        else:
            summary = "remote DT pipeline passed"
            status = "pass"
            exit_code = 0

        payload = self._base_payload(
            action="pipeline",
            status=status,
            exit_code=exit_code,
            summary=summary,
            steps=steps,
        )
        self._merge_step_findings(payload, [item for item in steps if item.get("status") != "skipped"])
        self._write_outputs(payload)
        return payload

    def _pull_logs_action(self) -> dict[str, Any]:
        pulls = self._pull_artifacts(include_coverage=True)
        failed = [item for item in pulls if item["exit_code"] != 0]
        status = "fail" if failed else "pass"
        payload = self._base_payload(
            action="pull-logs",
            status=status,
            exit_code=1 if failed else 0,
            summary="remote DT artifacts pulled" if not failed else "remote DT artifact pull failed",
            steps=[],
            details={"pulls": pulls},
        )
        self._merge_logs_findings(payload)
        self._write_outputs(payload)
        return payload

    def _run_remote_step(self, step: str) -> dict[str, Any]:
        remote_command = self._remote_step_script(step)
        argv = self._ssh_argv(remote_command)
        started = time.monotonic()
        timeout = int(self.remote_cfg.get("timeouts", {}).get(STEP_TIMEOUTS[step], 600))
        result = self.runner(argv, timeout)
        duration = round(time.monotonic() - started, 3)
        pulls = self._pull_artifacts(step=step, include_coverage=(step == "coverage"))

        local_log = self._local_log_path(step)
        parsed = parse_dt_log(local_log, step)
        status = "pass" if result.returncode == 0 else "fail"
        errors = parsed["errors"]
        if result.timed_out:
            errors.append(
                {
                    "step": step,
                    "file": "",
                    "line": None,
                    "message": f"remote DT {step} timed out after {timeout}s",
                    "raw": result.stderr or result.stdout or "timeout",
                }
            )
        elif result.returncode != 0 and not errors:
            errors.append(
                {
                    "step": step,
                    "file": "",
                    "line": None,
                    "message": f"remote DT {step} exited with code {result.returncode}",
                    "raw": (result.stderr or result.stdout or "").strip(),
                }
            )
        failed_pulls = [item for item in pulls if item["exit_code"] != 0]
        step_exit_code = int(result.returncode)
        if failed_pulls:
            status = "fail"
            if step_exit_code == 0:
                step_exit_code = 1
            for pull in failed_pulls:
                errors.append(
                    {
                        "step": step,
                        "file": "",
                        "line": None,
                        "message": "failed to pull remote DT artifact",
                        "raw": pull.get("stderr") or pull.get("stdout") or pull.get("command", ""),
                    }
                )

        return {
            "name": step,
            "status": status,
            "exit_code": step_exit_code,
            "remote_exit_code": int(result.returncode),
            "duration_sec": duration,
            "remote_command": self._display_command(argv),
            "remote_log_path": self._remote_step_log(step),
            "local_log_path": self._display_path(local_log),
            "error_count": len(errors),
            "warning_count": len(parsed["warnings"]),
            "pulls": pulls,
            "errors": errors,
            "warnings": parsed["warnings"],
            "test_failures": parsed["test_failures"],
        }

    def _pull_artifacts(self, *, step: str | None = None, include_coverage: bool = False) -> list[dict[str, Any]]:
        pulls: list[tuple[list[str], Path]] = []
        if step:
            pulls.append((self._scp_argv(self._remote_step_log(step), self._local_logs_dir()), self._local_logs_dir()))
            pulls.append((self._scp_argv(self._remote_step_result(step), self._local_results_dir()), self._local_results_dir()))
        else:
            artifact_cfg = self.remote_cfg.get("artifacts", {})
            log_dir = artifact_cfg.get("remote_log_dir", ".agent_workbench_remote_dt/logs")
            result_dir = artifact_cfg.get("remote_result_dir", ".agent_workbench_remote_dt/results")
            pulls.append((self._scp_argv(f"{log_dir}/dt_*.log", self._local_logs_dir()), self._local_logs_dir()))
            pulls.append((self._scp_argv(f"{result_dir}/dt_*.json", self._local_results_dir()), self._local_results_dir()))
        if include_coverage:
            coverage_remote = self.remote_cfg.get("artifacts", {}).get("remote_coverage_dir", "coverage")
            pulls.append((self._scp_argv(coverage_remote, self._local_artifact_dir(), recursive=True), self._local_artifact_dir()))

        results: list[dict[str, Any]] = []
        pull_timeout = int(self.remote_cfg.get("timeouts", {}).get("pull_sec", 300))
        for argv, dest in pulls:
            ensure_dir(dest)
            result = self.runner(argv, pull_timeout)
            results.append(
                {
                    "command": self._display_command(argv),
                    "exit_code": int(result.returncode),
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            )
        return results

    def _ssh_argv(self, remote_command: str) -> list[str]:
        ssh = self.remote_cfg.get("ssh", {}) if isinstance(self.remote_cfg.get("ssh", {}), dict) else {}
        argv = self._command_prefix("ssh_command", "ssh")
        argv.extend(["-p", str(int(self.remote_cfg.get("port", 22)))])
        argv.extend(["-o", f"ConnectTimeout={int(ssh.get('connect_timeout_sec', 10))}"])
        if ssh.get("strict_host_key_checking", False) is False:
            argv.extend(["-o", "StrictHostKeyChecking=no"])
        identity = str(ssh.get("identity_file", "")).strip()
        if identity:
            argv.extend(["-i", identity])
        argv.extend([self._remote_login(), "bash", "-lc", remote_command])
        return argv

    def _scp_argv(self, remote_path: str, local_dest: Path, *, recursive: bool = False) -> list[str]:
        ssh = self.remote_cfg.get("ssh", {}) if isinstance(self.remote_cfg.get("ssh", {}), dict) else {}
        argv = self._command_prefix("scp_command", "scp")
        if recursive:
            argv.append("-r")
        argv.extend(["-P", str(int(self.remote_cfg.get("port", 22)))])
        argv.extend(["-o", f"ConnectTimeout={int(ssh.get('connect_timeout_sec', 10))}"])
        if ssh.get("strict_host_key_checking", False) is False:
            argv.extend(["-o", "StrictHostKeyChecking=no"])
        identity = str(ssh.get("identity_file", "")).strip()
        if identity:
            argv.extend(["-i", identity])
        argv.extend([self._remote_spec(remote_path), str(local_dest)])
        return argv

    def _remote_step_script(self, step: str) -> str:
        scripts = self.remote_cfg.get("scripts", {})
        artifacts = self.remote_cfg.get("artifacts", {})
        script_cmd = str(scripts.get(STEP_SCRIPTS[step], "")).strip()
        remote_project = shlex.quote(str(self.remote_cfg.get("remote_project_dir", "")).strip())
        log_dir = shlex.quote(str(artifacts.get("remote_log_dir", ".agent_workbench_remote_dt/logs")))
        result_dir = shlex.quote(str(artifacts.get("remote_result_dir", ".agent_workbench_remote_dt/results")))
        log_path = shlex.quote(self._remote_step_log(step))
        result_path = shlex.quote(self._remote_step_result(step))
        return (
            "set -o pipefail\n"
            f"cd {remote_project}\n"
            f"mkdir -p {log_dir} {result_dir}\n"
            "START_TS=$(date +%s)\n"
            f"( {script_cmd} ) > {log_path} 2>&1\n"
            "EXIT_CODE=$?\n"
            "END_TS=$(date +%s)\n"
            f"printf '{{\"step\":\"{step}\",\"exit_code\":%s,\"start_ts\":%s,\"end_ts\":%s}}\\n' "
            '"$EXIT_CODE" "$START_TS" "$END_TS" '
            f"> {result_path}\n"
            'exit "$EXIT_CODE"'
        )

    def _remote_step_log(self, step: str) -> str:
        log_dir = self.remote_cfg.get("artifacts", {}).get("remote_log_dir", ".agent_workbench_remote_dt/logs")
        return f"{log_dir.rstrip('/')}/{DT_LOG_FILES[step]}"

    def _remote_step_result(self, step: str) -> str:
        result_dir = self.remote_cfg.get("artifacts", {}).get("remote_result_dir", ".agent_workbench_remote_dt/results")
        return f"{result_dir.rstrip('/')}/{DT_RESULT_FILES[step]}"

    def _remote_spec(self, remote_path: str) -> str:
        remote_project = str(self.remote_cfg.get("remote_project_dir", "")).rstrip("/")
        if remote_path.startswith("/"):
            absolute = remote_path
        else:
            absolute = f"{remote_project}/{remote_path}"
        return f"{self._remote_login()}:{shlex.quote(absolute)}"

    def _remote_login(self) -> str:
        return f"{self.remote_cfg.get('user')}@{self.remote_cfg.get('host')}"

    def _command_prefix(self, key: str, default: str) -> list[str]:
        ssh = self.remote_cfg.get("ssh", {}) if isinstance(self.remote_cfg.get("ssh", {}), dict) else {}
        configured = str(ssh.get(key, "")).strip()
        if not configured:
            return [default]
        parts = split_command(configured)
        return parts or [default]

    def _local_artifact_dir(self) -> Path:
        configured = str(self.remote_cfg.get("local_artifact_dir", "agent_workbench/runtime/remote_dt")).strip()
        path = Path(configured)
        return path if path.is_absolute() else (self.project_root / path).resolve()

    def _local_logs_dir(self) -> Path:
        return self._local_artifact_dir() / "logs"

    def _local_results_dir(self) -> Path:
        return self._local_artifact_dir() / "results"

    def _local_coverage_dir(self) -> Path:
        return self._local_artifact_dir() / "coverage"

    def _local_log_path(self, step: str) -> Path:
        return self._local_logs_dir() / DT_LOG_FILES[step]

    def _artifacts(self) -> dict[str, str]:
        root = self._local_artifact_dir()
        return {
            "result_json": self._display_path(root / "dt_remote_result.json"),
            "summary_md": self._display_path(root / "dt_remote_summary.md"),
            "log_dir": self._display_path(self._local_logs_dir()),
            "build_log": self._display_path(self._local_log_path("build")),
            "execute_log": self._display_path(self._local_log_path("execute")),
            "coverage_log": self._display_path(self._local_log_path("coverage")),
            "coverage_dir": self._display_path(self._local_coverage_dir()),
        }

    def _base_payload(
        self,
        *,
        action: str,
        status: str,
        exit_code: int,
        summary: str,
        steps: list[dict[str, Any]] | None = None,
        details: dict[str, Any] | None = None,
        errors: list[dict[str, Any]] | None = None,
        warnings: list[dict[str, Any]] | None = None,
        test_failures: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return {
            "command": "remote-dt",
            "action": action,
            "status": status,
            "exit_code": int(exit_code),
            "summary": summary,
            "steps": steps or [],
            "details": details or {},
            "artifacts": self._artifacts(),
            "errors": errors or [],
            "warnings": warnings or [],
            "test_failures": test_failures or [],
            "timestamp": utc_now_iso(),
        }

    def _merge_step_findings(self, payload: dict[str, Any], steps: list[dict[str, Any]]) -> None:
        payload["errors"] = [item for step in steps for item in step.get("errors", [])]
        payload["warnings"] = [item for step in steps for item in step.get("warnings", [])]
        payload["test_failures"] = [item for step in steps for item in step.get("test_failures", [])]
        for step in payload.get("steps", []):
            step.pop("errors", None)
            step.pop("warnings", None)
            step.pop("test_failures", None)

    def _merge_logs_findings(self, payload: dict[str, Any]) -> None:
        steps = []
        for step in ("build", "execute", "coverage"):
            parsed = parse_dt_log(self._local_log_path(step), step)
            steps.append({"errors": parsed["errors"], "warnings": parsed["warnings"], "test_failures": parsed["test_failures"]})
        self._merge_step_findings(payload, steps)

    def _write_outputs(self, payload: dict[str, Any]) -> None:
        root = self._local_artifact_dir()
        ensure_dir(root)
        ensure_dir(self._local_logs_dir())
        ensure_dir(self._local_results_dir())
        ensure_dir(self._local_coverage_dir())
        result_path = root / "dt_remote_result.json"
        summary_path = root / "dt_remote_summary.md"
        write_json(result_path, payload)
        summary_path.write_text(render_summary_md(payload), encoding="utf-8")

    def _display_path(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(self.project_root)).replace("\\", "/")
        except ValueError:
            return str(path).replace("\\", "/")

    @staticmethod
    def _display_command(argv: Sequence[str]) -> str:
        return subprocess.list2cmdline([str(item) for item in argv])

    @staticmethod
    def _subprocess_runner(argv: Sequence[str], timeout: int) -> CommandResult:
        try:
            proc = subprocess.run(
                [str(item) for item in argv],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            return CommandResult(list(map(str, argv)), int(proc.returncode), proc.stdout, proc.stderr, False)
        except subprocess.TimeoutExpired as exc:
            return CommandResult(
                list(map(str, argv)),
                124,
                exc.stdout if isinstance(exc.stdout, str) else "",
                exc.stderr if isinstance(exc.stderr, str) else "",
                True,
            )


def parse_dt_log(path: Path, step: str) -> dict[str, list[dict[str, Any]]]:
    text = read_text(path)
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    test_failures: list[dict[str, Any]] = []
    for line in text.splitlines():
        raw = line.strip()
        if not raw:
            continue
        lower = raw.lower()
        item = _parse_log_line(raw, step)
        if any(pattern in lower for pattern in WARNING_PATTERNS):
            warnings.append(item)
        if any(pattern in lower for pattern in ERROR_PATTERNS):
            errors.append(item)
        if any(pattern in lower for pattern in TEST_FAILURE_PATTERNS):
            test_failures.append(item)
    return {"errors": errors, "warnings": warnings, "test_failures": test_failures}


def render_summary_md(payload: dict[str, Any]) -> str:
    failure_stage = next((item.get("name", "") for item in payload.get("steps", []) if item.get("status") == "fail"), "")
    suggestion = _suggestion_for_failure(failure_stage)
    lines = [
        "# Remote DT 执行摘要",
        "",
        "## 结论",
        f"- {str(payload.get('status', '')).upper()}",
        f"- 失败阶段: {failure_stage or '无'}",
        f"- 后续建议: {suggestion}",
        "",
        "## 执行步骤",
        "| 阶段 | 状态 | Exit Code | 耗时 | 本地日志 |",
        "|---|---|---:|---:|---|",
    ]
    for step in payload.get("steps", []):
        lines.append(
            "| {name} | {status} | {exit_code} | {duration} | {log} |".format(
                name=step.get("name", ""),
                status=step.get("status", ""),
                exit_code=step.get("exit_code", ""),
                duration=step.get("duration_sec", ""),
                log=step.get("local_log_path", ""),
            )
        )
    lines.extend(["", "## 关键错误"])
    lines.extend(_finding_lines(payload.get("errors", []), "- 暂无关键错误"))
    lines.extend(["", "## 关键告警"])
    lines.extend(_finding_lines(payload.get("warnings", []), "- 暂无关键告警"))
    lines.extend(["", "## 测试失败"])
    lines.extend(_finding_lines(payload.get("test_failures", []), "- 暂无测试失败"))
    artifacts = payload.get("artifacts", {})
    lines.extend(
        [
            "",
            "## 产物路径",
            f"- result_json: {artifacts.get('result_json', '')}",
            f"- 日志目录: {artifacts.get('log_dir', '')}",
            f"- 覆盖率目录: {artifacts.get('coverage_dir', '')}",
            "",
        ]
    )
    return "\n".join(lines)


def _parse_log_line(raw: str, step: str) -> dict[str, Any]:
    file_name = ""
    line_no: int | None = None
    message = raw
    match = re.search(r"(?P<file>(?:[A-Za-z]:)?[^:\s][^:]*?):(?P<line>\d+)(?::\d+)?:\s*(?P<message>.*)", raw)
    if match:
        file_name = match.group("file")
        line_no = int(match.group("line"))
        message = match.group("message")
    return {
        "step": step,
        "file": file_name,
        "line": line_no,
        "message": message,
        "raw": raw,
    }


def _finding_lines(items: list[dict[str, Any]], empty: str) -> list[str]:
    if not items:
        return [empty]
    lines = []
    for item in items[:20]:
        location = ""
        if item.get("file"):
            location = str(item["file"])
            if item.get("line") is not None:
                location += f":{item['line']}"
            location += " "
        lines.append(f"- [{item.get('step', '')}] {location}{item.get('message', '')}")
    return lines


def _suggestion_for_failure(step: str) -> str:
    if step == "build":
        return "优先分析 dt_build.log，先修复远程编译或链接错误。"
    if step == "execute":
        return "优先分析 dt_execute.log，再修复 DT 用例或业务逻辑。"
    if step == "coverage":
        return "优先分析 dt_coverage.log，再修复覆盖率脚本或产物路径。"
    return "以 remote-dt pipeline 的 JSON 结果和 DT 日志为准。"
