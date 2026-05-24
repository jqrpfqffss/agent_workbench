from __future__ import annotations
import sys
from pathlib import Path

attempt_dir = Path(sys.argv[1])
token = sys.argv[2]
texts = []
for name in ["stdout.log", "stderr.log", "review_stdout.log", "review_stderr.log"]:
    path = attempt_dir / name
    if path.exists():
        texts.append(path.read_text(encoding="utf-8", errors="ignore"))
combined = "\n".join(texts)
if token in combined:
    print(f"found {token}")
    raise SystemExit(0)
print(f"missing {token}")
raise SystemExit(5)
