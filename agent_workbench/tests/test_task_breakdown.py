from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agent_workbench.core.task_breakdown import derive_task_breakdown, write_task_breakdown
from agent_workbench.core.task_spec import load_task_spec


class TaskBreakdownTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / "runtime" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="awb_breakdown_", dir=temp_root))
        self.generated_root = self.temp_dir / "generated"
        self.generated_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _cfg(self) -> dict:
        return {
            "outputs": {
                "generated_root_path": self.generated_root,
            }
        }

    def _task_path(self, extra: str = "") -> Path:
        task_path = self.temp_dir / "task.yaml"
        task_path.write_text(
            "id: timer_led_blink\n"
            "mode: feature\n"
            "goal: blink red led using timer\n"
            "scope:\n"
            "  include: [Core/Src/main.c, Core/Src/stm32f1xx_it.c]\n"
            "  exclude: []\n"
            "acceptance:\n"
            "  blackbox: []\n"
            "  unit: []\n"
            "observability:\n"
            "  notes:\n"
            "    - keep banner stable\n"
            "verify:\n"
            "  sequence: [doctor, build, test, debug]\n"
            "  cli_commands: [help, status]\n"
            "implementation:\n"
            "  read_candidates: [Core/Src/main.c, Core/Src/stm32f1xx_it.c]\n"
            "  edit_candidates: [Core/Src/main.c]\n"
            "  stable_strings: ['STM32 UART CLI ready.']\n"
            "  max_edit_files: 1\n"
            f"{extra}",
            encoding="utf-8",
        )
        return task_path

    def test_feature_breakdown_is_derived_when_missing(self) -> None:
        task = load_task_spec(self._task_path())

        payload = derive_task_breakdown(self._cfg(), task)

        self.assertEqual(payload["task_id"], "timer_led_blink")
        self.assertEqual(payload["stage_map"]["analyze"], ["S1", "S2", "S3"])
        self.assertEqual(payload["stage_map"]["implement"], ["S4", "S5", "S6"])
        self.assertEqual(payload["stage_map"]["verify"], ["S7", "S8"])

    def test_manual_subtasks_override_defaults(self) -> None:
        task = load_task_spec(
            self._task_path(
                extra=
                "decomposition:\n"
                "  subtasks:\n"
                "    - id: S10\n"
                "      stage: analyze\n"
                "      title: inspect timer config\n"
                "      objective: read only timer files\n"
                "      inputs: [Core/Src/main.c]\n"
                "      done_when: timer config is clear\n"
            )
        )

        payload = derive_task_breakdown(self._cfg(), task)

        self.assertEqual([item["id"] for item in payload["subtasks"]], ["S10"])
        self.assertEqual(payload["stage_map"]["analyze"], ["S10"])

    def test_write_task_breakdown_outputs_md_and_json(self) -> None:
        task_path = self._task_path()

        md_path = write_task_breakdown(self._cfg(), task_path)

        json_path = md_path.with_suffix(".json")
        board_path = md_path.with_name("task_board.md")
        progress_path = md_path.with_name("task_progress.json")
        self.assertTrue(md_path.exists())
        self.assertTrue(json_path.exists())
        self.assertTrue(board_path.exists())
        self.assertTrue(progress_path.exists())
        self.assertIn("## Subtasks", md_path.read_text(encoding="utf-8"))
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["task_id"], "timer_led_blink")
        self.assertIn("progress_summary", payload)
