from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agent_workbench.core.planner import Planner


class PlannerRegressionSuiteTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / "runtime" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="awb_planner_matrix_", dir=temp_root))
        (self.temp_dir / "Core" / "Src").mkdir(parents=True, exist_ok=True)
        (self.temp_dir / "Core" / "Inc").mkdir(parents=True, exist_ok=True)
        (self.temp_dir / "Core" / "Src" / "main.c").write_text(
            "void MX_GPIO_Init(void) {}\n"
            "void MX_USART2_UART_Init(void) {}\n"
            "void MX_ADC1_Init(void) {}\n"
            "void MX_I2C1_Init(void) {}\n"
            "void MX_SPI1_Init(void) {}\n",
            encoding="utf-8",
        )
        (self.temp_dir / "Core" / "Inc" / "main.h").write_text("#pragma once\n", encoding="utf-8")
        (self.temp_dir / "Core" / "Src" / "cli.c").write_text("void cli(void) {}\n", encoding="utf-8")
        (self.temp_dir / "Core" / "Src" / "app_cli_commands.c").write_text("void app_cli(void) {}\n", encoding="utf-8")
        (self.temp_dir / "Core" / "Inc" / "app_cli_commands.h").write_text("#pragma once\n", encoding="utf-8")
        (self.temp_dir / "Core" / "Src" / "stm32f1xx_it.c").write_text("void EXTI0_IRQHandler(void) {}\n", encoding="utf-8")
        (self.temp_dir / "Core" / "Inc" / "stm32f1xx_it.h").write_text("#pragma once\n", encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _cfg(self) -> dict:
        repo_root = Path(__file__).resolve().parents[2]
        return {
            "project": {
                "name": "serial",
                "source_dirs": ["Core"],
            },
            "project_root_path": self.temp_dir,
            "agent_workbench_root_path": repo_root / "agent_workbench",
            "planner": {
                "templates_dir_path": repo_root / "agent_workbench" / "templates" / "task_templates",
                "max_total_steps": 15,
            },
            "uart": {
                "enabled": True,
                "ready_banner": "STM32 UART CLI ready.",
                "prompt": "cli>",
                "probe_commands": ["help", "status"],
                "help_rows": [{"command": "help"}, {"command": "status"}],
            },
        }

    def test_regression_matrix_covers_common_request_categories(self) -> None:
        cfg = self._cfg()
        planner = Planner(cfg)
        cases_path = Path(__file__).resolve().parent / "data" / "planner_regression_cases.json"
        cases = json.loads(cases_path.read_text(encoding="utf-8"))

        mismatches: list[str] = []
        for item in cases:
            plan = planner.plan(str(item["request"]))
            if plan["template_id"] != item["template_id"]:
                mismatches.append(f"{item['request']} -> {plan['template_id']} (expected {item['template_id']})")

        self.assertEqual(mismatches, [], "\n".join(mismatches))
