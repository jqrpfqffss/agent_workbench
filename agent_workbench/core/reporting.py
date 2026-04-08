from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

from .utils import read_text, utc_now_iso, write_json


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(read_text(path))
    except Exception:
        return None


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in read_text(path).splitlines():
        text = line.strip()
        if not text:
            continue
        try:
            rows.append(json.loads(text))
        except Exception:
            continue
    return rows


def _clip(text: str, max_len: int = 140) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_len:
        return normalized
    return normalized[: max_len - 3] + "..."


def _monitor_stats(csv_path: Path) -> dict[str, dict[str, float]]:
    stats: dict[str, dict[str, float]] = {}
    if not csv_path.exists():
        return stats
    raw = read_text(csv_path)
    if not raw:
        return stats
    sanitized = raw.replace("\x00", "")
    reader = csv.DictReader(io.StringIO(sanitized, newline=""))
    for row in reader:
        if not row:
            continue
        item = str(row.get("item", "")).strip()
        if not item or str(row.get("ok", "0")).strip() != "1":
            continue
        try:
            value = float(str(row.get("value", "0")).strip())
        except ValueError:
            continue
        cur = stats.setdefault(item, {"count": 0.0, "min": value, "max": value, "last": value})
        cur["count"] += 1.0
        cur["min"] = min(cur["min"], value)
        cur["max"] = max(cur["max"], value)
        cur["last"] = value
    return stats


def _assertion_summary(session_dir: Path) -> dict[str, Any]:
    rows = _read_jsonl(session_dir / "assertions.jsonl")
    passed = sum(1 for row in rows if row.get("status") == "pass")
    failed_rows = [row for row in rows if row.get("status") == "fail"]
    skipped = sum(1 for row in rows if row.get("status") == "skip")
    return {
        "passed": passed,
        "failed": len(failed_rows),
        "skipped": skipped,
        "failed_rows": failed_rows,
    }


def _last_event(session_dir: Path, event_name: str) -> dict[str, Any] | None:
    for row in reversed(_read_jsonl(session_dir / "events.jsonl")):
        if row.get("event") == event_name:
            return row
    return None


def _cli_tail(session_dir: Path, limit: int = 12) -> list[str]:
    return read_text(session_dir / "cli_transcript.log").splitlines()[-limit:]


def derive_session_verdict(session_dir: Path) -> dict[str, Any]:
    manifest = _read_json(session_dir / "session_manifest.json") or {}
    diag = _read_json(session_dir / "cli_diag.json") or {}
    diag_class = diag.get("classification", {}) if isinstance(diag, dict) else {}
    assertions = _assertion_summary(session_dir)
    probe_event = _last_event(session_dir, "cli_probe_done") or {}
    probe_error = _last_event(session_dir, "cli_probe_error") or {}
    flash_event = _last_event(session_dir, "flash_done") or {}
    probe_code = int(probe_event.get("code", 0)) if str(probe_event.get("code", "")).strip() else 0
    flash_code = int(flash_event.get("code", 0)) if str(flash_event.get("code", "")).strip() else 0
    failed_rows = assertions["failed_rows"]

    status = "needs_review"
    summary = "Evidence exists but no final automated verdict is available."
    strongest = "Inspect the latest session brief."
    next_step = "Run `agent_workbench.bat report --latest` to rebuild the latest summaries."

    if flash_event and flash_code != 0:
        status = "fail"
        summary = "Firmware flash step failed."
        strongest = f"flash_done code={flash_code}"
        next_step = "Check the flash toolchain and target connection before rerunning verify."
    elif probe_error:
        status = "fail"
        summary = "CLI probe backend failed before command execution."
        strongest = _clip(str(probe_error.get("error", "cli_probe_error")))
        next_step = "Check COM port mapping or UART backend availability before rerunning verify."
    elif diag_class.get("code") and str(diag_class.get("code")) not in {"ok", "n/a"}:
        code = str(diag_class.get("code"))
        status = "fail"
        summary = str(diag_class.get("summary", "CLI diagnostics indicate a failure."))
        strongest = _clip(str(diag_class.get("detail", summary)))
        if code == "rx_zero":
            next_step = "Check UART path and rerun `agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status`."
        elif code == "parser_no_command":
            next_step = "Inspect the CLI parser path and rerun the verify stage."
        elif code == "tx_or_host_rx":
            next_step = "Inspect the host receive path and rerun the verify stage."
        else:
            next_step = "Use the diagnostic code to pick the smallest fix before rerunning verify."
    elif probe_event and probe_code != 0:
        status = "fail"
        summary = "CLI probe command failed."
        strongest = f"cli_probe_done code={probe_code}"
        next_step = "Replay the CLI probe path before changing source code."
    elif assertions["failed"] > 0:
        first_fail = failed_rows[0]
        status = "fail"
        summary = f"{assertions['failed']} black-box assertions failed."
        strongest = f"{first_fail.get('name', 'assertion')} | {_clip(str(first_fail.get('detail', '')))}"
        next_step = "Inspect the first failed assertion, then rerun the verify stage."
    elif probe_event:
        if probe_code == 0:
            status = "pass"
            summary = "CLI probe completed successfully."
            strongest = f"saw_ready={probe_event.get('saw_ready', False)} saw_prompt={probe_event.get('saw_prompt', False)}"
            next_step = "Reuse this session as the current baseline or continue with the next task."
        else:
            status = "fail"
            summary = "CLI probe command failed."
            strongest = f"cli_probe_done code={probe_code}"
            next_step = "Replay the CLI probe path before changing source code."
    elif assertions["passed"] > 0:
        status = "pass"
        summary = "Available assertions passed."
        strongest = f"assertions pass={assertions['passed']} fail=0 skip={assertions['skipped']}"
        next_step = "Reuse this session as the current baseline or continue with the next task."

    return {
        "generated_at": utc_now_iso(),
        "session": str(session_dir),
        "mode": manifest.get("mode", "unknown"),
        "task_id": str((manifest.get("task") or {}).get("id", "")).strip(),
        "status": status,
        "summary": summary,
        "strongest_evidence": strongest,
        "classification_code": str(diag_class.get("code", "")),
        "next_step": next_step,
        "assertions": {
            "passed": assertions["passed"],
            "failed": assertions["failed"],
            "skipped": assertions["skipped"],
        },
        "probe": {
            "code": probe_code,
            "saw_ready": probe_event.get("saw_ready", False),
            "saw_prompt": probe_event.get("saw_prompt", False),
            "timeout_commands": probe_event.get("timeout_commands", []),
        },
        "evidence": {
            "session_summary": str(session_dir / "session_summary.md"),
            "session_brief": str(session_dir / "session_brief.md"),
            "cli_diag": str(session_dir / "cli_diag.json"),
            "cli_transcript": str(session_dir / "cli_transcript.log"),
            "assertions": str(session_dir / "assertions.jsonl"),
        },
    }


def write_session_verdict(session_dir: Path) -> Path:
    return write_json(session_dir / "session_verdict.json", derive_session_verdict(session_dir))


def write_session_brief(session_dir: Path) -> Path:
    verdict = derive_session_verdict(session_dir)
    diag = _read_json(session_dir / "cli_diag.json")
    diag_class = (diag or {}).get("classification", {})
    assertions = verdict.get("assertions", {})
    brief_path = session_dir / "session_brief.md"
    with brief_path.open("w", encoding="utf-8") as fp:
        fp.write("# Session Brief\n\n")
        fp.write(f"- generated_at: {utc_now_iso()}\n")
        fp.write(f"- session: `{session_dir.name}`\n")
        fp.write(f"- status: `{verdict.get('status', 'needs_review')}`\n")
        fp.write(f"- summary: {verdict.get('summary', '')}\n")
        fp.write(f"- strongest_evidence: {verdict.get('strongest_evidence', '')}\n")
        fp.write(f"- next_step: {verdict.get('next_step', '')}\n")
        fp.write(
            f"- assertions: pass={assertions.get('passed', 0)} fail={assertions.get('failed', 0)} skip={assertions.get('skipped', 0)}\n"
        )
        if diag_class:
            fp.write(f"- cli_diag: {diag_class.get('code', '')} | {diag_class.get('summary', '')}\n")
        else:
            fp.write("- cli_diag: missing\n")
        fp.write("\n## Read First\n")
        fp.write(f"- `{session_dir / 'session_verdict.json'}`\n")
        fp.write(f"- `{session_dir / 'session_summary.md'}`\n")
        fp.write(f"- `{session_dir / 'cli_transcript.log'}`\n")
        fp.write("\n## CLI Tail\n")
        tail = _cli_tail(session_dir, limit=8)
        if not tail:
            fp.write("- cli transcript empty or unavailable\n")
        else:
            for line in tail:
                fp.write(f"- {_clip(line, 180)}\n")
    return brief_path


def write_session_summary(session_dir: Path) -> Path:
    verdict_path = write_session_verdict(session_dir)
    brief_path = write_session_brief(session_dir)
    verdict = _read_json(verdict_path) or derive_session_verdict(session_dir)
    monitor_stats = _monitor_stats(session_dir / "monitor_samples.csv")
    cli_diag = _read_json(session_dir / "cli_diag.json")
    assertions = verdict.get("assertions", {})
    summary_path = session_dir / "session_summary.md"

    with summary_path.open("w", encoding="utf-8") as fp:
        fp.write("# Session Summary\n\n")
        fp.write(f"- generated_at: {utc_now_iso()}\n")
        fp.write(f"- session_dir: `{session_dir}`\n")
        fp.write(f"- verdict: `{verdict.get('status', 'needs_review')}`\n")
        fp.write(f"- verdict_file: `{verdict_path}`\n")
        fp.write(f"- brief_file: `{brief_path}`\n")
        fp.write(f"- next_step: {verdict.get('next_step', '')}\n\n")

        fp.write("## Evidence Files\n")
        for name in [
            "session_manifest.json",
            "session_verdict.json",
            "session_brief.md",
            "commands.log",
            "doctor_report.md",
            "feature_summary.md",
            "cli_transcript.log",
            "cli_diag.json",
            "assertions.jsonl",
            "compare_brief.md",
        ]:
            target = session_dir / name
            fp.write(f"- {name}: {'exists' if target.exists() else 'missing'}\n")

        fp.write("\n## Verdict Snapshot\n")
        fp.write(f"- summary: {verdict.get('summary', '')}\n")
        fp.write(f"- strongest_evidence: {verdict.get('strongest_evidence', '')}\n")
        fp.write(
            f"- assertions: pass={assertions.get('passed', 0)} fail={assertions.get('failed', 0)} skip={assertions.get('skipped', 0)}\n"
        )

        fp.write("\n## CLI Diagnostics\n")
        if not cli_diag:
            fp.write("- cli_diag.json missing\n")
        else:
            classification = cli_diag.get("classification", {})
            fp.write(f"- status: {cli_diag.get('status', 'unknown')}\n")
            fp.write(f"- code: {classification.get('code', 'n/a')}\n")
            fp.write(f"- summary: {classification.get('summary', 'n/a')}\n")
            fp.write(f"- detail: {classification.get('detail', 'n/a')}\n")

        fp.write("\n## Failed Assertions\n")
        failed_rows = _assertion_summary(session_dir)["failed_rows"]
        if not failed_rows:
            fp.write("- none\n")
        else:
            for row in failed_rows[:3]:
                fp.write(f"- {row.get('name', '')}: {_clip(str(row.get('detail', '')))}\n")

        fp.write("\n## CLI Tail\n")
        tail = _cli_tail(session_dir, limit=12)
        if not tail:
            fp.write("- cli transcript empty or unavailable\n")
        else:
            for line in tail:
                fp.write(f"- {_clip(line, 180)}\n")

        fp.write("\n## Monitor Stats\n")
        if not monitor_stats:
            fp.write("- no valid monitor samples\n")
        else:
            for item, stat in monitor_stats.items():
                fp.write(
                    f"- {item}: count={int(stat['count'])} min={stat['min']:.4f} max={stat['max']:.4f} last={stat['last']:.4f}\n"
                )

    return summary_path


def write_feature_summary(session_dir: Path, task: dict) -> Path:
    verdict = _read_json(session_dir / "session_verdict.json") or derive_session_verdict(session_dir)
    assertion_rows = _read_jsonl(session_dir / "assertions.jsonl")
    failed_rows = [row for row in assertion_rows if row.get("status") == "fail"]
    feature_path = session_dir / "feature_summary.md"
    with feature_path.open("w", encoding="utf-8") as fp:
        fp.write("# Feature Session Summary\n\n")
        fp.write(f"- generated_at: {utc_now_iso()}\n")
        fp.write(f"- task_id: `{task.get('id', '')}`\n")
        fp.write(f"- goal: {task.get('goal', '')}\n")
        fp.write(f"- verdict: `{verdict.get('status', 'needs_review')}`\n")
        fp.write(f"- next_step: {verdict.get('next_step', '')}\n\n")

        fp.write("## Scope\n")
        fp.write(f"- include: {', '.join(task.get('scope', {}).get('include', [])) or 'none'}\n")
        fp.write(f"- exclude: {', '.join(task.get('scope', {}).get('exclude', [])) or 'none'}\n\n")

        fp.write("## Verify Commands\n")
        commands = task.get("verify", {}).get("cli_commands", [])
        fp.write(f"- cli_commands: {', '.join(commands) or 'none'}\n")
        fp.write(f"- verify.sequence: {', '.join(task.get('verify', {}).get('sequence', [])) or 'none'}\n\n")

        fp.write("## Assertion Summary\n")
        fp.write(f"- blackbox_total: {len(task.get('acceptance', {}).get('blackbox', []))}\n")
        fp.write(f"- unit_items: {len(task.get('acceptance', {}).get('unit', []))}\n")
        fp.write(f"- passed: {verdict.get('assertions', {}).get('passed', 0)}\n")
        fp.write(f"- failed: {verdict.get('assertions', {}).get('failed', 0)}\n")
        fp.write(f"- skipped: {verdict.get('assertions', {}).get('skipped', 0)}\n")
        if failed_rows:
            fp.write("- top_failed:\n")
            for row in failed_rows[:3]:
                fp.write(f"  - {row.get('name', '')}: {_clip(str(row.get('detail', '')))}\n")

        fp.write("\n## Evidence\n")
        fp.write(f"- session_brief: `{session_dir / 'session_brief.md'}`\n")
        fp.write(f"- session_summary: `{session_dir / 'session_summary.md'}`\n")
        fp.write(f"- cli_transcript: `{session_dir / 'cli_transcript.log'}`\n")
        fp.write(f"- assertions: `{session_dir / 'assertions.jsonl'}`\n")
    return feature_path
