from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - env specific
    raise RuntimeError(
        "PyYAML is required. Run agent_workbench\\bin\\setup.bat first."
    ) from exc


def _dedupe_text(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


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
    data["observability"].setdefault("notes", [])
    data["observability"].setdefault("manual_checks", [])
    data.setdefault("verify", {})
    data["verify"].setdefault("sequence", ["doctor", "build", "test", "debug"])
    data["verify"].setdefault("cli_commands", [])
    data.setdefault("implementation", {})
    data.setdefault("decomposition", {})
    include_items = [str(item).strip() for item in data["scope"].get("include", []) if str(item).strip()]
    note_items = [str(item).strip() for item in data["observability"].get("notes", []) if str(item).strip()]
    impl = data["implementation"]
    decomp = data["decomposition"]
    legacy_allowed = impl.pop("allowed_edits", []) if isinstance(impl.get("allowed_edits", []), list) else []
    if legacy_allowed and not impl.get("edit_candidates"):
        impl["edit_candidates"] = []
        for item in legacy_allowed:
            if isinstance(item, dict):
                file_text = str(item.get("file", "")).strip()
                if file_text:
                    impl["edit_candidates"].append(file_text)
            else:
                text = str(item).strip()
                if text:
                    impl["edit_candidates"].append(text)
    impl.setdefault("read_candidates", include_items[:3] or include_items[:])
    impl.setdefault("edit_candidates", include_items[:])
    impl.setdefault("stable_strings", note_items[:])
    impl["read_candidates"] = _dedupe_text([str(item).strip() for item in impl.get("read_candidates", []) if str(item).strip()])
    impl["edit_candidates"] = _dedupe_text([str(item).strip() for item in impl.get("edit_candidates", []) if str(item).strip()])
    impl["stable_strings"] = _dedupe_text([str(item).strip() for item in impl.get("stable_strings", []) if str(item).strip()])
    if impl["edit_candidates"]:
        for item in impl["edit_candidates"]:
            if item not in impl["read_candidates"]:
                impl["read_candidates"].append(item)
    default_max_edit = min(len(impl.get("edit_candidates", [])) or len(include_items) or 2, 2)
    impl.setdefault("max_edit_files", max(default_max_edit, 1))
    decomp.setdefault("enabled", True)
    decomp.setdefault("subtasks", [])

    normalized_blackbox: list[dict[str, Any]] = []
    manual_checks = data["observability"]["manual_checks"]
    for assertion in data["acceptance"].get("blackbox", []):
        kind = str((assertion or {}).get("type", "")).strip()
        if kind != "manual_observation":
            normalized_blackbox.append(assertion)
            continue
        entry = {
            "name": str(assertion.get("name", "manual_check")).strip() or "manual_check",
            "instructions": str(assertion.get("notes", "")).strip() or "Manual observation required.",
            "source": "acceptance.blackbox.manual_observation",
        }
        manual_checks.append(entry)
    data["acceptance"]["blackbox"] = normalized_blackbox
    data["observability"]["manual_checks"] = [
        item
        for item in manual_checks
        if isinstance(item, dict) and str(item.get("name", "")).strip()
    ]
    return data
