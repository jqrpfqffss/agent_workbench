from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agent_workbench.core.vscode_service import write_vscode_tasks


class VscodeServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / "runtime" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="awb_vscode_", dir=temp_root))
        (self.temp_dir / "agent_workbench" / "bin").mkdir(parents=True, exist_ok=True)
        (self.temp_dir / "agent_workbench" / "tasks").mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _cfg(self) -> dict:
        repo_root = Path(__file__).resolve().parents[2]
        return {
            "project_root_path": self.temp_dir,
            "agent_workbench_root_path": repo_root / "agent_workbench",
            "vscode": {
                "tasks_file_path": self.temp_dir / ".vscode" / "tasks.json",
            },
            "project": {
                "name": "demo",
                "source_dirs": ["Core", "Drivers"],
                "build_dir_path": self.temp_dir / "build",
            },
        }

    def test_generated_tasks_expose_integration_install_task(self) -> None:
        cfg = self._cfg()
        tasks_path = write_vscode_tasks(cfg)

        self.assertTrue(tasks_path.exists())
        payload = json.loads(tasks_path.read_text(encoding="utf-8"))
        commands = [item["command"] for item in payload["tasks"]]
        self.assertIn('cmd /c ".\\agent_workbench.bat integration install opencode"', commands)
        self.assertIn('cmd /c ".\\agent_workbench.bat scan-project --json"', commands)
        self.assertTrue(
            any(
                command.startswith('cmd /c ".\\agent_workbench.bat verify current --task ')
                and "cli_automation_regression.yaml" in command
                for command in commands
            )
        )
        self.assertIn('cmd /c ".\\agent_workbench.bat diag exec"', commands)
        self.assertTrue(all(command.startswith('cmd /c ".\\') for command in commands))
