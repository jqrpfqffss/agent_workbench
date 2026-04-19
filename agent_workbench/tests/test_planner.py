from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from agent_workbench.core.planner import Planner


class PlannerTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / "runtime" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="awb_planner_", dir=temp_root))
        (self.temp_dir / "Core" / "Src").mkdir(parents=True, exist_ok=True)
        (self.temp_dir / "Core" / "Inc").mkdir(parents=True, exist_ok=True)
        (self.temp_dir / "Core" / "Src" / "main.c").write_text(
            "void MX_GPIO_Init(void) {}\n"
            "void MX_USART2_UART_Init(void) {}\n",
            encoding="utf-8",
        )
        (self.temp_dir / "Core" / "Inc" / "main.h").write_text("#pragma once\n", encoding="utf-8")
        (self.temp_dir / "Core" / "Src" / "cli.c").write_text("void cli(void) {}\n", encoding="utf-8")
        (self.temp_dir / "Core" / "Src" / "app_cli_commands.c").write_text("void app_cli(void) {}\n", encoding="utf-8")
        (self.temp_dir / "Core" / "Inc" / "app_cli_commands.h").write_text("#pragma once\n", encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_pwm_request_matches_timer_pwm_template(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        cfg = {
            "project": {"name": "serial", "source_dirs": ["Core"]},
            "project_root_path": self.temp_dir,
            "agent_workbench_root_path": repo_root / "agent_workbench",
            "planner": {
                "templates_dir_path": repo_root / "agent_workbench" / "templates" / "task_templates",
                "hardware_knowledge_dir_path": repo_root / "agent_workbench" / "templates" / "hardware_knowledge",
                "max_total_steps": 15,
            },
            "continue": {"rules_dir_path": self.temp_dir / ".continue" / "rules"},
            "uart": {
                "enabled": True,
                "ready_banner": "STM32 UART CLI ready.",
                "prompt": "cli>",
                "probe_commands": ["help", "status"],
                "help_rows": [{"command": "help"}, {"command": "status"}],
            },
            "outputs": {
                "runtime_root_path": self.temp_dir / "agent_workbench" / "runtime",
                "evidence_root_path": self.temp_dir / "agent_workbench" / "evidence",
                "generated_root_path": self.temp_dir / "agent_workbench" / "generated",
            },
        }

        plan = Planner(cfg).plan("给STM32添加PWM蜂鸣器控制，频率1kHz，PA8引脚")

        self.assertEqual(plan["template_id"], "timer_pwm")
        self.assertIn("Core/Src/main.c", plan["constraints"]["allowed_edit_files"])
        self.assertTrue(any(step["action_type"] == "shell" and "build --json" in step["command"] for step in plan["steps"]))
        self.assertTrue(any(step.get("requires_confirmation") for step in plan["steps"] if step["action_type"] == "shell"))
