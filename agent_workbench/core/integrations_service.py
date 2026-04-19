from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - env specific
    raise RuntimeError(
        "PyYAML is required. Run agent_workbench\\bin\\setup.bat first."
    ) from exc

from .utils import ensure_dir, render_template


@dataclass
class IntegrationManifest:
    id: str
    display_name: str
    description: str
    files: list[dict]
    uses_values: list[str]
    doctor: dict
    pack_dir: Path


def _integration_root(workbench_root: Path) -> Path:
    return Path(workbench_root) / "integrations"


def _invalid_manifest(pack_dir: Path, message: str) -> IntegrationManifest:
    return IntegrationManifest(
        id=pack_dir.name,
        display_name=pack_dir.name,
        description=f"invalid manifest: {message}",
        files=[],
        uses_values=[],
        doctor={},
        pack_dir=pack_dir,
    )


def _normalize_file_specs(raw_files: Any) -> list[dict]:
    if not isinstance(raw_files, list):
        raise ValueError("files must be a list")
    specs: list[dict] = []
    for index, item in enumerate(raw_files, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"files[{index}] must be a mapping")
        src = str(item.get("src", "")).strip()
        dst = str(item.get("dst", "")).strip()
        if not src or not dst:
            raise ValueError(f"files[{index}] must include non-empty src and dst")
        specs.append(
            {
                "src": src.replace("\\", "/"),
                "dst": dst.replace("\\", "/"),
                "render": bool(item.get("render", True)),
            }
        )
    return specs


def _normalize_doctor(raw_doctor: Any) -> dict:
    if raw_doctor is None:
        return {"required_files": [], "markers": {}}
    if not isinstance(raw_doctor, dict):
        raise ValueError("doctor must be a mapping")
    required_files = [str(item).strip().replace("\\", "/") for item in raw_doctor.get("required_files", []) if str(item).strip()]
    markers: dict[str, list[str]] = {}
    raw_markers = raw_doctor.get("markers", {})
    if raw_markers:
        if not isinstance(raw_markers, dict):
            raise ValueError("doctor.markers must be a mapping")
        for path_text, marker_list in raw_markers.items():
            key = str(path_text).strip().replace("\\", "/")
            if not key:
                continue
            if isinstance(marker_list, list):
                values = [str(item) for item in marker_list if str(item).strip()]
            else:
                values = [str(marker_list)]
            markers[key] = values
    return {"required_files": required_files, "markers": markers}


def _safe_project_target(project_root: Path, relative_path: str) -> Path:
    root = Path(project_root)
    root_resolved = root.resolve()
    target = root / Path(relative_path)
    target_resolved = target.resolve()
    try:
        target_resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise RuntimeError(f"path escapes project root: {relative_path}") from exc
    return target


def _safe_pack_source(pack_dir: Path, relative_path: str) -> Path:
    files_root = Path(pack_dir) / "files"
    files_root_resolved = files_root.resolve()
    source = files_root / Path(relative_path)
    source_resolved = source.resolve()
    try:
        source_resolved.relative_to(files_root_resolved)
    except ValueError as exc:
        raise RuntimeError(f"path escapes integration pack: {relative_path}") from exc
    return source


def load_manifest(manifest_path: Path) -> IntegrationManifest:
    data = yaml.safe_load(Path(manifest_path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("manifest must be a mapping")

    manifest_id = str(data.get("id", "")).strip()
    display_name = str(data.get("display_name", "")).strip()
    description = str(data.get("description", "")).strip()
    if not manifest_id or not display_name or not description:
        raise ValueError("manifest requires id, display_name, and description")

    return IntegrationManifest(
        id=manifest_id,
        display_name=display_name,
        description=description,
        files=_normalize_file_specs(data.get("files", [])),
        uses_values=[str(item).strip() for item in data.get("uses_values", []) if str(item).strip()],
        doctor=_normalize_doctor(data.get("doctor")),
        pack_dir=Path(manifest_path).resolve().parent,
    )


def discover_integrations(workbench_root: Path) -> list[IntegrationManifest]:
    root = _integration_root(Path(workbench_root))
    if not root.exists():
        return []
    manifests: list[IntegrationManifest] = []
    for pack_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        manifest_path = pack_dir / "manifest.yaml"
        if not manifest_path.exists():
            continue
        try:
            manifests.append(load_manifest(manifest_path))
        except Exception as exc:
            manifests.append(_invalid_manifest(pack_dir, str(exc)))
    return manifests


def collect_values(cfg: dict) -> dict[str, str]:
    project = cfg.get("project", {})
    uart = cfg.get("uart", {})
    diag_uart = cfg.get("diag_uart", {})
    agent = cfg.get("agent", {})
    return {
        "project_name": str(project.get("name", "")),
        "ready_banner": str(uart.get("ready_banner", "")),
        "prompt": str(uart.get("prompt", "")),
        "uart_port": str(uart.get("port", "")),
        "uart_baud": str(uart.get("baudrate", "")),
        "diag_uart_port": str(diag_uart.get("port", "")),
        "build_dir": str(project.get("build_dir_path", "")),
        "default_profile": str(agent.get("default_profile", "")),
        "source_dirs_csv": ", ".join(str(item) for item in project.get("source_dirs", [])),
    }


def is_integration_installed(cfg: dict, manifest: IntegrationManifest) -> bool:
    if manifest.description.startswith("invalid manifest:"):
        return False
    project_root = Path(cfg["project_root_path"])
    for relative_path in manifest.doctor.get("required_files", []):
        if not _safe_project_target(project_root, str(relative_path)).exists():
            return False
    return True


def install_integration(cfg: dict, manifest: IntegrationManifest) -> list[Path]:
    if manifest.description.startswith("invalid manifest:"):
        raise RuntimeError(manifest.description)

    project_root = Path(cfg["project_root_path"])
    written: list[Path] = []
    values = collect_values(cfg)

    if not (manifest.pack_dir / "files").exists():
        raise RuntimeError(f"integration pack missing files directory: {manifest.pack_dir / 'files'}")

    for item in manifest.files:
        source_path = _safe_pack_source(manifest.pack_dir, str(item.get("src", "")))
        if not source_path.exists():
            raise RuntimeError(f"integration source file missing: {source_path}")
        if source_path.stat().st_size > 1_000_000:
            print(
                f"[integration:{manifest.id}] warning: large source file {source_path}",
                file=sys.stderr,
            )

        target_path = _safe_project_target(project_root, str(item.get("dst", "")))
        ensure_dir(target_path.parent)

        if bool(item.get("render", True)):
            rendered = render_template(source_path.read_text(encoding="utf-8"), values)
            target_path.write_text(rendered, encoding="utf-8")
        else:
            target_path.write_bytes(source_path.read_bytes())
        written.append(target_path)

    return written


def check_integration(cfg: dict, manifest: IntegrationManifest) -> list[dict]:
    results: list[dict] = []
    prefix = f"integration::{manifest.id}::"
    project_root = Path(cfg["project_root_path"])
    values = collect_values(cfg)

    if manifest.description.startswith("invalid manifest:"):
        return [
            {
                "name": f"{prefix}manifest",
                "level": "fail",
                "detail": manifest.description,
            }
        ]

    files_dir = manifest.pack_dir / "files"
    if not files_dir.exists():
        results.append(
            {
                "name": f"{prefix}pack",
                "level": "fail",
                "detail": f"missing files directory: {files_dir}",
            }
        )
        return results

    missing_sources: list[str] = []
    for item in manifest.files:
        try:
            source_path = _safe_pack_source(manifest.pack_dir, str(item.get("src", "")))
        except RuntimeError as exc:
            missing_sources.append(str(exc))
            continue
        if not source_path.exists():
            missing_sources.append(str(item.get("src", "")))
    if missing_sources:
        results.append(
            {
                "name": f"{prefix}pack",
                "level": "fail",
                "detail": f"missing pack files: {', '.join(missing_sources)}",
            }
        )

    doctor = manifest.doctor or {}
    marker_map = doctor.get("markers", {}) if isinstance(doctor.get("markers", {}), dict) else {}
    checked_paths: list[str] = []
    for relative_path in doctor.get("required_files", []):
        path_text = str(relative_path).strip().replace("\\", "/")
        if path_text and path_text not in checked_paths:
            checked_paths.append(path_text)
    for relative_path in marker_map:
        path_text = str(relative_path).strip().replace("\\", "/")
        if path_text and path_text not in checked_paths:
            checked_paths.append(path_text)

    for relative_path in checked_paths:
        name = f"{prefix}{relative_path}"
        try:
            target = _safe_project_target(project_root, relative_path)
        except RuntimeError as exc:
            results.append({"name": name, "level": "fail", "detail": str(exc)})
            continue

        if not target.exists():
            results.append({"name": name, "level": "warn", "detail": f"missing {target}"})
            continue

        missing_markers: list[str] = []
        markers = marker_map.get(relative_path, [])
        if markers:
            text = target.read_text(encoding="utf-8", errors="ignore")
            for marker in markers:
                rendered_marker = render_template(str(marker), values)
                if rendered_marker and rendered_marker not in text:
                    missing_markers.append(rendered_marker)
        if missing_markers:
            detail = f"missing markers: {', '.join(missing_markers)}"
            results.append({"name": name, "level": "warn", "detail": detail})
        else:
            results.append({"name": name, "level": "ok", "detail": str(target)})

    return results


def remove_integration(cfg: dict, manifest: IntegrationManifest) -> list[Path]:
    project_root = Path(cfg["project_root_path"])
    project_root_resolved = project_root.resolve()
    removed: list[Path] = []

    for item in manifest.files:
        target = _safe_project_target(project_root, str(item.get("dst", "")))
        if not target.exists():
            continue
        if target.is_dir():
            raise RuntimeError(f"integration target must be a file: {target}")
        target.unlink()
        removed.append(target)

        parent = target.parent
        while parent.resolve() != project_root_resolved and parent.exists():
            if any(parent.iterdir()):
                break
            parent.rmdir()
            parent = parent.parent

    return removed
