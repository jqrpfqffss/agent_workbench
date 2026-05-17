from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from subprocess import run

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import workbench
from core.remote_dt_service import CommandResult, DT_LOG_FILES, RemoteDtService, parse_dt_log


class FakeRemoteRunner:
    def __init__(
        self,
        logs: dict[str, str] | None = None,
        exit_codes: dict[str, int] | None = None,
        scp_exit_code: int = 0,
    ):
        self.logs = logs or {}
        self.exit_codes = exit_codes or {}
        self.scp_exit_code = scp_exit_code
        self.calls: list[list[str]] = []
        self.ssh_steps: list[str] = []

    def __call__(self, argv, timeout: int) -> CommandResult:
        call = [str(item) for item in argv]
        self.calls.append(call)
        if call[0] == "ssh":
            step = self._step_from_text(call[-1])
            self.ssh_steps.append(step)
            return CommandResult(call, self.exit_codes.get(step, 0), "", "")
        if call[0] == "scp":
            self._write_scp_dest(call)
            stderr = "scp failed" if self.scp_exit_code else ""
            return CommandResult(call, self.scp_exit_code, "", stderr)
        return CommandResult(call, 0, "", "")

    @staticmethod
    def _step_from_text(text: str) -> str:
        for step, name in DT_LOG_FILES.items():
            if name in text:
                return step
        return "unknown"

    def _write_scp_dest(self, call: list[str]) -> None:
        source = call[-2]
        dest = Path(call[-1])
        dest.mkdir(parents=True, exist_ok=True)
        for step, name in DT_LOG_FILES.items():
            if name in source or "dt_*.log" in source:
                (dest / name).write_text(self.logs.get(step, ""), encoding="utf-8")
        for step in ("build", "execute", "coverage"):
            result_name = f"dt_{step}_result.json"
            if result_name in source or "dt_*.json" in source:
                (dest / result_name).write_text(
                    json.dumps({"step": step, "exit_code": self.exit_codes.get(step, 0)}),
                    encoding="utf-8",
                )
        if "coverage" in source:
            coverage_dir = dest / "coverage"
            coverage_dir.mkdir(parents=True, exist_ok=True)
            (coverage_dir / "index.html").write_text("coverage", encoding="utf-8")


class RemoteDtServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / "runtime" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="awb_remote_dt_", dir=temp_root))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _cfg(self, **remote_overrides):
        remote = {
            "enabled": True,
            "host": "10.0.0.8",
            "user": "dtuser",
            "port": 2222,
            "remote_project_dir": "/srv/project with space",
            "local_artifact_dir": str(self.temp_dir / "remote_dt"),
            "ssh": {
                "identity_file": "C:/Users/test/.ssh/id_rsa",
                "connect_timeout_sec": 11,
                "strict_host_key_checking": False,
            },
            "scripts": {
                "build": "./build.sh",
                "execute": "./execute.sh",
                "coverage": "./gen_coverage.sh",
            },
            "timeouts": {
                "build_sec": 600,
                "execute_sec": 1200,
                "coverage_sec": 600,
                "pull_sec": 300,
            },
            "artifacts": {
                "remote_work_dir": ".agent_workbench_remote_dt",
                "remote_log_dir": ".agent_workbench_remote_dt/logs",
                "remote_result_dir": ".agent_workbench_remote_dt/results",
                "remote_coverage_dir": "coverage",
                "pull_patterns": [
                    ".agent_workbench_remote_dt/logs/dt_*.log",
                    ".agent_workbench_remote_dt/results/dt_*.json",
                    "coverage/**",
                ],
            },
        }
        remote.update(remote_overrides)
        return {"project_root_path": self.temp_dir, "remote_dt": remote}

    def test_missing_required_config_returns_fail(self) -> None:
        for action in ("build", "execute", "coverage", "pipeline"):
            cfg = self._cfg(host="")
            payload = RemoteDtService(cfg, runner=FakeRemoteRunner()).run(action)
            self.assertEqual(payload["status"], "fail")
            self.assertIn("host", payload["summary"])

    def test_disabled_remote_dt_returns_fail(self) -> None:
        payload = RemoteDtService(self._cfg(enabled=False), runner=FakeRemoteRunner()).run("build")
        self.assertEqual(payload["status"], "fail")
        self.assertIn("not enabled", payload["summary"])

    def test_ssh_and_scp_commands_are_composed_from_config(self) -> None:
        runner = FakeRemoteRunner(logs={"build": "ok\n"})
        payload = RemoteDtService(self._cfg(), runner=runner).run("build")

        self.assertEqual(payload["status"], "pass")
        ssh_call = runner.calls[0]
        self.assertEqual(ssh_call[0], "ssh")
        self.assertIn("-p", ssh_call)
        self.assertIn("2222", ssh_call)
        self.assertIn("ConnectTimeout=11", ssh_call)
        self.assertIn("StrictHostKeyChecking=no", ssh_call)
        self.assertIn("C:/Users/test/.ssh/id_rsa", ssh_call)
        self.assertIn("dtuser@10.0.0.8", ssh_call)
        self.assertIn("bash", ssh_call)
        self.assertIn("dt_build.log", ssh_call[-1])

        scp_calls = [call for call in runner.calls if call[0] == "scp"]
        self.assertTrue(scp_calls)
        self.assertIn("-P", scp_calls[0])
        self.assertIn("2222", scp_calls[0])
        self.assertIn("dtuser@10.0.0.8:", scp_calls[0][-2])
        self.assertIn("dt_build.log", scp_calls[0][-2])

    def test_build_failure_skips_execute_and_coverage(self) -> None:
        runner = FakeRemoteRunner(logs={"build": "main.c:12: error: broken\n"}, exit_codes={"build": 2})
        payload = RemoteDtService(self._cfg(), runner=runner).run("pipeline")

        self.assertEqual(payload["status"], "fail")
        self.assertEqual(runner.ssh_steps, ["build"])
        self.assertEqual(payload["steps"][1]["status"], "skipped")
        self.assertEqual(payload["steps"][2]["status"], "skipped")

    def test_execute_failure_skips_coverage(self) -> None:
        runner = FakeRemoteRunner(logs={"execute": "FAILED expected 1 actual 0\n"}, exit_codes={"execute": 7})
        payload = RemoteDtService(self._cfg(), runner=runner).run("pipeline")

        self.assertEqual(payload["status"], "fail")
        self.assertEqual(runner.ssh_steps, ["build", "execute"])
        self.assertEqual(payload["steps"][2]["status"], "skipped")
        self.assertTrue(payload["test_failures"])

    def test_pipeline_runs_build_execute_coverage_in_order(self) -> None:
        runner = FakeRemoteRunner()
        payload = RemoteDtService(self._cfg(), runner=runner).run("pipeline")

        self.assertEqual(payload["status"], "pass")
        self.assertEqual(runner.ssh_steps, ["build", "execute", "coverage"])

    def test_artifact_pull_failure_marks_step_failed(self) -> None:
        runner = FakeRemoteRunner(scp_exit_code=1)
        payload = RemoteDtService(self._cfg(), runner=runner).run("build")

        self.assertEqual(payload["status"], "fail")
        self.assertEqual(payload["steps"][0]["exit_code"], 1)
        self.assertEqual(payload["steps"][0]["remote_exit_code"], 0)
        self.assertIn("failed to pull remote DT artifact", payload["errors"][0]["message"])

    def test_outputs_result_json_and_summary_md(self) -> None:
        root = self.temp_dir / "remote_dt"
        payload = RemoteDtService(self._cfg(), runner=FakeRemoteRunner()).run("pipeline")

        self.assertEqual(payload["status"], "pass")
        self.assertTrue((root / "dt_remote_result.json").exists())
        self.assertTrue((root / "dt_remote_summary.md").exists())

    def test_log_parser_recognizes_common_findings(self) -> None:
        log_path = self.temp_dir / "dt_build.log"
        log_path.write_text(
            "foo.c:10:5: error: bad token\n"
            "bar.c:20: warning: unused variable\n"
            "undefined reference to `x'\n"
            "No such file or directory\n"
            "Permission denied\n"
            "FAILED expected true actual false\n",
            encoding="utf-8",
        )

        parsed = parse_dt_log(log_path, "build")

        self.assertGreaterEqual(len(parsed["errors"]), 4)
        self.assertEqual(len(parsed["warnings"]), 1)
        self.assertTrue(parsed["test_failures"])

    def test_all_dt_log_file_names_use_dt_prefix(self) -> None:
        for name in DT_LOG_FILES.values():
            self.assertTrue(name.startswith("dt_"))

    def test_remote_dt_doctor_subcommand_does_not_exist(self) -> None:
        parser = workbench.build_parser()
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parser.parse_args(["remote-dt", "doctor"])

    def test_real_cli_pipeline_with_fake_ssh_scp_on_windows(self) -> None:
        fake_bin = self.temp_dir / "fake_bin"
        fake_bin.mkdir(parents=True, exist_ok=True)
        call_log = self.temp_dir / "calls.txt"
        artifact_dir = self.temp_dir / "cli_remote_dt"
        config_path = self.temp_dir / "agent_workbench.yaml"
        root_bat = Path(__file__).resolve().parents[2] / "agent_workbench.bat"
        self._write_fake_ssh_scp(fake_bin, call_log)
        fake_ssh = (fake_bin / "fake_ssh.py").resolve()
        fake_scp = (fake_bin / "fake_scp.py").resolve()
        py_exe = str(sys.executable).replace(chr(92), "/")
        fake_ssh_text = str(fake_ssh).replace(chr(92), "/")
        fake_scp_text = str(fake_scp).replace(chr(92), "/")
        config_path.write_text(
            "project:\n"
            "  root: ../../..\n"
            "remote_dt:\n"
            "  enabled: true\n"
            "  host: 127.0.0.1\n"
            "  user: dtuser\n"
            "  port: 2200\n"
            "  remote_project_dir: /srv/remote project\n"
            f"  local_artifact_dir: {str(artifact_dir).replace(chr(92), '/')}\n"
            "  ssh:\n"
            "    identity_file: ''\n"
            "    connect_timeout_sec: 3\n"
            "    strict_host_key_checking: false\n"
            f"    ssh_command: '\"{py_exe}\" \"{fake_ssh_text}\"'\n"
            f"    scp_command: '\"{py_exe}\" \"{fake_scp_text}\"'\n"
            "  scripts:\n"
            "    build: ./build.sh\n"
            "    execute: ./execute.sh\n"
            "    coverage: ./gen_coverage.sh\n",
            encoding="utf-8",
        )

        env = dict(os.environ)
        env["FAKE_REMOTE_DT_CALL_LOG"] = str(call_log)
        proc = run(
            [
                "cmd",
                "/c",
                str(root_bat),
                "remote-dt",
                "pipeline",
                "--config",
                str(config_path),
                "--json",
            ],
            cwd=str(Path(__file__).resolve().parents[2]),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(call_log.read_text(encoding="utf-8").splitlines(), ["build", "execute", "coverage"])
        self.assertTrue((artifact_dir / "dt_remote_result.json").exists())
        self.assertTrue((artifact_dir / "dt_remote_summary.md").exists())
        self.assertTrue((artifact_dir / "logs" / "dt_build.log").exists())
        self.assertTrue((artifact_dir / "logs" / "dt_execute.log").exists())
        self.assertTrue((artifact_dir / "logs" / "dt_coverage.log").exists())
        self.assertTrue((artifact_dir / "coverage" / "index.html").exists())

    def test_real_cli_pipeline_stops_after_fake_build_failure(self) -> None:
        fake_bin = self.temp_dir / "fake_bin_fail"
        fake_bin.mkdir(parents=True, exist_ok=True)
        call_log = self.temp_dir / "calls_fail.txt"
        artifact_dir = self.temp_dir / "cli_remote_dt_fail"
        config_path = self.temp_dir / "agent_workbench_fail.yaml"
        root_bat = Path(__file__).resolve().parents[2] / "agent_workbench.bat"
        self._write_fake_ssh_scp(fake_bin, call_log)
        fake_ssh = (fake_bin / "fake_ssh.py").resolve()
        fake_scp = (fake_bin / "fake_scp.py").resolve()
        py_exe = str(sys.executable).replace(chr(92), "/")
        fake_ssh_text = str(fake_ssh).replace(chr(92), "/")
        fake_scp_text = str(fake_scp).replace(chr(92), "/")
        config_path.write_text(
            "project:\n"
            "  root: ../../..\n"
            "remote_dt:\n"
            "  enabled: true\n"
            "  host: 127.0.0.1\n"
            "  user: dtuser\n"
            "  remote_project_dir: /srv/remote project\n"
            f"  local_artifact_dir: {str(artifact_dir).replace(chr(92), '/')}\n"
            "  ssh:\n"
            f"    ssh_command: '\"{py_exe}\" \"{fake_ssh_text}\"'\n"
            f"    scp_command: '\"{py_exe}\" \"{fake_scp_text}\"'\n",
            encoding="utf-8",
        )

        env = dict(os.environ)
        env["FAKE_REMOTE_DT_CALL_LOG"] = str(call_log)
        env["FAKE_REMOTE_DT_FAIL_STEP"] = "build"
        proc = run(
            [
                "cmd",
                "/c",
                str(root_bat),
                "remote-dt",
                "pipeline",
                "--config",
                str(config_path),
                "--json",
            ],
            cwd=str(Path(__file__).resolve().parents[2]),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["status"], "fail")
        self.assertEqual(call_log.read_text(encoding="utf-8").splitlines(), ["build"])
        self.assertEqual(payload["steps"][1]["status"], "skipped")
        self.assertEqual(payload["steps"][2]["status"], "skipped")
        self.assertTrue(payload["errors"])

    def _write_fake_ssh_scp(self, fake_bin: Path, call_log: Path) -> None:
        fake_ssh = fake_bin / "fake_ssh.py"
        fake_scp = fake_bin / "fake_scp.py"
        fake_ssh.write_text(
            "from __future__ import annotations\n"
            "import os, sys\n"
            "text = sys.argv[-1]\n"
            "step = 'unknown'\n"
            "for candidate in ('build', 'execute', 'coverage'):\n"
            "    if f'dt_{candidate}.log' in text:\n"
            "        step = candidate\n"
            "log = os.environ.get('FAKE_REMOTE_DT_CALL_LOG')\n"
            "if log:\n"
            "    with open(log, 'a', encoding='utf-8') as fp:\n"
            "        fp.write(step + '\\n')\n"
            "sys.exit(2 if os.environ.get('FAKE_REMOTE_DT_FAIL_STEP') == step else 0)\n",
            encoding="utf-8",
        )
        fake_scp.write_text(
            "from __future__ import annotations\n"
            "import json, os, pathlib, sys\n"
            "source = sys.argv[-2]\n"
            "dest = pathlib.Path(sys.argv[-1])\n"
            "dest.mkdir(parents=True, exist_ok=True)\n"
            "fail_step = os.environ.get('FAKE_REMOTE_DT_FAIL_STEP', '')\n"
            "def content(step):\n"
            "    if step == fail_step:\n"
            "        return 'main.c:12: error: fake compile error\\nFAILED expected 1 actual 0\\n'\n"
            "    return f'{step} ok\\n'\n"
            "for step in ('build', 'execute', 'coverage'):\n"
            "    if f'dt_{step}.log' in source or 'dt_*.log' in source:\n"
            "        (dest / f'dt_{step}.log').write_text(content(step), encoding='utf-8')\n"
            "    if f'dt_{step}_result.json' in source or 'dt_*.json' in source:\n"
            "        code = 2 if step == fail_step else 0\n"
            "        (dest / f'dt_{step}_result.json').write_text(json.dumps({'step': step, 'exit_code': code}), encoding='utf-8')\n"
            "if 'coverage' in source:\n"
            "    cov = dest / 'coverage'\n"
            "    cov.mkdir(parents=True, exist_ok=True)\n"
            "    (cov / 'index.html').write_text('coverage ok', encoding='utf-8')\n"
            "sys.exit(0)\n",
            encoding="utf-8",
        )
        (fake_bin / "ssh.cmd").write_text(f"@echo off\r\n\"{sys.executable}\" \"{fake_ssh}\" %*\r\n", encoding="utf-8")
        (fake_bin / "scp.cmd").write_text(f"@echo off\r\n\"{sys.executable}\" \"{fake_scp}\" %*\r\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
