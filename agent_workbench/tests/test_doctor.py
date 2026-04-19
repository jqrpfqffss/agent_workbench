from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agent_workbench.core.doctor import run_doctor


class DoctorTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / "runtime" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="awb_doctor_", dir=temp_root))
        self.runtime_root = self.temp_dir / "runtime"
        self.evidence_root = self.temp_dir / "evidence"
        self.generated_root = self.temp_dir / "generated"
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        self.evidence_root.mkdir(parents=True, exist_ok=True)
        self.generated_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_doctor_reports_local_model_state_and_budget(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        brief_path = self.runtime_root / "context_brief.md"
        paste_path = self.runtime_root / "context_paste.md"
        task_path = self.temp_dir / "task.yaml"
        toolchain_path = self.temp_dir / "toolchain.cmake"

        # OpenCode 产物
        agents_file = self.temp_dir / "AGENTS.md"
        agents_dir = self.temp_dir / ".opencode" / "agent"
        commands_dir = self.temp_dir / ".opencode" / "command"
        agents_dir.mkdir(parents=True, exist_ok=True)
        commands_dir.mkdir(parents=True, exist_ok=True)

        # AGENTS.md 要包含项目名/ready banner/prompt，否则 binding 检查会 warn
        agents_file.write_text(
            "# Test AGENTS\nproject=demo\nready=ready\nprompt=cli>\n",
            encoding="utf-8",
        )
        for name in ("stm32_auto.md", "weak_model.md", "code_planner.md", "hardware_verifier.md"):
            (agents_dir / name).write_text(f"# {name}\n", encoding="utf-8")
        for name in ("plan-stm32.md", "verify.md", "fix-build.md", "uart-smoke.md", "flash-reset.md"):
            (commands_dir / name).write_text(f"# {name}\n", encoding="utf-8")
        for name in ("deepseek_r1", "glm", "qwen7b"):
            (agents_dir / f"model_{name}.md").write_text(f"# model {name}\n", encoding="utf-8")

        # 模板目录存在
        tpl_dir = self.temp_dir / "agent_workbench" / "templates" / "opencode_agents"
        tpl_dir.mkdir(parents=True, exist_ok=True)

        brief_path.write_text("one two three\n", encoding="utf-8")
        paste_path.write_text("paste\n", encoding="utf-8")
        toolchain_path.write_text("# toolchain\n", encoding="utf-8")
        task_path.write_text(
            "id: demo\n"
            "mode: feature\n"
            "goal: demo goal\n"
            "scope:\n"
            "  include: [Core/Src/a.c]\n"
            "  exclude: []\n"
            "acceptance: {}\n"
            "observability: {}\n"
            "verify: {}\n",
            encoding="utf-8",
        )
        state_path = self.runtime_root / "agent_state.json"
        state_path.write_text(
            json.dumps(
                {
                    "task_path": str(task_path),
                    "generated_files": {"brief": str(brief_path), "paste": str(paste_path)},
                }
            ),
            encoding="utf-8",
        )
        cfg = {
            "project": {
                "name": "demo",
                "artifact_elf_path": self.temp_dir / "missing.elf",
                "compile_commands_path": self.temp_dir / "missing.json",
            },
            "tools": {
                "cmake": {"toolchain_file_path": str(toolchain_path)},
                "openocd": {"daemon_cmd": "openocd"},
                "flash": {"default_method": "openocd_cmd", "methods": {"openocd_cmd": {"flash": "openocd"}}},
            },
            "outputs": {
                "runtime_root_path": self.runtime_root,
                "evidence_root_path": self.evidence_root,
                "generated_root_path": self.generated_root,
            },
            "agent_workbench_root_path": repo_root / "agent_workbench",
            "uart": {
                "enabled": True,
                "port": "COM3",
                "baudrate": 115200,
                "line_timeout_sec": 0.2,
                "ready_banner": "ready",
                "prompt": "cli>",
                "probe_commands": ["help"],
            },
            "diag_uart": {
                "enabled": True,
                "port": "COM99",
                "baudrate": 115200,
                "encoding": "utf-8",
                "read_timeout_sec": 0.05,
                "default_hex_requests": ["68 65 6C 70 0D 0A"],
            },
            "checks": {"unit": {"enabled": False}},
            "hardware": {"mode": "prefer"},
            "template_values": {},
            "planner": {
                "templates_dir_path": repo_root / "agent_workbench" / "templates" / "task_templates",
                "minimum_template_count": 15,
            },
            "opencode": {
                "agents_file_path": agents_file,
                "agents_dir_path": agents_dir,
                "commands_dir_path": commands_dir,
                "agents_template_dir_path": tpl_dir,
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
            "agent": {
                "state_path": state_path,
                "default_profile": "balanced_local",
                "profiles": {
                    "balanced_local": {
                        "max_pack_words": 50,
                        "max_fact_items": 10,
                        "max_cli_tail_lines": 4,
                        "max_failed_assertions_shown": 2,
                        "max_extra_reads": 2,
                        "max_edit_files": 2,
                        "require_fact_citations": True,
                        "prefer_ascii_runtime_artifacts": True,
                        "session_pick_strategy": "latest_failed_then_latest_pass",
                    }
                },
            },
        }

        code, summary = run_doctor(cfg, self.runtime_root)

        self.assertEqual(code, 0)
        names = {item["name"]: item for item in summary["results"]}
        self.assertIn("agent_state", names)
        self.assertIn("context_budget", names)
        self.assertIn("paste_card", names)
        self.assertIn("diag_uart_backend", names)
        self.assertIn("diag_uart_requests", names)
        self.assertIn("opencode_agents_file", names)
        self.assertIn("opencode_agents", names)
        self.assertIn("opencode_commands", names)
        self.assertIn("opencode_model_profiles", names)
        self.assertIn("planner_templates", names)
        self.assertIn("migration_docs", names)
        self.assertEqual(names["agent_state"]["level"], "ok")
        self.assertEqual(names["paste_card"]["level"], "ok")
        self.assertEqual(names["opencode_agents_file"]["level"], "ok")
        self.assertEqual(names["opencode_agents"]["level"], "ok")
        self.assertEqual(names["opencode_commands"]["level"], "ok")
        self.assertEqual(names["opencode_model_profiles"]["level"], "ok")
        self.assertEqual(names["planner_templates"]["level"], "ok")
