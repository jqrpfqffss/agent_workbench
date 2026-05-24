from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from .cli_output import build_result_payload
from .utils import ensure_dir, local_now_tag, read_text, split_command, utc_now_iso, write_json


MAX_SUMMARY_CHARS = 300
MAX_CONTEXT_LINES = 80
MAX_CONTEXT_CHARS = 8000


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


def _tail_context(paths: list[Path], *, max_lines: int = MAX_CONTEXT_LINES, max_chars: int = MAX_CONTEXT_CHARS) -> str:
    sections: list[str] = []
    for path in paths:
        text = read_text(path)
        if not text.strip():
            continue
        lines = text.splitlines()[-max_lines:]
        section = f"## {path.name}\n" + "\n".join(lines)
        sections.append(section)
    context = "\n\n".join(sections).strip()
    if len(context) <= max_chars:
        return context
    return context[-max_chars:]


def _run_git(argv: list[str], cwd: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "argv": argv,
        "exit_code": 2,
        "stdout": "",
        "stderr": "",
    }
    try:
        proc = subprocess.run(
            argv,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            shell=False,
        )
    except Exception as exc:
        result["error"] = str(exc)
        return result
    result["exit_code"] = int(proc.returncode)
    result["stdout"] = proc.stdout or ""
    result["stderr"] = proc.stderr or ""
    return result


def _git_status_porcelain(cwd: Path, *, ignore_path: Path | None = None) -> dict[str, Any]:
    result = _run_git(["git", "status", "--porcelain=v1", "-z"], cwd)
    stdout = str(result.get("stdout") or "")
    entries = [item for item in stdout.split("\0") if item]
    filtered = entries
    if ignore_path is not None:
        try:
            rel = ignore_path.resolve().relative_to(cwd.resolve()).as_posix().rstrip("/")
            filtered = []
            for entry in entries:
                path_text = entry[3:] if len(entry) > 3 else entry
                normalized = path_text.rstrip("/")
                if normalized == rel or normalized.startswith(rel + "/") or rel.startswith(normalized + "/"):
                    continue
                filtered.append(entry)
        except ValueError:
            filtered = entries
    result["dirty"] = bool(filtered)
    result["entries"] = filtered
    return result


def _git_preserve_excludes(project_root: Path, preserve_path: Path) -> list[str]:
    rel = preserve_path.resolve().relative_to(project_root.resolve()).as_posix()
    parts = rel.split("/")
    excludes: list[str] = []
    for index in range(1, len(parts) + 1):
        prefix = "/".join(parts[:index])
        excludes.extend(["-e", prefix, "-e", f"{prefix}/"])
    return excludes


def _git_pathspec_excluding(project_root: Path, exclude_path: Path) -> list[str]:
    rel = exclude_path.resolve().relative_to(project_root.resolve()).as_posix().rstrip("/")
    return ["--", ".", f":(exclude){rel}", f":(exclude){rel}/**"]


def _git_path_is_ignored(project_root: Path, path: Path) -> bool:
    try:
        rel = path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return False
    result = _run_git(["git", "check-ignore", "-q", rel], project_root)
    return int(result.get("exit_code", 1)) == 0


def _git_stash_top(cwd: Path) -> str:
    result = _run_git(["git", "rev-parse", "-q", "--verify", "refs/stash"], cwd)
    if int(result.get("exit_code", 1)) != 0:
        return ""
    return str(result.get("stdout") or "").strip()


def _git_stash_selector(cwd: Path, stash_hash: str) -> str:
    result = _run_git(["git", "stash", "list", "--format=%H%x00%gd"], cwd)
    if int(result.get("exit_code", 1)) != 0:
        return ""
    for line in str(result.get("stdout") or "").splitlines():
        commit_hash, _, selector = line.partition("\0")
        if commit_hash == stash_hash:
            return selector
    return ""


def _git_drop_snapshot(project_root: Path, snapshot: dict[str, Any] | None) -> dict[str, Any]:
    stash_hash = str((snapshot or {}).get("stash") or "")
    if not stash_hash:
        return {"status": "pass", "reason": "no git baseline stash to drop", "commands": []}
    selector = _git_stash_selector(project_root, stash_hash)
    if not selector:
        return {"status": "pass", "reason": "git baseline stash already absent", "commands": []}
    result = _run_git(["git", "stash", "drop", selector], project_root)
    status = "pass" if int(result.get("exit_code", 1)) == 0 else "fail"
    return {
        "status": status,
        "reason": "dropped git baseline stash" if status == "pass" else result.get("stderr") or result.get("error") or "git stash drop failed",
        "commands": [result],
    }


def _git_capture_worktree_snapshot(project_root: Path, preserve_path: Path) -> dict[str, Any]:
    commands: list[dict[str, Any]] = []
    before = _git_stash_top(project_root)
    argv = [
        "git",
        "stash",
        "push",
        "--include-untracked",
        "--message",
        "agent-workbench opencode-auto run baseline",
    ]
    if not _git_path_is_ignored(project_root, preserve_path):
        argv.extend(_git_pathspec_excluding(project_root, preserve_path))
    push = _run_git(argv, project_root)
    commands.append(push)
    if int(push.get("exit_code", 1)) != 0:
        return {
            "status": "fail",
            "reason": push.get("stderr") or push.get("error") or "git stash baseline failed",
            "commands": commands,
        }
    after = _git_stash_top(project_root)
    stash_hash = after if after and after != before else ""
    if stash_hash:
        apply = _run_git(["git", "stash", "apply", "--index", stash_hash], project_root)
        commands.append(apply)
        if int(apply.get("exit_code", 1)) != 0:
            return {
                "status": "fail",
                "stash": stash_hash,
                "reason": apply.get("stderr") or apply.get("error") or "git baseline restore failed",
                "commands": commands,
            }
    return {
        "status": "pass",
        "stash": stash_hash,
        "reason": "captured git worktree baseline" if stash_hash else "git worktree baseline is clean",
        "commands": commands,
    }


def _git_cleanup_failed_attempt(project_root: Path, preserve_path: Path) -> dict[str, Any]:
    commands = [
        ["git", "reset", "--hard", "HEAD"],
        ["git", "clean", "-fd", *_git_preserve_excludes(project_root, preserve_path), "--", "."],
    ]
    results = []
    for argv in commands:
        item = _run_git(argv, project_root)
        results.append(item)
        if int(item.get("exit_code", 1)) != 0:
            return {"status": "fail", "commands": results, "reason": item.get("stderr") or item.get("error") or "git cleanup failed"}
    return {"status": "pass", "commands": results, "reason": "cleaned failed attempt changes"}


def _git_restore_worktree_snapshot(project_root: Path, preserve_path: Path, snapshot: dict[str, Any] | None) -> dict[str, Any]:
    cleanup = _git_cleanup_failed_attempt(project_root, preserve_path)
    commands = list(cleanup.get("commands") or [])
    if cleanup.get("status") != "pass":
        return cleanup
    stash_hash = str((snapshot or {}).get("stash") or "")
    if stash_hash:
        apply = _run_git(["git", "stash", "apply", "--index", stash_hash], project_root)
        commands.append(apply)
        if int(apply.get("exit_code", 1)) != 0:
            return {
                "status": "fail",
                "commands": commands,
                "reason": apply.get("stderr") or apply.get("error") or "git baseline restore failed",
            }
    return {"status": "pass", "commands": commands, "reason": "restored git worktree baseline"}


def _render_attempt_md(attempt: dict[str, Any]) -> str:
    executor = attempt.get("executor") or {}
    review = attempt.get("review") or {}
    lines = [
        f"# OpenCode Retry Attempt {attempt.get('attempt')}",
        "",
        f"- status: {attempt.get('status')}",
        f"- reason: {attempt.get('reason', '')}",
        f"- executor_exit_code: {executor.get('exit_code')}",
        f"- executor_timeout: {executor.get('timeout')}",
    ]
    if review:
        lines.extend(
            [
                f"- reviewer_exit_code: {review.get('exit_code')}",
                f"- reviewer_timeout: {review.get('timeout')}",
            ]
        )
    lines.extend(
        [
            f"- stdout: {executor.get('stdout_path', '')}",
            f"- stderr: {executor.get('stderr_path', '')}",
        ]
    )
    if review:
        lines.extend(
            [
                f"- review_stdout: {review.get('stdout_path', '')}",
                f"- review_stderr: {review.get('stderr_path', '')}",
            ]
        )
    cleanup = attempt.get("cleanup")
    if cleanup:
        lines.extend(["", "## Cleanup", "", f"- status: {cleanup.get('status')}", f"- reason: {cleanup.get('reason', '')}"])
        for item in cleanup.get("commands", []):
            lines.append(f"- command: {' '.join(item.get('argv', []))} exit={item.get('exit_code')}")
    context = attempt.get("final_context") or ""
    if context:
        lines.extend(["", "## Final Context", "", "```text", context, "```"])
    return "\n".join(lines).rstrip() + "\n"


def _render_retry_summary_md(summary: dict[str, Any]) -> str:
    lines = [
        "# OpenCode Retry Summary",
        "",
        f"- status: {summary.get('status')}",
        f"- reason: {summary.get('reason', '')}",
        f"- attempts: {summary.get('counts', {}).get('attempts', 0)}",
        f"- passed_attempt: {summary.get('counts', {}).get('passed_attempt')}",
        f"- run_dir: {summary.get('artifacts', {}).get('run_dir', '')}",
        "",
        "## Attempts",
        "",
    ]
    for attempt in summary.get("attempts", []):
        lines.append(
            f"- attempt {attempt.get('attempt')}: {attempt.get('status')} - {attempt.get('reason', '')} "
            f"({attempt.get('result_md', '')})"
        )
    return "\n".join(lines).rstrip() + "\n"


def run_opencode_retry(
    cfg: dict[str, Any],
    *,
    task_text: str,
    dry_run: bool = False,
    opencode_cmd_template: str = "",
    review_cmd_template: str = "",
    max_attempts: int = 3,
    timeout_seconds: int = 1800,
    git_cleanup: bool = True,
) -> dict[str, Any]:
    runtime_root = Path(cfg["outputs"]["runtime_root_path"])
    project_root = Path(cfg["project_root_path"])
    base_run_dir = runtime_root / "opencode_retry" / local_now_tag()
    run_dir = base_run_dir
    suffix = 2
    while run_dir.exists():
        run_dir = Path(f"{base_run_dir}_{suffix}")
        suffix += 1
    ensure_dir(run_dir)
    task_file = run_dir / "task.md"
    summary_json = run_dir / "summary.json"
    summary_md = run_dir / "summary.md"
    task_file.write_text(task_text, encoding="utf-8")

    attempts: list[dict[str, Any]] = []
    summary: dict[str, Any] = {
        "status": "running",
        "reason": "",
        "counts": {"attempts": 0, "passed_attempt": None, "failed_attempts": 0},
        "attempts": attempts,
        "artifacts": {"run_dir": str(run_dir), "task_file": str(task_file), "summary_json": str(summary_json), "summary_md": str(summary_md)},
    }

    def save_summary() -> None:
        _write_summary(summary_json, summary)
        summary_md.write_text(_render_retry_summary_md(summary), encoding="utf-8")

    if not dry_run and not opencode_cmd_template.strip():
        summary["status"] = "fail"
        summary["reason"] = "missing opencode command template; pass --opencode-cmd-template or --dry-run"
        save_summary()
        return build_result_payload(
            "opencode-auto retry",
            2,
            summary=summary["reason"],
            details={**summary["counts"], "final_reason": summary["reason"]},
            artifacts=summary["artifacts"],
        )

    baseline_status = None
    if not dry_run and git_cleanup:
        baseline_status = _git_status_porcelain(project_root, ignore_path=run_dir)
        if int(baseline_status.get("exit_code", 1)) != 0:
            summary["status"] = "fail"
            summary["reason"] = _short(baseline_status.get("stderr") or baseline_status.get("error") or "git status failed")
            summary["git_baseline"] = baseline_status
            save_summary()
            return build_result_payload(
                "opencode-auto retry",
                2,
                summary=summary["reason"],
                details={**summary["counts"], "final_reason": summary["reason"]},
                artifacts=summary["artifacts"],
            )
        if baseline_status.get("dirty"):
            summary["status"] = "fail"
            summary["reason"] = "git worktree is dirty; retry cleanup requires a clean baseline"
            summary["git_baseline"] = baseline_status
            save_summary()
            return build_result_payload(
                "opencode-auto retry",
                2,
                summary=summary["reason"],
                details={**summary["counts"], "final_reason": summary["reason"]},
                artifacts=summary["artifacts"],
            )
        summary["git_baseline"] = {"status": "clean", "exit_code": baseline_status.get("exit_code")}
        save_summary()

    max_attempts = max(1, int(max_attempts))
    for attempt_index in range(1, max_attempts + 1):
        attempt_dir = ensure_dir(run_dir / f"attempt_{attempt_index:03d}")
        attempt_task_file = attempt_dir / "task.md"
        attempt_task_file.write_text(task_text, encoding="utf-8")
        values = {
            "task_file": attempt_task_file,
            "attempt_dir": attempt_dir,
            "run_dir": run_dir,
            "attempt": attempt_index,
        }
        if dry_run:
            stdout_path = attempt_dir / "stdout.log"
            stderr_path = attempt_dir / "stderr.log"
            stdout_path.write_text(f"dry-run attempt {attempt_index}\n", encoding="utf-8")
            stderr_path.write_text("", encoding="utf-8")
            exec_result = {"command": "dry-run", "argv": [], "exit_code": 0, "timeout": False, "stdout_path": str(stdout_path), "stderr_path": str(stderr_path)}
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
        passed = int(exec_result.get("exit_code", 1)) == 0 and not exec_result.get("timeout")
        if passed and review_cmd_template.strip():
            review_result = _run_template(
                review_cmd_template,
                values,
                project_root,
                attempt_dir / "review_stdout.log",
                attempt_dir / "review_stderr.log",
                timeout_seconds=timeout_seconds,
            )
            passed = int(review_result.get("exit_code", 1)) == 0 and not review_result.get("timeout")

        final_context_paths = [attempt_dir / "stdout.log", attempt_dir / "stderr.log"]
        if review_result:
            final_context_paths.extend([attempt_dir / "review_stdout.log", attempt_dir / "review_stderr.log"])
        final_context = _tail_context(final_context_paths)
        reason = "passed" if passed else _short(
            str(exec_result.get("error") or "")
            or read_text(attempt_dir / "stderr.log")
            or f"executor exit={exec_result.get('exit_code')}"
        )
        attempt_result = {
            "attempt": attempt_index,
            "status": "pass" if passed else "fail",
            "reason": reason,
            "executor": exec_result,
            "review": review_result,
            "final_context": final_context,
            "attempt_dir": str(attempt_dir),
            "result_json": str(attempt_dir / "result.json"),
            "result_md": str(attempt_dir / "result.md"),
        }
        if not passed and git_cleanup and not dry_run:
            cleanup = _git_cleanup_failed_attempt(project_root, run_dir)
            attempt_result["cleanup"] = cleanup
            if cleanup.get("status") != "pass":
                reason = _short(cleanup.get("reason", "git cleanup failed"))
                attempt_result["reason"] = reason
                write_json(attempt_dir / "result.json", attempt_result)
                (attempt_dir / "result.md").write_text(_render_attempt_md(attempt_result), encoding="utf-8")
                attempts.append({k: attempt_result[k] for k in ["attempt", "status", "reason", "attempt_dir", "result_json", "result_md"]})
                summary["counts"]["attempts"] = attempt_index
                summary["counts"]["failed_attempts"] = attempt_index
                summary["status"] = "fail"
                summary["reason"] = reason
                save_summary()
                return build_result_payload(
                    "opencode-auto retry",
                    1,
                    summary=f"opencode-auto retry attempts={attempt_index} passed=none reason={reason}",
                    details={**summary["counts"], "final_reason": reason},
                    artifacts=summary["artifacts"],
                )

        write_json(attempt_dir / "result.json", attempt_result)
        (attempt_dir / "result.md").write_text(_render_attempt_md(attempt_result), encoding="utf-8")
        attempts.append({k: attempt_result[k] for k in ["attempt", "status", "reason", "attempt_dir", "result_json", "result_md"]})
        summary["counts"]["attempts"] = attempt_index
        summary["counts"]["failed_attempts"] = len([item for item in attempts if item["status"] != "pass"])
        summary["reason"] = reason
        if passed:
            summary["status"] = "pass"
            summary["counts"]["passed_attempt"] = attempt_index
            save_summary()
            return build_result_payload(
                "opencode-auto retry",
                0,
                summary=f"opencode-auto retry attempts={attempt_index} passed={attempt_index}",
                details={**summary["counts"], "final_reason": reason},
                artifacts=summary["artifacts"],
            )
        save_summary()

    summary["status"] = "fail"
    summary["reason"] = summary.get("reason") or "max attempts exceeded"
    save_summary()
    return build_result_payload(
        "opencode-auto retry",
        1,
        summary=f"opencode-auto retry attempts={summary['counts']['attempts']} passed=none reason={summary['reason']}",
        details={**summary["counts"], "final_reason": summary["reason"]},
        artifacts=summary["artifacts"],
    )


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
    git_cleanup: bool = True,
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
            task_snapshot = None
            if git_cleanup and not dry_run:
                task_snapshot = _git_capture_worktree_snapshot(project_root, run_dir)
                compact["git_baseline"] = {
                    "status": task_snapshot.get("status"),
                    "reason": task_snapshot.get("reason"),
                    "has_stash": bool(task_snapshot.get("stash")),
                }
                _write_summary(summary_path, summary)
                if task_snapshot.get("status") != "pass":
                    reason = _short(str(task_snapshot.get("reason") or "git baseline capture failed"))
                    compact["status"] = "failed_git_baseline"
                    compact["reason"] = reason
                    summary["status"] = "fail"
                    summary["reason"] = reason
                    summary["counts"]["skipped"] += 1
                    _write_summary(summary_path, summary)
                    return build_result_payload(
                        "opencode-auto run",
                        2,
                        status="fail",
                        summary=f"opencode-auto git baseline failed: {reason}",
                        details={"total": len(tasks), "passed": summary["counts"]["passed"], "skipped": summary["counts"]["skipped"], "tasks": task_results},
                        artifacts={**summary["artifacts"], "summary_path": str(summary_path)},
                    )
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
                if not attempt_passed and git_cleanup and not dry_run:
                    cleanup = _git_restore_worktree_snapshot(project_root, run_dir, task_snapshot)
                    attempt_summary["cleanup"] = cleanup
                    if cleanup.get("status") != "pass":
                        last_reason = _short(str(cleanup.get("reason") or "git cleanup failed"))
                        attempt_summary["reason"] = last_reason
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
                        compact["status"] = "failed_git_cleanup"
                        compact["reason"] = last_reason
                        summary["status"] = "fail"
                        summary["reason"] = last_reason
                        summary["counts"]["skipped"] += 1
                        _write_summary(summary_path, summary)
                        _git_drop_snapshot(project_root, task_snapshot)
                        return build_result_payload(
                            "opencode-auto run",
                            1,
                            status="fail",
                            summary=f"opencode-auto git cleanup failed: {last_reason}",
                            details={"total": len(tasks), "passed": summary["counts"]["passed"], "skipped": summary["counts"]["skipped"], "tasks": task_results},
                            artifacts={**summary["artifacts"], "summary_path": str(summary_path)},
                        )
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
            drop_result = _git_drop_snapshot(project_root, task_snapshot) if git_cleanup and not dry_run else None
            if drop_result and drop_result.get("status") != "pass":
                compact["git_baseline_drop"] = {
                    "status": drop_result.get("status"),
                    "reason": _short(str(drop_result.get("reason") or "git baseline drop failed")),
                }
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
