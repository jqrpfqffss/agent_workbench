from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agent_workbench.core import session_service
from agent_workbench.core.uart_service import UartExecResult


class DirectVerifyTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / "runtime" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="awb_direct_verify_", dir=temp_root))
        self.runtime_root = self.temp_dir / "runtime"
        self.evidence_root = self.temp_dir / "evidence"
        self.generated_root = self.temp_dir / "generated"
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        self.evidence_root.mkdir(parents=True, exist_ok=True)
        self.generated_root.mkdir(parents=True, exist_ok=True)
        self.task_path = self.temp_dir / "task.yaml"
        self.task_path.write_text(
            "id: demo_verify\n"
            "mode: feature\n"
            "goal: verify demo path\n"
            "scope:\n"
            "  include: [Core/Src/cli.c]\n"
            "  exclude: []\n"
            "acceptance:\n"
            "  blackbox: []\n"
            "  unit: []\n"
            "observability:\n"
            "  notes: []\n"
            "verify:\n"
            "  sequence: [doctor, build, test, debug]\n"
            "  cli_commands: [help, status]\n",
            encoding="utf-8",
        )
        self.cfg = {
            "outputs": {
                "runtime_root_path": self.runtime_root,
                "evidence_root_path": self.evidence_root,
                "generated_root_path": self.generated_root,
            },
            "uart": {
                "enabled": True,
            },
            "project_root_path": self.temp_dir,
        }

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_run_current_verify_writes_pass_summary(self) -> None:
        unit_log = self.runtime_root / "unit.log"
        unit_log.write_text("ok\n", encoding="utf-8")
        generated_dir = self.generated_root / "tasks" / "demo_verify"
        generated_dir.mkdir(parents=True, exist_ok=True)

        with mock.patch.object(session_service, "run_doctor", return_value=(0, {"fail_count": 0, "warn_count": 0})), mock.patch.object(
            session_service, "run_build", return_value=0
        ), mock.patch.object(session_service, "generate_tests", return_value=generated_dir), mock.patch.object(
            session_service, "run_tests", return_value=(0, unit_log)
        ), mock.patch.object(
            session_service,
            "execute_uart_commands",
            return_value=UartExecResult(0, ["ready", "cli>"], True, True, []),
        ), mock.patch.object(
            session_service, "run_feature_session", return_value=0
        ), mock.patch.object(
            session_service, "rebuild_report", side_effect=lambda session_dir: session_dir / "session_summary.md"
        ), mock.patch.object(
            session_service, "derive_session_verdict", return_value={"status": "pass", "summary": "Feature verification passed."}
        ), mock.patch.object(
            session_service, "find_previous_session", return_value=None
        ):
            code, summary_path = session_service.run_current_verify(self.cfg, self.task_path, session_name="direct_pass")

        self.assertEqual(code, 0)
        self.assertTrue(summary_path.exists())
        payload = json.loads((self.runtime_root / "direct_verify_summary.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["steps"][3]["name"], "test_run")
        self.assertEqual(payload["steps"][4]["status"], "pass")

    def test_run_current_verify_marks_blocked_and_skips_feature_session_when_smoke_is_blocked(self) -> None:
        unit_log = self.runtime_root / "unit.log"
        unit_log.write_text("ok\n", encoding="utf-8")
        generated_dir = self.generated_root / "tasks" / "demo_verify"
        generated_dir.mkdir(parents=True, exist_ok=True)

        with mock.patch.object(session_service, "run_doctor", return_value=(0, {"fail_count": 0, "warn_count": 0})), mock.patch.object(
            session_service, "run_build", return_value=0
        ), mock.patch.object(session_service, "generate_tests", return_value=generated_dir), mock.patch.object(
            session_service, "run_tests", return_value=(0, unit_log)
        ), mock.patch.object(
            session_service,
            "execute_uart_commands",
            return_value=UartExecResult(35, [], False, False, []),
        ), mock.patch.object(
            session_service, "run_feature_session", return_value=0
        ) as feature_mock:
            code, summary_path = session_service.run_current_verify(self.cfg, self.task_path, session_name="direct_blocked")

        self.assertEqual(code, 1)
        self.assertTrue(summary_path.exists())
        payload = json.loads((self.runtime_root / "direct_verify_summary.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(payload["steps"][4]["status"], "blocked")
        self.assertEqual(payload["steps"][5]["status"], "blocked")
        feature_mock.assert_not_called()
