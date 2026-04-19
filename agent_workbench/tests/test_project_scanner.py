from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from agent_workbench.core.project_scanner import scan_project


class ProjectScannerTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / "runtime" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="awb_scanner_", dir=temp_root))
        (self.temp_dir / "Core" / "Src").mkdir(parents=True, exist_ok=True)
        (self.temp_dir / "Core" / "Inc").mkdir(parents=True, exist_ok=True)
        (self.temp_dir / "agent_workbench" / "runtime" / "test_tmp").mkdir(parents=True, exist_ok=True)
        (self.temp_dir / "Core" / "Src" / "main.c").write_text(
            "TIM_HandleTypeDef htim1;\n"
            "/* USER CODE BEGIN PV */\n/* USER CODE END PV */\n"
            "void MX_GPIO_Init(void) {}\n",
            encoding="utf-8",
        )
        (self.temp_dir / "Core" / "Inc" / "main.h").write_text("#pragma once\n", encoding="utf-8")
        (self.temp_dir / "Core" / "Src" / "app_cli_commands.c").write_text(
            'static const CliCommand app_cli_commands[] = {\n'
            '  { "help", "List commands", "help", AppCli_Help },\n'
            '};\n',
            encoding="utf-8",
        )
        (self.temp_dir / "agent_workbench" / "runtime" / "test_tmp" / "noise.c").write_text("int noise;\n", encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_scan_project_excludes_runtime_noise_and_reports_structured_details(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        cfg = {
            "project": {"name": "demo", "source_dirs": ["Core", "agent_workbench"]},
            "project_root_path": self.temp_dir,
            "agent_workbench_root_path": repo_root / "agent_workbench",
            "outputs": {
                "runtime_root_path": self.temp_dir / "agent_workbench" / "runtime",
                "evidence_root_path": self.temp_dir / "agent_workbench" / "evidence",
                "generated_root_path": self.temp_dir / "agent_workbench" / "generated",
            },
            "planner": {"templates_dir_path": repo_root / "agent_workbench" / "templates" / "task_templates"},
            "opencode": {
                "agents_file_path": self.temp_dir / "AGENTS.md",
                "agents_dir_path": self.temp_dir / ".opencode" / "agent",
                "commands_dir_path": self.temp_dir / ".opencode" / "command",
            },
            "uart": {
                "enabled": True,
                "ready_banner": "STM32 UART CLI ready.",
                "prompt": "cli>",
                "probe_commands": ["help"],
                "help_rows": [{"command": "help"}],
            },
        }

        snapshot = scan_project(cfg)

        self.assertIn("Core/Src/main.c", snapshot["source_files"])
        self.assertNotIn("agent_workbench/runtime/test_tmp/noise.c", snapshot["source_files"])
        self.assertGreaterEqual(snapshot["planner_template_count"], 15)
        self.assertTrue(any(item["name"] == "htim1" for item in snapshot["existing_handles"]))
        self.assertTrue(any(item["command"] == "help" for item in snapshot["cli_commands"]))
        self.assertTrue(any(item["name"] == "USER CODE BEGIN PV" for item in snapshot["user_code_regions"]))
