from __future__ import annotations

import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import workbench  # type: ignore  # noqa: E402


class WorkbenchMonitorTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / "runtime" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="awb_workbench_", dir=temp_root))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_removed_commands_are_not_registered(self) -> None:
        parser = workbench.build_parser()
        commands = parser._subparsers._group_actions[0].choices

        self.assertNotIn("scan-project", commands)
        self.assertNotIn("context", commands)
        self.assertNotIn("test", commands)
        self.assertNotIn("verify", commands)
        self.assertNotIn("report", commands)
        self.assertNotIn("compare", commands)
        self.assertNotIn("session", commands)

    def test_monitor_only_exposes_kept_actions(self) -> None:
        parser = workbench.build_parser()
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parser.parse_args(["monitor", "probe"])
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parser.parse_args(["monitor", "run", "--out-dir", str(self.temp_dir)])
        parsed = parser.parse_args(["monitor", "stats"])
        self.assertEqual(parsed.action, "stats")

    def test_hidden_monitor_run_internal_accepts_out_dir(self) -> None:
        parser = workbench.build_parser()
        parsed = parser.parse_args(["__monitor-run", "--out-dir", str(self.temp_dir)])
        self.assertEqual(parsed.command, "__monitor-run")
        self.assertEqual(parsed.out_dir, str(self.temp_dir))

    def test_opencode_auto_run_is_registered(self) -> None:
        parser = workbench.build_parser()
        parsed = parser.parse_args(["opencode-auto", "run", "--task", "do work", "--dry-run", "--json"])
        self.assertEqual(parsed.command, "opencode-auto")
        self.assertEqual(parsed.action, "run")
        self.assertEqual(parsed.task, "do work")
        self.assertTrue(parsed.dry_run)

    def test_opencode_auto_retry_is_registered(self) -> None:
        parser = workbench.build_parser()
        parsed = parser.parse_args(
            ["opencode-auto", "retry", "--task", "do work", "--max-attempts", "5", "--dry-run", "--json"]
        )
        self.assertEqual(parsed.command, "opencode-auto")
        self.assertEqual(parsed.action, "retry")
        self.assertEqual(parsed.task, "do work")
        self.assertEqual(parsed.max_attempts, 5)
        self.assertTrue(parsed.dry_run)

    def test_opencode_auto_template_file_flags(self) -> None:
        parser = workbench.build_parser()
        parsed = parser.parse_args(
            [
                "opencode-auto",
                "run",
                "--task",
                "do work",
                "--planner-cmd-template-file",
                "planner.txt",
                "--opencode-cmd-template-file",
                "worker.txt",
                "--review-cmd-template-file",
                "review.txt",
            ]
        )
        self.assertEqual(parsed.planner_cmd_template_file, "planner.txt")
        self.assertEqual(parsed.opencode_cmd_template_file, "worker.txt")
        self.assertEqual(parsed.review_cmd_template_file, "review.txt")

    def test_opencode_auto_template_file_strips_utf8_bom(self) -> None:
        config_path = self.temp_dir / "agent_workbench.yaml"
        config_path.write_text(
            "\n".join(
                [
                    "project:",
                    "  name: probe",
                    "  root: .",
                    "outputs:",
                    "  runtime_root: runtime",
                    "  evidence_root: evidence",
                    "  generated_root: generated",
                ]
            ),
            encoding="utf-8",
        )
        template_path = self.temp_dir / "worker-template.txt"
        template_path.write_bytes(b"\xef\xbb\xbfignored command")

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = workbench.dispatch_args(
                [
                    "opencode-auto",
                    "run",
                    "--config",
                    str(config_path),
                    "--task",
                    "hello",
                    "--dry-run",
                    "--opencode-cmd-template-file",
                    str(template_path),
                    "--json",
                ]
            )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(payload["exit_code"], 0)

    def test_opencode_auto_task_file_strips_utf8_bom(self) -> None:
        config_path = self.temp_dir / "agent_workbench.yaml"
        config_path.write_text(
            "\n".join(
                [
                    "project:",
                    "  name: probe",
                    "  root: .",
                    "outputs:",
                    "  runtime_root: runtime",
                    "  evidence_root: evidence",
                    "  generated_root: generated",
                ]
            ),
            encoding="utf-8",
        )
        task_path = self.temp_dir / "task.md"
        task_path.write_bytes(b"\xef\xbb\xbfhello")

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = workbench.dispatch_args(
                [
                    "opencode-auto",
                    "run",
                    "--config",
                    str(config_path),
                    "--task-file",
                    str(task_path),
                    "--dry-run",
                    "--json",
                ]
            )

        payload = json.loads(stdout.getvalue())
        run_dir = Path(payload["artifacts"]["run_dir"])
        written_task = (run_dir / "task.md").read_text(encoding="utf-8")
        self.assertEqual(code, 0)
        self.assertFalse(written_task.startswith("\ufeff"))


if __name__ == "__main__":
    unittest.main()
