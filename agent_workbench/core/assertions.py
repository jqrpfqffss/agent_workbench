from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .utils import append_jsonl, read_text, utc_now_iso


def _monitor_last_value(csv_path: Path, item_name: str) -> float | None:
    if not csv_path.exists():
        return None
    last_value = None
    with csv_path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            if row.get("item") != item_name or row.get("ok", "0") != "1":
                continue
            try:
                last_value = float(row.get("value", "0"))
            except ValueError:
                continue
    return last_value


def _transcript_rx_text(text: str) -> str:
    rx_lines: list[str] = []
    for line in text.splitlines():
        marker = "] < "
        index = line.find(marker)
        if index >= 0:
            rx_lines.append(line[index + len(marker):])
    return "\n".join(rx_lines)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _get_nested(data: dict[str, Any] | None, field_path: str) -> Any:
    if not data:
        return None
    current: Any = data
    for part in field_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def evaluate_assertions(session_dir: Path, assertions: list[dict[str, Any]]) -> tuple[int, int, int]:
    out_path = session_dir / "assertions.jsonl"
    passed = 0
    failed = 0
    skipped = 0
    uart_text = read_text(session_dir / "uart.log")
    cli_text = read_text(session_dir / "cli_transcript.log")
    cli_rx_text = _transcript_rx_text(cli_text)
    cli_diag = _read_json(session_dir / "cli_diag.json")
    uart_available = (session_dir / "uart.log").exists()
    cli_available = (session_dir / "cli_transcript.log").exists()
    monitor_available = (session_dir / "monitor_samples.csv").exists()

    for assertion in assertions:
        kind = assertion.get("type", "")
        name = assertion.get("name", kind or "unnamed")
        ok = False
        status = "fail"
        detail = ""

        if kind == "file_exists":
            target = Path(assertion.get("path", ""))
            if not target.is_absolute():
                target = session_dir / target
            ok = target.exists()
            detail = str(target)
        elif kind == "uart_contains":
            needle = assertion.get("needle", "")
            if not uart_available:
                status = "skip"
                detail = "uart.log missing"
            else:
                ok = needle in uart_text
                detail = needle
        elif kind == "uart_not_contains":
            needle = assertion.get("needle", "")
            if not uart_available:
                status = "skip"
                detail = "uart.log missing"
            else:
                ok = needle not in uart_text
                detail = needle
        elif kind == "cli_contains":
            needle = assertion.get("needle", "")
            if not cli_available:
                status = "skip"
                detail = "cli_transcript.log missing"
            else:
                ok = needle in cli_rx_text
                detail = needle
        elif kind == "cli_not_contains":
            needle = assertion.get("needle", "")
            if not cli_available:
                status = "skip"
                detail = "cli_transcript.log missing"
            else:
                ok = needle not in cli_rx_text
                detail = needle
        elif kind == "cli_ready":
            needle = assertion.get("needle", "cli ready")
            if not cli_available:
                status = "skip"
                detail = "cli_transcript.log missing"
            else:
                ok = needle in cli_rx_text
                detail = needle
        elif kind == "cli_no_timeout":
            if not cli_available:
                status = "skip"
                detail = "cli_transcript.log missing"
            else:
                ok = "[timeout]" not in cli_rx_text
                detail = "no [timeout] expected"
        elif kind == "cli_prompt_seen":
            needle = assertion.get("needle", "cli>")
            if not cli_available:
                status = "skip"
                detail = "cli_transcript.log missing"
            else:
                ok = needle in cli_rx_text
                detail = needle
        elif kind == "cli_diag_field_between":
            field = str(assertion.get("field", "")).strip()
            min_value = float(assertion.get("min", 0))
            max_value = float(assertion.get("max", 0))
            if cli_diag is None:
                status = "skip"
                detail = "cli_diag.json missing"
            else:
                value = _get_nested(cli_diag, field)
                try:
                    numeric = float(value)
                except (TypeError, ValueError):
                    numeric = None
                ok = numeric is not None and min_value <= numeric <= max_value
                detail = f"field={field} value={value} range=[{min_value},{max_value}]"
        elif kind == "monitor_last_between":
            item = assertion.get("item", "")
            min_value = float(assertion.get("min", 0))
            max_value = float(assertion.get("max", 0))
            if not monitor_available:
                status = "skip"
                detail = "monitor_samples.csv missing"
            else:
                last_value = _monitor_last_value(session_dir / "monitor_samples.csv", item)
                ok = last_value is not None and min_value <= last_value <= max_value
                detail = f"item={item} last={last_value} range=[{min_value},{max_value}]"
        else:
            detail = f"unsupported assertion type: {kind}"

        if status != "skip":
            status = "pass" if ok else "fail"
        append_jsonl(
            out_path,
            {
                "ts": utc_now_iso(),
                "name": name,
                "type": kind,
                "ok": ok,
                "status": status,
                "detail": detail,
            },
        )
        if status == "pass":
            passed += 1
        elif status == "skip":
            skipped += 1
        else:
            failed += 1

    return passed, failed, skipped
