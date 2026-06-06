from __future__ import annotations

import contextlib
import hashlib
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
        step_returns: dict[str, int] | None = None,
    ):
        self.logs = logs or {}
        self.exit_codes = exit_codes or {}
        self.scp_exit_code = scp_exit_code
        self.step_returns = step_returns or {}
        self.calls: list[list[str]] = []
        self.ssh_steps: list[str] = []

    def __call__(self, argv, timeout: int) -> CommandResult:
        call = [str(item) for item in argv]
        self.calls.append(call)
        if call[0] == "ssh":
            remote_cmd = call[-1]
            if remote_cmd.startswith("mkdir -p "):
                code = self.step_returns.get("mkdir", 0)
                return CommandResult(call, code, "", "mkdir failed" if code else "")
            if " && chmod +x " in remote_cmd:
                code = self.step_returns.get("chmod", 0)
                return CommandResult(call, code, "", "chmod failed" if code else "")
            if "REMOTE_DT_SCRIPT_CRLF" in remote_cmd:
                code = self.step_returns.get("verify", 0)
                stdout = ""
                if code == 21:
                    stdout = "REMOTE_DT_SCRIPT_CRLF:build.sh"
                return CommandResult(call, code, stdout, "verify failed" if code else "")
            step = self._step_from_text(remote_cmd)
            self.ssh_steps.append(step)
            return CommandResult(call, self.exit_codes.get(step, 0), "", "")
        if call[0] == "scp":
            if "@" in call[-1]:
                return CommandResult(call, self.scp_exit_code, "", "scp failed" if self.scp_exit_code else "")
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
            "dest_arg = sys.argv[-1]\n"
            "if '@' in dest_arg and ':' in dest_arg:\n"
            "    log = os.environ.get('FAKE_REMOTE_DT_CALL_LOG')\n"
            "    if log:\n"
            "        with open(log, 'a', encoding='utf-8') as fp:\n"
            "            fp.write('scp-push\\n')\n"
            "    sys.exit(0)\n"
            "dest = pathlib.Path(dest_arg)\n"
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


    def _create_upload_dir(
        self,
        with_build_sh_crlf: bool = True,
        with_build_lf: bool = False,
        with_extensionless_shebang: bool = False,
        with_binary: bool = False,
    ) -> Path:
        base_dir = self.temp_dir / "dt_upload"
        base_dir.mkdir(parents=True, exist_ok=True)
        (base_dir / "src").mkdir(parents=True, exist_ok=True)
        (base_dir / "src" / "main.c").write_text("int main() { return 0; }\n", encoding="utf-8")
        if with_build_sh_crlf:
            (base_dir / "build.sh").write_bytes(b"#!/bin/bash\r\necho hello\r\n")
        if with_build_lf:
            (base_dir / "build_lf.sh").write_bytes(b"#!/bin/bash\necho hello\n")
        (base_dir / "notes.txt").write_bytes(b"hello\r\nworld\r\n")
        if with_binary:
            (base_dir / "data.bin").write_bytes(bytes(range(256)))
        if with_extensionless_shebang:
            (base_dir / "build").write_bytes(b"#!/bin/bash\r\necho build\r\n")
        pycache = base_dir / "__pycache__"
        pycache.mkdir(exist_ok=True)
        (pycache / "cache.pyc").write_bytes(b"\x00\x01")
        return base_dir

    def _cfg_push_files(self, **overrides):
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
            "push_files": {
                "enabled": True,
                "local_dir": str(self.temp_dir / "dt_upload"),
                "remote_dir": "/home/dtuser/project/upload",
                "timeout_sec": 600,
                "dry_run": False,
                "exclude": ["**/__pycache__/**", "**/*.pyc"],
                "normalize_lf_for_shell_scripts": True,
                "chmod_executable_for_shell_scripts": True,
                "verify_shell_scripts_after_upload": True,
            },
        }
        remote.update(overrides)
        return {"project_root_path": self.temp_dir, "remote_dt": remote}

    # -- push-files parser tests --

    def test_parser_accepts_push_files(self) -> None:
        parser = workbench.build_parser()
        args = parser.parse_args(["remote-dt", "push-files", "--json"])
        self.assertEqual(args.action, "push-files")
        self.assertTrue(args.json)

    def test_local_dir_and_remote_dir_read_from_config(self) -> None:
        self._create_upload_dir()
        payload = RemoteDtService(
            self._cfg_push_files(), runner=FakeRemoteRunner()
        ).run("push-files")
        self.assertEqual(payload["status"], "pass")
        details = payload["details"]
        self.assertIn("dt_upload", details["local_dir"])
        self.assertEqual(details["remote_dir"], "/home/dtuser/project/upload")

    def test_dry_run_true_does_not_call_runner_and_counts_files(self) -> None:
        self._create_upload_dir()
        runner = FakeRemoteRunner()
        payload = RemoteDtService(
            self._cfg_push_files(**{"push_files": {"enabled": True, "local_dir": str(self.temp_dir / "dt_upload"), "remote_dir": "", "dry_run": True, "timeout_sec": 600, "exclude": [], "normalize_lf_for_shell_scripts": True, "chmod_executable_for_shell_scripts": True, "verify_shell_scripts_after_upload": True}}),
            runner=runner,
        ).run("push-files")
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(len(runner.calls), 0)
        self.assertGreater(payload["details"]["file_count"], 0)
        self.assertTrue(payload["details"]["dry_run"])

    def test_non_dry_run_composes_ssh_mkdir_then_scp(self) -> None:
        self._create_upload_dir()
        runner = FakeRemoteRunner()
        payload = RemoteDtService(
            self._cfg_push_files(), runner=runner
        ).run("push-files")
        self.assertEqual(payload["status"], "pass")
        self.assertGreaterEqual(len(runner.calls), 2)
        ssh_calls = [c for c in runner.calls if c[0] == "ssh"]
        scp_calls = [c for c in runner.calls if c[0] == "scp"]
        self.assertTrue(ssh_calls)
        self.assertTrue(scp_calls)
        # ssh mkdir comes before scp
        ssh_indices = [i for i, c in enumerate(runner.calls) if c[0] == "ssh"]
        scp_indices = [i for i, c in enumerate(runner.calls) if c[0] == "scp"]
        self.assertLess(ssh_indices[0], scp_indices[0])
        # scp has -r, port, ConnectTimeout, StrictHostKeyChecking, identity_file
        scp_call = scp_calls[0]
        self.assertIn("-r", scp_call)
        self.assertIn("-P", scp_call)
        self.assertIn("2222", scp_call)
        self.assertIn("ConnectTimeout=11", " ".join(scp_call))
        self.assertIn("StrictHostKeyChecking=no", " ".join(scp_call))
        self.assertIn("C:/Users/test/.ssh/id_rsa", " ".join(scp_call))
        self.assertIn("dtuser@10.0.0.8:", scp_call[-1])
        # source is staging content (ends with /.)
        self.assertTrue(scp_call[-2].endswith("/."), f"expected staging/., got {scp_call[-2]}")

    def test_push_files_details_include_verify_and_command_fields(self) -> None:
        self._create_upload_dir()
        payload = RemoteDtService(
            self._cfg_push_files(), runner=FakeRemoteRunner()
        ).run("push-files")
        details = payload["details"]
        self.assertEqual(payload["status"], "pass")
        self.assertTrue(details["normalize_lf_for_shell_scripts"])
        self.assertTrue(details["chmod_executable_for_shell_scripts"])
        self.assertTrue(details["verify_shell_scripts_after_upload"])
        self.assertIn("mkdir -p", details["mkdir_command"])
        self.assertIn("scp", details["scp_command"])
        self.assertIn("chmod +x", details["chmod_command"])
        self.assertIn("bash -n build.sh", details["verify_command"])
        self.assertTrue(details["verify"]["executed"])
        self.assertFalse(details["verify"]["build_sh_has_crlf"])
        self.assertTrue(details["verify"]["build_sh_bash_n"])
        self.assertIn("REMOTE_DT_VERIFY_BUILD_SH_OK", details["diagnostics"])

    def test_missing_local_dir_returns_fail(self) -> None:
        payload = RemoteDtService(
            self._cfg_push_files(**{"push_files": {"enabled": True, "local_dir": str(self.temp_dir / "nonexistent"), "remote_dir": "", "timeout_sec": 600, "dry_run": True, "exclude": [], "normalize_lf_for_shell_scripts": True, "chmod_executable_for_shell_scripts": True, "verify_shell_scripts_after_upload": True}}),
            runner=FakeRemoteRunner(),
        ).run("push-files")
        self.assertEqual(payload["status"], "fail")
        self.assertIn("does not exist", payload["summary"])

    def test_local_dir_as_file_returns_fail(self) -> None:
        file_path = self.temp_dir / "a_file.txt"
        file_path.write_text("not a dir", encoding="utf-8")
        payload = RemoteDtService(
            self._cfg_push_files(**{"push_files": {"enabled": True, "local_dir": str(file_path), "remote_dir": "", "timeout_sec": 600, "dry_run": True, "exclude": [], "normalize_lf_for_shell_scripts": True, "chmod_executable_for_shell_scripts": True, "verify_shell_scripts_after_upload": True}}),
            runner=FakeRemoteRunner(),
        ).run("push-files")
        self.assertEqual(payload["status"], "fail")
        self.assertIn("not a directory", payload["summary"])

    def test_mkdir_failure_returns_fail_no_scp(self) -> None:
        self._create_upload_dir()
        runner = FakeRemoteRunner(step_returns={"mkdir": 1})
        payload = RemoteDtService(
            self._cfg_push_files(), runner=runner
        ).run("push-files")
        self.assertEqual(payload["status"], "fail")
        steps = payload["steps"]
        self.assertEqual(steps[0]["name"], "prepare-staging")
        # No scp step
        step_names = [s["name"] for s in steps]
        self.assertNotIn("scp", step_names)

    def test_scp_failure_returns_fail(self) -> None:
        self._create_upload_dir()
        runner = FakeRemoteRunner(scp_exit_code=1)
        payload = RemoteDtService(
            self._cfg_push_files(), runner=runner
        ).run("push-files")
        self.assertEqual(payload["status"], "fail")
        step_names = [s["name"] for s in payload["steps"]]
        self.assertIn("scp", step_names)

    def test_exclude_filters_stats_and_staging(self) -> None:
        self._create_upload_dir()
        runner = FakeRemoteRunner()
        payload = RemoteDtService(
            self._cfg_push_files(), runner=runner
        ).run("push-files")
        self.assertGreater(payload["details"]["excluded_count"], 0)
        # __pycache__ files should be excluded
        details = payload["details"]
        self.assertGreater(details["excluded_count"], 0)

    def test_crlf_build_sh_source_stays_crlf_staging_becomes_lf(self) -> None:
        self._create_upload_dir(with_build_sh_crlf=True)
        build_sh = self.temp_dir / "dt_upload" / "build.sh"
        # Source stays CRLF
        self.assertIn(b"\r\n", build_sh.read_bytes())
        runner = FakeRemoteRunner()
        RemoteDtService(self._cfg_push_files(), runner=runner).run("push-files")
        # Source unchanged
        self.assertIn(b"\r\n", build_sh.read_bytes())

    def test_crlf_build_sh_normalized_files_includes_build_sh(self) -> None:
        self._create_upload_dir(with_build_sh_crlf=True)
        runner = FakeRemoteRunner()
        payload = RemoteDtService(
            self._cfg_push_files(), runner=runner
        ).run("push-files")
        self.assertIn("build.sh", payload["details"]["normalized_files"])

    def test_lf_build_sh_unchanged_not_listed_as_normalized(self) -> None:
        upload = self._create_upload_dir(with_build_sh_crlf=False, with_build_lf=True)
        # Verify build_lf.sh has LF only
        content = (upload / "build_lf.sh").read_bytes()
        self.assertNotIn(b"\r", content)
        runner = FakeRemoteRunner()
        payload = RemoteDtService(
            self._cfg_push_files(**{"push_files": {"enabled": True, "local_dir": str(upload), "remote_dir": "", "dry_run": True, "timeout_sec": 600, "exclude": ["**/__pycache__/**", "**/*.pyc"], "normalize_lf_for_shell_scripts": True, "chmod_executable_for_shell_scripts": True, "verify_shell_scripts_after_upload": True}}),
            runner=runner,
        ).run("push-files")
        self.assertNotIn("build_lf.sh", payload["details"]["normalized_files"])

    def test_extensionless_shebang_build_detected_normalized_chmod(self) -> None:
        self._create_upload_dir(with_build_sh_crlf=False, with_extensionless_shebang=True)
        runner = FakeRemoteRunner()
        payload = RemoteDtService(
            self._cfg_push_files(**{"push_files": {"enabled": True, "local_dir": str(self.temp_dir / "dt_upload"), "remote_dir": "", "dry_run": True, "timeout_sec": 600, "exclude": ["**/__pycache__/**", "**/*.pyc"], "normalize_lf_for_shell_scripts": True, "chmod_executable_for_shell_scripts": True, "verify_shell_scripts_after_upload": True}}),
            runner=runner,
        ).run("push-files")
        self.assertIn("build", payload["details"]["shell_script_files"])
        self.assertIn("build", payload["details"]["chmod_files"])

    def test_nested_shell_script_keeps_relative_path_for_chmod(self) -> None:
        upload = self._create_upload_dir(with_build_sh_crlf=False)
        scripts = upload / "scripts"
        scripts.mkdir()
        (scripts / "run.sh").write_bytes(b"#!/bin/bash\r\necho nested\r\n")
        payload = RemoteDtService(
            self._cfg_push_files(**{"push_files": {"enabled": True, "local_dir": str(upload), "remote_dir": "", "dry_run": True, "timeout_sec": 600, "exclude": ["**/__pycache__/**", "**/*.pyc"], "normalize_lf_for_shell_scripts": True, "chmod_executable_for_shell_scripts": True, "verify_shell_scripts_after_upload": True}}),
            runner=FakeRemoteRunner(),
        ).run("push-files")
        self.assertIn("scripts/run.sh", payload["details"]["shell_script_files"])
        self.assertIn("scripts/run.sh", payload["details"]["chmod_files"])
        self.assertIn("scripts/run.sh", payload["details"]["normalized_files"])

    def test_ordinary_crlf_notes_txt_not_normalized(self) -> None:
        self._create_upload_dir(with_build_sh_crlf=False, with_build_lf=True)
        notes = self.temp_dir / "dt_upload" / "notes.txt"
        notes.write_bytes(b"hello\r\nworld\r\n")
        runner = FakeRemoteRunner()
        payload = RemoteDtService(
            self._cfg_push_files(**{"push_files": {"enabled": True, "local_dir": str(self.temp_dir / "dt_upload"), "remote_dir": "", "dry_run": True, "timeout_sec": 600, "exclude": ["**/__pycache__/**", "**/*.pyc"], "normalize_lf_for_shell_scripts": True, "chmod_executable_for_shell_scripts": True, "verify_shell_scripts_after_upload": True}}),
            runner=runner,
        ).run("push-files")
        self.assertNotIn("notes.txt", payload["details"]["normalized_files"])

    def test_binary_file_sha256_unchanged_in_staging(self) -> None:
        self._create_upload_dir(with_build_sh_crlf=False, with_binary=True)
        bin_path = self.temp_dir / "dt_upload" / "data.bin"
        orig_hash = hashlib.sha256(bin_path.read_bytes()).hexdigest()
        runner = FakeRemoteRunner()
        payload = RemoteDtService(
            self._cfg_push_files(**{"push_files": {"enabled": True, "local_dir": str(self.temp_dir / "dt_upload"), "remote_dir": "", "dry_run": True, "timeout_sec": 600, "exclude": ["**/__pycache__/**", "**/*.pyc"], "normalize_lf_for_shell_scripts": True, "chmod_executable_for_shell_scripts": True, "verify_shell_scripts_after_upload": True}}),
            runner=runner,
        ).run("push-files")
        self.assertEqual(payload["status"], "pass")
        # Source binary unchanged
        self.assertEqual(orig_hash, hashlib.sha256(bin_path.read_bytes()).hexdigest())

    def test_chmod_failure_returns_fail(self) -> None:
        self._create_upload_dir()
        runner = FakeRemoteRunner(step_returns={"chmod": 1})
        payload = RemoteDtService(
            self._cfg_push_files(), runner=runner
        ).run("push-files")
        self.assertEqual(payload["status"], "fail")
        step_names = [s["name"] for s in payload["steps"]]
        self.assertIn("chmod-shell-scripts", step_names)

    def test_verify_exit_code_21_with_crlf_returns_fail(self) -> None:
        self._create_upload_dir()
        runner = FakeRemoteRunner(step_returns={"verify": 21})
        payload = RemoteDtService(
            self._cfg_push_files(), runner=runner
        ).run("push-files")
        self.assertEqual(payload["status"], "fail")
        self.assertTrue(
            any("REMOTE_DT_SCRIPT_CRLF" in e.get("message", "") for e in payload["errors"])
        )

    def test_cli_level_fake_ssh_scp_push_files(self) -> None:
        self._create_upload_dir()
        fake_bin = self.temp_dir / "fake_bin_push"
        fake_bin.mkdir(parents=True, exist_ok=True)
        call_log = self.temp_dir / "calls_push.txt"
        artifact_dir = self.temp_dir / "cli_push_dt"
        config_path = self.temp_dir / "agent_workbench_push.yaml"
        root_bat = Path(__file__).resolve().parents[2] / "agent_workbench.bat"
        self._write_fake_ssh_scp(fake_bin, call_log)
        fake_ssh = (fake_bin / "fake_ssh.py").resolve()
        fake_scp = (fake_bin / "fake_scp.py").resolve()
        py_exe = str(sys.executable).replace(chr(92), "/")
        fake_ssh_text = str(fake_ssh).replace(chr(92), "/")
        fake_scp_text = str(fake_scp).replace(chr(92), "/")
        upload_dir = str(self.temp_dir / "dt_upload").replace(chr(92), "/")
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
            "  push_files:\n"
            "    enabled: true\n"
            f"    local_dir: {upload_dir}\n"
            "    remote_dir: /home/dtuser/project/upload\n"
            "    timeout_sec: 600\n"
            "    dry_run: false\n"
            "    exclude:\n"
            "      - '**/__pycache__/**'\n"
            "      - '**/*.pyc'\n"
            "    normalize_lf_for_shell_scripts: false\n"
            "    chmod_executable_for_shell_scripts: false\n"
            "    verify_shell_scripts_after_upload: false\n",
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
                "push-files",
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
        self.assertTrue((artifact_dir / "dt_remote_result.json").exists())
        self.assertTrue((artifact_dir / "dt_remote_summary.md").exists())

    def test_non_json_push_files_outputs_marker_lines(self) -> None:
        upload = self._create_upload_dir()
        config_path = self.temp_dir / "agent_workbench_non_json_push.yaml"
        config_path.write_text(
            "project:\n"
            "  root: ../../..\n"
            "remote_dt:\n"
            "  enabled: true\n"
            "  remote_project_dir: /srv/project\n"
            f"  local_artifact_dir: {str(self.temp_dir / 'non_json_artifacts').replace(chr(92), '/')}\n"
            "  push_files:\n"
            "    enabled: true\n"
            f"    local_dir: {str(upload).replace(chr(92), '/')}\n"
            "    remote_dir: ''\n"
            "    dry_run: true\n"
            "    exclude:\n"
            "      - '**/__pycache__/**'\n"
            "      - '**/*.pyc'\n",
            encoding="utf-8",
        )

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = workbench.dispatch_args(["remote-dt", "push-files", "--config", str(config_path)])

        self.assertEqual(code, 0)
        text = stdout.getvalue()
        self.assertIn("REMOTE_DT_PUSH_FILES_START", text)
        self.assertIn("REMOTE_DT_PUSH_FILES_PREPARE_STAGING", text)
        self.assertIn("REMOTE_DT_SHELL_SCRIPT_DETECTED: build.sh", text)
        self.assertIn("REMOTE_DT_NORMALIZED_LF: build.sh", text)


if __name__ == "__main__":
    unittest.main()
