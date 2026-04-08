from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from agent_workbench.core.task_spec import load_task_spec


class TaskSpecTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / "runtime" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="awb_task_", dir=temp_root))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_task_defaults_are_filled(self) -> None:
        task_path = self.temp_dir / "task.yaml"
        task_path.write_text(
            "id: demo\n"
            "mode: feature\n"
            "goal: test goal\n"
            "scope: {}\n"
            "acceptance: {}\n"
            "observability: {}\n"
            "verify: {}\n",
            encoding="utf-8",
        )
        task = load_task_spec(task_path)
        self.assertEqual(task["id"], "demo")
        self.assertEqual(task["acceptance"]["blackbox"], [])
        self.assertEqual(task["verify"]["sequence"], ["doctor", "build", "test", "debug"])
        self.assertEqual(task["verify"]["cli_commands"], [])
        self.assertEqual(task["implementation"]["read_candidates"], [])
        self.assertEqual(task["implementation"]["edit_candidates"], [])
        self.assertEqual(task["implementation"]["stable_strings"], [])
        self.assertEqual(task["implementation"]["max_edit_files"], 2)
