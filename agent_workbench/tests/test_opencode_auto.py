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
from core.opencode_auto_service import (  # type: ignore  # noqa: E402
    _extract_json_object,
    _extract_plan_from_stdout,
    _file_terms,
    _normalize_plan,
    _plan_mentions_file_terms,
    _safe_task_id,
    _unique_run_dir,
)


class OpencodeAutoCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / "runtime" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="awb_oa_", dir=temp_root))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_opencode_auto_is_registered(self) -> None:
        parser = workbench.build_parser()
        commands = parser._subparsers._group_actions[0].choices
        self.assertIn("opencode-auto", commands)

    def test_opencode_auto_requires_task(self) -> None:
        parser = workbench.build_parser()
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parser.parse_args(["opencode-auto", "run"])

    def test_opencode_auto_accepts_task_and_flags(self) -> None:
        parser = workbench.build_parser()
        parsed = parser.parse_args(
            ["opencode-auto", "run", "--task", "Do something", "--dry-run", "--max-retries", "2", "--json"]
        )
        self.assertEqual(parsed.command, "opencode-auto")
        self.assertEqual(parsed.action, "run")
        self.assertEqual(parsed.task, "Do something")
        self.assertTrue(parsed.dry_run)
        self.assertEqual(parsed.max_retries, 2)
        self.assertTrue(parsed.json)

    def test_opencode_auto_accepts_plan_file(self) -> None:
        parser = workbench.build_parser()
        parsed = parser.parse_args(
            ["opencode-auto", "run", "--task", "x", "--plan-file", str(self.temp_dir / "plan.json")]
        )
        self.assertEqual(parsed.plan_file, str(self.temp_dir / "plan.json"))


class TaskNormalizationTests(unittest.TestCase):
    def test_normalize_from_dict_tasks_array(self) -> None:
        plan = {
            "tasks": [
                {"id": "t1", "title": "Install deps", "prompt": "Install all deps"},
                {
                    "id": "t2",
                    "title": "Run tests",
                    "prompt": "Run the test suite",
                    "acceptance": ["all pass"],
                },
            ]
        }
        tasks = _normalize_plan(plan, "")
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0]["id"], "t1")
        self.assertEqual(tasks[0]["title"], "Install deps")
        self.assertEqual(tasks[1]["acceptance"], ["all pass"])

    def test_normalize_from_flat_list(self) -> None:
        plan = [
            "Do first thing",
            {"title": "Second thing", "prompt": "Do second thing"},
        ]
        tasks = _normalize_plan(plan, "")
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0]["id"], "task_001")
        self.assertEqual(tasks[0]["title"], "Do first thing")
        self.assertEqual(tasks[0]["prompt"], "Do first thing")
        self.assertEqual(tasks[1]["id"], "task_002")

    def test_normalize_fallback_when_empty(self) -> None:
        tasks = _normalize_plan({}, "fallback task text")
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["id"], "task_001")
        self.assertEqual(tasks[0]["title"], "Task 1")
        self.assertEqual(tasks[0]["prompt"], "fallback task text")

    def test_normalize_skips_placeholder_prompt_and_falls_back(self) -> None:
        tasks = _normalize_plan({"tasks": [{"title": "...", "prompt": "..."}]}, "real task")
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["title"], "Task 1")
        self.assertEqual(tasks[0]["prompt"], "real task")

    def test_normalize_fallback_empty_when_no_fallback(self) -> None:
        tasks = _normalize_plan({}, "")
        self.assertEqual(len(tasks), 0)

    def test_normalize_title_falls_back_to_title_as_prompt(self) -> None:
        plan = {"tasks": [{"title": "no prompt"}, {"title": "has prompt", "prompt": "do it"}]}
        tasks = _normalize_plan(plan, "")
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0]["prompt"], "no prompt")
        self.assertEqual(tasks[1]["prompt"], "do it")

    def test_normalize_string_acceptance_to_list(self) -> None:
        plan = {"tasks": [{"title": "x", "prompt": "y", "acceptance": "one check"}]}
        tasks = _normalize_plan(plan, "")
        self.assertEqual(tasks[0]["acceptance"], ["one check"])

    def test_safe_task_id_normal(self) -> None:
        self.assertEqual(_safe_task_id(1, "hello_world"), "hello_world")

    def test_safe_task_id_special_chars(self) -> None:
        self.assertEqual(_safe_task_id(1, "hello world!"), "hello_world")

    def test_safe_task_id_numeric_fallback(self) -> None:
        self.assertEqual(_safe_task_id(3, "!@#$%"), "task_003")

    def test_file_terms_extracts_known_source_and_text_files(self) -> None:
        self.assertEqual(_file_terms("Edit Core/Src/main.c and result.txt"), ["main.c", "result.txt"])

    def test_plan_relevance_requires_file_terms_from_original_task(self) -> None:
        tasks = [{"title": "scan project", "prompt": "Read README.md", "acceptance": []}]
        self.assertFalse(_plan_mentions_file_terms(tasks, "Update validation.txt and result.txt"))

    def test_plan_relevance_passes_when_no_file_terms(self) -> None:
        tasks = [{"title": "turn on led", "prompt": "Use CLI to turn on red LED", "acceptance": []}]
        self.assertTrue(_plan_mentions_file_terms(tasks, "Turn on red LED"))


class JSONExtractionTests(unittest.TestCase):
    def test_extract_simple_object(self) -> None:
        result = _extract_json_object('{"key": "value"}')
        self.assertIsNotNone(result)
        self.assertEqual(result["key"], "value")  # type: ignore[index]

    def test_extract_nested_object(self) -> None:
        result = _extract_json_object(
            'prefix text {"tasks":[{"id":"1","prompt":"hello"}]} suffix'
        )
        self.assertIsNotNone(result)
        self.assertIn("tasks", result)
        self.assertEqual(result["tasks"][0]["id"], "1")  # type: ignore[index]

    def test_extract_returns_none_for_no_json(self) -> None:
        result = _extract_json_object("no json here at all")
        self.assertIsNone(result)

    def test_extract_returns_none_for_empty_string(self) -> None:
        result = _extract_json_object("")
        self.assertIsNone(result)

    def test_extract_plan_from_stdout_direct_json(self) -> None:
        stdout = json.dumps({"tasks": [{"id": "1", "prompt": "hello"}]})
        result = _extract_plan_from_stdout(stdout)
        self.assertIsNotNone(result)
        self.assertIn("tasks", result)

    def test_extract_plan_from_stdout_no_tasks_key(self) -> None:
        stdout = json.dumps({"key": "value"})
        result = _extract_plan_from_stdout(stdout)
        self.assertIsNone(result)

    def test_extract_plan_from_jsonl(self) -> None:
        lines = [
            json.dumps({"delta": "step one"}),
            json.dumps({"delta": "step two"}),
            json.dumps({"text": '{"tasks":[{"id":"1","prompt":"go"}]}'}),
        ]
        result = _extract_plan_from_stdout("\n".join(lines))
        self.assertIsNotNone(result)
        self.assertIn("tasks", result)


class UniqueRunDirTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / "runtime" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="awb_urd_", dir=temp_root))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_creates_unique_directory(self) -> None:
        dir1 = _unique_run_dir(self.temp_dir)
        dir2 = _unique_run_dir(self.temp_dir)
        self.assertTrue(dir1.exists())
        self.assertTrue(dir2.exists())
        self.assertNotEqual(str(dir1), str(dir2))

    def test_directory_naming_follows_timestamp_pattern(self) -> None:
        dir1 = _unique_run_dir(self.temp_dir)
        name = dir1.name
        self.assertRegex(name, r"^\d{8}_\d{6}")


if __name__ == "__main__":
    unittest.main()
