from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.opencode_auto_service import fallback_split_task, run_opencode_auto, run_opencode_retry  # type: ignore  # noqa: E402


class OpencodeAutoServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / "runtime" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="awb_opencode_auto_", dir=temp_root))
        self.cfg = {
            "project_root_path": self.temp_dir,
            "outputs": {
                "runtime_root_path": self.temp_dir / "runtime",
            },
        }

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_fallback_split_markdown_lists(self) -> None:
        tasks = fallback_split_task(
            """
Large task

1. Add planner command
- Add executor command
- [ ] Add review command
"""
        )

        self.assertEqual([item["id"] for item in tasks], ["task_001", "task_002", "task_003"])
        self.assertEqual(tasks[0]["title"], "Add planner command")
        self.assertEqual(tasks[2]["body"], "Add review command")

    def test_dry_run_writes_artifacts(self) -> None:
        payload = run_opencode_auto(
            self.cfg,
            task_text="- First task\n- Second task",
            dry_run=True,
            max_retries=0,
            timeout_seconds=5,
        )

        self.assertEqual(payload["exit_code"], 0)
        self.assertEqual(payload["details"]["total"], 2)
        self.assertEqual(payload["details"]["passed"], 2)
        run_dir = Path(payload["artifacts"]["run_dir"])
        self.assertTrue((run_dir / "task.md").exists())
        self.assertTrue((run_dir / "plan.json").exists())
        self.assertTrue((run_dir / "summary.json").exists())
        summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["status"], "pass")
        first_attempt = run_dir / "tasks" / "task_001" / "attempt_001" / "result.json"
        self.assertTrue(first_attempt.exists())

    def test_failed_executor_retries_then_skips(self) -> None:
        script = self.temp_dir / "fail_task.py"
        script.write_text("import sys\nsys.exit(7)\n", encoding="utf-8")
        self._init_git_repo(self.temp_dir)
        template = f'"{sys.executable}" "{script}"'

        payload = run_opencode_auto(
            self.cfg,
            task_text="- Always fails",
            opencode_cmd_template=template,
            max_retries=2,
            timeout_seconds=5,
        )

        self.assertEqual(payload["exit_code"], 1)
        self.assertEqual(payload["details"]["skipped"], 1)
        task = payload["details"]["tasks"][0]
        self.assertEqual(task["status"], "failed_skipped")
        self.assertEqual(task["attempt_count"], 3)
        self.assertEqual(len(task["attempts"]), 3)

    def test_run_failed_subtask_cleanup_preserves_previous_success(self) -> None:
        tracked = self.temp_dir / "tracked.txt"
        tracked.write_text("clean\n", encoding="utf-8")
        script = self.temp_dir / "run_worker.py"
        script.write_text(
            "\n".join(
                [
                    "from pathlib import Path",
                    "import sys",
                    "task = Path(sys.argv[1]).read_text(encoding='utf-8')",
                    "if 'Successful first' in task:",
                    "    Path('tracked.txt').write_text('success\\n', encoding='utf-8')",
                    "    raise SystemExit(0)",
                    "Path('tracked.txt').write_text('failed\\n', encoding='utf-8')",
                    "Path('failed_new.txt').write_text('new\\n', encoding='utf-8')",
                    "raise SystemExit(7)",
                ]
            ),
            encoding="utf-8",
        )
        self._init_git_repo(self.temp_dir)
        template = f'"{sys.executable}" "{script}" "{{task_file}}"'

        payload = run_opencode_auto(
            self.cfg,
            task_text="- Successful first\n- Failing second",
            opencode_cmd_template=template,
            max_retries=0,
            timeout_seconds=5,
        )

        self.assertEqual(payload["exit_code"], 1)
        self.assertEqual(payload["details"]["passed"], 1)
        self.assertEqual(payload["details"]["skipped"], 1)
        self.assertEqual(tracked.read_text(encoding="utf-8"), "success\n")
        self.assertFalse((self.temp_dir / "failed_new.txt").exists())
        failed_attempt = payload["details"]["tasks"][1]["attempts"][0]
        result = json.loads(Path(failed_attempt["result_path"]).read_text(encoding="utf-8"))
        self.assertEqual(result["cleanup"]["status"], "pass")

    def test_run_failed_subtask_cleanup_preserves_dirty_baseline(self) -> None:
        tracked = self.temp_dir / "tracked.txt"
        tracked.write_text("clean\n", encoding="utf-8")
        script = self.temp_dir / "fail_and_dirty.py"
        script.write_text(
            "\n".join(
                [
                    "from pathlib import Path",
                    "Path('tracked.txt').write_text('failed\\n', encoding='utf-8')",
                    "Path('pre_existing.txt').write_text('failed preexisting\\n', encoding='utf-8')",
                    "Path('failed_new.txt').write_text('new\\n', encoding='utf-8')",
                    "raise SystemExit(7)",
                ]
            ),
            encoding="utf-8",
        )
        self._init_git_repo(self.temp_dir)
        tracked.write_text("user change\n", encoding="utf-8")
        pre_existing = self.temp_dir / "pre_existing.txt"
        pre_existing.write_text("user untracked\n", encoding="utf-8")
        template = f'"{sys.executable}" "{script}"'

        payload = run_opencode_auto(
            self.cfg,
            task_text="- Failing dirty baseline",
            opencode_cmd_template=template,
            max_retries=0,
            timeout_seconds=5,
        )

        self.assertEqual(payload["exit_code"], 1)
        self.assertEqual(tracked.read_text(encoding="utf-8"), "user change\n")
        self.assertEqual(pre_existing.read_text(encoding="utf-8"), "user untracked\n")
        self.assertFalse((self.temp_dir / "failed_new.txt").exists())

    def test_run_no_git_cleanup_leaves_failed_subtask_changes(self) -> None:
        tracked = self.temp_dir / "tracked.txt"
        tracked.write_text("clean\n", encoding="utf-8")
        script = self.temp_dir / "fail_without_cleanup.py"
        script.write_text(
            "\n".join(
                [
                    "from pathlib import Path",
                    "Path('tracked.txt').write_text('failed\\n', encoding='utf-8')",
                    "Path('failed_new.txt').write_text('new\\n', encoding='utf-8')",
                    "raise SystemExit(7)",
                ]
            ),
            encoding="utf-8",
        )
        self._init_git_repo(self.temp_dir)
        template = f'"{sys.executable}" "{script}"'

        payload = run_opencode_auto(
            self.cfg,
            task_text="- Failing without cleanup",
            opencode_cmd_template=template,
            max_retries=0,
            timeout_seconds=5,
            git_cleanup=False,
        )

        self.assertEqual(payload["exit_code"], 1)
        self.assertEqual(tracked.read_text(encoding="utf-8"), "failed\n")
        self.assertTrue((self.temp_dir / "failed_new.txt").exists())
        failed_attempt = payload["details"]["tasks"][0]["attempts"][0]
        result = json.loads(Path(failed_attempt["result_path"]).read_text(encoding="utf-8"))
        self.assertNotIn("cleanup", result)

    def test_missing_executor_requires_dry_run(self) -> None:
        payload = run_opencode_auto(
            self.cfg,
            task_text="- Needs executor",
            max_retries=0,
            timeout_seconds=5,
        )

        self.assertEqual(payload["exit_code"], 2)
        self.assertIn("missing opencode command template", payload["summary"])

    def test_retry_dry_run_writes_markdown_artifacts(self) -> None:
        payload = run_opencode_retry(
            self.cfg,
            task_text="Do the large thing",
            dry_run=True,
            max_attempts=3,
            timeout_seconds=5,
        )

        self.assertEqual(payload["exit_code"], 0)
        self.assertEqual(payload["details"]["attempts"], 1)
        run_dir = Path(payload["artifacts"]["run_dir"])
        self.assertTrue((run_dir / "summary.json").exists())
        self.assertTrue((run_dir / "summary.md").exists())
        self.assertTrue((run_dir / "attempt_001" / "result.json").exists())
        self.assertTrue((run_dir / "attempt_001" / "result.md").exists())

    def test_retry_missing_executor_requires_dry_run(self) -> None:
        payload = run_opencode_retry(
            self.cfg,
            task_text="Needs executor",
            max_attempts=1,
            timeout_seconds=5,
        )

        self.assertEqual(payload["exit_code"], 2)
        self.assertIn("missing opencode command template", payload["summary"])
        self.assertTrue(Path(payload["artifacts"]["summary_md"]).exists())

    def test_retry_stops_after_first_pass(self) -> None:
        script = self.temp_dir / "pass_task.py"
        script.write_text("print('done')\n", encoding="utf-8")
        self._init_git_repo(self.temp_dir)
        template = f'"{sys.executable}" "{script}"'

        payload = run_opencode_retry(
            self.cfg,
            task_text="Pass once",
            opencode_cmd_template=template,
            max_attempts=3,
            timeout_seconds=5,
        )

        self.assertEqual(payload["exit_code"], 0)
        self.assertEqual(payload["details"]["attempts"], 1)
        self.assertEqual(payload["details"]["passed_attempt"], 1)

    def test_retry_cleans_failed_attempt_from_clean_git_baseline(self) -> None:
        tracked = self.temp_dir / "tracked.txt"
        tracked.write_text("clean\n", encoding="utf-8")
        script = self.temp_dir / "fail_and_modify.py"
        script.write_text(
            "\n".join(
                [
                    "from pathlib import Path",
                    "Path('tracked.txt').write_text('dirty\\n', encoding='utf-8')",
                    "Path('new_file.txt').write_text('new\\n', encoding='utf-8')",
                    "raise SystemExit(7)",
                ]
            ),
            encoding="utf-8",
        )
        self._init_git_repo(self.temp_dir)
        template = f'"{sys.executable}" "{script}"'

        payload = run_opencode_retry(
            self.cfg,
            task_text="Fail and clean",
            opencode_cmd_template=template,
            max_attempts=1,
            timeout_seconds=5,
        )

        self.assertEqual(payload["exit_code"], 1)
        self.assertEqual(tracked.read_text(encoding="utf-8"), "clean\n")
        self.assertFalse((self.temp_dir / "new_file.txt").exists())
        run_dir = Path(payload["artifacts"]["run_dir"])
        result = json.loads((run_dir / "attempt_001" / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(result["cleanup"]["status"], "pass")

    def test_retry_dirty_baseline_fails_before_executor(self) -> None:
        tracked = self.temp_dir / "tracked.txt"
        tracked.write_text("clean\n", encoding="utf-8")
        self._init_git_repo(self.temp_dir)
        tracked.write_text("user change\n", encoding="utf-8")
        script = self.temp_dir / "would_modify.py"
        script.write_text("from pathlib import Path\nPath('ran.txt').write_text('bad', encoding='utf-8')\n", encoding="utf-8")
        template = f'"{sys.executable}" "{script}"'

        payload = run_opencode_retry(
            self.cfg,
            task_text="Should not run",
            opencode_cmd_template=template,
            max_attempts=1,
            timeout_seconds=5,
        )

        self.assertEqual(payload["exit_code"], 2)
        self.assertIn("dirty", payload["summary"])
        self.assertEqual(tracked.read_text(encoding="utf-8"), "user change\n")
        self.assertFalse((self.temp_dir / "ran.txt").exists())

    def _init_git_repo(self, cwd: Path) -> None:
        subprocess.run(["git", "init"], cwd=str(cwd), check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "config", "user.email", "agent@example.invalid"], cwd=str(cwd), check=True)
        subprocess.run(["git", "config", "user.name", "Agent Workbench Test"], cwd=str(cwd), check=True)
        subprocess.run(["git", "add", "."], cwd=str(cwd), check=True)
        subprocess.run(["git", "commit", "-m", "baseline"], cwd=str(cwd), check=True, stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    unittest.main()
