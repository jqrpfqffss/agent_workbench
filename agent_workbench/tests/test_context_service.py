from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agent_workbench.core.context_service import write_context_pack


class ContextServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / "runtime" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="awb_context_", dir=temp_root))
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
                "name": "demo",
                "build_dir_path": self.temp_dir / "build",
                "artifact_elf_path": self.temp_dir / "build" / "demo.elf",
                "compile_commands_path": self.temp_dir / "build" / "compile_commands.json",
                "source_dirs": ["Core", "Drivers"],
            },
            "outputs": {
                "runtime_root_path": self.runtime_root,
                "evidence_root_path": self.evidence_root,
                "generated_root_path": self.generated_root,
            },
            "agent": {
                "state_path": self.runtime_root / "agent_state.json",
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
                    },
                    "deepseek16k": {
                        "max_pack_words": 90,
                        "max_fact_items": 6,
                        "max_cli_tail_lines": 3,
                        "max_failed_assertions_shown": 2,
                        "max_extra_reads": 1,
                        "max_edit_files": 1,
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
                "probe_commands": ["help", "version"],
            },
        }

    def _task_path(self) -> Path:
        task_path = self.temp_dir / "task.yaml"
        task_path.write_text(
            "id: add_version_cli\n"
            "mode: feature\n"
            "goal: add version command\n"
            "scope:\n"
            "  include: [Core/Src/app_cli_commands.c, Core/Src/cli.c]\n"
            "  exclude: [Drivers]\n"
            "acceptance:\n"
            "  blackbox:\n"
            "    - name: version_seen\n"
            "      type: cli_contains\n"
            "      needle: 'FW version: demo 1.0.0'\n"
            "  unit:\n"
            "    - version command is registered\n"
            "observability:\n"
            "  notes:\n"
            "    - keep output stable\n"
            "verify:\n"
            "  sequence: [doctor, build, test, debug]\n"
            "  cli_commands: [help, version]\n"
            "implementation:\n"
            "  read_candidates: [Core/Src/app_cli_commands.c, Core/Src/cli.c]\n"
            "  edit_candidates: [Core/Src/app_cli_commands.c]\n"
            "  stable_strings: ['FW version: demo 1.0.0']\n"
            "  max_edit_files: 1\n",
            encoding="utf-8",
        )
        return task_path

    def _session(self, name: str, *, status: str, diag_code: str = "", failed_assertion: str = "") -> Path:
        session_dir = self.evidence_root / name
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "session_manifest.json").write_text(
            json.dumps(
                {
                    "generated_at": "2026-04-08T10:00:00+00:00",
                    "mode": "feature",
                    "task": {"id": "add_version_cli"},
                }
            ),
            encoding="utf-8",
        )
        if status == "fail":
            (session_dir / "assertions.jsonl").write_text(
                json.dumps({"status": "fail", "name": failed_assertion or "version_seen", "detail": "missing expected needle"}) + "\n",
                encoding="utf-8",
            )
        else:
            (session_dir / "assertions.jsonl").write_text(
                json.dumps({"status": "pass", "name": "version_seen"}) + "\n",
                encoding="utf-8",
            )
        diag_payload = {}
        if diag_code:
            diag_payload = {
                "status": "error",
                "classification": {"code": diag_code, "summary": diag_code, "detail": f"detail {diag_code}"},
            }
        (session_dir / "cli_diag.json").write_text(json.dumps(diag_payload), encoding="utf-8")
        (session_dir / "cli_transcript.log").write_text(
            "[ts] < STM32 UART CLI ready.\n[ts] < cli>\n[ts] > version\n[ts] < [error] unknown command: version\n",
            encoding="utf-8",
        )
        (session_dir / "events.jsonl").write_text(
            json.dumps({"event": "cli_probe_done", "code": 1 if status == "fail" else 0, "saw_ready": True, "saw_prompt": True}) + "\n",
            encoding="utf-8",
        )
        return session_dir

    def test_analyze_stage_prefers_latest_failed_session_and_writes_state(self) -> None:
        cfg = self._cfg()
        task_path = self._task_path()
        self._session("feature_pass", status="pass")
        failed_session = self._session("feature_fail", status="fail", failed_assertion="version_seen")

        out_path = write_context_pack(cfg, mode="feature", stage="analyze", task_path=task_path)

        self.assertTrue(out_path.exists())
        text = out_path.read_text(encoding="utf-8")
        self.assertIn("stage: `analyze`", text)
        self.assertIn("F07: latest_session = feature_fail", text)
        self.assertTrue((self.runtime_root / "agent_state.json").exists())
        state = json.loads((self.runtime_root / "agent_state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["latest_session"], failed_session.name)
        self.assertEqual(state["latest_verdict"], "fail")

    def test_implement_stage_limits_edits_and_generates_cards(self) -> None:
        cfg = self._cfg()
        task_path = self._task_path()
        self._session("feature_fail", status="fail", failed_assertion="version_seen")

        out_path = write_context_pack(cfg, mode="feature", stage="implement", task_path=task_path)

        state = json.loads((self.runtime_root / "agent_state.json").read_text(encoding="utf-8"))
        facts_path = Path(str(state["generated_files"]["facts"]))
        constraints_path = Path(str(state["generated_files"]["constraints"]))
        paste_path = Path(str(state["generated_files"]["paste"]))
        breakdown_path = Path(str(state["generated_files"]["task_breakdown"]))

        self.assertTrue(out_path.exists())
        self.assertTrue(facts_path.exists())
        self.assertTrue(constraints_path.exists())
        self.assertTrue(paste_path.exists())
        self.assertTrue(breakdown_path.exists())

        constraints = json.loads(constraints_path.read_text(encoding="utf-8"))
        self.assertEqual(constraints["mode"], "feature")
        self.assertEqual(constraints["stage"], "implement")
        self.assertEqual(len(constraints["allowed_edits"]), 1)
        self.assertEqual(constraints["current_subtasks"], ["S4", "S5"])
        self.assertIn("Core\\Src\\app_cli_commands.c", constraints["allowed_edits"][0])
        self.assertIn("## Current Subtasks", out_path.read_text(encoding="utf-8"))
        self.assertIn("Complete only these subtasks in this round: S4, S5.", paste_path.read_text(encoding="utf-8"))
        self.assertIn("implement the smallest safe change only", paste_path.read_text(encoding="utf-8"))

    def test_verify_stage_brief_stays_under_budget(self) -> None:
        cfg = self._cfg()
        task_path = self._task_path()
        self._session("feature_pass", status="pass")

        out_path = write_context_pack(cfg, mode="feature", stage="verify", task_path=task_path)

        words = sum(1 for item in out_path.read_text(encoding="utf-8").split() if item.strip())
        self.assertLessEqual(words, 550)
        self.assertIn("## Next Commands", out_path.read_text(encoding="utf-8"))

    def test_resume_stage_reuses_saved_state(self) -> None:
        cfg = self._cfg()
        task_path = self._task_path()
        self._session("feature_fail", status="fail", diag_code="parser_no_command")
        write_context_pack(cfg, mode="feature", stage="implement", task_path=task_path)

        out_path = write_context_pack(cfg, mode="debug", stage="resume")

        self.assertTrue(out_path.exists())
        state = json.loads((self.runtime_root / "agent_state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["stage"], "resume")
        self.assertEqual(state["mode"], "feature")

    def test_deepseek_profile_clips_brief_to_budget(self) -> None:
        cfg = self._cfg()
        task_path = self._task_path()
        self._session("feature_fail", status="fail", failed_assertion="version_seen")

        out_path = write_context_pack(cfg, mode="feature", stage="implement", profile_name="deepseek16k", task_path=task_path)

        words = sum(1 for item in out_path.read_text(encoding="utf-8").split() if item.strip())
        self.assertLessEqual(words, 90)

    def test_direct_cli_task_skips_implement_and_generates_uart_exec_verify_commands(self) -> None:
        cfg = self._cfg()
        task_path = self.temp_dir / "direct_cli_task.yaml"
        task_path.write_text(
            "id: autoflow_cli_red_on\n"
            "mode: feature\n"
            "goal: point the red LED on using existing CLI\n"
            "scope:\n"
            "  include: []\n"
            "  exclude: [Drivers]\n"
            "acceptance:\n"
            "  blackbox:\n"
            "    - name: cli_command_ack_seen\n"
            "      type: cli_contains\n"
            "      needle: '[ok] red -> on'\n"
            "  unit:\n"
            "    - no code changes required\n"
            "observability:\n"
            "  notes:\n"
            "    - Treat this as a direct CLI operation.\n"
            "verify:\n"
            "  sequence: [uart_smoke]\n"
            "  cli_commands: ['red on', 'status']\n"
            "implementation:\n"
            "  read_candidates: []\n"
            "  edit_candidates: []\n"
            "  stable_strings: ['[ok] red -> on']\n"
            "  max_edit_files: 0\n"
            "decomposition:\n"
            "  enabled: true\n"
            "  subtasks:\n"
            "    - id: S1\n"
            "      stage: analyze\n"
            "      title: confirm command\n"
            "    - id: S2\n"
            "      stage: analyze\n"
            "      title: skip edits\n"
            "    - id: S3\n"
            "      stage: verify\n"
            "      title: run uart\n"
            "    - id: S4\n"
            "      stage: verify\n"
            "      title: report from transcript\n",
            encoding="utf-8",
        )

        analyze_path = write_context_pack(cfg, mode="feature", stage="analyze", task_path=task_path)
        analyze_state = json.loads((self.runtime_root / "agent_state.json").read_text(encoding="utf-8"))
        self.assertEqual(analyze_state["current_subtasks"], ["S1", "S2"])
        self.assertIn("autoflow --done S1,S2", analyze_state["next_commands"][0])
        self.assertEqual(len(analyze_state["next_commands"]), 2)
        self.assertIn("F06B: task_max_edit_files = 0", analyze_path.read_text(encoding="utf-8"))

        verify_path = write_context_pack(cfg, mode="feature", stage="verify", task_path=task_path)
        verify_state = json.loads((self.runtime_root / "agent_state.json").read_text(encoding="utf-8"))
        self.assertEqual(verify_state["current_subtasks"], ["S3", "S4"])
        self.assertTrue(any('uart exec --reset-first --expect-ready --command ""red on"" --command ""status""' in command for command in verify_state["next_commands"]))
        self.assertTrue(any("autoflow --done S3,S4" in command for command in verify_state["next_commands"]))
        self.assertIn("## Next Commands", verify_path.read_text(encoding="utf-8"))
