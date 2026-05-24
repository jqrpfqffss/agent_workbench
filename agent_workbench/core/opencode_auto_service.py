from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .cli_output import build_result_payload
from .utils import ensure_dir, local_now_tag, read_text, write_json


@dataclass
class ProcessResult:
    exit_code: int
    stdout: str
    stderr: str
    elapsed_sec: float
    timed_out: bool = False


def _unique_run_dir(root: Path) -> Path:
    ensure_dir(root)
    tag = local_now_tag()
    candidate = root / tag
    suffix = 2
    while candidate.exists():
        candidate = root / f"{tag}_{suffix}"
        suffix += 1
    ensure_dir(candidate)
    return candidate


def _safe_task_id(index: int, value: Any) -> str:
    text = str(value or "").strip()
    cleaned = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in text)
    cleaned = cleaned.strip("_")
    return cleaned or f"task_{index:03d}"


def _extract_json_object(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    if not stripped:
        return None
    try:
        obj = json.loads(stripped)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for start, char in enumerate(text):
        if char != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    return None


def _strings_from_json(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(_strings_from_json(item))
        return result
    if isinstance(value, dict):
        result: list[str] = []
        for key in ("content", "text", "message", "delta", "summary"):
            if key in value:
                result.extend(_strings_from_json(value[key]))
        for nested in value.values():
            if isinstance(nested, (dict, list)):
                result.extend(_strings_from_json(nested))
        return result
    return []


def _extract_plan_from_stdout(stdout: str) -> dict[str, Any] | None:
    direct = _extract_json_object(stdout)
    if direct and "tasks" in direct:
        return direct

    collected: list[str] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        collected.extend(_strings_from_json(event))
    if collected:
        return _extract_json_object("\n".join(collected))
    return None


def _normalize_plan(plan: Any, fallback_task: str) -> list[dict[str, Any]]:
    raw_tasks: Any
    if isinstance(plan, dict):
        raw_tasks = plan.get("tasks", [])
    elif isinstance(plan, list):
        raw_tasks = plan
    else:
        raw_tasks = []

    tasks: list[dict[str, Any]] = []
    for index, item in enumerate(raw_tasks, start=1):
        if isinstance(item, str):
            item = {"title": item, "prompt": item}
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or item.get("name") or f"Task {index}").strip()
        prompt = str(item.get("prompt") or item.get("task") or title).strip()
        if not prompt or prompt in {".", "...", "TODO", "todo"}:
            continue
        task_id = _safe_task_id(index, item.get("id") or f"task_{index:03d}")
        acceptance = item.get("acceptance", [])
        if isinstance(acceptance, str):
            acceptance = [acceptance]
        if not isinstance(acceptance, list):
            acceptance = []
        if title in {".", "...", "TODO", "todo"}:
            title = f"Task {index}"
        tasks.append({"id": task_id, "title": title, "prompt": prompt, "acceptance": acceptance})

    if not tasks and fallback_task.strip():
        tasks.append(
            {
                "id": "task_001",
                "title": "Task 1",
                "prompt": fallback_task.strip(),
                "acceptance": [],
            }
        )
    return tasks


def _file_terms(text: str) -> list[str]:
    pattern = r"[\w.-]+\.(?:c|h|cpp|hpp|txt|md|json|ya?ml|py|bat|ps1|sh|cmake|csv|log)"
    return sorted({match.group(0).lower() for match in re.finditer(pattern, text, flags=re.IGNORECASE)})


def _plan_mentions_file_terms(tasks: list[dict[str, Any]], original_task: str) -> bool:
    terms = _file_terms(original_task)
    if not terms:
        return True
    plan_text = "\n".join(
        f"{task.get('title', '')}\n{task.get('prompt', '')}\n{' '.join(map(str, task.get('acceptance', [])))}"
        for task in tasks
    ).lower()
    return all(term in plan_text for term in terms)


def _run_process(argv: list[str], cwd: Path, timeout_sec: int) -> ProcessResult:
    start = time.monotonic()
    resolved_argv = list(argv)
    if resolved_argv:
        resolved_argv[0] = shutil.which(resolved_argv[0]) or resolved_argv[0]
    try:
        proc = subprocess.run(
            resolved_argv,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=max(1, int(timeout_sec)),
            check=False,
        )
        return ProcessResult(
            exit_code=int(proc.returncode),
            stdout=proc.stdout,
            stderr=proc.stderr,
            elapsed_sec=round(time.monotonic() - start, 3),
        )
    except subprocess.TimeoutExpired as exc:
        return ProcessResult(
            exit_code=124,
            stdout=exc.stdout or "",
            stderr=(exc.stderr or "") + f"\nprocess timed out after {timeout_sec}s",
            elapsed_sec=round(time.monotonic() - start, 3),
            timed_out=True,
        )
    except OSError as exc:
        return ProcessResult(
            exit_code=127,
            stdout="",
            stderr=str(exc),
            elapsed_sec=round(time.monotonic() - start, 3),
        )


class OpencodeAutoService:
    def __init__(self, cfg: dict[str, Any]):
        self.cfg = cfg
        self.project_root = Path(cfg["project_root_path"])
        self.options = cfg.get("opencode_auto", {})
        self.git_options = self.options.get("git", {})

    def run(
        self,
        task: str,
        *,
        plan_file: str = "",
        max_retries: int | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        run_dir = _unique_run_dir(Path(self.options["runtime_dir_path"]))
        task_path = run_dir / "task.md"
        task_path.write_text(task, encoding="utf-8")

        if not str(task).strip():
            return self._finish(
                run_dir,
                build_result_payload(
                    "opencode-auto run",
                    2,
                    summary="opencode-auto requires --task",
                    artifacts={"run_dir": str(run_dir), "task": str(task_path)},
                ),
                [],
            )

        if not self.options.get("enabled", True):
            return self._finish(
                run_dir,
                build_result_payload(
                    "opencode-auto run",
                    3,
                    status="blocked",
                    summary="opencode-auto is disabled in config",
                    artifacts={"run_dir": str(run_dir), "task": str(task_path)},
                ),
                [],
            )

        if dry_run:
            tasks = _normalize_plan({"tasks": [{"id": "task_001", "title": "dry run", "prompt": task}]}, task)
            plan_path = write_json(run_dir / "plan.json", {"tasks": tasks, "dry_run": True})
            return self._finish(
                run_dir,
                build_result_payload(
                    "opencode-auto run",
                    0,
                    summary=f"opencode-auto dry-run tasks={len(tasks)}",
                    details={"dry_run": True, "task_count": len(tasks), "passed_count": 0, "failed_count": 0},
                    artifacts={"run_dir": str(run_dir), "task": str(task_path), "plan": str(plan_path)},
                ),
                [],
            )

        clean_error = self._check_clean(preserve_dir=run_dir)
        if clean_error:
            return self._finish(
                run_dir,
                build_result_payload(
                    "opencode-auto run",
                    3,
                    status="blocked",
                    summary=clean_error["summary"],
                    details={"git": self._git_details(), "dirty": clean_error["dirty"]},
                    artifacts={"run_dir": str(run_dir), "task": str(task_path)},
                ),
                [],
            )

        plan_result = self._load_or_create_plan(task, plan_file, run_dir)
        if plan_result["exit_code"] != 0:
            return self._finish(run_dir, plan_result, [])

        tasks = plan_result["tasks"]
        plan_path = plan_result["plan_path"]
        retries = int(max_retries if max_retries is not None else self.options.get("max_retries", 1))
        summary_tasks: list[dict[str, Any]] = []
        passed_count = 0
        failed_count = 0
        retry_count = 0
        stopped_task: dict[str, Any] | None = None

        for task_item in tasks:
            item_result = self._run_task(task_item, run_dir, retries)
            summary_tasks.append(item_result)
            retry_count += max(0, int(item_result["attempts"]) - 1)
            if item_result["status"] == "pass":
                add_result = self._git_add()
                item_result["git_add"] = add_result
                if add_result["exit_code"] != 0:
                    failed_count += 1
                    stopped_task = task_item
                    item_result["status"] = "fail"
                    item_result["error"] = "git add failed"
                    break
                passed_count += 1
                continue

            failed_count += 1
            stopped_task = task_item
            break

        exit_code = 0 if failed_count == 0 and passed_count == len(tasks) else 1
        artifacts = {
            "run_dir": str(run_dir),
            "task": str(task_path),
            "plan": str(plan_path),
            "summary_json": str(run_dir / "summary.json"),
            "summary_md": str(run_dir / "summary.md"),
        }
        details = {
            "task_count": len(tasks),
            "passed_count": passed_count,
            "failed_count": failed_count,
            "retry_count": retry_count,
            "stopped_task": stopped_task,
            "git": self._git_details(),
            "tasks": summary_tasks,
        }
        payload = build_result_payload(
            "opencode-auto run",
            exit_code,
            summary=f"opencode-auto tasks={len(tasks)} passed={passed_count} failed={failed_count} retries={retry_count}",
            details=details,
            artifacts=artifacts,
        )
        return self._finish(run_dir, payload, summary_tasks)

    def _load_or_create_plan(self, task: str, plan_file: str, run_dir: Path) -> dict[str, Any]:
        planner_stdout = run_dir / "planner_stdout.log"
        planner_stderr = run_dir / "planner_stderr.log"
        if plan_file:
            path = Path(plan_file)
            if not path.is_absolute():
                path = (self.project_root / path).resolve()
            text = read_text(path)
            plan = _extract_json_object(text)
            tasks = _normalize_plan(plan, task)
            plan_path = write_json(run_dir / "plan.json", {"tasks": tasks, "source": str(path)})
            if tasks:
                return {"exit_code": 0, "tasks": tasks, "plan_path": plan_path}
            return build_result_payload(
                "opencode-auto run",
                2,
                summary=f"plan file contains no tasks: {path}",
                artifacts={"run_dir": str(run_dir), "plan_file": str(path), "plan": str(plan_path)},
            )

        prompt = self._planner_prompt(task)
        argv = [str(self.options.get("command", "opencode")), *map(str, self.options.get("planner_args", [])), prompt]
        result = _run_process(argv, self.project_root, int(self.options.get("planner_timeout_sec", 600)))
        planner_stdout.write_text(result.stdout, encoding="utf-8")
        planner_stderr.write_text(result.stderr, encoding="utf-8")
        plan = _extract_plan_from_stdout(result.stdout)
        tasks = _normalize_plan(plan, task)
        if not _plan_mentions_file_terms(tasks, task):
            tasks = _normalize_plan(None, task)
        plan_path = write_json(run_dir / "plan.json", {"tasks": tasks, "raw_plan": plan})
        if result.exit_code == 0 and tasks:
            return {"exit_code": 0, "tasks": tasks, "plan_path": plan_path}
        return build_result_payload(
            "opencode-auto run",
            2,
            summary=f"planner failed or returned no tasks exit={result.exit_code}",
            details={"planner_exit_code": result.exit_code, "task_count": len(tasks), "timed_out": result.timed_out},
            artifacts={
                "run_dir": str(run_dir),
                "plan": str(plan_path),
                "planner_stdout": str(planner_stdout),
                "planner_stderr": str(planner_stderr),
            },
        )

    def _planner_prompt(self, task: str) -> str:
        return (
            "你是任务规划器。请把下面的大任务拆成可串行执行的小任务。"
            "只输出严格 JSON，不要 Markdown，不要解释。格式为："
            '{"tasks":[{"id":"task_001","title":"...","prompt":"...","acceptance":["..."]}]}'
            "\n\n大任务：\n"
            f"{task}"
        )

    def _run_task(self, task_item: dict[str, Any], run_dir: Path, retries: int) -> dict[str, Any]:
        task_dir = ensure_dir(run_dir / "tasks" / str(task_item["id"]))
        (task_dir / "task.md").write_text(self._task_prompt(task_item), encoding="utf-8")
        attempts: list[dict[str, Any]] = []
        max_attempts = max(1, retries + 1)

        for attempt_index in range(1, max_attempts + 1):
            attempt_dir = ensure_dir(task_dir / f"attempt_{attempt_index:03d}")
            argv = [
                str(self.options.get("command", "opencode")),
                *map(str, self.options.get("args", [])),
                self._task_prompt(task_item),
            ]
            result = _run_process(argv, self.project_root, int(self.options.get("timeout_sec", 1800)))
            stdout_path = attempt_dir / "stdout.log"
            stderr_path = attempt_dir / "stderr.log"
            stdout_path.write_text(result.stdout, encoding="utf-8")
            stderr_path.write_text(result.stderr, encoding="utf-8")
            attempt_payload = {
                "attempt": attempt_index,
                "exit_code": result.exit_code,
                "elapsed_sec": result.elapsed_sec,
                "timed_out": result.timed_out,
                "stdout": str(stdout_path),
                "stderr": str(stderr_path),
                "parsed_json": _extract_json_object(result.stdout),
            }
            write_json(attempt_dir / "result.json", attempt_payload)
            attempts.append(attempt_payload)
            if result.exit_code == 0:
                return {
                    "id": task_item["id"],
                    "title": task_item["title"],
                    "status": "pass",
                    "attempts": attempt_index,
                    "artifacts": {"task_dir": str(task_dir), "last_attempt": str(attempt_dir)},
                    "attempt_results": attempts,
                }
            rollback = self._git_rollback(preserve_dir=run_dir)
            attempt_payload["rollback"] = rollback
            if attempt_index >= max_attempts:
                return {
                    "id": task_item["id"],
                    "title": task_item["title"],
                    "status": "fail",
                    "attempts": attempt_index,
                    "artifacts": {"task_dir": str(task_dir), "last_attempt": str(attempt_dir)},
                    "attempt_results": attempts,
                }

        raise AssertionError("unreachable")

    def _task_prompt(self, task_item: dict[str, Any]) -> str:
        acceptance = "\n".join(f"- {item}" for item in task_item.get("acceptance", []))
        return (
            f"{task_item.get('prompt', '')}\n\n"
            f"子任务标题：{task_item.get('title', '')}\n\n"
            "要求：完成后自行运行相关验证；如果无法完成，请以非零退出。"
            + (f"\n\n验收点：\n{acceptance}" if acceptance else "")
        )

    def _git_details(self) -> dict[str, Any]:
        return {
            "enabled": bool(self.git_options.get("enabled", True)),
            "worktree": str(self.git_options.get("worktree_path", "")),
            "paths": list(self.git_options.get("paths", ["."])),
            "require_clean": bool(self.git_options.get("require_clean", True)),
        }

    def _git(self, args: list[str]) -> ProcessResult:
        return _run_process(["git", *args], Path(self.git_options["worktree_path"]), 300)

    def _check_clean(self, *, preserve_dir: Path | None = None) -> dict[str, Any] | None:
        if not self.git_options.get("enabled", True) or not self.git_options.get("require_clean", True):
            return None
        paths = list(self.git_options.get("paths", ["."]))
        result = self._git(["status", "--porcelain", "--untracked-files=all", "--", *paths])
        if result.exit_code != 0:
            return {"summary": f"git status failed exit={result.exit_code}", "dirty": result.stderr or result.stdout}
        lines = result.stdout.splitlines()
        lines = self._filter_preserved_status_lines(lines, preserve_dir)
        runtime_root_str = str(self.options.get("runtime_dir_path", "")).strip()
        if runtime_root_str:
            lines = self._filter_preserved_status_lines(lines, Path(runtime_root_str))
        dirty_lines = self._unstaged_or_untracked_status_lines(lines)
        dirty = "\n".join(dirty_lines).strip()
        if dirty:
            return {"summary": "configured git paths are dirty before opencode-auto run", "dirty": dirty}
        return None

    def _git_add(self) -> dict[str, Any]:
        if not self.git_options.get("enabled", True):
            return {"exit_code": 0, "skipped": True}
        paths = self._existing_or_tracked_paths()
        if not paths:
            return {"exit_code": 0, "skipped": True, "reason": "no existing or tracked configured paths"}
        result = self._git(["add", "-A", "--", *paths])
        return {"exit_code": result.exit_code, "stdout": result.stdout, "stderr": result.stderr, "paths": paths}

    def _git_rollback(self, *, preserve_dir: Path | None = None) -> dict[str, Any]:
        if not self.git_options.get("enabled", True):
            return {"exit_code": 0, "skipped": True}
        paths = list(self.git_options.get("paths", ["."]))
        tracked = self._git(["ls-files", "--", *paths])
        tracked_paths = [line.strip() for line in tracked.stdout.splitlines() if line.strip()]
        if tracked.exit_code == 0 and tracked_paths:
            restore = self._git(["restore", "--worktree", "--", *tracked_paths])
        elif tracked.exit_code == 0:
            restore = ProcessResult(0, "", "", 0)
        else:
            restore = tracked
        clean_args = ["clean", "-fd"]
        excluded = self._clean_exclude_args(preserve_dir)
        clean_args.extend(excluded)
        clean_args.extend(["--", *paths])
        clean = self._git(clean_args)
        return {
            "exit_code": 0 if restore.exit_code == 0 and clean.exit_code == 0 else 1,
            "tracked_paths": tracked_paths if tracked.exit_code == 0 else [],
            "clean_excludes": excluded,
            "restore": {"exit_code": restore.exit_code, "stdout": restore.stdout, "stderr": restore.stderr},
            "clean": {"exit_code": clean.exit_code, "stdout": clean.stdout, "stderr": clean.stderr},
        }

    def _clean_exclude_args(self, preserve_dir: Path | None) -> list[str]:
        if preserve_dir is None:
            return []
        worktree = Path(self.git_options["worktree_path"]).resolve()
        try:
            relative = preserve_dir.resolve().relative_to(worktree).as_posix()
        except ValueError:
            return []
        return ["-e", relative, "-e", f"{relative}/**"]

    def _filter_preserved_status_lines(self, lines: list[str], preserve_dir: Path | None) -> list[str]:
        if preserve_dir is None:
            return lines
        worktree = Path(self.git_options["worktree_path"]).resolve()
        try:
            relative = preserve_dir.resolve().relative_to(worktree).as_posix().rstrip("/")
        except ValueError:
            return lines
        prefix = f"{relative}/"
        filtered: list[str] = []
        for line in lines:
            path = line[3:].replace("\\", "/") if len(line) > 3 else ""
            if path == relative or path.startswith(prefix):
                continue
            filtered.append(line)
        return filtered

    def _unstaged_or_untracked_status_lines(self, lines: list[str]) -> list[str]:
        dirty: list[str] = []
        for line in lines:
            if line.startswith("??"):
                dirty.append(line)
                continue
            if len(line) >= 2 and line[1] != " ":
                dirty.append(line)
        return dirty

    def _existing_or_tracked_paths(self) -> list[str]:
        paths = list(self.git_options.get("paths", ["."]))
        worktree = Path(self.git_options["worktree_path"])
        selected: list[str] = []
        for path in paths:
            if (worktree / path).exists():
                selected.append(path)
        tracked = self._git(["ls-files", "--", *paths])
        if tracked.exit_code == 0:
            for line in tracked.stdout.splitlines():
                text = line.strip()
                if text and text not in selected:
                    selected.append(text)
        return selected

    def _finish(self, run_dir: Path, payload: dict[str, Any], tasks: list[dict[str, Any]]) -> dict[str, Any]:
        payload.setdefault("artifacts", {})
        payload["artifacts"].setdefault("run_dir", str(run_dir))
        payload["artifacts"].setdefault("summary_json", str(run_dir / "summary.json"))
        payload["artifacts"].setdefault("summary_md", str(run_dir / "summary.md"))
        write_json(run_dir / "summary.json", payload)
        lines = [
            f"# opencode-auto summary",
            "",
            f"- status: {payload.get('status')}",
            f"- exit_code: {payload.get('exit_code')}",
            f"- summary: {payload.get('summary')}",
            f"- tasks: {len(tasks)}",
        ]
        (run_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return payload
