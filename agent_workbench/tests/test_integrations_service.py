from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from agent_workbench.core import integrations_service


class IntegrationsServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="awb_integ_"))
        self.workbench_root = self.tmp / "agent_workbench"
        self.project_root = self.tmp / "project"
        self.project_root.mkdir(parents=True)
        pack_dir = self.workbench_root / "integrations" / "dummy"
        (pack_dir / "files").mkdir(parents=True)
        (pack_dir / "manifest.yaml").write_text(
            "id: dummy\n"
            "display_name: Dummy\n"
            "description: test pack\n"
            "files:\n"
            "  - src: hello.md.tpl\n"
            "    dst: hello.md\n"
            "uses_values: [project_name]\n"
            "doctor:\n"
            "  required_files:\n"
            "    - hello.md\n"
            "  markers:\n"
            "    hello.md:\n"
            '      - "{project_name}"\n',
            encoding="utf-8",
        )
        (pack_dir / "files" / "hello.md.tpl").write_text(
            "project is {project_name}\n", encoding="utf-8"
        )
        self.cfg = {
            "project_root_path": self.project_root,
            "agent_workbench_root_path": self.workbench_root,
            "project": {"name": "demo_proj", "source_dirs": [], "build_dir_path": self.tmp / "build"},
            "uart": {"ready_banner": "R", "prompt": "P", "port": "COM3", "baudrate": 115200},
            "diag_uart": {"port": "COM4"},
            "agent": {"default_profile": "balanced_local"},
        }

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_discover_integrations_finds_manifest_subdirs(self) -> None:
        manifests = integrations_service.discover_integrations(self.workbench_root)
        ids = [manifest.id for manifest in manifests]
        self.assertIn("dummy", ids)

    def test_install_integration_writes_expected_files_with_rendered_values(self) -> None:
        [manifest] = integrations_service.discover_integrations(self.workbench_root)
        written = integrations_service.install_integration(self.cfg, manifest)
        hello = self.project_root / "hello.md"
        self.assertIn(hello, written)
        self.assertEqual(hello.read_text(encoding="utf-8"), "project is demo_proj\n")

    def test_install_integration_rejects_path_traversal(self) -> None:
        pack_dir = self.workbench_root / "integrations" / "evil"
        (pack_dir / "files").mkdir(parents=True)
        (pack_dir / "manifest.yaml").write_text(
            "id: evil\n"
            "display_name: Evil\n"
            "description: x\n"
            "files:\n"
            "  - src: x.tpl\n"
            "    dst: ../outside.md\n"
            "doctor: {required_files: [], markers: {}}\n",
            encoding="utf-8",
        )
        (pack_dir / "files" / "x.tpl").write_text("x\n", encoding="utf-8")
        [manifest] = [item for item in integrations_service.discover_integrations(self.workbench_root) if item.id == "evil"]
        with self.assertRaises(RuntimeError):
            integrations_service.install_integration(self.cfg, manifest)

    def test_check_integration_reports_missing_files_as_warn(self) -> None:
        [manifest] = [item for item in integrations_service.discover_integrations(self.workbench_root) if item.id == "dummy"]
        results = integrations_service.check_integration(self.cfg, manifest)
        levels = [item["level"] for item in results]
        self.assertIn("warn", levels)

    def test_remove_integration_deletes_only_manifest_files(self) -> None:
        [manifest] = [item for item in integrations_service.discover_integrations(self.workbench_root) if item.id == "dummy"]
        integrations_service.install_integration(self.cfg, manifest)
        self.assertTrue((self.project_root / "hello.md").exists())
        removed = integrations_service.remove_integration(self.cfg, manifest)
        self.assertIn(self.project_root / "hello.md", removed)
        self.assertFalse((self.project_root / "hello.md").exists())
