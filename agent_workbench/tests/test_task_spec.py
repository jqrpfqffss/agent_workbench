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
        self.assertTrue(task["decomposition"]["enabled"])
        self.assertEqual(task["decomposition"]["subtasks"], [])

    def test_legacy_fields_and_manual_observation_are_normalized(self) -> None:
        task_path = self.temp_dir / "legacy.yaml"
        task_path.write_text(
            "id: timer_led_blink\n"
            "mode: feature\n"
            "goal: blink red led\n"
            "scope:\n"
            "  include: [Core/Src/main.c]\n"
            "  exclude: []\n"
            "acceptance:\n"
            "  blackbox:\n"
            "    - name: cli_ok\n"
            "      type: cli_ready\n"
            "      needle: STM32 UART CLI ready.\n"
            "    - name: red_led_blinks\n"
            "      type: manual_observation\n"
            "      notes: verify blinking on hardware\n"
            "observability: {}\n"
            "verify: {}\n"
            "implementation:\n"
            "  allowed_edits:\n"
            "    - file: Core/Src/main.c\n"
            "      changes: [demo]\n",
            encoding="utf-8",
        )

        task = load_task_spec(task_path)

        self.assertEqual(task["implementation"]["edit_candidates"], ["Core/Src/main.c"])
        self.assertEqual(task["implementation"]["read_candidates"], ["Core/Src/main.c"])
        self.assertEqual(len(task["acceptance"]["blackbox"]), 1)
        self.assertEqual(task["acceptance"]["blackbox"][0]["name"], "cli_ok")
        self.assertEqual(len(task["observability"]["manual_checks"]), 1)
        self.assertEqual(task["observability"]["manual_checks"][0]["name"], "red_led_blinks")
