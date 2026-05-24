from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import workbench  # type: ignore  # noqa: E402

from agent_workbench.core.config import load_config
from agent_workbench.core.opencode_auto_service import OpencodeAutoService


class OpencodeAutoServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / "runtime" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="awb_opencode_auto_", dir=temp_root))
        self.workbench_root = self.temp_dir / "agent_workbench"
        self.project_root = self.temp_dir / "Git Project With Spaces"
        self.workbench_root.mkdir(parents=True)
        self.project_root.mkdir(parents=True)
        self.worker = self.project_root / "fake_worker.py"
        self.marker = self.project_root / "retry-marker.txt"
        self._write_worker()
        (self.project_root / "tracked.txt").write_text("base\n", encoding="utf-8")
        self._git("init")
        self._git("add", "tracked.txt")
        self._git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "init")

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_parser_exposes_opencode_auto(self) -> None:
        parser = workbench.build_parser()
        parsed = parser.parse_args(["opencode-auto", "run", "--task", "demo", "--json"])
        self.assertEqual(parsed.command, "opencode-auto")
        self.assertEqual(parsed.action, "run")
        self.assertEqual(parsed.task, "demo")
        self.assertTrue(parsed.json)

    def test_config_defaults_resolve_opencode_auto_paths(self) -> None:
        config_path = self._write_config(paths=["tracked.txt"])
        cfg = load_config(config_path)
        self.assertTrue(
            str(cfg["opencode_auto"]["runtime_dir_path"]).endswith(
                f"runtime{os.sep}opencode_auto"
            )
        )
        self.assertEqual(Path(cfg["opencode_auto"]["git"]["worktree_path"]), self.project_root.resolve())
        self.assertEqual(cfg["opencode_auto"]["git"]["paths"], ["tracked.txt"])
        self.assertIn("**/*.pyc", cfg["opencode_auto"]["git"]["exclude_paths"])

    def test_all_planned_subtasks_pass_and_stage_changes(self) -> None:
        cfg = load_config(self._write_config(paths=["tracked.txt", "created.txt"]))
        plan = self._write_plan(
            [
                {"id": "task_001", "title": "PASS_ONE", "prompt": "PASS_ONE"},
                {"id": "task_002", "title": "PASS_TWO", "prompt": "PASS_TWO"},
            ]
        )

        payload = OpencodeAutoService(cfg).run("large task", plan_file=str(plan))

        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["details"]["passed_count"], 2)
        cached = self._git("diff", "--cached", "--name-only").stdout
        self.assertIn("tracked.txt", cached)
        self.assertIn("PASS_TWO", (self.project_root / "tracked.txt").read_text(encoding="utf-8"))

    def test_success_stages_runtime_artifacts_when_configured(self) -> None:
        cfg = load_config(self._write_config(paths=["tracked.txt", "runtime"]))
        plan = self._write_plan([{"id": "task_001", "title": "PASS_ONE", "prompt": "PASS_ONE"}])

        payload = OpencodeAutoService(cfg).run("large task", plan_file=str(plan))

        self.assertEqual(payload["status"], "pass")
        cached = self._git("diff", "--cached", "--name-only").stdout
        self.assertIn("tracked.txt", cached)
        self.assertIn("runtime/opencode_auto", cached.replace("\\", "/"))
        self.assertIn("summary.json", cached)

    def test_failed_subtask_rolls_back_tracked_and_untracked_changes(self) -> None:
        cfg = load_config(self._write_config(paths=["tracked.txt", "created.txt", "runtime"]))
        plan = self._write_plan([{"id": "task_001", "title": "FAIL_ALWAYS", "prompt": "FAIL_ALWAYS"}])

        payload = OpencodeAutoService(cfg).run("large task", plan_file=str(plan), max_retries=0)

        self.assertEqual(payload["status"], "fail")
        self.assertEqual((self.project_root / "tracked.txt").read_text(encoding="utf-8"), "base\n")
        self.assertFalse((self.project_root / "created.txt").exists())
        self.assertTrue(Path(payload["artifacts"]["summary_json"]).exists())
        self.assertEqual(self._git("diff", "--cached", "--name-only").stdout.strip(), "")

    def test_retry_success_stages_only_final_success(self) -> None:
        cfg = load_config(self._write_config(paths=["tracked.txt", "created.txt"]))
        plan = self._write_plan([{"id": "task_001", "title": "FLAKY", "prompt": "FLAKY"}])

        payload = OpencodeAutoService(cfg).run("large task", plan_file=str(plan), max_retries=1)

        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["details"]["retry_count"], 1)
        text = (self.project_root / "tracked.txt").read_text(encoding="utf-8")
        self.assertIn("flaky pass", text)
        self.assertNotIn("flaky fail", text)
        self.assertIn("tracked.txt", self._git("diff", "--cached", "--name-only").stdout)

    def test_dirty_paths_block_without_rollback(self) -> None:
        cfg = load_config(self._write_config(paths=["tracked.txt"]))
        (self.project_root / "tracked.txt").write_text("user dirty\n", encoding="utf-8")
        plan = self._write_plan([{"id": "task_001", "title": "PASS", "prompt": "PASS"}])

        payload = OpencodeAutoService(cfg).run("large task", plan_file=str(plan), max_retries=0)

        self.assertEqual(payload["status"], "blocked")
        self.assertEqual((self.project_root / "tracked.txt").read_text(encoding="utf-8"), "user dirty\n")

    def test_staged_changes_do_not_block(self) -> None:
        cfg = load_config(self._write_config(paths=["tracked.txt"]))
        (self.project_root / "tracked.txt").write_text("staged user work\n", encoding="utf-8")
        self._git("add", "tracked.txt")
        plan = self._write_plan([{"id": "task_001", "title": "PASS", "prompt": "PASS"}])

        payload = OpencodeAutoService(cfg).run("large task", plan_file=str(plan), max_retries=0)

        self.assertEqual(payload["status"], "pass")
        cached = self._git("diff", "--cached", "--name-only").stdout
        self.assertIn("tracked.txt", cached)

    def test_untracked_file_still_blocks(self) -> None:
        cfg = load_config(self._write_config(paths=["untracked.txt"]))
        (self.project_root / "untracked.txt").write_text("new user work\n", encoding="utf-8")
        plan = self._write_plan([{"id": "task_001", "title": "PASS", "prompt": "PASS"}])

        payload = OpencodeAutoService(cfg).run("large task", plan_file=str(plan), max_retries=0)

        self.assertEqual(payload["status"], "blocked")
        self.assertIn("untracked.txt", payload["details"]["dirty"])

    def test_tracked_python_cache_is_ignored_and_not_staged(self) -> None:
        pycache = self.project_root / "agent_workbench" / "core" / "__pycache__"
        pycache.mkdir(parents=True)
        pyc = pycache / "config.cpython-38.pyc"
        pyc.write_text("cached-before\n", encoding="utf-8")
        self._git("add", "agent_workbench/core/__pycache__/config.cpython-38.pyc")
        self._git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "track pyc")
        pyc.write_text("cached-after\n", encoding="utf-8")
        cfg = load_config(self._write_config(paths=["tracked.txt", "agent_workbench"]))
        plan = self._write_plan([{"id": "task_001", "title": "PASS", "prompt": "PASS"}])

        payload = OpencodeAutoService(cfg).run("large task", plan_file=str(plan), max_retries=0)

        self.assertEqual(payload["status"], "pass")
        cached = self._git("diff", "--cached", "--name-only").stdout
        self.assertIn("tracked.txt", cached)
        self.assertNotIn(".pyc", cached)

    def test_ignored_untracked_directories_do_not_break_success_staging(self) -> None:
        (self.project_root / ".gitignore").write_text("agent_workbench/runtime/ignored_validation/\n", encoding="utf-8")
        ignored_dir = self.project_root / "agent_workbench" / "runtime" / "ignored_validation"
        ignored_dir.mkdir(parents=True)
        (ignored_dir / "agent_workbench.yaml").write_text("ignored\n", encoding="utf-8")
        self._git("add", ".gitignore")
        self._git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "ignore runtime")
        cfg = load_config(self._write_config(paths=["tracked.txt", "agent_workbench"]))
        plan = self._write_plan([{"id": "task_001", "title": "PASS", "prompt": "PASS"}])

        payload = OpencodeAutoService(cfg).run("large task", plan_file=str(plan), max_retries=0)

        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["details"]["tasks"][0]["git_add"]["exit_code"], 0)
        self.assertIn("tracked.txt", self._git("diff", "--cached", "--name-only").stdout)

    def test_failed_attempt_restores_index_to_baseline(self) -> None:
        cfg = load_config(self._write_config(paths=["tracked.txt", "created.txt"]))
        (self.project_root / "tracked.txt").write_text("staged baseline\n", encoding="utf-8")
        self._git("add", "tracked.txt")
        plan = self._write_plan([{"id": "task_001", "title": "STAGE_AND_FAIL", "prompt": "STAGE_AND_FAIL"}])

        payload = OpencodeAutoService(cfg).run("large task", plan_file=str(plan), max_retries=0)

        self.assertEqual(payload["status"], "fail")
        self.assertEqual((self.project_root / "tracked.txt").read_text(encoding="utf-8"), "staged baseline\n")
        cached = self._git("diff", "--cached", "--name-only").stdout
        self.assertIn("tracked.txt", cached)
        self.assertNotIn("created.txt", cached)
        self.assertFalse((self.project_root / "created.txt").exists())
        self.assertEqual(self._git("diff", "--name-only").stdout.strip(), "")

    def test_dispatch_dry_run_returns_json(self) -> None:
        config_path = self._write_config(paths=["tracked.txt"])
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = workbench.dispatch_args(
                [
                    "opencode-auto",
                    "run",
                    "--config",
                    str(config_path),
                    "--task",
                    "dry smoke",
                    "--dry-run",
                    "--json",
                ]
            )
        payload = json.loads(stdout.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "pass")
        self.assertTrue(payload["details"]["dry_run"])

    def _write_config(self, *, paths: list[str]) -> Path:
        config_path = self.workbench_root / "agent_workbench.yaml"
        config_path.write_text(
            "project:\n"
            "  name: demo\n"
            "  root: ../Git Project With Spaces\n"
            "  build_dir: build\n"
            "  artifact_file: build/demo.elf\n"
            "  compile_commands: build/compile_commands.json\n"
            "opencode_auto:\n"
            f"  command: {json.dumps(sys.executable)}\n"
            "  args:\n"
            f"    - {json.dumps(str(self.worker))}\n"
            "  planner_args:\n"
            f"    - {json.dumps(str(self.worker))}\n"
            "  max_retries: 1\n"
            "  timeout_sec: 30\n"
            "  planner_timeout_sec: 30\n"
            "  runtime_dir: runtime/opencode_auto\n"
            "  git:\n"
            "    enabled: true\n"
            "    worktree: .\n"
            "    require_clean: true\n"
            "    paths:\n"
            + "".join(f"      - {json.dumps(path)}\n" for path in paths),
            encoding="utf-8",
        )
        return config_path

    def _write_plan(self, tasks: list[dict[str, str]]) -> Path:
        path = self.project_root / "plan.json"
        path.write_text(json.dumps({"tasks": tasks}, ensure_ascii=False), encoding="utf-8")
        return path

    def _write_worker(self) -> None:
        self.worker.write_text(
            textwrap.dedent(
                f"""
                import json
                import subprocess
                import sys
                from pathlib import Path

                root = Path.cwd()
                prompt = sys.argv[-1]
                tracked = root / "tracked.txt"
                created = root / "created.txt"
                marker = Path({str(self.marker)!r})

                if "FAIL_ALWAYS" in prompt:
                    tracked.write_text("failed attempt\\n", encoding="utf-8")
                    created.write_text("untracked failed\\n", encoding="utf-8")
                    print(json.dumps({{"ok": False}}))
                    raise SystemExit(7)

                if "STAGE_AND_FAIL" in prompt:
                    tracked.write_text("staged failed attempt\\n", encoding="utf-8")
                    created.write_text("staged created\\n", encoding="utf-8")
                    subprocess.run(["git", "add", "tracked.txt", "created.txt"], cwd=str(root), check=False)
                    print(json.dumps({{"ok": False, "staged": True}}))
                    raise SystemExit(9)

                if "FLAKY" in prompt and not marker.exists():
                    marker.write_text("seen", encoding="utf-8")
                    tracked.write_text("flaky fail\\n", encoding="utf-8")
                    created.write_text("untracked flaky\\n", encoding="utf-8")
                    print(json.dumps({{"ok": False, "flaky": True}}))
                    raise SystemExit(8)

                with tracked.open("a", encoding="utf-8") as fp:
                    fp.write(("flaky pass" if "FLAKY" in prompt else prompt.splitlines()[0]) + "\\n")
                print(json.dumps({{"ok": True}}))
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )

    def _git(self, *args: str) -> subprocess.CompletedProcess[str]:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(self.project_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if proc.returncode != 0:
            self.fail(f"git {' '.join(args)} failed: {proc.stderr}")
        return proc


if __name__ == "__main__":
    unittest.main()
