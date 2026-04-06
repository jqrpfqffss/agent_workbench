from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from pathlib import Path

from .utils import ensure_dir, read_text, utc_now_iso


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
    old_warn = sum(1 for line in old_uart if any(tag in line.lower() for tag in ("warn", "error", "fault", "panic", "assert")))
    new_warn = sum(1 for line in new_uart if any(tag in line.lower() for tag in ("warn", "error", "fault", "panic", "assert")))
    old_monitor = _monitor_stats(old_dir / "monitor_samples.csv")
    new_monitor = _monitor_stats(new_dir / "monitor_samples.csv")
    items = sorted(set(old_monitor) | set(new_monitor))

    with out_path.open("w", encoding="utf-8") as fp:
        fp.write("# Session Compare Report\n\n")
        fp.write(f"- generated_at: {utc_now_iso()}\n")
        fp.write(f"- old_session: `{old_dir}`\n")
        fp.write(f"- new_session: `{new_dir}`\n\n")
        fp.write("## UART Metrics\n")
        fp.write("| metric | old | new | delta |\n")
        fp.write("|---|---:|---:|---:|\n")
        fp.write(f"| lines | {len(old_uart)} | {len(new_uart)} | {len(new_uart) - len(old_uart)} |\n")
        fp.write(f"| warn_like | {old_warn} | {new_warn} | {new_warn - old_warn} |\n\n")
        fp.write("## Monitor Metrics\n")
        fp.write("| item | old_count | new_count | old_last | new_last | delta_last |\n")
        fp.write("|---|---:|---:|---:|---:|---:|\n")
        for item in items:
            old_item = old_monitor.get(item, {})
            new_item = new_monitor.get(item, {})
            old_last = old_item.get("last", 0.0)
            new_last = new_item.get("last", 0.0)
            fp.write(
                f"| {item} | {int(old_item.get('count', 0))} | {int(new_item.get('count', 0))} | "
                f"{old_last:.6f} | {new_last:.6f} | {(new_last - old_last):.6f} |\n"
            )
        fp.write("\n## New Unique UART Lines (tail)\n")
        unique_lines = [line for line in new_uart if line not in set(old_uart)]
        if not unique_lines:
            fp.write("- no unique lines in new session tail\n")
        else:
            fp.write("```text\n")
            fp.write("\n".join(unique_lines[-20:]))
            fp.write("\n```\n")
    return out_path


def compare_latest(sessions_root: Path) -> Path:
    old_dir, new_dir = pick_latest_two_sessions(sessions_root)
    return compare_sessions(old_dir, new_dir, new_dir / f"compare_vs_{old_dir.name}.md")
