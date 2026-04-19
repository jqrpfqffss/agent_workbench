from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .reporting import derive_session_verdict
from .utils import ensure_dir, read_text, utc_now_iso, write_json


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


def _read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="ignore").splitlines() if path.exists() else []


def _transcript_rx_lines(path: Path) -> list[str]:
    lines: list[str] = []
    for line in _read_lines(path):
        marker = "] < "
        index = line.find(marker)
        if index >= 0:
            lines.append(line[index + len(marker):])
    return lines


def _assertion_counts(path: Path) -> dict[str, int]:
    rows = _read_jsonl(path)
    return {
        "passed": sum(1 for row in rows if row.get("status") == "pass"),
        "failed": sum(1 for row in rows if row.get("status") == "fail"),
        "skipped": sum(1 for row in rows if row.get("status") == "skip"),
    }


def _diag_code(path: Path) -> str:
    diag = _read_json(path) or {}
    return str((diag.get("classification") or {}).get("code", "")).strip()


def _session_sort_key(path: Path) -> tuple[float, str]:
    manifest_path = path / "session_manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(read_text(manifest_path))
            generated_at = manifest.get("generated_at", "")
            if generated_at:
                return (datetime.fromisoformat(generated_at).timestamp(), path.name)
        except Exception:
            pass
    return (path.stat().st_mtime, path.name)


def _session_mode(path: Path) -> str:
    manifest_path = path / "session_manifest.json"
    if not manifest_path.exists():
        return ""
    try:
        manifest = json.loads(read_text(manifest_path))
    except Exception:
        return ""
    return str(manifest.get("mode", "")).strip().lower()


def list_session_dirs(sessions_root: Path) -> list[Path]:
    if not sessions_root.exists():
        return []
    return sorted((p for p in sessions_root.iterdir() if p.is_dir()), key=_session_sort_key)


def pick_latest_two_sessions(sessions_root: Path) -> tuple[Path, Path]:
    sessions = list_session_dirs(sessions_root)
    if len(sessions) < 2:
        raise RuntimeError(f"need at least 2 sessions under {sessions_root}, got {len(sessions)}")
    return sessions[-2], sessions[-1]


def find_previous_session(sessions_root: Path, current_session: Path) -> Path | None:
    previous = None
    current_resolved = current_session.resolve()
    current_mode = _session_mode(current_session)
    for session in list_session_dirs(sessions_root):
        if current_mode and _session_mode(session) not in {"", current_mode}:
            continue
        if session.resolve() == current_resolved:
            return previous
        previous = session
    return None


def compare_sessions(old_dir: Path, new_dir: Path, out_path: Path) -> Path:
    old_dir = old_dir.resolve()
    new_dir = new_dir.resolve()
    out_path = out_path.resolve()
    ensure_dir(out_path.parent)

    old_uart = _read_lines(old_dir / "uart.log")
    new_uart = _read_lines(new_dir / "uart.log")
    old_cli = _transcript_rx_lines(old_dir / "cli_transcript.log")
    new_cli = _transcript_rx_lines(new_dir / "cli_transcript.log")
    old_warn = sum(1 for line in old_uart if any(tag in line.lower() for tag in ("warn", "error", "fault", "panic", "assert")))
    new_warn = sum(1 for line in new_uart if any(tag in line.lower() for tag in ("warn", "error", "fault", "panic", "assert")))
    old_monitor = _monitor_stats(old_dir / "monitor_samples.csv")
    new_monitor = _monitor_stats(new_dir / "monitor_samples.csv")
    old_assert = _assertion_counts(old_dir / "assertions.jsonl")
    new_assert = _assertion_counts(new_dir / "assertions.jsonl")
    old_diag = _diag_code(old_dir / "cli_diag.json")
    new_diag = _diag_code(new_dir / "cli_diag.json")
    old_verdict = derive_session_verdict(old_dir)
    new_verdict = derive_session_verdict(new_dir)
    cli_unique = [line for line in new_cli if line not in set(old_cli)]
    monitor_items = sorted(set(old_monitor) | set(new_monitor))

    delta_payload = {
        "generated_at": utc_now_iso(),
        "old_session": str(old_dir),
        "new_session": str(new_dir),
        "verdict": {
            "old": old_verdict.get("status", ""),
            "new": new_verdict.get("status", ""),
        },
        "uart": {
            "old_lines": len(old_uart),
            "new_lines": len(new_uart),
            "delta_lines": len(new_uart) - len(old_uart),
            "old_warn_like": old_warn,
            "new_warn_like": new_warn,
            "delta_warn_like": new_warn - old_warn,
        },
        "cli": {
            "old_lines": len(old_cli),
            "new_lines": len(new_cli),
            "delta_lines": len(new_cli) - len(old_cli),
            "new_unique_lines": cli_unique[-10:],
        },
        "assertions": {
            "old": old_assert,
            "new": new_assert,
            "delta_failed": new_assert["failed"] - old_assert["failed"],
        },
        "diag": {
            "old": old_diag,
            "new": new_diag,
        },
    }
    write_json(out_path.with_name("compare_delta.json"), delta_payload)

    with out_path.with_name("compare_brief.md").open("w", encoding="utf-8") as fp:
        fp.write("# Compare Brief\n\n")
        fp.write(f"- old_session: `{old_dir.name}`\n")
        fp.write(f"- new_session: `{new_dir.name}`\n")
        fp.write(f"- verdict: `{old_verdict.get('status', '')}` -> `{new_verdict.get('status', '')}`\n")
        fp.write(f"- assertions.failed: {old_assert['failed']} -> {new_assert['failed']}\n")
        fp.write(f"- diag.code: `{old_diag or 'none'}` -> `{new_diag or 'none'}`\n")
        fp.write(f"- cli.delta_lines: {len(new_cli) - len(old_cli)}\n")
        if cli_unique:
            fp.write("\n## New CLI Lines\n")
            for line in cli_unique[-6:]:
                fp.write(f"- {line}\n")

    with out_path.open("w", encoding="utf-8") as fp:
        fp.write("# Session Compare Report\n\n")
        fp.write(f"- generated_at: {utc_now_iso()}\n")
        fp.write(f"- old_session: `{old_dir}`\n")
        fp.write(f"- new_session: `{new_dir}`\n\n")

        fp.write("## Verdict Delta\n")
        fp.write(f"- old: `{old_verdict.get('status', '')}` | {old_verdict.get('summary', '')}\n")
        fp.write(f"- new: `{new_verdict.get('status', '')}` | {new_verdict.get('summary', '')}\n\n")

        fp.write("## UART Metrics\n")
        fp.write("| metric | old | new | delta |\n")
        fp.write("|---|---:|---:|---:|\n")
        fp.write(f"| lines | {len(old_uart)} | {len(new_uart)} | {len(new_uart) - len(old_uart)} |\n")
        fp.write(f"| warn_like | {old_warn} | {new_warn} | {new_warn - old_warn} |\n\n")

        fp.write("## CLI Metrics\n")
        fp.write("| metric | old | new | delta |\n")
        fp.write("|---|---:|---:|---:|\n")
        fp.write(f"| rx_lines | {len(old_cli)} | {len(new_cli)} | {len(new_cli) - len(old_cli)} |\n")
        fp.write(f"| diag_code | {old_diag or 'none'} | {new_diag or 'none'} | n/a |\n\n")

        fp.write("## Assertion Metrics\n")
        fp.write("| metric | old | new | delta |\n")
        fp.write("|---|---:|---:|---:|\n")
        for name in ("passed", "failed", "skipped"):
            fp.write(f"| {name} | {old_assert[name]} | {new_assert[name]} | {new_assert[name] - old_assert[name]} |\n")

        fp.write("\n## Monitor Metrics\n")
        fp.write("| item | old_count | new_count | old_last | new_last | delta_last |\n")
        fp.write("|---|---:|---:|---:|---:|---:|\n")
        for item in monitor_items:
            old_item = old_monitor.get(item, {})
            new_item = new_monitor.get(item, {})
            old_last = old_item.get("last", 0.0)
            new_last = new_item.get("last", 0.0)
            fp.write(
                f"| {item} | {int(old_item.get('count', 0))} | {int(new_item.get('count', 0))} | "
                f"{old_last:.6f} | {new_last:.6f} | {(new_last - old_last):.6f} |\n"
            )

        fp.write("\n## New Unique CLI Lines\n")
        if not cli_unique:
            fp.write("- no unique CLI lines in new session\n")
        else:
            for line in cli_unique[-10:]:
                fp.write(f"- {line}\n")
    return out_path


def compare_latest(sessions_root: Path) -> Path:
    old_dir, new_dir = pick_latest_two_sessions(sessions_root)
    return compare_sessions(old_dir, new_dir, new_dir / f"compare_vs_{old_dir.name}.md")
