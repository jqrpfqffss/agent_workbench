from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .compare_service import list_session_dirs
from .task_breakdown import (
    derive_task_breakdown,
    load_task_progress,
    pick_focus_subtasks,
    task_generated_paths,
    write_task_breakdown,
)
from .task_spec import load_task_spec
from .utils import ensure_dir, read_text, utc_now_iso, write_json


DEFAULT_STAGE = "analyze"
DEFAULT_PROFILE = "balanced_local"
STAGES = {"analyze", "implement", "verify", "resume"}


def _ps_safe_workbench(command_text: str) -> str:
    escaped = str(command_text).replace('"', '""')
    return f'cmd /c ".\\{escaped}"'


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(read_text(path))
    except Exception:
        return None


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not path.exists():
        return items
    for line in read_text(path).splitlines():
        text = line.strip()
        if not text:
            continue
        try:
            items.append(json.loads(text))
        except Exception:
            continue
    return items


def _clip(text: str, max_len: int = 140) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_len:
        return normalized
    return normalized[: max_len - 3] + "..."


def _word_count(text: str) -> int:
    return sum(1 for item in text.split() if item.strip())


def _slug(text: str) -> str:
    cleaned = []
    for char in text.strip().lower():
        if char.isalnum():
            cleaned.append(char)
        else:
            cleaned.append("_")
    slug = "".join(cleaned).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "item"


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []
    for path in paths:
        key = str(path.resolve()) if path.exists() else str(path)
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result


def _profile_cfg(cfg: dict, profile_name: str | None) -> tuple[str, dict[str, Any]]:
    agent_cfg = cfg.get("agent", {})
    profiles = agent_cfg.get("profiles", {})
    chosen_name = (profile_name or agent_cfg.get("default_profile") or DEFAULT_PROFILE).strip() or DEFAULT_PROFILE
    return chosen_name, dict(profiles.get(chosen_name, profiles.get(DEFAULT_PROFILE, {})))


def _task_id(task: dict[str, Any] | None) -> str:
    return str((task or {}).get("id", "")).strip()


def _session_event(session_dir: Path, event_name: str) -> dict[str, Any] | None:
    events = _read_jsonl(session_dir / "events.jsonl")
    for row in reversed(events):
        if row.get("event") == event_name:
            return row
    return None


def _session_assertions(session_dir: Path) -> tuple[int, int, int, list[dict[str, Any]]]:
    rows = _read_jsonl(session_dir / "assertions.jsonl")
    passed = sum(1 for row in rows if row.get("status") == "pass")
    failed_rows = [row for row in rows if row.get("status") == "fail"]
    skipped = sum(1 for row in rows if row.get("status") == "skip")
    return passed, len(failed_rows), skipped, failed_rows


def _cli_tail_lines(session_dir: Path, limit: int) -> list[str]:
    lines = read_text(session_dir / "cli_transcript.log").splitlines()
    return [_clip(line, 180) for line in lines[-limit:]]


def _session_verdict(session_dir: Path) -> dict[str, Any]:
    verdict_path = session_dir / "session_verdict.json"
    verdict = _read_json(verdict_path)
    if verdict:
        return verdict

    passed, failed, skipped, failed_rows = _session_assertions(session_dir)
    cli_diag = _read_json(session_dir / "cli_diag.json") or {}
    classification = cli_diag.get("classification", {}) if isinstance(cli_diag, dict) else {}
    cli_probe = _session_event(session_dir, "cli_probe_done") or {}
    probe_code = int(cli_probe.get("code", 0)) if str(cli_probe.get("code", "")).strip() else 0

    status = "needs_review"
    summary = "No automated verdict available yet."
    strongest = "Evidence set is incomplete."
    next_step = "Rebuild session artifacts with `agent_workbench.bat report --latest`."

    if failed > 0:
        first = failed_rows[0]
        status = "fail"
        summary = f"{failed} black-box assertions failed."
        strongest = f"{first.get('name', 'assertion')} | {_clip(str(first.get('detail', '')))}"
        next_step = "Inspect the first failed assertion and then run the verify stage again."
    elif classification.get("code"):
        code = str(classification.get("code", ""))
        if code not in {"ok", "n/a"}:
            status = "fail"
            summary = str(classification.get("summary", "CLI validation failed."))
            strongest = _clip(str(classification.get("detail", summary)))
            next_step = "Use the diagnostic code to choose the smallest fix before rerunning verify."
    elif probe_code != 0:
        status = "fail"
        summary = "CLI probe command failed."
        strongest = f"cli_probe_done code={probe_code}"
        next_step = "Replay the CLI probe path before changing code."
    elif passed > 0 or cli_probe:
        status = "pass"
        summary = "Latest session passed its available automated checks."
        strongest = f"assertions pass={passed} fail={failed} skip={skipped}"
        next_step = "Reuse this session as the current baseline or continue with the next task."

    return {
        "generated_at": utc_now_iso(),
        "session": str(session_dir),
        "status": status,
        "summary": summary,
        "strongest_evidence": strongest,
        "classification_code": classification.get("code", ""),
        "next_step": next_step,
        "assertions": {"passed": passed, "failed": failed, "skipped": skipped},
    }


def _matching_sessions(sessions_root: Path, mode: str, task_id: str) -> list[Path]:
    candidates: list[Path] = []
    for session_dir in list_session_dirs(sessions_root):
        manifest = _read_json(session_dir / "session_manifest.json") or {}
        manifest_mode = str(manifest.get("mode", "")).strip().lower()
        manifest_task = str((manifest.get("task") or {}).get("id", "")).strip()
        if mode and manifest_mode and manifest_mode != mode:
            continue
        if task_id and manifest_task and manifest_task != task_id:
            continue
        if task_id and not manifest_task:
            continue
        candidates.append(session_dir)
    return candidates


def _pick_session(sessions_root: Path, mode: str, task_id: str, strategy: str) -> Path | None:
    sessions = _matching_sessions(sessions_root, mode, task_id)
    if not sessions:
        if task_id:
            return None
        sessions = list_session_dirs(sessions_root)
    if not sessions:
        return None
    if strategy != "latest_failed_then_latest_pass":
        return sessions[-1]

    ordered = list(reversed(sessions))
    for wanted in ("fail", "pass", "needs_review"):
        for session_dir in ordered:
            if _session_verdict(session_dir).get("status") == wanted:
                return session_dir
    return sessions[-1]


def _session_artifacts(session_dir: Path | None) -> dict[str, Path]:
    if session_dir is None:
        return {}
    return {
        "session_summary": session_dir / "session_summary.md",
        "session_brief": session_dir / "session_brief.md",
        "session_verdict": session_dir / "session_verdict.json",
        "feature_summary": session_dir / "feature_summary.md",
        "cli_transcript": session_dir / "cli_transcript.log",
        "cli_diag": session_dir / "cli_diag.json",
        "assertions": session_dir / "assertions.jsonl",
        "compare_brief": session_dir / "compare_brief.md",
    }


def _task_generated_files(cfg: dict, task: dict[str, Any] | None) -> dict[str, Path]:
    if task is None:
        return {}
    generated = dict(task_generated_paths(cfg, task))
    generated_root = generated["generated_dir"]
    generated.update(
        {
            "implementation_brief": generated_root / "implementation_brief.md",
            "task_snapshot": generated_root / "task_snapshot.json",
            "unit_plan": generated_root / "unit_test_plan.md",
        }
    )
    return generated


def _allowed_reads(
    cfg: dict,
    stage: str,
    profile_name: str,
    task: dict[str, Any] | None,
    task_path: Path | None,
    session_dir: Path | None,
) -> list[Path]:
    _, profile = _profile_cfg(cfg, profile_name)
    max_reads = int(profile.get("max_extra_reads", 2))
    session_files = _session_artifacts(session_dir)
    generated = _task_generated_files(cfg, task)
    impl = (task or {}).get("implementation", {})
    candidates: list[Path] = []
    if stage == "analyze":
        for key in ("session_brief", "session_summary", "cli_diag", "assertions", "cli_transcript"):
            path = session_files.get(key)
            if path is not None:
                candidates.append(path)
        if task_path is not None:
            candidates.append(task_path)
        impl_brief = generated.get("implementation_brief")
        if impl_brief is not None:
            candidates.append(impl_brief)
        for key in ("task_breakdown", "task_board", "task_progress"):
            path = generated.get(key)
            if path is not None:
                candidates.append(path)
    elif stage == "implement":
        if task_path is not None:
            candidates.append(task_path)
        impl_brief = generated.get("implementation_brief")
        if impl_brief is not None:
            candidates.append(impl_brief)
        for key in ("task_breakdown", "task_board", "task_progress"):
            path = generated.get(key)
            if path is not None:
                candidates.append(path)
        for item in impl.get("read_candidates", [])[:max_reads]:
            candidates.append(Path(cfg["project_root_path"]) / str(item))
    elif stage == "verify":
        if task_path is not None:
            candidates.append(task_path)
        for key in ("task_breakdown", "task_board", "task_progress"):
            path = generated.get(key)
            if path is not None:
                candidates.append(path)
        for key in ("session_verdict", "session_brief", "compare_brief"):
            path = session_files.get(key)
            if path is not None:
                candidates.append(path)
    else:
        state_path = Path(cfg["agent"]["state_path"])
        candidates.append(state_path)
        for key in ("session_brief", "session_verdict"):
            path = session_files.get(key)
            if path is not None:
                candidates.append(path)
        if task_path is not None:
            candidates.append(task_path)
        for key in ("task_board", "task_progress"):
            path = generated.get(key)
            if path is not None:
                candidates.append(path)
    return _dedupe_paths(candidates)


def _allowed_edits(cfg: dict, stage: str, profile_name: str, task: dict[str, Any] | None) -> list[Path]:
    if stage != "implement" or task is None:
        return []
    _, profile = _profile_cfg(cfg, profile_name)
    impl = task.get("implementation", {})
    max_edit_files = int(impl.get("max_edit_files", profile.get("max_edit_files", 2)))
    return _dedupe_paths(
        [Path(cfg["project_root_path"]) / str(item) for item in impl.get("edit_candidates", [])[:max_edit_files]]
    )


def _focus_subtasks(
    breakdown: dict[str, Any] | None,
    progress: dict[str, Any] | None,
    stage: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    return pick_focus_subtasks(breakdown, progress, stage)


def _unknowns(task: dict[str, Any] | None, session_dir: Path | None, session_verdict: dict[str, Any]) -> list[str]:
    items: list[str] = []
    if task is None:
        items.append("No task yaml is attached to this stage.")
    if session_dir is None:
        items.append("No matching evidence session is available.")
    if session_dir is not None and not (session_dir / "cli_diag.json").exists():
        items.append("No CLI diagnostic file exists for the selected session.")
    if session_verdict.get("status") == "needs_review":
        items.append("The current verdict is incomplete and may require one more validation pass.")
    return items or ["No blocking unknowns are currently recorded."]


def _forbidden_assumptions(stage: str) -> list[str]:
    common = [
        "Do not conclude from source inspection alone.",
        "Do not read the whole repo when the brief already names the next files.",
        "Do not invent evidence that is not present in facts or session artifacts.",
    ]
    if stage == "analyze":
        return common + ["Do not edit code in this round."]
    if stage == "implement":
        return common + ["Do not edit files outside allowed_edits.", "Do not expand scope beyond the task goal."]
    if stage == "verify":
        return common + ["Do not change code in this round.", "Do not claim pass until new evidence is generated."]
    return common + ["Do not restart the workflow from README; resume from the saved state."]


def _task_stage_sequence(task: dict[str, Any] | None) -> list[str]:
    if task is None:
        return ["analyze", "implement", "verify"]
    payload = derive_task_breakdown({}, task)
    stage_map = payload.get("stage_map", {})
    sequence = [item for item in ("analyze", "implement", "verify") if stage_map.get(item)]
    return sequence or ["analyze", "implement", "verify"]


def _task_is_autoflow(task: dict[str, Any] | None) -> bool:
    if task is None:
        return False
    metadata = task.get("metadata", {}) if isinstance(task.get("metadata", {}), dict) else {}
    return str(metadata.get("generated_by", "")).strip() == "agent_workbench.autoflow" or str(task.get("id", "")).startswith("autoflow_")


def _autoflow_mark_command(task_text: str, focus_ids: list[str], status: str = "done") -> str:
    subtask_arg = ",".join(item for item in focus_ids if item)
    task_arg = f" --task {task_text}" if task_text else ""
    return _ps_safe_workbench(f"agent_workbench.bat autoflow --{status} {subtask_arg}{task_arg}")


def _verification_commands(mode: str, task: dict[str, Any] | None, task_text: str) -> list[str]:
    if mode == "debug" and task is None:
        return [
            _ps_safe_workbench("agent_workbench.bat doctor"),
            _ps_safe_workbench("agent_workbench.bat build"),
            _ps_safe_workbench("agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status"),
            _ps_safe_workbench("agent_workbench.bat session debug"),
            _ps_safe_workbench("agent_workbench.bat compare --latest"),
        ]

    task_verify = (task or {}).get("verify", {}) if isinstance((task or {}).get("verify", {}), dict) else {}
    sequence = [str(item).strip().lower() for item in task_verify.get("sequence", []) if str(item).strip()]
    cli_commands = [str(item).strip() for item in task_verify.get("cli_commands", []) if str(item).strip()]
    built: list[str] = []

    def add(command_text: str) -> None:
        wrapped = _ps_safe_workbench(command_text)
        if wrapped not in built:
            built.append(wrapped)

    if not sequence:
        sequence = ["doctor", "build", "test", "debug"] if mode == "feature" else ["doctor", "build", "debug"]

    for item in sequence:
        if item == "doctor":
            add("agent_workbench.bat doctor")
            continue
        if item == "build":
            add("agent_workbench.bat build")
            continue
        if item == "test" and task_text:
            add(f"agent_workbench.bat test generate --task {task_text}")
            add("agent_workbench.bat test run")
            continue
        if item in {"debug", "uart_smoke", "uart_exec", "cli"}:
            cli_part = " ".join(f'--command "{command}"' for command in (cli_commands or ["help", "status"]))
            add(f"agent_workbench.bat uart exec --reset-first --expect-ready {cli_part}".strip())
            continue
        if item in {"session_debug", "debug_session"}:
            add("agent_workbench.bat session debug")
            continue
        if item in {"feature", "session_feature", "feature_session"} and task_text:
            add(f"agent_workbench.bat session feature --task {task_text}")
            continue
        if item in {"compare", "compare_latest"}:
            add("agent_workbench.bat compare --latest")
            continue
        if item in {"report", "report_latest"}:
            add("agent_workbench.bat report --latest")
            continue

    if built:
        return built
    if mode == "debug":
        return [
            _ps_safe_workbench("agent_workbench.bat doctor"),
            _ps_safe_workbench("agent_workbench.bat build"),
            _ps_safe_workbench("agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status"),
        ]
    if mode == "feature" and task_text:
        return [
            _ps_safe_workbench("agent_workbench.bat doctor"),
            _ps_safe_workbench("agent_workbench.bat build"),
            _ps_safe_workbench(f"agent_workbench.bat test generate --task {task_text}"),
            _ps_safe_workbench("agent_workbench.bat test run"),
            _ps_safe_workbench(f"agent_workbench.bat session feature --task {task_text}"),
            _ps_safe_workbench("agent_workbench.bat compare --latest"),
        ]
    if mode == "test" and task_text:
        return [
            _ps_safe_workbench("agent_workbench.bat doctor"),
            _ps_safe_workbench("agent_workbench.bat build"),
            _ps_safe_workbench(f"agent_workbench.bat test generate --task {task_text}"),
            _ps_safe_workbench("agent_workbench.bat test run"),
        ]
    return [_ps_safe_workbench("agent_workbench.bat report --latest")]


def _next_commands(
    mode: str,
    stage: str,
    profile_name: str,
    task_path: Path | None,
    task: dict[str, Any] | None,
    focus_ids: list[str] | None = None,
) -> list[str]:
    task_text = str(task_path).replace("\\", "/") if task_path else ""
    task_arg = f" --task {task_text}" if task_text else ""
    profile_arg = f" --profile {profile_name}"
    stage_sequence = _task_stage_sequence(task)
    current_index = stage_sequence.index(stage) if stage in stage_sequence else 0
    next_stage = stage_sequence[min(current_index + 1, len(stage_sequence) - 1)] if stage_sequence else "verify"
    should_resume = _task_is_autoflow(task)
    finish_commands: list[str] = []
    if should_resume and focus_ids:
        finish_commands = [
            _autoflow_mark_command(task_text, focus_ids, status="done"),
            _ps_safe_workbench("agent_workbench.bat autoflow --resume"),
        ]
    if stage == "analyze":
        if finish_commands:
            return finish_commands
        commands = [_ps_safe_workbench(f"agent_workbench.bat context --mode {mode} --stage {next_stage}{task_arg}{profile_arg}")]
        if should_resume:
            commands.append(_ps_safe_workbench("agent_workbench.bat autoflow --resume"))
        return commands
    if stage == "implement":
        commands = [_ps_safe_workbench("agent_workbench.bat build")]
        if mode == "test" and task_text:
            commands.append(_ps_safe_workbench(f"agent_workbench.bat test generate --task {task_text}"))
            commands.append(_ps_safe_workbench("agent_workbench.bat test run"))
        elif mode == "feature" and task_text:
            commands.append(_ps_safe_workbench("agent_workbench.bat test run"))
        if finish_commands:
            commands.extend(finish_commands)
        else:
            commands.append(_ps_safe_workbench(f"agent_workbench.bat context --mode {mode} --stage {next_stage}{task_arg}{profile_arg}"))
            if should_resume:
                commands.append(_ps_safe_workbench("agent_workbench.bat autoflow --resume"))
        return commands
    if stage == "verify":
        commands = _verification_commands(mode, task, task_text)
        if finish_commands:
            commands.extend(finish_commands)
        return commands
    return [_ps_safe_workbench(f"agent_workbench.bat context --mode {mode} --stage analyze{task_arg}{profile_arg}")]


def _fact_items(
    cfg: dict,
    mode: str,
    stage: str,
    profile_name: str,
    task: dict[str, Any] | None,
    task_path: Path | None,
    session_dir: Path | None,
    verdict: dict[str, Any],
    progress: dict[str, Any] | None = None,
    focus_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    _, profile = _profile_cfg(cfg, profile_name)
    max_items = int(profile.get("max_fact_items", 12))
    uart = cfg.get("uart", {})
    facts: list[dict[str, Any]] = [
        {
            "fact_id": "F01",
            "name": "project",
            "value": cfg.get("project", {}).get("name", ""),
            "source": "config",
            "evidence": cfg["config_path"],
        },
        {
            "fact_id": "F02",
            "name": "mode_stage_profile",
            "value": f"{mode}/{stage}/{profile_name}",
            "source": "context",
            "evidence": "runtime state",
        },
        {
            "fact_id": "F03",
            "name": "uart_contract",
            "value": f"{uart.get('port', 'n/a')} @ {uart.get('baudrate', 'n/a')} ready={uart.get('ready_banner', '')} prompt={uart.get('prompt', '')}",
            "source": "config",
            "evidence": cfg["config_path"],
        },
    ]
    if task is not None:
        facts.extend(
            [
                {
                    "fact_id": "F04",
                    "name": "task_id",
                    "value": _task_id(task),
                    "source": "task",
                    "evidence": str(task_path) if task_path else "task yaml",
                },
                {
                    "fact_id": "F05",
                    "name": "task_goal",
                    "value": str(task.get("goal", "")),
                    "source": "task",
                    "evidence": str(task_path) if task_path else "task yaml",
                },
                {
                    "fact_id": "F06",
                    "name": "task_verify_commands",
                    "value": ", ".join(task.get("verify", {}).get("cli_commands", [])[:6]) or "none",
                    "source": "task",
                    "evidence": str(task_path) if task_path else "task yaml",
                },
                {
                    "fact_id": "F06B",
                    "name": "task_max_edit_files",
                    "value": str(task.get("implementation", {}).get("max_edit_files", "")),
                    "source": "task",
                    "evidence": str(task_path) if task_path else "task yaml",
                },
            ]
        )
        progress_summary = (progress or {}).get("summary", {})
        if progress_summary:
            counts = progress_summary.get("counts", {})
            facts.append(
                {
                    "fact_id": "F06C",
                    "name": "task_progress",
                    "value": (
                        f"workflow={progress_summary.get('workflow_status', 'active')} "
                        f"done={counts.get('done', 0)} "
                        f"pending={counts.get('pending', 0)} "
                        f"in_progress={counts.get('in_progress', 0)} "
                        f"blocked={counts.get('blocked', 0)}"
                    ),
                    "source": "task_progress",
                    "evidence": str(task_generated_paths(cfg, task)["task_progress"]),
                }
            )
    if session_dir is not None:
        facts.extend(
            [
                {
                    "fact_id": "F07",
                    "name": "latest_session",
                    "value": session_dir.name,
                    "source": "session",
                    "evidence": str(session_dir / "session_manifest.json"),
                },
                {
                    "fact_id": "F08",
                    "name": "verdict_status",
                    "value": str(verdict.get("status", "needs_review")),
                    "source": "session",
                    "evidence": str(session_dir / "session_verdict.json"),
                },
                {
                    "fact_id": "F09",
                    "name": "verdict_summary",
                    "value": str(verdict.get("summary", "")),
                    "source": "session",
                    "evidence": str(session_dir / "session_verdict.json"),
                },
                {
                    "fact_id": "F10",
                    "name": "strongest_evidence",
                    "value": str(verdict.get("strongest_evidence", "")),
                    "source": "session",
                    "evidence": str(session_dir / "session_verdict.json"),
                },
            ]
        )
        cli_diag = _read_json(session_dir / "cli_diag.json") or {}
        classification = cli_diag.get("classification", {}) if isinstance(cli_diag, dict) else {}
        if classification:
            facts.append(
                {
                    "fact_id": "F11",
                    "name": "cli_diag_code",
                    "value": str(classification.get("code", "")),
                    "source": "cli_diag",
                    "evidence": str(session_dir / "cli_diag.json"),
                }
            )
        passed, failed, skipped, _ = _session_assertions(session_dir)
        facts.append(
            {
                "fact_id": "F12",
                "name": "assertion_counts",
                "value": f"pass={passed} fail={failed} skip={skipped}",
                "source": "assertions",
                "evidence": str(session_dir / "assertions.jsonl"),
            }
        )
    if focus_ids:
        facts.append(
            {
                "fact_id": "F13",
                "name": "current_subtasks",
                "value": ", ".join(focus_ids),
                "source": "task_breakdown",
                "evidence": "generated task breakdown",
            }
        )
    return facts[:max_items]


def _brief_text(
    cfg: dict,
    mode: str,
    stage: str,
    profile_name: str,
    facts: list[dict[str, Any]],
    focus_subtasks: list[dict[str, Any]],
    allowed_reads: list[Path],
    allowed_edits: list[Path],
    unknowns: list[str],
    forbidden: list[str],
    next_commands: list[str],
    session_dir: Path | None,
) -> str:
    _, profile = _profile_cfg(cfg, profile_name)
    cli_limit = int(profile.get("max_cli_tail_lines", 6))
    lines = [
        "# Local Model Brief",
        "",
        f"- mode: `{mode}`",
        f"- stage: `{stage}`",
        f"- profile: `{profile_name}`",
    ]
    for fact in facts:
        lines.append(f"- {fact['fact_id']}: {fact['name']} = {_clip(str(fact['value']), 110)}")
    lines.append("")
    if focus_subtasks:
        lines.append("## Current Subtasks")
        for item in focus_subtasks:
            title = _clip(str(item.get("title", "")), 100)
            objective = _clip(str(item.get("objective", "")), 110)
            status = str(item.get("status", "pending")).strip().lower() or "pending"
            lines.append(f"- {item.get('id', '')} [{status}]: {title}")
            if objective:
                lines.append(f"- objective: {objective}")
            if item.get("note"):
                lines.append(f"- note: {_clip(str(item.get('note', '')), 110)}")
        lines.append("")
    lines.append("## Allowed Reads")
    if allowed_reads:
        for path in allowed_reads:
            lines.append(f"- `{path}`")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Allowed Edits")
    if allowed_edits:
        for path in allowed_edits:
            lines.append(f"- `{path}`")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Unknowns")
    for item in unknowns[:3]:
        lines.append(f"- {_clip(item, 120)}")
    lines.append("")
    lines.append("## Forbidden Assumptions")
    for item in forbidden[:3]:
        lines.append(f"- {_clip(item, 120)}")
    if session_dir is not None:
        cli_tail = _cli_tail_lines(session_dir, cli_limit)
        if cli_tail:
            lines.append("")
            lines.append("## CLI Tail")
            for item in cli_tail:
                lines.append(f"- {item}")
    lines.append("")
    lines.append("## Next Commands")
    for command in next_commands[:6]:
        lines.append(f"- `{command}`")
    text = "\n".join(lines).strip() + "\n"
    max_words = int(profile.get("max_pack_words", 550))
    if _word_count(text) <= max_words:
        return text
    clipped_lines: list[str] = []
    for line in lines:
        candidate = "\n".join(clipped_lines + [line]).strip() + "\n"
        if _word_count(candidate) > max_words:
            break
        clipped_lines.append(line)
    return "\n".join(clipped_lines).strip() + "\n"


def _paste_text(
    brief_path: Path,
    facts_path: Path,
    constraints_path: Path,
    breakdown_path: Path | None,
    task_board_path: Path | None,
    stage: str,
    focus_ids: list[str],
    next_commands: list[str],
) -> str:
    action = {
        "analyze": "analyze evidence only",
        "implement": "implement the smallest safe change only",
        "verify": "run validation only",
        "resume": "resume from saved state only",
    }.get(stage, "do one stage only")
    lines = [
        "# Paste To Continue",
        "",
        "```text",
        "Read only these files first:",
        f"- {brief_path.as_posix()}",
        f"- {facts_path.as_posix()}",
        f"- {constraints_path.as_posix()}",
    ]
    if breakdown_path is not None:
        lines.append(f"- {breakdown_path.as_posix()}")
    if task_board_path is not None:
        lines.append(f"- {task_board_path.as_posix()}")
    lines.extend(
        [
            "",
        f"This round must: {action}.",
        f"Complete only these subtasks in this round: {', '.join(focus_ids) or 'none'}.",
        "Do not read large files unless they are explicitly listed in allowed_reads.",
        "Do not make claims without citing fact_id or session evidence.",
        "Use agent_workbench.bat for all automation actions.",
        "Run the listed commands in order. If `autoflow --done ...` appears, execute it only after the evidence-producing commands for this round are finished.",
        "",
        "Then run or prepare only these next commands:",
        ]
    )
    for command in next_commands[:4]:
        lines.append(f"- {command}")
    lines.extend(["```", ""])
    return "\n".join(lines)


def _resume_text(state: dict[str, Any]) -> str:
    generated = state.get("generated_files", {})
    lines = [
        "# Resume Card",
        "",
        f"- mode: `{state.get('mode', '')}`",
        f"- stage: `{state.get('stage', '')}`",
        f"- profile: `{state.get('profile', '')}`",
        f"- task_id: `{state.get('task_id', '')}`",
        f"- latest_session: `{state.get('latest_session', '')}`",
        f"- latest_verdict: `{state.get('latest_verdict', '')}`",
        "",
        "## Continue From",
    ]
    for key in ("brief", "facts", "constraints", "task_breakdown", "task_board", "task_progress", "paste"):
        value = generated.get(key, "")
        if value:
            lines.append(f"- {key}: `{value}`")
    lines.append("")
    lines.append("## Next Commands")
    for command in state.get("next_commands", [])[:6]:
        lines.append(f"- `{command}`")
    lines.append("")
    return "\n".join(lines)


def write_context_pack(
    cfg: dict,
    *,
    mode: str,
    stage: str = DEFAULT_STAGE,
    profile_name: str | None = None,
    task_path: Path | None = None,
    session_dir: Path | None = None,
    out_path: Path | None = None,
) -> Path:
    runtime_root = Path(cfg["outputs"]["runtime_root_path"])
    ensure_dir(runtime_root)

    state_path = Path(cfg["agent"]["state_path"])
    previous_state = _read_json(state_path) or {}
    chosen_stage = stage if stage in STAGES else DEFAULT_STAGE
    chosen_mode = mode
    if chosen_stage == "resume" and previous_state:
        chosen_mode = str(previous_state.get("mode", chosen_mode)).strip() or chosen_mode
        if task_path is None and previous_state.get("task_path"):
            task_path = Path(str(previous_state["task_path"]))
        if session_dir is None and previous_state.get("latest_session_path"):
            session_dir = Path(str(previous_state["latest_session_path"]))
        if not profile_name:
            profile_name = str(previous_state.get("profile", "")).strip() or None

    chosen_profile, profile = _profile_cfg(cfg, profile_name)
    task = load_task_spec(task_path) if task_path else None
    breakdown_path: Path | None = None
    task_board_path: Path | None = None
    task_progress_path: Path | None = None
    breakdown: dict[str, Any] | None = None
    progress: dict[str, Any] | None = None
    focus_subtasks: list[dict[str, Any]] = []
    focus_ids: list[str] = []
    if task is not None and bool(task.get("decomposition", {}).get("enabled", True)):
        breakdown_path = write_task_breakdown(cfg, task_path)
        breakdown = derive_task_breakdown(cfg, task, task_path)
        generated = _task_generated_files(cfg, task)
        task_board_path = generated.get("task_board")
        task_progress_path = generated.get("task_progress")
        progress = load_task_progress(cfg, task)
        focus_subtasks, focus_ids = _focus_subtasks(breakdown, progress, chosen_stage)
    current_task_id = _task_id(task)
    strategy = str(profile.get("session_pick_strategy", "latest_failed_then_latest_pass"))
    selected_session = session_dir.resolve() if session_dir else _pick_session(
        Path(cfg["outputs"]["evidence_root_path"]),
        chosen_mode,
        current_task_id,
        strategy,
    )
    if selected_session is not None:
        session_files = _session_artifacts(selected_session)
        if not all(path.exists() for key, path in session_files.items() if key in {"session_summary", "session_brief", "session_verdict"}):
            from .reporting import write_feature_summary, write_session_summary

            write_session_summary(selected_session)
            manifest = _read_json(selected_session / "session_manifest.json") or {}
            manifest_task = manifest.get("task")
            if manifest_task and not (selected_session / "feature_summary.md").exists():
                write_feature_summary(selected_session, manifest_task)
    verdict = _session_verdict(selected_session) if selected_session is not None else {
        "status": "needs_review",
        "summary": "No matching session has been selected yet.",
        "strongest_evidence": "session missing",
        "next_step": "Run a validation session before drawing conclusions.",
    }

    suffix = chosen_mode
    if current_task_id:
        suffix += "_" + current_task_id
    base_name = f"context_pack_{suffix}_{chosen_stage}_{_slug(chosen_profile)}"
    brief_path = out_path.resolve() if out_path else (runtime_root / f"{base_name}_brief.md")
    base_prefix = brief_path.with_suffix("")
    facts_path = base_prefix.with_name(base_prefix.name.replace("_brief", "") + "_facts.json")
    constraints_path = base_prefix.with_name(base_prefix.name.replace("_brief", "") + "_constraints.json")
    resume_path = base_prefix.with_name(base_prefix.name.replace("_brief", "") + "_resume.md")
    paste_path = base_prefix.with_name(base_prefix.name.replace("_brief", "") + "_paste.md")
    legacy_brief_path = runtime_root / f"context_pack_{suffix}.md"

    allowed_reads = _allowed_reads(cfg, chosen_stage, chosen_profile, task, task_path, selected_session)
    allowed_edits = _allowed_edits(cfg, chosen_stage, chosen_profile, task)
    unknown_items = _unknowns(task, selected_session, verdict)
    forbidden = _forbidden_assumptions(chosen_stage)
    next_commands = _next_commands(chosen_mode, chosen_stage, chosen_profile, task_path, task, focus_ids)
    facts = _fact_items(
        cfg,
        chosen_mode,
        chosen_stage,
        chosen_profile,
        task,
        task_path,
        selected_session,
        verdict,
        progress,
        focus_ids,
    )

    constraints = {
        "generated_at": utc_now_iso(),
        "mode": chosen_mode,
        "stage": chosen_stage,
        "profile": chosen_profile,
        "task_id": current_task_id,
        "task_path": str(task_path) if task_path else "",
        "session_dir": str(selected_session) if selected_session else "",
        "max_pack_words": int(profile.get("max_pack_words", 550)),
        "max_fact_items": int(profile.get("max_fact_items", 12)),
        "max_cli_tail_lines": int(profile.get("max_cli_tail_lines", 6)),
        "max_failed_assertions_shown": int(profile.get("max_failed_assertions_shown", 3)),
        "max_extra_reads": int(profile.get("max_extra_reads", 2)),
        "max_edit_files": int(task.get("implementation", {}).get("max_edit_files", profile.get("max_edit_files", 2))) if task else int(profile.get("max_edit_files", 2)),
        "require_fact_citations": bool(profile.get("require_fact_citations", True)),
        "prefer_ascii_runtime_artifacts": bool(profile.get("prefer_ascii_runtime_artifacts", True)),
        "allowed_reads": [str(path) for path in allowed_reads],
        "allowed_edits": [str(path) for path in allowed_edits],
        "task_breakdown_path": str(breakdown_path) if breakdown_path else "",
        "task_board_path": str(task_board_path) if task_board_path else "",
        "task_progress_path": str(task_progress_path) if task_progress_path else "",
        "current_subtasks": focus_ids,
        "workflow_status": str((progress or {}).get("summary", {}).get("workflow_status", "active")),
        "unknowns": unknown_items,
        "forbidden_assumptions": forbidden,
        "next_commands": next_commands,
    }

    facts_payload = {
        "generated_at": utc_now_iso(),
        "mode": chosen_mode,
        "stage": chosen_stage,
        "profile": chosen_profile,
        "task_id": current_task_id,
        "session_dir": str(selected_session) if selected_session else "",
        "task_progress_path": str(task_progress_path) if task_progress_path else "",
        "facts": facts,
    }

    brief_text = _brief_text(
        cfg,
        chosen_mode,
        chosen_stage,
        chosen_profile,
        facts,
        focus_subtasks,
        allowed_reads,
        allowed_edits,
        unknown_items,
        forbidden,
        next_commands,
        selected_session,
    )
    ensure_dir(brief_path.parent)
    brief_path.write_text(brief_text, encoding="utf-8")
    if legacy_brief_path.resolve() != brief_path.resolve():
        legacy_brief_path.write_text(brief_text, encoding="utf-8")

    write_json(facts_path, facts_payload)
    write_json(constraints_path, constraints)

    state = {
        "generated_at": utc_now_iso(),
        "mode": chosen_mode,
        "stage": chosen_stage,
        "profile": chosen_profile,
        "task_id": current_task_id,
        "task_path": str(task_path) if task_path else "",
        "latest_session": selected_session.name if selected_session else "",
        "latest_session_path": str(selected_session) if selected_session else "",
        "latest_verdict": verdict.get("status", "needs_review"),
        "latest_verdict_summary": verdict.get("summary", ""),
        "next_commands": next_commands,
        "current_subtasks": focus_ids,
        "workflow_status": str((progress or {}).get("summary", {}).get("workflow_status", "active")),
        "task_progress_summary": (progress or {}).get("summary", {}),
        "allowed_reads": [str(path) for path in allowed_reads],
        "allowed_edits": [str(path) for path in allowed_edits],
        "unknowns": unknown_items,
        "generated_files": {
            "brief": str(brief_path),
            "facts": str(facts_path),
            "constraints": str(constraints_path),
            "resume": str(resume_path),
            "paste": str(paste_path),
            "task_breakdown": str(breakdown_path) if breakdown_path else "",
            "task_board": str(task_board_path) if task_board_path else "",
            "task_progress": str(task_progress_path) if task_progress_path else "",
        },
    }
    write_json(state_path, state)

    paste_path.write_text(
        _paste_text(
            brief_path,
            facts_path,
            constraints_path,
            breakdown_path,
            task_board_path,
            chosen_stage,
            focus_ids,
            next_commands,
        ),
        encoding="utf-8",
    )
    resume_path.write_text(_resume_text(state), encoding="utf-8")
    return brief_path
