from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from .utils import read_text, utc_now_iso


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


def write_session_summary(session_dir: Path) -> Path:
    summary_path = session_dir / "session_summary.md"
    monitor_stats = _monitor_stats(session_dir / "monitor_samples.csv")
    uart_tail = read_text(session_dir / "uart.log").splitlines()[-40:]
    cli_tail = read_text(session_dir / "cli_transcript.log").splitlines()[-40:]
    cli_diag = None
    cli_diag_path = session_dir / "cli_diag.json"
    if cli_diag_path.exists():
        try:
            cli_diag = json.loads(cli_diag_path.read_text(encoding="utf-8"))
        except Exception:
            cli_diag = {"status": "error", "error": "invalid json"}
    manifest = read_text(session_dir / "session_manifest.json")

    with summary_path.open("w", encoding="utf-8") as fp:
        fp.write("# Debug Session Summary\n\n")
        fp.write(f"- generated_at: {utc_now_iso()}\n")
        fp.write(f"- session_dir: `{session_dir}`\n\n")
        fp.write("## Evidence Files\n")
        for name in [
            "session_manifest.json",
            "commands.log",
            "doctor_report.md",
            "uart.log",
            "cli_transcript.log",
            "cli_diag.json",
            "monitor_samples.csv",
            "assertions.jsonl",
        ]:
            target = session_dir / name
            fp.write(f"- {name}: {'exists' if target.exists() else 'missing'}\n")
        fp.write("\n## Monitor Stats\n")
        if not monitor_stats:
            fp.write("- no valid monitor samples\n")
        else:
            for item, stat in monitor_stats.items():
                fp.write(
                    f"- {item}: count={int(stat['count'])} min={stat['min']:.4f} "
                    f"max={stat['max']:.4f} last={stat['last']:.4f}\n"
                )
        fp.write("\n## UART Tail\n")
        if not uart_tail:
            fp.write("- uart log empty or unavailable\n")
        else:
            fp.write("```text\n")
            fp.write("\n".join(uart_tail))
            fp.write("\n```\n")
        fp.write("\n## CLI Tail\n")
        if not cli_tail:
            fp.write("- cli transcript empty or unavailable\n")
        else:
            fp.write("```text\n")
            fp.write("\n".join(cli_tail))
            fp.write("\n```\n")
        fp.write("\n## CLI Diagnostics\n")
        if not cli_diag:
            fp.write("- cli_diag.json missing\n")
        else:
            classification = cli_diag.get("classification", {})
            fp.write(f"- status: {cli_diag.get('status', 'unknown')}\n")
            fp.write(f"- summary: {classification.get('summary', 'n/a')}\n")
            fp.write(f"- detail: {classification.get('detail', 'n/a')}\n")
            stats = cli_diag.get("stats", {})
            if stats:
                fp.write(
                    "- stats: "
                    f"rx_bytes={stats.get('rx_bytes', 'n/a')} "
                    f"rx_lines={stats.get('rx_lines', 'n/a')} "
                    f"cmd_ok={stats.get('cmd_ok', 'n/a')} "
                    f"cmd_err={stats.get('cmd_err', 'n/a')} "
                    f"rx_overflow={stats.get('rx_overflow', 'n/a')} "
                    f"uart_error={stats.get('uart_error', 'n/a')} "
                    f"last_cmd={stats.get('last_cmd', 'n/a')}\n"
                )
        fp.write("\n## Manifest Snapshot\n")
        if manifest:
            fp.write("```json\n")
            fp.write(manifest)
            fp.write("\n```\n")
        else:
            fp.write("- manifest missing\n")
    return summary_path


def write_feature_summary(session_dir: Path, task: dict) -> Path:
    summary_path = session_dir / "feature_summary.md"
    with summary_path.open("w", encoding="utf-8") as fp:
        fp.write("# Feature Session Summary\n\n")
        fp.write(f"- generated_at: {utc_now_iso()}\n")
        fp.write(f"- task_id: `{task.get('id', '')}`\n")
        fp.write(f"- goal: {task.get('goal', '')}\n\n")
        fp.write("## Scope\n")
        fp.write(f"- include: {', '.join(task.get('scope', {}).get('include', [])) or 'none'}\n")
        fp.write(f"- exclude: {', '.join(task.get('scope', {}).get('exclude', [])) or 'none'}\n\n")
        fp.write("## Acceptance\n")
        fp.write(f"- blackbox assertions: {len(task.get('acceptance', {}).get('blackbox', []))}\n")
        fp.write(f"- unit items: {len(task.get('acceptance', {}).get('unit', []))}\n")
    return summary_path
