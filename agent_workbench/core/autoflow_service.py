from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - env specific
    raise RuntimeError(
        "PyYAML is required. Run agent_workbench\\bin\\setup.bat first."
    ) from exc

from .context_service import write_context_pack
from .task_breakdown import (
    derive_task_breakdown,
    load_task_progress,
    mark_task_subtasks,
    task_generated_paths,
    write_task_breakdown,
)
from .task_spec import load_task_spec
from .test_service import generate_tests
from .utils import ensure_dir, local_now_tag, read_text, utc_now_iso, write_json


STAGE_ORDER = ["analyze", "implement", "verify"]


def _slug(text: str) -> str:
    chars: list[str] = []
    for char in str(text).strip().lower():
        if char.isascii() and char.isalnum():
            chars.append(char)
        else:
            chars.append("_")
    slug = "".join(chars).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    if slug:
        return slug
    digest = hashlib.sha1(str(text).encode("utf-8", errors="ignore")).hexdigest()[:10]
    return f"task_{digest}"


def _clip(text: str, max_len: int = 100) -> str:
    normalized = " ".join(str(text).split())
    if len(normalized) <= max_len:
        return normalized
    return normalized[: max_len - 3] + "..."


def _ps_safe_workbench(command_text: str) -> str:
    escaped = str(command_text).replace('"', '""')
    return f'cmd /c ".\\{escaped}"'


def _stage_after(stage: str, stage_sequence: list[str] | None = None) -> str:
    sequence = [item for item in (stage_sequence or STAGE_ORDER) if item in STAGE_ORDER]
    if not sequence:
        sequence = STAGE_ORDER
    if stage not in sequence:
        return sequence[min(1, len(sequence) - 1)]
    index = sequence.index(stage)
    return sequence[min(index + 1, len(sequence) - 1)]


def _runtime_autoflow_state_path(cfg: dict) -> Path:
    return Path(cfg["agent"]["autoflow_state_path"])


def _runtime_autoflow_start_path(cfg: dict) -> Path:
    return Path(cfg["outputs"]["runtime_root_path"]) / "autoflow_start.md"


def _runtime_continue_autoflow_start_path(cfg: dict) -> Path:
    return Path(cfg["outputs"]["continue_runtime_root_path"]) / "autoflow_start.md"


def _project_prompt_dir(cfg: dict) -> Path | None:
    project_root = Path(cfg["project_root_path"])
    continue_root = project_root / ".continue" / "prompts"
    return continue_root if continue_root.parent.parent.exists() else None


def _infer_mode(goal: str) -> str:
    lowered = goal.lower()
    if any(token in lowered for token in ["debug", "fix", "修复", "排查", "故障", "调试"]):
        return "debug"
    if any(token in lowered for token in ["test", "测试", "验证用例", "断言", "回归"]):
        return "test"
    return "feature"


def _contains_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def _direct_cli_goal(goal: str) -> dict[str, str] | None:
    lowered = goal.lower()
    compact = "".join(str(goal).split()).lower()

    canonical_map = {
        "red on": {"slug": "red_on", "ack": "[ok] red -> on", "status": "LED RED"},
        "red off": {"slug": "red_off", "ack": "[ok] red -> off", "status": "LED RED"},
        "red toggle": {"slug": "red_toggle", "ack": "[ok] red -> toggle", "status": "LED RED"},
        "green on": {"slug": "green_on", "ack": "[ok] green -> on", "status": "LED GREEN"},
        "green off": {"slug": "green_off", "ack": "[ok] green -> off", "status": "LED GREEN"},
        "green toggle": {"slug": "green_toggle", "ack": "[ok] green -> toggle", "status": "LED GREEN"},
        "blue on": {"slug": "blue_on", "ack": "[ok] blue -> on", "status": "LED BLUE"},
        "blue off": {"slug": "blue_off", "ack": "[ok] blue -> off", "status": "LED BLUE"},
        "blue toggle": {"slug": "blue_toggle", "ack": "[ok] blue -> toggle", "status": "LED BLUE"},
        "all on": {"slug": "all_on", "ack": "[ok] all -> on", "status": "LED RED"},
        "all off": {"slug": "all_off", "ack": "[ok] all -> off", "status": "LED RED"},
        "all toggle": {"slug": "all_toggle", "ack": "[ok] all -> toggle", "status": "LED RED"},
        "status": {"slug": "status", "ack": "System status:", "status": "UART: USART2 @ 115200 8N1"},
        "help": {"slug": "help", "ack": "Available commands:", "status": "Available commands:"},
    }
    for command, meta in canonical_map.items():
        if command in lowered:
            return {"command": command, **meta}

    led_targets = [
        ("red", ["红灯", "redled", "red led", "red"]),
        ("green", ["绿灯", "greenled", "green led", "green"]),
        ("blue", ["蓝灯", "blueled", "blue led", "blue"]),
        ("all", ["全部", "所有led", "allled", "all led", "all"]),
    ]
    verb_map = {
        "on": ["点亮", "打开", "开启", "开灯", "亮起", "turnon", "switchon"],
        "off": ["关闭", "关掉", "熄灭", "turnoff", "switchoff"],
        "toggle": ["切换", "翻转", "toggle"],
    }
    for target, names in led_targets:
        if not (_contains_any(compact, names) or _contains_any(lowered, names)):
            continue
        for action, verbs in verb_map.items():
            if _contains_any(compact, verbs) or _contains_any(lowered, verbs):
                meta = canonical_map.get(f"{target} {action}")
                if meta is not None:
                    return {"command": f"{target} {action}", **meta}
    return None


def _stable_cli_strings(cfg: dict) -> list[str]:
    uart_cfg = cfg.get("uart", {})
    strings = [str(uart_cfg.get("ready_banner", "")).strip(), str(uart_cfg.get("prompt", "")).strip()]
    help_rows = uart_cfg.get("help_rows", [])
    if help_rows:
        strings.append("Available commands:")
    return [item for item in strings if item]


def _feature_scope_from_goal(goal: str, cfg: dict) -> dict[str, Any]:
    lowered = goal.lower()
    stable_strings = _stable_cli_strings(cfg)
    base = {
        "include": ["Core/Src/main.c"],
        "exclude": ["Drivers"],
        "read_candidates": ["Core/Src/main.c"],
        "edit_candidates": ["Core/Src/main.c"],
        "max_edit_files": 2,
        "blackbox": [],
        "unit": [],
        "manual_checks": [],
        "verify_sequence": ["doctor", "build", "uart_smoke"],
        "cli_commands": ["help", "status"],
        "notes": ["Keep the change minimal and do not break the UART CLI."],
        "stable_strings": stable_strings,
    }
    if all(token in lowered for token in ["tim3", "red", "pb0"]) or (
        any(token in lowered for token in ["timer", "tim3", "定时器"])
        and any(token in lowered for token in ["led", "pb0", "red", "闪烁", "blink"])
    ):
        return {
            "include": [
                "Core/Src/main.c",
                "Core/Src/stm32f1xx_it.c",
                "Core/Inc/stm32f1xx_hal_conf.h",
            ],
            "exclude": ["Drivers", "Core/Src/cli.c", "Core/Src/app_cli_commands.c"],
            "read_candidates": [
                "Core/Src/main.c",
                "Core/Src/stm32f1xx_it.c",
                "Core/Inc/stm32f1xx_hal_conf.h",
            ],
            "edit_candidates": [
                "Core/Src/main.c",
                "Core/Src/stm32f1xx_it.c",
                "Core/Inc/stm32f1xx_hal_conf.h",
            ],
            "max_edit_files": 3,
            "blackbox": [
                {"name": "cli_ready_banner_seen", "type": "cli_ready", "needle": str(cfg["uart"].get("ready_banner", "")).strip()},
                {"name": "cli_prompt_seen", "type": "cli_prompt_seen", "needle": str(cfg["uart"].get("prompt", "cli>")).strip()},
                {"name": "cli_still_responsive", "type": "cli_contains", "needle": "Available commands:"},
            ],
            "unit": [
                "TIM3 is initialized with the expected prescaler and auto-reload values.",
                "TIM3 interrupt toggles LED_RED_Pin.",
                "Timer start is triggered after the existing peripheral initialization path.",
                "Existing UART CLI behavior remains available.",
            ],
            "manual_checks": [
                {
                    "name": "red_led_blinks",
                    "instructions": "Verify on hardware that RED LED(PB0) toggles about every 500 ms, producing about 1 Hz blinking.",
                    "source": "autoflow_goal",
                }
            ],
            "verify_sequence": ["doctor", "build", "uart_smoke"],
            "cli_commands": ["help", "status"],
            "notes": [
                "Use TIM3 interrupt-driven toggling for RED LED(PB0).",
                "Keep UART CLI ready banner, prompt, and help text stable.",
            ],
            "stable_strings": stable_strings + ["Available commands:"],
        }
    if any(token in lowered for token in ["cli", "uart", "命令", "串口"]):
        return {
            "include": ["Core/Src/cli.c", "Core/Src/app_cli_commands.c", "Core/Src/main.c"],
            "exclude": ["Drivers"],
            "read_candidates": ["Core/Src/cli.c", "Core/Src/app_cli_commands.c", "Core/Src/main.c"],
            "edit_candidates": ["Core/Src/cli.c", "Core/Src/app_cli_commands.c"],
            "max_edit_files": 2,
            "blackbox": [
                {"name": "cli_ready_banner_seen", "type": "cli_ready", "needle": str(cfg["uart"].get("ready_banner", "")).strip()},
                {"name": "cli_prompt_seen", "type": "cli_prompt_seen", "needle": str(cfg["uart"].get("prompt", "cli>")).strip()},
            ],
            "unit": ["CLI command table and parser remain internally consistent."],
            "manual_checks": [],
            "verify_sequence": ["doctor", "build", "test", "uart_smoke"],
            "cli_commands": ["help", "status"],
            "notes": ["Keep the text CLI contract stable for host automation."],
            "stable_strings": stable_strings + ["Available commands:"],
        }
    return base


def _draft_task_payload(cfg: dict, goal: str, mode: str) -> dict[str, Any]:
    direct_cli = _direct_cli_goal(goal)
    if direct_cli is not None:
        task_id = f"autoflow_cli_{direct_cli['slug']}"
        command = direct_cli["command"]
        status_command = "status" if command != "status" else "help"
        return {
            "id": task_id,
            "mode": "feature",
            "goal": goal,
            "scope": {
                "include": [],
                "exclude": ["Drivers"],
            },
            "acceptance": {
                "blackbox": [
                    {"name": "cli_ready_banner_seen", "type": "cli_ready", "needle": str(cfg["uart"].get("ready_banner", "")).strip()},
                    {"name": "cli_prompt_seen", "type": "cli_prompt_seen", "needle": str(cfg["uart"].get("prompt", "cli>")).strip()},
                    {"name": "cli_command_ack_seen", "type": "cli_contains", "needle": direct_cli["ack"]},
                ],
                "unit": [
                    "No firmware code changes are required for this task.",
                    "The existing UART CLI command should be sufficient.",
                ],
            },
            "observability": {
                "notes": [
                    "Treat this as a direct CLI operation, not a code implementation task.",
                    "Do not modify source files unless UART evidence proves the existing command path is broken.",
                ],
                "manual_checks": [],
            },
            "verify": {
                "sequence": ["uart_smoke"],
                "cli_commands": [command, status_command],
            },
            "implementation": {
                "read_candidates": [],
                "edit_candidates": [],
                "stable_strings": [
                    str(cfg["uart"].get("ready_banner", "")).strip(),
                    str(cfg["uart"].get("prompt", "cli>")).strip(),
                    direct_cli["ack"],
                    direct_cli["status"],
                ],
                "max_edit_files": 0,
            },
            "decomposition": {
                "enabled": True,
                "batch_size": 2,
                "subtasks": [
                    {
                        "id": "S1",
                        "stage": "analyze",
                        "title": "Confirm the exact existing CLI command.",
                        "objective": "Map the natural-language goal to a built-in UART CLI command without inventing code work.",
                        "inputs": ["task yaml", "verify.cli_commands"],
                        "done_when": "The exact UART command is fixed for this run.",
                    },
                    {
                        "id": "S2",
                        "stage": "analyze",
                        "title": "Lock the verify-only path.",
                        "objective": "Confirm that no code edits are required and the next round should jump directly to verification.",
                        "inputs": ["implementation.max_edit_files", "stable_strings"],
                        "done_when": "The task is confirmed as verify-only.",
                    },
                    {
                        "id": "S3",
                        "stage": "verify",
                        "title": "Run the UART CLI command.",
                        "objective": "Execute the exact UART command and capture transcript evidence.",
                        "inputs": [command, status_command],
                        "done_when": "A fresh transcript shows the command response.",
                    },
                    {
                        "id": "S4",
                        "stage": "verify",
                        "title": "Report from transcript evidence only.",
                        "objective": "Use the transcript and diagnostics to report pass, fail, blocked, or needs_review.",
                        "inputs": ["cli_transcript.log", "cli_diag.json"],
                        "done_when": "The result is supported by fresh UART evidence.",
                    },
                ],
            },
            "metadata": {
                "generated_by": "agent_workbench.autoflow",
                "project": str(cfg.get("project", {}).get("name", "project")).strip() or "project",
                "created_at": utc_now_iso(),
                "goal_summary": _clip(goal, 140),
                "autoflow_kind": "direct_cli",
                "direct_cli_command": command,
            },
        }

    inferred = _feature_scope_from_goal(goal, cfg)
    project_name = str(cfg.get("project", {}).get("name", "project")).strip() or "project"
    task_id = _slug(goal)
    if mode == "debug":
        task_id = f"autoflow_debug_{task_id}"
    elif mode == "test":
        task_id = f"autoflow_test_{task_id}"
    else:
        task_id = f"autoflow_feature_{task_id}"
    return {
        "id": task_id,
        "mode": mode,
        "goal": goal,
        "scope": {
            "include": inferred["include"],
            "exclude": inferred["exclude"],
        },
        "acceptance": {
            "blackbox": inferred["blackbox"],
            "unit": inferred["unit"],
        },
        "observability": {
            "notes": inferred["notes"],
            "manual_checks": inferred["manual_checks"],
        },
        "verify": {
            "sequence": inferred["verify_sequence"],
            "cli_commands": inferred["cli_commands"],
        },
        "implementation": {
            "read_candidates": inferred["read_candidates"],
            "edit_candidates": inferred["edit_candidates"],
            "stable_strings": inferred["stable_strings"],
            "max_edit_files": inferred["max_edit_files"],
        },
        "decomposition": {
            "enabled": True,
            "batch_size": 2,
            "subtasks": [],
        },
        "metadata": {
            "generated_by": "agent_workbench.autoflow",
            "project": project_name,
            "created_at": utc_now_iso(),
            "goal_summary": _clip(goal, 140),
        },
    }


def write_goal_task_draft(cfg: dict, goal: str, mode: str | None = None) -> Path:
    chosen_mode = (mode or _infer_mode(goal)).strip().lower() or "feature"
    payload = _draft_task_payload(cfg, goal, chosen_mode)
    requests_root = Path(cfg["outputs"]["requests_root_path"])
    request_dir = ensure_dir(requests_root / f"{_slug(goal)[:48]}_{local_now_tag()}")
    task_path = request_dir / "task_draft.yaml"
    task_path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return task_path


def _load_agent_state(cfg: dict) -> dict[str, Any]:
    state_path = Path(cfg["agent"]["state_path"])
    if not state_path.exists():
        return {}
    try:
        return json.loads(read_text(state_path))
    except Exception:
        return {}


def _load_autoflow_state(cfg: dict) -> dict[str, Any]:
    state_path = _runtime_autoflow_state_path(cfg)
    if not state_path.exists():
        return {}
    try:
        return json.loads(read_text(state_path))
    except Exception:
        return {}


def _task_runtime_state(cfg: dict, task_path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    task = load_task_spec(task_path)
    write_task_breakdown(cfg, task_path)
    breakdown = derive_task_breakdown(cfg, task, task_path)
    progress = load_task_progress(cfg, task) or {}
    return task, breakdown, progress


def _stage_sequence(breakdown: dict[str, Any], progress: dict[str, Any]) -> list[str]:
    sequence = [str(item).strip() for item in progress.get("stage_sequence", []) if str(item).strip()]
    if sequence:
        return sequence
    stage_map = breakdown.get("stage_map", {})
    sequence = [item for item in STAGE_ORDER if stage_map.get(item)]
    return sequence or STAGE_ORDER


def _generated_dir(cfg: dict, task: dict[str, Any], previous_state: dict[str, Any] | None = None) -> Path:
    previous_generated = ((previous_state or {}).get("generated_files", {}) or {}).get("generated_dir", "")
    if str(previous_generated).strip():
        return Path(str(previous_generated))
    return task_generated_paths(cfg, task)["generated_dir"]


def _autoflow_state_payload(
    cfg: dict,
    *,
    goal: str,
    mode: str,
    profile_name: str,
    task: dict[str, Any],
    task_path: Path,
    breakdown: dict[str, Any],
    progress: dict[str, Any],
    generated_dir: Path,
    agent_state: dict[str, Any],
    start_path: Path,
    next_commands_override: list[str] | None = None,
) -> dict[str, Any]:
    summary = progress.get("summary", {})
    stage_sequence = _stage_sequence(breakdown, progress)
    current_stage = str(summary.get("current_stage", "")).strip()
    workflow_status = str(summary.get("workflow_status", "active")).strip() or "active"
    if not current_stage and stage_sequence:
        current_stage = stage_sequence[-1] if workflow_status == "complete" else stage_sequence[0]
    generated = task_generated_paths(cfg, task)
    generated_files = dict(agent_state.get("generated_files", {}))
    generated_files.update(
        {
            "task_draft": str(task_path),
            "generated_dir": str(generated_dir),
            "task_breakdown": str(generated["task_breakdown"]),
            "task_progress": str(generated["task_progress"]),
            "task_board": str(generated["task_board"]),
            "start_card": str(start_path),
        }
    )
    next_commands = list(next_commands_override) if next_commands_override is not None else list(agent_state.get("next_commands", []))
    if workflow_status == "complete":
        next_commands = []
    return {
        "generated_at": utc_now_iso(),
        "goal": goal,
        "mode": mode,
        "profile": profile_name,
        "task_id": str(task.get("id", "")).strip(),
        "task_path": str(task_path),
        "stage": current_stage,
        "stage_sequence": stage_sequence,
        "workflow_status": workflow_status,
        "progress_counts": dict(summary.get("counts", {})),
        "completed_subtasks": list(summary.get("completed_subtasks", [])),
        "current_subtasks": list(summary.get("current_subtasks", [])),
        "next_stage": str(summary.get("next_stage", _stage_after(current_stage, stage_sequence))).strip() or "complete",
        "next_commands": next_commands,
        "latest_session": str(agent_state.get("latest_session", "")).strip(),
        "latest_session_path": str(agent_state.get("latest_session_path", "")).strip(),
        "latest_verdict": str(agent_state.get("latest_verdict", "")).strip(),
        "latest_verdict_summary": str(agent_state.get("latest_verdict_summary", "")).strip(),
        "stop_conditions": [
            "Stop if a workbench command returns a non-zero exit code.",
            "Stop if the current stage card, task board, or task progress file is missing.",
            "Stop when manual_checks_pending becomes true and wait for manual confirmation.",
            "Stop when verify evidence is incomplete and the result is still needs_review.",
        ],
        "generated_files": generated_files,
    }


def _write_autoflow_start_card(cfg: dict, state: dict[str, Any]) -> Path:
    start_path = _runtime_autoflow_start_path(cfg)
    ensure_dir(start_path.parent)
    generated = state.get("generated_files", {})
    paste_path = generated.get("paste", "")
    breakdown_path = generated.get("task_breakdown", "")
    task_board_path = generated.get("task_board", "")
    task_progress_path = generated.get("task_progress", "")
    task_path = generated.get("task_draft", "") or state.get("task_path", "")
    counts = state.get("progress_counts", {})
    completed = list(state.get("completed_subtasks", []))
    lines = [
        "# Autoflow Start",
        "",
        f"- goal: {state.get('goal', '')}",
        f"- task_id: `{state.get('task_id', '')}`",
        f"- task_path: `{state.get('task_path', '')}`",
        f"- workflow_status: `{state.get('workflow_status', 'active')}`",
        f"- current_stage: `{state.get('stage', '') or 'complete'}`",
        f"- stage_sequence: `{', '.join(state.get('stage_sequence', []))}`",
        f"- current_subtasks: {', '.join(state.get('current_subtasks', [])) or 'none'}",
        f"- next_stage: `{state.get('next_stage', '')}`",
        f"- progress: done={counts.get('done', 0)} skipped={counts.get('skipped', 0)} pending={counts.get('pending', 0)} in_progress={counts.get('in_progress', 0)} blocked={counts.get('blocked', 0)}",
        "",
        "## Read First",
        f"- `{paste_path}`" if paste_path else "- paste card missing",
        f"- `{breakdown_path}`" if breakdown_path else "- task breakdown missing",
        f"- `{task_board_path}`" if task_board_path else "- task board missing",
        f"- `{task_progress_path}`" if task_progress_path else "- task progress missing",
        f"- `{task_path}`" if task_path else "- task draft missing",
        "",
        "## Continue Rules",
        "1. Read the current stage paste card first.",
        "2. Complete only the listed current_subtasks for this round.",
        "3. Use agent_workbench.bat for every automation action.",
        "4. After a subtask batch is truly finished, run `agent_workbench.bat autoflow --done <IDs>` to checkpoint progress.",
        "5. Then run `agent_workbench.bat autoflow --resume` to load the next pending batch.",
        "6. Stop immediately if a command fails or if manual checks become pending.",
    ]
    if completed:
        lines.extend(
            [
                "",
                "## Completed",
                f"- {', '.join(completed[:8])}",
            ]
        )
    lines.extend(["", "## Next Commands"])
    if state.get("next_commands"):
        for command in state.get("next_commands", [])[:6]:
            lines.append(f"- `{command}`")
    else:
        lines.append("- none")
    lines.append("")
    start_text = "\n".join(lines)
    start_path.write_text(start_text, encoding="utf-8")

    continue_runtime_path = _runtime_continue_autoflow_start_path(cfg)
    ensure_dir(continue_runtime_path.parent)
    continue_runtime_path.write_text(start_text, encoding="utf-8")

    project_prompt_dir = _project_prompt_dir(cfg)
    if project_prompt_dir is not None:
        ensure_dir(project_prompt_dir)
        (project_prompt_dir / "autoflow_start.md").write_text(start_text, encoding="utf-8")
    return start_path


def _refresh_autoflow_state(
    cfg: dict,
    *,
    task_path: Path,
    goal: str,
    mode: str,
    profile_name: str,
    previous_state: dict[str, Any] | None = None,
    rewrite_context: bool,
    next_commands_override: list[str] | None = None,
) -> Path:
    task, breakdown, progress = _task_runtime_state(cfg, task_path)
    actual_mode = str(task.get("mode", mode or "feature")).strip() or "feature"
    actual_goal = str(goal).strip() or str(task.get("goal", "")).strip()
    summary = progress.get("summary", {})
    if rewrite_context and str(summary.get("workflow_status", "active")) != "complete":
        current_stage = str(summary.get("current_stage", "")).strip() or "analyze"
        write_context_pack(
            cfg,
            mode=actual_mode,
            stage=current_stage,
            profile_name=profile_name,
            task_path=task_path,
        )
    agent_state = _load_agent_state(cfg)
    start_path = _runtime_autoflow_start_path(cfg)
    state = _autoflow_state_payload(
        cfg,
        goal=actual_goal,
        mode=actual_mode,
        profile_name=profile_name,
        task=task,
        task_path=task_path,
        breakdown=breakdown,
        progress=progress,
        generated_dir=_generated_dir(cfg, task, previous_state),
        agent_state=agent_state,
        start_path=start_path,
        next_commands_override=next_commands_override,
    )
    write_json(_runtime_autoflow_state_path(cfg), state)
    return _write_autoflow_start_card(cfg, state)


def run_autoflow(
    cfg: dict,
    *,
    goal: str,
    mode: str | None = None,
    profile_name: str | None = None,
    task_path: Path | None = None,
) -> Path:
    chosen_profile = str(profile_name or cfg.get("agent", {}).get("default_profile", "balanced_local")).strip() or "balanced_local"
    actual_task_path = task_path.resolve() if task_path else write_goal_task_draft(cfg, goal, mode)
    task = load_task_spec(actual_task_path)
    actual_goal = str(goal).strip() or str(task.get("goal", "")).strip()
    generate_tests(cfg, actual_task_path)
    return _refresh_autoflow_state(
        cfg,
        task_path=actual_task_path,
        goal=actual_goal,
        mode=str(task.get("mode", mode or "feature")).strip() or "feature",
        profile_name=chosen_profile,
        previous_state=None,
        rewrite_context=True,
    )


def resume_autoflow(cfg: dict) -> Path:
    previous_state = _load_autoflow_state(cfg)
    if not previous_state:
        raise RuntimeError("autoflow state is missing. Run `agent_workbench.bat autoflow --goal \"...\"` first.")
    task_path_text = str(previous_state.get("task_path", "")).strip()
    if not task_path_text:
        raise RuntimeError("autoflow task_path is missing from state.")
    return _refresh_autoflow_state(
        cfg,
        task_path=Path(task_path_text),
        goal=str(previous_state.get("goal", "")).strip(),
        mode=str(previous_state.get("mode", "feature")).strip() or "feature",
        profile_name=str(previous_state.get("profile", "")).strip() or str(cfg.get("agent", {}).get("default_profile", "balanced_local")).strip() or "balanced_local",
        previous_state=previous_state,
        rewrite_context=True,
    )


def mark_autoflow_progress(
    cfg: dict,
    *,
    status: str,
    subtask_ids: list[str],
    note: str = "",
    task_path: Path | None = None,
) -> Path:
    previous_state = _load_autoflow_state(cfg)
    actual_task_path = task_path
    if actual_task_path is None:
        task_path_text = str(previous_state.get("task_path", "")).strip()
        if not task_path_text:
            raise RuntimeError("autoflow state is missing task_path. Start autoflow first or pass --task.")
        actual_task_path = Path(task_path_text)

    task = load_task_spec(actual_task_path)
    mark_task_subtasks(
        cfg,
        task,
        task_path=actual_task_path,
        status=status,
        subtask_ids=subtask_ids,
        note=note,
    )
    write_task_breakdown(cfg, actual_task_path)
    summary = (load_task_progress(cfg, task) or {}).get("summary", {})
    next_commands_override = [] if str(summary.get("workflow_status", "active")) == "complete" else [_ps_safe_workbench("agent_workbench.bat autoflow --resume")]
    return _refresh_autoflow_state(
        cfg,
        task_path=actual_task_path,
        goal=str(previous_state.get("goal", "")).strip() or str(task.get("goal", "")).strip(),
        mode=str(previous_state.get("mode", task.get("mode", "feature"))).strip() or str(task.get("mode", "feature")).strip() or "feature",
        profile_name=str(previous_state.get("profile", "")).strip() or str(cfg.get("agent", {}).get("default_profile", "balanced_local")).strip() or "balanced_local",
        previous_state=previous_state,
        rewrite_context=False,
        next_commands_override=next_commands_override,
    )


def status_autoflow(cfg: dict, *, task_path: Path | None = None) -> Path:
    previous_state = _load_autoflow_state(cfg)
    actual_task_path = task_path
    if actual_task_path is None:
        task_path_text = str(previous_state.get("task_path", "")).strip()
        if not task_path_text:
            raise RuntimeError("autoflow state is missing. Run `agent_workbench.bat autoflow --goal \"...\"` first.")
        actual_task_path = Path(task_path_text)
    task = load_task_spec(actual_task_path)
    return _refresh_autoflow_state(
        cfg,
        task_path=actual_task_path,
        goal=str(previous_state.get("goal", "")).strip() or str(task.get("goal", "")).strip(),
        mode=str(previous_state.get("mode", task.get("mode", "feature"))).strip() or str(task.get("mode", "feature")).strip() or "feature",
        profile_name=str(previous_state.get("profile", "")).strip() or str(cfg.get("agent", {}).get("default_profile", "balanced_local")).strip() or "balanced_local",
        previous_state=previous_state,
        rewrite_context=False,
        next_commands_override=None,
    )
