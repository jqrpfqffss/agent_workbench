from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - env specific
    raise RuntimeError(
        "PyYAML is required. Run agent_workbench\\bin\\setup.bat first."
    ) from exc


def normalize_task_spec(data: dict[str, Any] | None, *, strict: bool = True) -> dict[str, Any]:
    data = dict(data or {})
    required = ["id", "mode", "goal", "scope", "acceptance", "observability", "verify"]
    missing = [key for key in required if key not in data]
    if missing:
        if strict:
            raise RuntimeError(f"task missing required fields: {', '.join(missing)}")
        data.setdefault("id", "ad_hoc_task")
        data.setdefault("mode", "feature")
        data.setdefault("goal", "")
        data.setdefault("scope", {})
        data.setdefault("acceptance", {})
        data.setdefault("observability", {})
        data.setdefault("verify", {})

    data.setdefault("scope", {})
    data["scope"].setdefault("include", [])
    data["scope"].setdefault("exclude", [])
    data.setdefault("acceptance", {})
    data["acceptance"].setdefault("blackbox", [])
    data["acceptance"].setdefault("unit", [])
    data.setdefault("observability", {})
    data["observability"].setdefault("notes", [])
    data.setdefault("verify", {})
    data["verify"].setdefault("sequence", ["doctor", "build", "test", "debug"])
    data["verify"].setdefault("cli_commands", [])
    data.setdefault("implementation", {})
    include_items = [str(item).strip() for item in data["scope"].get("include", []) if str(item).strip()]
    note_items = [str(item).strip() for item in data["observability"].get("notes", []) if str(item).strip()]
    impl = data["implementation"]
    impl.setdefault("read_candidates", include_items[:3] or include_items[:])
    impl.setdefault("edit_candidates", include_items[:])
    impl.setdefault("stable_strings", note_items[:])
    impl["read_candidates"] = [str(item).strip() for item in impl.get("read_candidates", []) if str(item).strip()]
    impl["edit_candidates"] = [str(item).strip() for item in impl.get("edit_candidates", []) if str(item).strip()]
    impl["stable_strings"] = [str(item).strip() for item in impl.get("stable_strings", []) if str(item).strip()]
    default_max_edit = min(len(impl.get("edit_candidates", [])) or len(include_items) or 2, 2)
    impl.setdefault("max_edit_files", max(default_max_edit, 1))
    return data


def load_task_spec(task_path: Path, *, strict: bool = True) -> dict[str, Any]:
    if not task_path.exists():
        raise FileNotFoundError(f"task not found: {task_path}")
    data = yaml.safe_load(task_path.read_text(encoding="utf-8")) or {}
    return normalize_task_spec(data, strict=strict)
