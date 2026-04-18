from __future__ import annotations

from pathlib import Path

try:
    import yaml
except ModuleNotFoundError as exc:
    raise RuntimeError(
        "PyYAML is required. Run agent_workbench\\bin\\setup.bat first."
    ) from exc

from .task_spec import load_task_spec
from .task_breakdown import write_task_breakdown
from .utils import ensure_dir, render_template, run_command, write_json


def generate_tests(cfg: dict, task_path: Path) -> Path:
    task = load_task_spec(task_path)
    out_dir = ensure_dir(cfg["outputs"]["generated_root_path"] / "tasks" / task["id"])
    write_task_breakdown(cfg, task_path)
    impl_cfg = task.get("implementation", {})
    (out_dir / "blackbox_assertions.yaml").write_text(
        yaml.safe_dump({"assertions": task.get("acceptance", {}).get("blackbox", [])}, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )
    acceptance_unit = task.get("acceptance", {}).get("unit", [])
    (out_dir / "unit_test_plan.md").write_text(
        "# Unit Test Plan\n\n"
        f"- task_id: `{task['id']}`\n"
        f"- goal: {task['goal']}\n\n"
        "## Unit Acceptance\n"
        + ("\n".join(f"- {item}" for item in acceptance_unit) or "- no unit acceptance defined\n"),
        encoding="utf-8",
    )
    if acceptance_unit:
        (out_dir / f"{task['id']}_host_test_skeleton.c").write_text(
            "#include <assert.h>\n\n"
            "int main(void) {\n"
            "  /* TODO: fill generated host-side test skeleton. */\n"
            "  assert(1);\n"
            "  return 0;\n"
            "}\n",
            encoding="utf-8",
        )
    (out_dir / "implementation_brief.md").write_text(
        "# Implementation Brief\n\n"
        f"- task_id: `{task['id']}`\n"
        f"- mode: `{task['mode']}`\n"
        f"- goal: {task['goal']}\n"
        f"- include: {', '.join(task.get('scope', {}).get('include', [])) or 'none'}\n"
        f"- exclude: {', '.join(task.get('scope', {}).get('exclude', [])) or 'none'}\n"
        f"- verify: {', '.join(task.get('verify', {}).get('sequence', []))}\n"
        f"- read_candidates: {', '.join(impl_cfg.get('read_candidates', [])) or 'none'}\n"
        f"- edit_candidates: {', '.join(impl_cfg.get('edit_candidates', [])) or 'none'}\n"
        f"- stable_strings: {', '.join(impl_cfg.get('stable_strings', [])) or 'none'}\n"
        f"- max_edit_files: {impl_cfg.get('max_edit_files', 'n/a')}\n",
        encoding="utf-8",
    )
    write_json(out_dir / "task_snapshot.json", task)
    return out_dir


def run_tests(cfg: dict, session_dir: Path | None = None) -> tuple[int, Path]:
    unit_cfg = cfg["checks"].get("unit", {})
    log_path = (session_dir or cfg["outputs"]["runtime_root_path"]) / "unit.log"
    ensure_dir(log_path.parent)
    if not unit_cfg.get("enabled", False):
        log_path.write_text("unit checks disabled by config\n", encoding="utf-8")
        return 0, log_path
    command = render_template(unit_cfg.get("command", ""), cfg["template_values"])
    if not command.strip():
        log_path.write_text("unit checks enabled but command is empty\n", encoding="utf-8")
        return 0, log_path
    return run_command(command, cwd=cfg["project_root_path"], log_path=log_path), log_path
