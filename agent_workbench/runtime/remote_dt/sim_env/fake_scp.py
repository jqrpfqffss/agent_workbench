from __future__ import annotations

import glob
import os
import shutil
import sys
from pathlib import Path


def _source_path(source: str) -> str:
    remote = source.split(":", 1)[1] if ":" in source else source
    remote = remote.strip()
    if len(remote) >= 2 and remote[0] == remote[-1] and remote[0] in {"'", '"'}:
        remote = remote[1:-1]
    root = Path(os.environ.get("REMOTE_DT_SIM_ROOT", Path(__file__).resolve().parent / "remote_root")).resolve()
    return str(root / remote.strip("/").replace("/", os.sep))


def _copy_one(source: Path, dest_dir: Path) -> None:
    if source.is_dir():
        target = dest_dir / source.name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)
    else:
        shutil.copy2(source, dest_dir / source.name)


def main() -> int:
    if len(sys.argv) < 3:
        return 2
    source_arg = sys.argv[-2]
    dest_dir = Path(sys.argv[-1])
    dest_dir.mkdir(parents=True, exist_ok=True)
    source_pattern = _source_path(source_arg)
    matches = [Path(item) for item in glob.glob(source_pattern, recursive=True)]
    calls_path = os.environ.get("REMOTE_DT_SIM_CALLS", str(Path(__file__).resolve().parent / "sim_calls.log"))
    if calls_path:
        with open(calls_path, "a", encoding="utf-8") as fp:
            fp.write(f"scp:{source_arg}:matches={len(matches)}\n")
    if not matches:
        print(f"fake scp: no match for {source_arg}", file=sys.stderr)
        return 1
    for match in matches:
        _copy_one(match, dest_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
