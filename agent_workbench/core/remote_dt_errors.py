from __future__ import annotations

from typing import Any


class RemoteDtConfigError(RuntimeError):
    """Raised when remote_dt configuration is disabled or incomplete."""


class RemoteDtCommandError(RuntimeError):
    """Raised when a remote DT command cannot complete successfully."""


class RemoteDtTimeoutError(RemoteDtCommandError):
    """Raised when a remote DT command exceeds its timeout."""


def error_to_dict(exc: BaseException, *, step: str = "", kind: str | None = None) -> dict[str, Any]:
    return {
        "step": step,
        "kind": kind or exc.__class__.__name__,
        "message": str(exc),
        "raw": str(exc),
    }
