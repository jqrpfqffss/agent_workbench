from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from agent_workbench.core.planner import Planner


class PlannerE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / "runtime" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="awb_planner_e2e_", dir=temp_root))
        (self.temp_dir / "Core" / "Src").mkdir(parents=True, exist_ok=True)
        (self.temp_dir / "Core" / "Inc").mkdir(parents=True, exist_ok=True)
        (self.temp_dir / "Core" / "Src" / "main.c").write_text(
            "/* USER CODE BEGIN PV */\n/* USER CODE END PV */\n"
            "/* USER CODE BEGIN PFP */\n/* USER CODE END PFP */\n"
            "void MX_GPIO_Init(void) {}\n"
            "void MX_USART2_UART_Init(void) {}\n"
            "/* USER CODE BEGIN 2 */\n/* USER CODE END 2 */\n"
            "/* USER CODE BEGIN 4 */\n/* USER CODE END 4 */\n",
            encoding="utf-8",
        )
        (self.temp_dir / "Core" / "Inc" / "main.h").write_text(
            "/* USER CODE BEGIN EFP */\n/* USER CODE END EFP */\n",
            encoding="utf-8",
        )
        (self.temp_dir / "Core" / "Src" / "cli.c").write_text("void cli(void) {}\n", encoding="utf-8")
        (self.temp_dir / "Core" / "Src" / "app_cli_commands.c").write_text(
            'static const CliCommand app_cli_commands[] = {\n'
            '  { "help", "List commands", "help", AppCli_Help },\n'
            '  { "status", "Show status", "status", AppCli_Status },\n'
            '};\n',
            encoding="utf-8",
        )
        (self.temp_dir / "Core" / "Inc" / "app_cli_commands.h").write_text("#pragma once\n", encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _cfg(self) -> dict:
        repo_root = Path(__file__).resolve().parents[2]
        return {
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

    def test_pwm_request_extracts_all_parameters_and_hardware_context(self) -> None:
        plan = Planner(self._cfg()).plan("给STM32添加PWM蜂鸣器，1kHz，PA8，50%占空比")

        self.assertEqual(plan["parameter_extractions"]["frequency_hz"], 1000)
        self.assertEqual(plan["parameter_extractions"]["pin"], "PA8")
        self.assertEqual(plan["parameter_extractions"]["duty_percent"], 50)
        self.assertEqual(plan["hardware_context"]["timer_config"]["prescaler"], 71)
        self.assertEqual(plan["hardware_context"]["timer_config"]["period"], 999)
        self.assertEqual(plan["hardware_context"]["timer_config"]["ccr"], 500)
        self.assertEqual(plan["hardware_context"]["pin_mapping"]["recommended"], "TIM1_CH1")

        edit_steps = [item for item in plan["steps"] if item["action_type"] == "edit_file"]
        self.assertGreater(len(edit_steps), 0)
        self.assertTrue(any(hint["type"] == "add_function" for hint in edit_steps[0]["code_change_hints"]))

    def test_cli_command_request_extracts_command_name(self) -> None:
        plan = Planner(self._cfg()).plan("添加一个CLI命令uptime显示运行时间")

        self.assertEqual(plan["template_id"], "uart_cli_command")
        self.assertEqual(plan["parameter_extractions"]["cli_command_name"], "uptime")

    def test_existing_timer_handle_creates_warning_note(self) -> None:
        main_c_path = self.temp_dir / "Core" / "Src" / "main.c"
        main_c_path.write_text(
            "TIM_HandleTypeDef htim1;\n"
            "/* USER CODE BEGIN PV */\n/* USER CODE END PV */\n"
            "/* USER CODE BEGIN PFP */\n/* USER CODE END PFP */\n"
            "void MX_GPIO_Init(void) {}\n"
            "void MX_USART2_UART_Init(void) {}\n"
            "/* USER CODE BEGIN 2 */\n/* USER CODE END 2 */\n"
            "/* USER CODE BEGIN 4 */\n/* USER CODE END 4 */\n",
            encoding="utf-8",
        )

        plan = Planner(self._cfg()).plan("给STM32添加PWM蜂鸣器，1kHz，PA8")

        self.assertTrue(any("htim1" in note for note in plan.get("notes", [])))
