from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agent_workbench.core.autoflow_service import resume_autoflow, run_autoflow
from agent_workbench.core.task_spec import load_task_spec


class AutoflowServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / "runtime" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="awb_autoflow_", dir=temp_root))
        (self.temp_dir / ".continue").mkdir(parents=True, exist_ok=True)
        self.runtime_root = self.temp_dir / "runtime"
        self.evidence_root = self.temp_dir / "evidence" / "sessions"
        self.generated_root = self.temp_dir / "generated"
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        self.evidence_root.mkdir(parents=True, exist_ok=True)
        self.generated_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _cfg(self) -> dict:
        return {
            "config_path": str(self.temp_dir / "agent_workbench.yaml"),
            "project_root_path": self.temp_dir,
            "project": {
                "name": "serial",
            },
            "outputs": {
                "runtime_root_path": self.runtime_root,
                "evidence_root_path": self.evidence_root,
                "generated_root_path": self.generated_root,
                "requests_root_path": self.generated_root / "requests",
                "continue_runtime_root_path": self.runtime_root / "continue",
            },
            "agent": {
                "state_path": self.runtime_root / "agent_state.json",
                "autoflow_state_path": self.runtime_root / "autoflow_state.json",
                "default_profile": "balanced_local",
                "profiles": {
                    "balanced_local": {
                        "max_pack_words": 550,
                        "max_fact_items": 12,
                        "max_cli_tail_lines": 6,
                        "max_failed_assertions_shown": 3,
                        "max_extra_reads": 2,
                        "max_edit_files": 2,
                        "require_fact_citations": True,
                        "prefer_ascii_runtime_artifacts": True,
                        "session_pick_strategy": "latest_failed_then_latest_pass",
                    }
                },
            },
            "uart": {
                "enabled": True,
                "port": "COM3",
                "baudrate": 115200,
                "ready_banner": "STM32 UART CLI ready.",
                "prompt": "cli>",
                "probe_commands": ["help", "status"],
                "help_rows": [{"command": "help", "detail": "help text"}],
            },
        }

    def test_autoflow_timer_goal_generates_task_breakdown_and_state(self) -> None:
        cfg = self._cfg()

        start_path = run_autoflow(cfg, goal="使用 TIM3 定时器让 RED LED(PB0) 以约 1 Hz 闪烁")

        self.assertTrue(start_path.exists())
        state = json.loads((self.runtime_root / "autoflow_state.json").read_text(encoding="utf-8"))
        task_path = Path(state["task_path"])
        breakdown_path = Path(state["generated_files"]["task_breakdown"])
        self.assertTrue(task_path.exists())
        self.assertTrue(breakdown_path.exists())
        task = load_task_spec(task_path)
        self.assertIn("Core/Inc/stm32f1xx_hal_conf.h", task["scope"]["include"])
        self.assertIn("Core/Src/main.c", task["implementation"]["edit_candidates"])
        self.assertEqual(task["observability"]["manual_checks"][0]["name"], "red_led_blinks")
        payload = json.loads(breakdown_path.with_suffix(".json").read_text(encoding="utf-8"))
        self.assertEqual(payload["stage_map"]["analyze"], ["S1", "S2"])
        self.assertEqual(payload["stage_map"]["implement"], ["S3", "S4"])
        self.assertEqual(payload["stage_map"]["verify"], ["S5", "S6"])
        self.assertEqual(state["stage"], "analyze")
        self.assertEqual(state["current_subtasks"], ["S1", "S2"])
        self.assertEqual(state["latest_session"], "")
        text = start_path.read_text(encoding="utf-8")
        self.assertIn("autoflow --resume", text)
        self.assertIn("current_stage: `analyze`", text)

    def test_autoflow_resume_syncs_with_agent_state(self) -> None:
        cfg = self._cfg()

        run_autoflow(cfg, goal="使用 TIM3 定时器让 RED LED(PB0) 以约 1 Hz 闪烁")
        agent_state_path = self.runtime_root / "agent_state.json"
        agent_state = json.loads(agent_state_path.read_text(encoding="utf-8"))
        agent_state["stage"] = "implement"
        agent_state["current_subtasks"] = ["S3", "S4"]
        agent_state["next_commands"] = ["agent_workbench.bat build", "agent_workbench.bat context --mode feature --stage verify"]
        agent_state_path.write_text(json.dumps(agent_state, ensure_ascii=False, indent=2), encoding="utf-8")

        start_path = resume_autoflow(cfg)

        state = json.loads((self.runtime_root / "autoflow_state.json").read_text(encoding="utf-8"))
        self.assertTrue(start_path.exists())
        self.assertEqual(state["stage"], "implement")
        self.assertEqual(state["next_stage"], "verify")
        self.assertEqual(state["current_subtasks"], ["S3", "S4"])

    def test_autoflow_direct_cli_goal_becomes_verify_only_path(self) -> None:
        cfg = self._cfg()

        start_path = run_autoflow(cfg, goal="请通过 CLI 点亮红灯")

        self.assertTrue(start_path.exists())
        state = json.loads((self.runtime_root / "autoflow_state.json").read_text(encoding="utf-8"))
        task_path = Path(state["task_path"])
        task = load_task_spec(task_path)
        self.assertEqual(task["id"], "autoflow_cli_red_on")
        self.assertEqual(task["implementation"]["edit_candidates"], [])
        self.assertEqual(task["implementation"]["max_edit_files"], 0)
        self.assertEqual(task["verify"]["cli_commands"], ["red on", "status"])
        self.assertEqual(state["stage"], "analyze")
        self.assertEqual(state["next_stage"], "verify")
        self.assertEqual(state["stage_sequence"], ["analyze", "verify"])
        start_text = start_path.read_text(encoding="utf-8")
        self.assertIn("stage_sequence: `analyze, verify`", start_text)
