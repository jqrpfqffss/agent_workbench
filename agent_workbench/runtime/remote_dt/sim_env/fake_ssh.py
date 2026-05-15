from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path


def _remote_path(path_text: str) -> Path:
    root = Path(os.environ.get("REMOTE_DT_SIM_ROOT", Path(__file__).resolve().parent / "remote_root")).resolve()
    return root / path_text.strip("/").replace("/", os.sep)


def _step_from_command(command: str) -> str:
    for step in ("build", "execute", "coverage"):
        if f"dt_{step}.log" in command:
            return step
    return "unknown"


def _project_dir_from_command(command: str) -> str:
    for line in command.splitlines():
        line = line.strip()
        if line.startswith("cd "):
            value = line[3:].strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                return value[1:-1]
            return value
    return "/remote/project"


def _write_step_outputs(step: str, command: str, exit_code: int) -> None:
    project_dir = _project_dir_from_command(command)
    project = _remote_path(project_dir)
    log_dir = project / ".agent_workbench_remote_dt" / "logs"
    result_dir = project / ".agent_workbench_remote_dt" / "results"
    coverage_dir = project / "coverage"
    log_dir.mkdir(parents=True, exist_ok=True)
    result_dir.mkdir(parents=True, exist_ok=True)

    if exit_code:
        log_text = (
            "main.c:12:5: error: simulated compile failure\n"
            "collect2: error: ld returned 1 exit status\n"
            "FAILED expected true actual false\n"
        )
    elif step == "coverage":
        coverage_dir.mkdir(parents=True, exist_ok=True)
        (coverage_dir / "index.html").write_text("<html>coverage ok</html>\n", encoding="utf-8")
        log_text = "coverage generated\n"
    elif step == "execute":
        log_text = "DT execute passed\n"
    else:
        log_text = "DT build passed\n"

    start_ts = int(time.time())
    end_ts = start_ts + 1
    (log_dir / f"dt_{step}.log").write_text(log_text, encoding="utf-8")
    (result_dir / f"dt_{step}_result.json").write_text(
        json.dumps({"step": step, "exit_code": exit_code, "start_ts": start_ts, "end_ts": end_ts}),
        encoding="utf-8",
    )


def main() -> int:
    command = sys.argv[-1] if len(sys.argv) > 1 else ""
    step = _step_from_command(command)
    exit_code = 2 if "fail_build.sh" in command or "fail_execute.sh" in command or "fail_coverage.sh" in command else 0
    _write_step_outputs(step, command, exit_code)
    calls_path = os.environ.get("REMOTE_DT_SIM_CALLS", str(Path(__file__).resolve().parent / "sim_calls.log"))
    if calls_path:
        with open(calls_path, "a", encoding="utf-8") as fp:
            fp.write(f"ssh:{step}:exit={exit_code}\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
