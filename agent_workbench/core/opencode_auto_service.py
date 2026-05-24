from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from .cli_output import build_result_payload
from .utils import ensure_dir, local_now_tag, read_text, split_command, utc_now_iso, write_json


MAX_SUMMARY_CHARS = 300


def _short(text: str, limit: int = MAX_SUMMARY_CHARS) -> str:
    compact = " ".join(str(text or "").split())
    if len(compact) <= limit:
        return compact
    return compact[: max(0, limit - 3)] + "..."


def _title_from_body(body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip(" #-*\t")
        if stripped:
            return _short(stripped, 80)
    return "Untitled task"


def _normalize_tasks(items: Any) -> list[dict[str, str]]:
    if isinstance(items, dict):
        if isinstance(items.get("tasks"), list):
            items = items["tasks"]
        elif isinstance(items.get("subtasks"), list):
            items = items["subtasks"]
        else:
            items = [items]
    if not isinstance(items, list):
        return []

    tasks: list[dict[str, str]] = []
    for index, item in enumerate(items, start=1):
        task_id = f"task_{index:03d}"
        if isinstance(item, str):
            body = item.strip()
            title = _title_from_body(body)
        elif isinstance(item, dict):
            body = str(item.get("body") or item.get("task") or item.get("description") or "").strip()
            title = str(item.get("title") or item.get("name") or _title_from_body(body)).strip()
            raw_id = str(item.get("id") or "").strip()
            if re.fullmatch(r"[A-Za-z0-9_.-]+", raw_id):
                task_id = raw_id
        else:
            continue
        if not body:
            body = title
        if not title:
            title = _title_from_body(body)
        tasks.append({"id": task_id, "title": title, "body": body})
    return tasks


def fallback_split_task(task_text: str) -> list[dict[str, str]]:
    bullets: list[str] = []
    patterns = [
        re.compile(r"^\s*[-*+]\s+\[[ xX]\]\s+(.+?)\s*$"),
        re.compile(r"^\s*\d+[\.)]\s+(.+?)\s*$"),
        re.compile(r"^\s*[-*+]\s+(.+?)\s*$"),
    ]
    for line in task_text.splitlines():
        for pattern in patterns:
            match = pattern.match(line)
            if match:
                bullets.append(match.group(1).strip())
                break
    if bullets:
        return _normalize_tasks(bullets)
    return _normalize_tasks([task_text.strip() or "Run requested OpenCode task"])


def _json_loads_maybe(text: str) -> Any:
    stripped = text.strip()
    if not stripped:
        raise ValueError("empty JSON")
    return json.loads(stripped)


def _render_template(template: str, values: dict[str, Any]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{" + key + "}", str(value))
    return rendered


def _run_template(
    template: str,
    values: dict[str, Any],
    cwd: Path,
    stdout_path: Path,
    stderr_path: Path,
    *,
    timeout_seconds: int,
) -> dict[str, Any]:
    command = _render_template(template, values)
    argv = split_command(command)
    result: dict[str, Any] = {
        "command": command,
        "argv": argv,
        "exit_code": 2,
        "timeout": False,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
    }
    ensure_dir(stdout_path.parent)
    if not argv:
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text("empty command template", encoding="utf-8")
        result["error"] = "empty command template"
        return result
    try:
        proc = subprocess.run(
            argv,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=max(1, int(timeout_seconds)),
            shell=False,
        )
        stdout_path.write_text(proc.stdout or "", encoding="utf-8")
        stderr_path.write_text(proc.stderr or "", encoding="utf-8")
        result["exit_code"] = int(proc.returncode)
        return result
    except subprocess.TimeoutExpired as exc:
        stdout_path.write_text(exc.stdout or "", encoding="utf-8")
        stderr_path.write_text(exc.stderr or "", encoding="utf-8")
        result["exit_code"] = 124
        result["timeout"] = True
        result["error"] = f"timed out after {timeout_seconds}s"
        return result
    except OSError as exc:
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text(str(exc), encoding="utf-8")
        result["exit_code"] = 127
        result["error"] = str(exc)
        return result


def _make_run_dir(runtime_root: Path) -> Path:
    base = runtime_root / "opencode_auto" / local_now_tag()
    candidate = base
    suffix = 2
    while candidate.exists():
        candidate = Path(f"{base}_{suffix}")
        suffix += 1
    return ensure_dir(candidate)


def _load_planner_tasks(
    planner_template: str,
    task_file: Path,
    run_dir: Path,
    plan_file: Path,
    cwd: Path,
    timeout_seconds: int,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    planner_dir = ensure_dir(run_dir / "planner")
    stdout_path = planner_dir / "stdout.log"
    stderr_path = planner_dir / "stderr.log"
    values = {
        "task_file": task_file,
        "run_dir": run_dir,
        "plan_file": plan_file,
    }
    result = _run_template(
        planner_template,
        values,
        cwd,
        stdout_path,
        stderr_path,
        timeout_seconds=timeout_seconds,
    )
    raw_json = read_text(stdout_path)
    if not raw_json.strip() and plan_file.exists():
        raw_json = read_text(plan_file)
    try:
        tasks = _normalize_tasks(_json_loads_maybe(raw_json))
    except Exception as exc:
        result["plan_error"] = str(exc)
        return [], result
    if not tasks:
        result["plan_error"] = "planner returned no tasks"
    return tasks, result


def _write_summary(summary_path: Path, summary: dict[str, Any]) -> None:
    summary["updated_at"] = utc_now_iso()
    write_json(summary_path, summary)


def run_opencode_auto(
    cfg: dict[str, Any],
    *,
    task_text: str,
    dry_run: bool = False,
    planner_cmd_template: str = "",
    opencode_cmd_template: str = "",
    review_cmd_template: str = "",
    max_retries: int = 3,
    timeout_seconds: int = 1800,
) -> dict[str, Any]:
    runtime_root = Path(cfg["outputs"]["runtime_root_path"])
    project_root = Path(cfg["project_root_path"])
    run_dir = _make_run_dir(runtime_root)
    original_task_file = run_dir / "task.md"
    plan_file = run_dir / "plan.json"
    summary_path = run_dir / "summary.json"
    original_task_file.write_text(task_text, encoding="utf-8")

    planner_result: dict[str, Any] | None = None
    tasks: list[dict[str, str]] = []
    if planner_cmd_template.strip():
        tasks, planner_result = _load_planner_tasks(
            planner_cmd_template,
            original_task_file,
            run_dir,
            plan_file,
            project_root,
            timeout_seconds,
        )
    plan_source = "planner"
    if not tasks:
        tasks = fallback_split_task(task_text)
        plan_source = "fallback"
    write_json(plan_file, {"source": plan_source, "tasks": tasks, "planner_result": planner_result})

    max_attempts = 1 + max(0, int(max_retries))
    if not dry_run and not opencode_cmd_template.strip():
        summary = {
            "status": "fail",
            "reason": "missing opencode command template; pass --opencode-cmd-template or --dry-run",
            "counts": {"total": len(tasks), "passed": 0, "skipped": len(tasks)},
            "tasks": [],
            "artifacts": {"run_dir": str(run_dir), "plan_file": str(plan_file), "task_file": str(original_task_file)},
        }
        _write_summary(summary_path, summary)
        return build_result_payload(
            "opencode-auto run",
            2,
            summary=summary["reason"],
            details={"total": len(tasks), "passed": 0, "skipped": len(tasks), "tasks": []},
            artifacts={**summary["artifacts"], "summary_path": str(summary_path)},
        )

    task_results: list[dict[str, Any]] = []
    summary = {
        "status": "running",
        "counts": {"total": len(tasks), "passed": 0, "skipped": 0},
        "tasks": task_results,
        "artifacts": {"run_dir": str(run_dir), "plan_file": str(plan_file), "task_file": str(original_task_file)},
    }

    try:
        for task in tasks:
            task_dir = ensure_dir(run_dir / "tasks" / task["id"])
            task_file = run_dir / "tasks" / f"{task['id']}.md"
            task_file.write_text(f"# {task['title']}\n\n{task['body']}\n", encoding="utf-8")
            compact = {
                "id": task["id"],
                "title": task["title"],
                "status": "running",
                "attempt_count": 0,
                "task_file": str(task_file),
                "attempts": [],
            }
            task_results.append(compact)
            task_passed = False
            last_reason = "not attempted"
            for attempt_index in range(1, max_attempts + 1):
                attempt_dir = ensure_dir(task_dir / f"attempt_{attempt_index:03d}")
                values = {
                    "task_file": task_file,
                    "attempt_dir": attempt_dir,
                    "run_dir": run_dir,
                    "task_id": task["id"],
                }
                if dry_run:
                    stdout_path = attempt_dir / "stdout.log"
                    stderr_path = attempt_dir / "stderr.log"
                    stdout_path.write_text(f"dry-run: {task['id']} {task['title']}\n", encoding="utf-8")
                    stderr_path.write_text("", encoding="utf-8")
                    exec_result = {
                        "command": "dry-run",
                        "argv": [],
                        "exit_code": 0,
                        "timeout": False,
                        "stdout_path": str(stdout_path),
                        "stderr_path": str(stderr_path),
                    }
                else:
                    exec_result = _run_template(
                        opencode_cmd_template,
                        values,
                        project_root,
                        attempt_dir / "stdout.log",
                        attempt_dir / "stderr.log",
                        timeout_seconds=timeout_seconds,
                    )
                review_result = None
                attempt_passed = int(exec_result["exit_code"]) == 0 and not exec_result.get("timeout")
                if attempt_passed and review_cmd_template.strip():
                    review_result = _run_template(
                        review_cmd_template,
                        values,
                        project_root,
                        attempt_dir / "review_stdout.log",
                        attempt_dir / "review_stderr.log",
                        timeout_seconds=timeout_seconds,
                    )
                    attempt_passed = int(review_result["exit_code"]) == 0 and not review_result.get("timeout")
                last_reason = "passed" if attempt_passed else _short(
                    str(exec_result.get("error") or "")
                    or read_text(attempt_dir / "stderr.log")
                    or f"executor exit={exec_result['exit_code']}"
                )
                attempt_summary = {
                    "attempt": attempt_index,
                    "status": "pass" if attempt_passed else "fail",
                    "reason": last_reason,
                    "executor": exec_result,
                    "review": review_result,
                    "attempt_dir": str(attempt_dir),
                }
                write_json(attempt_dir / "result.json", attempt_summary)
                compact["attempts"].append(
                    {
                        "attempt": attempt_index,
                        "status": attempt_summary["status"],
                        "reason": last_reason,
                        "attempt_dir": str(attempt_dir),
                        "result_path": str(attempt_dir / "result.json"),
                    }
                )
                compact["attempt_count"] = attempt_index
                _write_summary(summary_path, summary)
                if attempt_passed:
                    task_passed = True
                    break
            if task_passed:
                compact["status"] = "passed"
                summary["counts"]["passed"] += 1
            else:
                compact["status"] = "failed_skipped"
                compact["reason"] = last_reason
                summary["counts"]["skipped"] += 1
            _write_summary(summary_path, summary)
    except KeyboardInterrupt:
        summary["status"] = "interrupted"
        _write_summary(summary_path, summary)
        return build_result_payload(
            "opencode-auto run",
            130,
            status="fail",
            summary="opencode-auto interrupted",
            details={**summary["counts"], "tasks": task_results},
            artifacts={**summary["artifacts"], "summary_path": str(summary_path)},
        )

    skipped = int(summary["counts"]["skipped"])
    passed = int(summary["counts"]["passed"])
    total = int(summary["counts"]["total"])
    exit_code = 0 if skipped == 0 else 1
    summary["status"] = "pass" if exit_code == 0 else "fail"
    _write_summary(summary_path, summary)
    return build_result_payload(
        "opencode-auto run",
        exit_code,
        summary=f"opencode-auto total={total} passed={passed} skipped={skipped}",
        details={"total": total, "passed": passed, "skipped": skipped, "tasks": task_results},
        artifacts={**summary["artifacts"], "summary_path": str(summary_path)},
    )
