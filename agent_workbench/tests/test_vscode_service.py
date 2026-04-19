from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agent_workbench.core.vscode_service import write_opencode_agents, write_vscode_tasks


class VscodeServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / "runtime" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="awb_vscode_", dir=temp_root))
        (self.temp_dir / "agent_workbench" / "bin").mkdir(parents=True, exist_ok=True)
        (self.temp_dir / "agent_workbench" / "tasks").mkdir(parents=True, exist_ok=True)
        tpl_root = self.temp_dir / "agent_workbench" / "templates" / "opencode_agents"
        (tpl_root / "agent").mkdir(parents=True, exist_ok=True)
        (tpl_root / "command").mkdir(parents=True, exist_ok=True)
        (tpl_root / "model_profiles").mkdir(parents=True, exist_ok=True)
        # AGENTS.md 模板
        (tpl_root / "AGENTS.md.tpl").write_text(
            "project={project_name} ready={ready_banner} prompt={prompt} uart={uart_port} diag={diag_uart_port} profile={default_profile}\n",
            encoding="utf-8",
        )
        # 4 个 sub-agent
        for name in ("stm32_auto.md", "weak_model.md", "code_planner.md", "hardware_verifier.md"):
            (tpl_root / "agent" / f"{name}.tpl").write_text(
                f"---\ndescription: test {name}\n---\nproject={{project_name}} ready={{ready_banner}}\n",
                encoding="utf-8",
            )
        # 5 个 slash 命令
        for name in ("plan-stm32.md", "verify.md", "fix-build.md", "uart-smoke.md", "flash-reset.md"):
            (tpl_root / "command" / f"{name}.tpl").write_text(
                f"---\ndescription: test {name}\n---\nproject={{project_name}}\n",
                encoding="utf-8",
            )
        # opencode.json 模板
        (tpl_root / "opencode.json.tpl").write_text(
            '{"$schema":"https://opencode.ai/config.json","instructions":["AGENTS.md"]}\n',
            encoding="utf-8",
        )
        # model profile 模板
        for name in ("deepseek_r1", "glm", "qwen7b"):
            (tpl_root / "model_profiles" / f"{name}.md.tpl").write_text(
                f"---\ndescription: {name}\n---\nproject={{project_name}}\n",
                encoding="utf-8",
            )

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _cfg(self) -> dict:
        return {
            "project_root_path": self.temp_dir,
            "agent_workbench_root_path": self.temp_dir / "agent_workbench",
            "outputs": {
                "opencode_runtime_root_path": self.temp_dir / "agent_workbench" / "runtime" / "opencode",
            },
            "vscode": {
                "tasks_file_path": self.temp_dir / ".vscode" / "tasks.json",
            },
            "agent": {
                "default_profile": "deepseek16k",
            },
            "opencode": {
                "agents_file_path": self.temp_dir / "AGENTS.md",
                "agents_dir_path": self.temp_dir / ".opencode" / "agent",
                "commands_dir_path": self.temp_dir / ".opencode" / "command",
                "project_config_file_path": self.temp_dir / "opencode.json",
                "agents_template_dir_path": self.temp_dir / "agent_workbench" / "templates" / "opencode_agents",
                "required_agents": [
                    "stm32_auto.md",
                    "weak_model.md",
                    "code_planner.md",
                    "hardware_verifier.md",
                ],
                "required_commands": [
                    "plan-stm32.md",
                    "verify.md",
                    "fix-build.md",
                    "uart-smoke.md",
                    "flash-reset.md",
                ],
                "model_profiles": {
                    "deepseek_r1": {"profile_file": "model_profiles/deepseek_r1.md", "min_lines": 5},
                    "glm": {"profile_file": "model_profiles/glm.md", "min_lines": 5},
                    "qwen7b": {"profile_file": "model_profiles/qwen7b.md", "min_lines": 5},
                },
            },
            "project": {
                "name": "demo",
                "source_dirs": ["Core", "Drivers"],
                "build_dir_path": self.temp_dir / "build",
            },
            "uart": {
                "ready_banner": "STM32 UART CLI ready.",
                "prompt": "cli>",
                "port": "COM3",
                "baudrate": 115200,
            },
            "diag_uart": {
                "port": "COM4",
            },
        }

    def test_generated_tasks_expose_opencode_init_task(self) -> None:
        cfg = self._cfg()
        tasks_path = write_vscode_tasks(cfg)

        self.assertTrue(tasks_path.exists())
        payload = json.loads(tasks_path.read_text(encoding="utf-8"))
        commands = [item["command"] for item in payload["tasks"]]
        self.assertIn('cmd /c ".\\agent_workbench.bat init-opencode-agents"', commands)
        self.assertIn('cmd /c ".\\agent_workbench.bat scan-project --json"', commands)
        self.assertIn(
            'cmd /c ".\\agent_workbench.bat verify current --task agent_workbench/tasks/cli_automation_regression.yaml"',
            commands,
        )
        self.assertIn('cmd /c ".\\agent_workbench.bat diag exec"', commands)
        self.assertTrue(all(command.startswith('cmd /c ".\\') for command in commands))

    def test_write_opencode_agents_generates_expected_files(self) -> None:
        cfg = self._cfg()
        generated = write_opencode_agents(cfg)

        # AGENTS.md + 4 sub-agents + 5 commands + opencode.json + 3 model profiles = 14
        self.assertGreaterEqual(len(generated), 13)

        agents_file = self.temp_dir / "AGENTS.md"
        agents_dir = self.temp_dir / ".opencode" / "agent"
        commands_dir = self.temp_dir / ".opencode" / "command"
        project_config = self.temp_dir / "opencode.json"

        self.assertTrue(agents_file.exists())
        self.assertIn("demo", agents_file.read_text(encoding="utf-8"))
        self.assertIn("STM32 UART CLI ready.", agents_file.read_text(encoding="utf-8"))

        for name in ("stm32_auto.md", "weak_model.md", "code_planner.md", "hardware_verifier.md"):
            self.assertTrue((agents_dir / name).exists(), f"agent missing: {name}")
        for name in ("plan-stm32.md", "verify.md", "fix-build.md", "uart-smoke.md", "flash-reset.md"):
            self.assertTrue((commands_dir / name).exists(), f"command missing: {name}")

        self.assertTrue(project_config.exists())
        self.assertIn("opencode.ai", project_config.read_text(encoding="utf-8"))

        # 模型 profile 也生成
        self.assertTrue((agents_dir / "model_deepseek_r1.md").exists())
        self.assertTrue((agents_dir / "model_glm.md").exists())
        self.assertTrue((agents_dir / "model_qwen7b.md").exists())
