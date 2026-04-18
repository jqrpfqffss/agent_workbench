from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .task_spec import load_task_spec
from .utils import ensure_dir, read_text, utc_now_iso, write_json


DEFAULT_BATCH_SIZE = 2
FINAL_SUBTASK_STATUSES = {"done", "skipped"}
ACTIVE_SUBTASK_STATUSES = {"pending", "in_progress", "blocked"}
VALID_SUBTASK_STATUSES = ACTIVE_SUBTASK_STATUSES | FINAL_SUBTASK_STATUSES
STAGE_ORDER = ("analyze", "implement", "verify")


def _clip(text: str, max_len: int = 120) -> str:
    normalized = " ".join(str(text).split())
    if len(normalized) <= max_len:
        return normalized
    return normalized[: max_len - 3] + "..."


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(read_text(path))
    except Exception:
        return None


def _task_generated_root(cfg: dict, task: dict[str, Any]) -> Path:
    return ensure_dir(Path(cfg["outputs"]["generated_root_path"]) / "tasks" / str(task["id"]).strip())


def task_generated_paths(cfg: dict, task: dict[str, Any]) -> dict[str, Path]:
    root = _task_generated_root(cfg, task)
    return {
        "generated_dir": root,
        "task_breakdown": root / "task_breakdown.md",
        "task_breakdown_json": root / "task_breakdown.json",
        "task_progress": root / "task_progress.json",
        "task_board": root / "task_board.md",
    }


def _normalized_candidates(items: list[Any]) -> list[str]:
    result: list[str] = []
    for item in items:
        text = str(item).strip()
        if text:
            result.append(text)
    return result


def _default_feature_subtasks(task: dict[str, Any]) -> list[dict[str, Any]]:
    impl = task.get("implementation", {})
    verify = task.get("verify", {})
    read_candidates = _normalized_candidates(impl.get("read_candidates", []))
    edit_candidates = _normalized_candidates(impl.get("edit_candidates", []))
    verify_sequence = _normalized_candidates(verify.get("sequence", []))
    cli_commands = _normalized_candidates(verify.get("cli_commands", []))
    return [
        {
            "id": "S1",
            "stage": "analyze",
            "title": "Restate the requested outcome and the non-goals.",
            "objective": "Translate the natural-language request into one concrete deliverable and explicit boundaries for this repo.",
            "inputs": ["task yaml", "implementation_brief.md", "latest session evidence if present"],
            "done_when": "The success condition and the things we must not change are both explicit.",
        },
        {
            "id": "S2",
            "stage": "analyze",
            "title": "Inspect only the smallest relevant evidence and files.",
            "objective": "Find the smallest code and evidence surface that can explain the task without reading the whole repo.",
            "inputs": read_candidates[:4] or ["implementation.read_candidates"],
            "done_when": "The first working area is reduced to a short file list.",
        },
        {
            "id": "S3",
            "stage": "analyze",
            "title": "Lock the execution plan for this task board.",
            "objective": "Confirm the order of work for this task so Continue can finish one small subtask batch at a time and resume safely later.",
            "inputs": ["task_breakdown.md", "task_progress.json", "task yaml"],
            "done_when": "The next few subtasks are still the smallest safe route and no wider scope is needed.",
        },
        {
            "id": "S4",
            "stage": "implement",
            "title": "Implement the smallest code slice in allowed files.",
            "objective": "Make the narrowest code change that moves the task forward without touching unrelated modules.",
            "inputs": edit_candidates[:4] or ["implementation.edit_candidates"],
            "done_when": "One reviewable code slice is landed inside the allowed edit scope.",
        },
        {
            "id": "S5",
            "stage": "implement",
            "title": "Keep tests and stable strings aligned.",
            "objective": "Update the smallest necessary automated checks or task assets so the new behavior stays verifiable.",
            "inputs": verify_sequence[:4] or ["doctor", "build", "test"],
            "done_when": "The change is testable locally and protected strings or CLI contracts are still stable.",
        },
        {
            "id": "S6",
            "stage": "implement",
            "title": "Run local quality gates before hardware validation.",
            "objective": "Catch build and local regression issues before the slower end-to-end verification path.",
            "inputs": verify_sequence[:4] or ["doctor", "build", "test"],
            "done_when": "The local gates required for this task are green or the first blocker is clearly identified.",
        },
        {
            "id": "S7",
            "stage": "verify",
            "title": "Run the task-specific validation flow.",
            "objective": "Generate fresh evidence for the user-visible behavior using the task verify sequence or CLI commands.",
            "inputs": cli_commands[:6] or ["verify.cli_commands"],
            "done_when": "Fresh transcript, diagnostics, assertions, or session summary artifacts exist for this task.",
        },
        {
            "id": "S8",
            "stage": "verify",
            "title": "Close the loop with evidence only.",
            "objective": "Decide pass, fail, blocked, or needs_review strictly from the latest evidence chain.",
            "inputs": ["session_verdict.json", "session_brief.md", "session_summary.md", "feature_summary.md"],
            "done_when": "The final result and the next step are both backed by evidence files.",
        },
    ]


def _default_debug_subtasks(task: dict[str, Any]) -> list[dict[str, Any]]:
    verify = task.get("verify", {})
    cli_commands = _normalized_candidates(verify.get("cli_commands", []))
    edit_candidates = _normalized_candidates(task.get("implementation", {}).get("edit_candidates", []))
    return [
        {
            "id": "S1",
            "stage": "analyze",
            "title": "Read the newest debug evidence first.",
            "objective": "Identify the first failing layer before deciding whether we need code, config, or environment changes.",
            "inputs": ["session_verdict.json", "session_brief.md", "cli_diag.json", "cli_transcript.log"],
            "done_when": "The earliest failing layer is explicit.",
        },
        {
            "id": "S2",
            "stage": "analyze",
            "title": "Narrow the smallest suspicion scope.",
            "objective": "Reduce the problem to one minimal environment, protocol, parser, or code area hypothesis.",
            "inputs": ["task yaml", "latest evidence"],
            "done_when": "One best hypothesis and one smallest next action are identified.",
        },
        {
            "id": "S3",
            "stage": "analyze",
            "title": "Lock the replay path for resume.",
            "objective": "Keep the repro and evidence path stable so the next round can resume without rediscovering context.",
            "inputs": ["task_breakdown.md", "task_progress.json"],
            "done_when": "The next debug replay path is fixed and repeatable.",
        },
        {
            "id": "S4",
            "stage": "implement",
            "title": "Fix only the smallest relevant point.",
            "objective": "Touch only the file or configuration point directly related to the first failing layer.",
            "inputs": edit_candidates[:4] or ["implementation.edit_candidates"],
            "done_when": "The fix stays tightly scoped to the identified cause.",
        },
        {
            "id": "S5",
            "stage": "verify",
            "title": "Replay the debug path.",
            "objective": "Rerun the failing flow and capture fresh evidence to confirm whether the issue changed.",
            "inputs": cli_commands[:6] or ["help", "status"],
            "done_when": "Fresh replay evidence exists for the failing path.",
        },
        {
            "id": "S6",
            "stage": "verify",
            "title": "Write the debug conclusion.",
            "objective": "Explain whether the issue is fixed, still blocked, or needs one more narrow experiment.",
            "inputs": ["session_verdict.json", "session_summary.md", "compare_brief.md"],
            "done_when": "The result and smallest next step are clear from evidence.",
        },
    ]


def _default_test_subtasks(task: dict[str, Any]) -> list[dict[str, Any]]:
    verify = task.get("verify", {})
    verify_sequence = _normalized_candidates(verify.get("sequence", []))
    return [
        {
            "id": "S1",
            "stage": "analyze",
            "title": "Read the task and generated test assets.",
            "objective": "Confirm the goal, assertions, and unit plan before blaming source code.",
            "inputs": ["task yaml", "blackbox_assertions.yaml", "unit_test_plan.md", "implementation_brief.md"],
            "done_when": "It is clear whether the next fix belongs in the task spec, test asset, or source code.",
        },
        {
            "id": "S2",
            "stage": "analyze",
            "title": "Lock the smallest trustworthy test scope.",
            "objective": "Keep only the assertions and fixtures needed for this round so the test authoring flow stays stable.",
            "inputs": ["task_breakdown.md", "task_progress.json", "blackbox_assertions.yaml"],
            "done_when": "The next test batch is small enough to trust and resume later.",
        },
        {
            "id": "S3",
            "stage": "implement",
            "title": "Refine the task or generated test assets first.",
            "objective": "Prefer fixing unstable assertions or task definitions before changing business logic.",
            "inputs": ["task yaml", "generated test assets"],
            "done_when": "The task spec and generated tests are aligned with the intended behavior.",
        },
        {
            "id": "S4",
            "stage": "implement",
            "title": "Generate or update the smallest missing coverage.",
            "objective": "Add only the missing unit or black-box coverage needed for the current task.",
            "inputs": verify_sequence[:4] or ["test generate", "test run"],
            "done_when": "The missing coverage for this round is present and reviewable.",
        },
        {
            "id": "S5",
            "stage": "verify",
            "title": "Rerun the tests and stop at the first failed layer.",
            "objective": "Capture the first failing layer instead of mixing every failing symptom together.",
            "inputs": ["unit.log", "blackbox_assertions.yaml"],
            "done_when": "Fresh test evidence identifies the first failed layer or confirms pass.",
        },
        {
            "id": "S6",
            "stage": "verify",
            "title": "Report the test result with evidence.",
            "objective": "Summarize pass, fail, or blocked strictly from the latest generated logs and assertions.",
            "inputs": ["unit.log", "session_summary.md", "assertions.jsonl"],
            "done_when": "The current test result and next step are backed by evidence.",
        },
    ]


def _normalize_manual_subtasks(items: list[Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        if isinstance(item, dict):
            step_id = str(item.get("id", f"S{index}")).strip() or f"S{index}"
            result.append(
                {
                    "id": step_id,
                    "stage": str(item.get("stage", "implement")).strip() or "implement",
                    "title": _clip(str(item.get("title", f"Subtask {index}"))),
                    "objective": _clip(str(item.get("objective", ""))),
                    "inputs": _normalized_candidates(item.get("inputs", [])),
                    "done_when": _clip(str(item.get("done_when", ""))),
                    "recommended_commands": _normalized_candidates(item.get("recommended_commands", [])),
                    "depends_on": _normalized_candidates(item.get("depends_on", [])),
                }
            )
        else:
            text = str(item).strip()
            if text:
                result.append(
                    {
                        "id": f"S{index}",
                        "stage": "implement",
                        "title": _clip(text),
                        "objective": "",
                        "inputs": [],
                        "done_when": "",
                        "recommended_commands": [],
                        "depends_on": [],
                    }
                )
    return result


def derive_task_breakdown(cfg: dict, task: dict[str, Any], task_path: Path | None = None) -> dict[str, Any]:
    decomposition = task.get("decomposition", {}) if isinstance(task.get("decomposition", {}), dict) else {}
    manual_subtasks = _normalize_manual_subtasks(decomposition.get("subtasks", []))
    if manual_subtasks:
        subtasks = manual_subtasks
        decomposition_kind = "manual"
    else:
        mode = str(task.get("mode", "feature")).strip().lower()
        if mode == "debug":
            subtasks = _default_debug_subtasks(task)
        elif mode == "test":
            subtasks = _default_test_subtasks(task)
        else:
            subtasks = _default_feature_subtasks(task)
        decomposition_kind = "default"

    stages: dict[str, list[str]] = {"analyze": [], "implement": [], "verify": [], "resume": []}
    for item in subtasks:
        stage = str(item.get("stage", "implement")).strip().lower()
        if stage not in stages:
            stage = "implement"
            item["stage"] = stage
        item.setdefault("recommended_commands", [])
        item.setdefault("depends_on", [])
        stages[stage].append(str(item["id"]))

    batch_size = max(int(decomposition.get("batch_size", DEFAULT_BATCH_SIZE) or DEFAULT_BATCH_SIZE), 1)
    return {
        "generated_at": utc_now_iso(),
        "task_id": str(task.get("id", "")).strip(),
        "task_path": str(task_path) if task_path else "",
        "mode": str(task.get("mode", "")).strip(),
        "goal": str(task.get("goal", "")).strip(),
        "summary": "Split the task into smaller stage-aligned subtasks so a local model can finish one focused step at a time.",
        "decomposition_kind": decomposition_kind,
        "batch_size": batch_size,
        "subtasks": subtasks,
        "stage_map": stages,
    }


def _subtask_progress_item(item: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    existing = existing or {}
    status = str(existing.get("status", "pending")).strip().lower()
    if status not in VALID_SUBTASK_STATUSES:
        status = "pending"
    return {
        "id": str(item.get("id", "")).strip(),
        "stage": str(item.get("stage", "implement")).strip().lower() or "implement",
        "title": str(item.get("title", "")).strip(),
        "status": status,
        "note": str(existing.get("note", "")).strip(),
        "evidence": [str(path).strip() for path in existing.get("evidence", []) if str(path).strip()],
        "updated_at": str(existing.get("updated_at", "")).strip(),
        "completed_at": str(existing.get("completed_at", "")).strip(),
    }


def _unresolved_stage_rows(progress_rows: list[dict[str, Any]], stage: str) -> list[dict[str, Any]]:
    return [
        item
        for item in progress_rows
        if str(item.get("stage", "")).strip().lower() == stage and str(item.get("status", "")).strip().lower() not in FINAL_SUBTASK_STATUSES
    ]


def _next_stage_from_rows(progress_rows: list[dict[str, Any]], stage_sequence: list[str], current_stage: str, batch_size: int) -> str:
    if current_stage:
        current_rows = _unresolved_stage_rows(progress_rows, current_stage)
        if len(current_rows) > batch_size:
            return current_stage
    if current_stage in stage_sequence:
        start_index = stage_sequence.index(current_stage) + 1
    else:
        start_index = 0
    for stage in stage_sequence[start_index:]:
        if _unresolved_stage_rows(progress_rows, stage):
            return stage
    return "complete"


def _progress_summary(progress_rows: list[dict[str, Any]], stage_sequence: list[str], batch_size: int) -> dict[str, Any]:
    counts = {status: 0 for status in VALID_SUBTASK_STATUSES}
    for item in progress_rows:
        status = str(item.get("status", "pending")).strip().lower()
        if status not in counts:
            status = "pending"
        counts[status] += 1

    current_stage = ""
    current_subtasks: list[str] = []
    for stage in stage_sequence:
        unresolved = _unresolved_stage_rows(progress_rows, stage)
        if unresolved:
            current_stage = stage
            current_subtasks = [str(item.get("id", "")).strip() for item in unresolved[:batch_size] if str(item.get("id", "")).strip()]
            break

    workflow_status = "complete" if not current_stage else "active"
    next_stage = "complete"
    if current_stage:
        next_stage = _next_stage_from_rows(progress_rows, stage_sequence, current_stage, batch_size)
        focus_rows = [item for item in progress_rows if str(item.get("id", "")).strip() in current_subtasks]
        if focus_rows and all(str(item.get("status", "")).strip().lower() == "blocked" for item in focus_rows):
            workflow_status = "blocked"

    return {
        "counts": counts,
        "current_stage": current_stage,
        "current_subtasks": current_subtasks,
        "completed_subtasks": [
            str(item.get("id", "")).strip()
            for item in progress_rows
            if str(item.get("status", "")).strip().lower() in FINAL_SUBTASK_STATUSES and str(item.get("id", "")).strip()
        ],
        "next_stage": next_stage,
        "workflow_status": workflow_status,
        "remaining_count": sum(
            1 for item in progress_rows if str(item.get("status", "")).strip().lower() not in FINAL_SUBTASK_STATUSES
        ),
        "total_count": len(progress_rows),
    }


def _task_board_text(task: dict[str, Any], breakdown: dict[str, Any], progress: dict[str, Any]) -> str:
    summary = progress.get("summary", {})
    counts = summary.get("counts", {})
    lines = [
        "# Task Board",
        "",
        f"- task_id: `{breakdown.get('task_id', '')}`",
        f"- goal: {breakdown.get('goal', '')}",
        f"- workflow_status: `{summary.get('workflow_status', 'active')}`",
        f"- current_stage: `{summary.get('current_stage', '') or 'complete'}`",
        f"- current_subtasks: {', '.join(summary.get('current_subtasks', [])) or 'none'}",
        f"- progress: done={counts.get('done', 0)} skipped={counts.get('skipped', 0)} pending={counts.get('pending', 0)} in_progress={counts.get('in_progress', 0)} blocked={counts.get('blocked', 0)}",
        "",
    ]
    for stage in STAGE_ORDER:
        lines.append(f"## {stage.title()}")
        stage_rows = [item for item in progress.get("subtasks", []) if str(item.get("stage", "")).strip().lower() == stage]
        if not stage_rows:
            lines.append("- none")
            lines.append("")
            continue
        for item in stage_rows:
            lines.append(
                f"- [{str(item.get('status', 'pending')).strip().lower()}] {item.get('id', '')}: {item.get('title', '')}"
            )
            note = str(item.get("note", "")).strip()
            if note:
                lines.append(f"  note: {_clip(note, 140)}")
        lines.append("")
    if str(task.get("metadata", {}).get("generated_by", "")).strip() == "agent_workbench.autoflow":
        lines.append("## Resume")
        lines.append("- After you truly finish the current_subtasks, run `agent_workbench.bat autoflow --done <IDs>`.")
        lines.append("- Then run `agent_workbench.bat autoflow --resume` to load the next pending batch.")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def load_task_progress(cfg: dict, task: dict[str, Any] | None) -> dict[str, Any] | None:
    if task is None:
        return None
    path = task_generated_paths(cfg, task)["task_progress"]
    return _read_json(path)


def sync_task_progress(
    cfg: dict,
    task: dict[str, Any],
    breakdown: dict[str, Any],
    task_path: Path | None = None,
) -> dict[str, Any]:
    paths = task_generated_paths(cfg, task)
    existing = _read_json(paths["task_progress"]) or {}
    existing_rows = {
        str(item.get("id", "")).strip(): item
        for item in existing.get("subtasks", [])
        if str(item.get("id", "")).strip()
    }
    stage_sequence = [stage for stage in STAGE_ORDER if breakdown.get("stage_map", {}).get(stage)]
    if not stage_sequence:
        stage_sequence = list(STAGE_ORDER)
    batch_size = max(int(breakdown.get("batch_size", DEFAULT_BATCH_SIZE) or DEFAULT_BATCH_SIZE), 1)
    progress_rows = [_subtask_progress_item(item, existing_rows.get(str(item.get("id", "")).strip())) for item in breakdown.get("subtasks", [])]
    summary = _progress_summary(progress_rows, stage_sequence, batch_size)
    payload = {
        "generated_at": utc_now_iso(),
        "task_id": str(task.get("id", "")).strip(),
        "task_path": str(task_path) if task_path else str(existing.get("task_path", "")).strip(),
        "mode": str(task.get("mode", "")).strip(),
        "goal": str(task.get("goal", "")).strip(),
        "stage_sequence": stage_sequence,
        "batch_size": batch_size,
        "subtasks": progress_rows,
        "summary": summary,
    }
    write_json(paths["task_progress"], payload)
    paths["task_board"].write_text(_task_board_text(task, breakdown, payload), encoding="utf-8")
    return payload


def pick_focus_subtasks(
    breakdown: dict[str, Any] | None,
    progress: dict[str, Any] | None,
    stage: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    if not breakdown:
        return [], []
    batch_size = max(int((progress or {}).get("batch_size", breakdown.get("batch_size", DEFAULT_BATCH_SIZE)) or DEFAULT_BATCH_SIZE), 1)
    unresolved_ids: set[str] = set()
    progress_map: dict[str, dict[str, Any]] = {}
    for item in (progress or {}).get("subtasks", []):
        item_id = str(item.get("id", "")).strip()
        if not item_id:
            continue
        progress_map[item_id] = item
        if str(item.get("status", "")).strip().lower() not in FINAL_SUBTASK_STATUSES:
            unresolved_ids.add(item_id)

    stage_rows = [
        item
        for item in breakdown.get("subtasks", [])
        if str(item.get("stage", "")).strip().lower() == stage
    ]
    if progress_map:
        stage_rows = [item for item in stage_rows if str(item.get("id", "")).strip() in unresolved_ids]
    focus = stage_rows[:batch_size]
    if not focus and stage_rows:
        focus = stage_rows[:batch_size]

    payload: list[dict[str, Any]] = []
    ids: list[str] = []
    for item in focus:
        item_id = str(item.get("id", "")).strip()
        if not item_id:
            continue
        row = dict(item)
        row["status"] = str(progress_map.get(item_id, {}).get("status", "pending")).strip().lower() or "pending"
        row["note"] = str(progress_map.get(item_id, {}).get("note", "")).strip()
        payload.append(row)
        ids.append(item_id)
    return payload, ids


def mark_task_subtasks(
    cfg: dict,
    task: dict[str, Any],
    *,
    task_path: Path | None = None,
    status: str,
    subtask_ids: list[str],
    note: str = "",
    evidence_paths: list[str] | None = None,
) -> dict[str, Any]:
    normalized_status = str(status).strip().lower()
    if normalized_status not in VALID_SUBTASK_STATUSES:
        raise RuntimeError(f"unsupported subtask status: {status}")

    breakdown = derive_task_breakdown(cfg, task, task_path)
    progress = sync_task_progress(cfg, task, breakdown, task_path)
    wanted = {str(item).strip() for item in subtask_ids if str(item).strip()}
    if not wanted:
        raise RuntimeError("at least one subtask id is required")

    found = False
    appended_evidence = [str(path).strip() for path in (evidence_paths or []) if str(path).strip()]
    for item in progress.get("subtasks", []):
        item_id = str(item.get("id", "")).strip()
        if item_id not in wanted:
            continue
        found = True
        item["status"] = normalized_status
        item["updated_at"] = utc_now_iso()
        if note:
            item["note"] = note.strip()
        if appended_evidence:
            merged = list(item.get("evidence", []))
            for path in appended_evidence:
                if path not in merged:
                    merged.append(path)
            item["evidence"] = merged
        if normalized_status in FINAL_SUBTASK_STATUSES:
            item["completed_at"] = utc_now_iso()
        else:
            item["completed_at"] = ""

    if not found:
        raise RuntimeError(f"subtasks not found in progress state: {', '.join(sorted(wanted))}")

    stage_sequence = [str(item).strip() for item in progress.get("stage_sequence", []) if str(item).strip()] or list(STAGE_ORDER)
    batch_size = max(int(progress.get("batch_size", DEFAULT_BATCH_SIZE) or DEFAULT_BATCH_SIZE), 1)
    progress["generated_at"] = utc_now_iso()
    progress["summary"] = _progress_summary(progress.get("subtasks", []), stage_sequence, batch_size)
    paths = task_generated_paths(cfg, task)
    write_json(paths["task_progress"], progress)
    paths["task_board"].write_text(_task_board_text(task, breakdown, progress), encoding="utf-8")
    return progress


def write_task_breakdown(cfg: dict, task_path: Path) -> Path:
    task = load_task_spec(task_path)
    payload = derive_task_breakdown(cfg, task, task_path)
    progress = sync_task_progress(cfg, task, payload, task_path)
    progress_map = {
        str(item.get("id", "")).strip(): item
        for item in progress.get("subtasks", [])
        if str(item.get("id", "")).strip()
    }
    payload["progress_path"] = str(task_generated_paths(cfg, task)["task_progress"])
    payload["task_board_path"] = str(task_generated_paths(cfg, task)["task_board"])
    payload["progress_summary"] = progress.get("summary", {})
    payload["subtasks"] = [
        {
            **item,
            "status": str(progress_map.get(str(item.get("id", "")).strip(), {}).get("status", "pending")).strip().lower() or "pending",
            "note": str(progress_map.get(str(item.get("id", "")).strip(), {}).get("note", "")).strip(),
        }
        for item in payload.get("subtasks", [])
    ]

    paths = task_generated_paths(cfg, task)
    write_json(paths["task_breakdown_json"], payload)
    with paths["task_breakdown"].open("w", encoding="utf-8") as fp:
        fp.write("# Task Breakdown\n\n")
        fp.write(f"- task_id: `{payload['task_id']}`\n")
        fp.write(f"- mode: `{payload['mode']}`\n")
        fp.write(f"- goal: {payload['goal']}\n")
        fp.write(f"- task_path: `{payload['task_path']}`\n")
        fp.write(f"- decomposition_kind: `{payload['decomposition_kind']}`\n")
        fp.write(f"- batch_size: `{payload['batch_size']}`\n")
        fp.write(f"- progress_path: `{payload['progress_path']}`\n")
        fp.write(f"- task_board_path: `{payload['task_board_path']}`\n\n")
        fp.write("## Progress Summary\n")
        summary = payload.get("progress_summary", {})
        counts = summary.get("counts", {})
        fp.write(f"- workflow_status: `{summary.get('workflow_status', 'active')}`\n")
        fp.write(f"- current_stage: `{summary.get('current_stage', '') or 'complete'}`\n")
        fp.write(f"- current_subtasks: {', '.join(summary.get('current_subtasks', [])) or 'none'}\n")
        fp.write(
            "- counts: "
            f"done={counts.get('done', 0)} skipped={counts.get('skipped', 0)} "
            f"pending={counts.get('pending', 0)} in_progress={counts.get('in_progress', 0)} blocked={counts.get('blocked', 0)}\n\n"
        )
        fp.write("## Stage Map\n")
        for stage in STAGE_ORDER:
            ids = payload["stage_map"].get(stage, [])
            fp.write(f"- {stage}: {', '.join(ids) or 'none'}\n")
        fp.write("\n## Subtasks\n")
        for item in payload["subtasks"]:
            fp.write(f"### {item['id']} [{item['stage']}] [{item.get('status', 'pending')}]\n")
            fp.write(f"- title: {item['title']}\n")
            if item.get("objective"):
                fp.write(f"- objective: {item['objective']}\n")
            if item.get("inputs"):
                fp.write(f"- inputs: {', '.join(item['inputs'])}\n")
            if item.get("depends_on"):
                fp.write(f"- depends_on: {', '.join(item['depends_on'])}\n")
            if item.get("recommended_commands"):
                fp.write(f"- recommended_commands: {', '.join(item['recommended_commands'])}\n")
            if item.get("done_when"):
                fp.write(f"- done_when: {item['done_when']}\n")
            if item.get("note"):
                fp.write(f"- note: {item['note']}\n")
            fp.write("\n")
    return paths["task_breakdown"]
