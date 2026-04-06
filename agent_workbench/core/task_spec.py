from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - env specific
    raise RuntimeError(
        "PyYAML is required. Run agent_workbench\\bin\\setup.bat first."
    ) from exc


def load_task_spec(task_path: Path) -> dict[str, Any]:
    if not task_path.exists():
        raise FileNotFoundError(f"task not found: {task_path}")
    data = yaml.safe_load(task_path.read_text(encoding="utf-8")) or {}
    required = ["id", "mode", "goal", "scope", "acceptance", "observability", "verify"]
    missing = [key for key in required if key not in data]
    if missing:
        raise RuntimeError(f"task missing required fields: {', '.join(missing)}")

    data.setdefault("scope", {})
    data["scope"].setdefault("include", [])
    data["scope"].setdefault("exclude", [])
    data.setdefault("acceptance", {})
    data["acceptance"].setdefault("blackbox", [])
    data["acceptance"].setdefault("unit", [])
    data.setdefault("observability", {})
    data.setdefault("verify", {})
    data["verify"].setdefault("sequence", ["doctor", "build", "test", "debug"])
    data["verify"].setdefault("cli_commands", [])
    return data
