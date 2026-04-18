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
        (self.temp_dir / ".continue").mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generated_tasks_follow_default_profile_without_hardcoding(self) -> None:
        cfg = {
            "project_root_path": self.temp_dir,
            "agent_workbench_root_path": self.temp_dir / "agent_workbench",
            "outputs": {
                "continue_runtime_root_path": self.temp_dir / "agent_workbench" / "runtime" / "continue",
            },
            "vscode": {
                "tasks_file_path": self.temp_dir / ".vscode" / "tasks.json",
            },
            "agent": {
                "default_profile": "deepseek16k",
            },
        }

        tasks_path = write_vscode_tasks(cfg)

        self.assertTrue(tasks_path.exists())
        payload = json.loads(tasks_path.read_text(encoding="utf-8"))
        commands = [item["command"] for item in payload["tasks"]]
        self.assertIn('cmd /c ".\\agent_workbench.bat context --mode debug --stage analyze"', commands)
        self.assertIn(
            'cmd /c ".\\agent_workbench.bat context --mode feature --stage implement --task agent_workbench/tasks/cli_automation_regression.yaml"',
            commands,
        )
        self.assertIn(
            'cmd /c ".\\agent_workbench.bat verify current --task agent_workbench/tasks/cli_automation_regression.yaml"',
            commands,
        )
        self.assertIn('cmd /c ".\\agent_workbench.bat diag exec"', commands)
        self.assertTrue(all("--profile" not in command for command in commands if " context " in f" {command} "))
        self.assertTrue(all(command.startswith('cmd /c ".\\') for command in commands))

        runtime_prompt = self.temp_dir / "agent_workbench" / "runtime" / "continue" / "local_model_debug_analyze.md"
        continue_prompt = self.temp_dir / ".continue" / "prompts" / "local_model_debug_analyze.md"
        self.assertTrue(runtime_prompt.exists())
        self.assertTrue(continue_prompt.exists())
        self.assertIn("deepseek16k", runtime_prompt.read_text(encoding="utf-8"))
