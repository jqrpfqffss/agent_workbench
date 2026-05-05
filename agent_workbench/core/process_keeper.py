from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a child process while keeping stdin open.")
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--log", default="")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        return 2

    log_fp = None
    try:
        stdout = subprocess.DEVNULL
        stderr = subprocess.DEVNULL
        if args.log:
            log_path = Path(args.log)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_fp = log_path.open("a", encoding="utf-8")
            stdout = log_fp
            stderr = subprocess.STDOUT

        popen_kwargs = {
            "cwd": args.cwd,
            "stdin": subprocess.PIPE,
            "stdout": stdout,
            "stderr": stderr,
            "close_fds": True,
        }
        proc = subprocess.Popen(command, **popen_kwargs)
        while proc.poll() is None:
            if proc.stdin is not None:
                try:
                    proc.stdin.write(b"\n")
                    proc.stdin.flush()
                except (BrokenPipeError, OSError):
                    pass
            time.sleep(1.0)
        return int(proc.returncode or 0)
    finally:
        if log_fp is not None:
            log_fp.close()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
