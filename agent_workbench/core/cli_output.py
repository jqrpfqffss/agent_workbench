from __future__ import annotations

import json
from typing import Any

from .utils import utc_now_iso


def status_from_exit_code(exit_code: int, *, blocked: bool = False) -> str:
    if blocked:
        return "blocked"
    return "pass" if int(exit_code) == 0 else "fail"


def build_result_payload(
    command: str,
    exit_code: int,
    *,
    status: str | None = None,
    summary: str = "",
    details: dict[str, Any] | None = None,
    artifacts: dict[str, Any] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "command": command,
        "exit_code": int(exit_code),
        "status": status or status_from_exit_code(exit_code),
        "summary": summary,
        "details": details or {},
        "artifacts": artifacts or {},
        "timestamp": utc_now_iso(),
    }
    for key, value in extra.items():
        if value is None:
            continue
        payload[key] = value
    return payload


def print_result_payload(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False))
