from __future__ import annotations
import json, os, pathlib, re, shlex, sys
root = pathlib.Path(os.environ['FAKE_REMOTE_ROOT'])
log_path = pathlib.Path(os.environ['FAKE_CALL_LOG'])

def log(item):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open('a', encoding='utf-8') as fp:
        fp.write(json.dumps(item, ensure_ascii=False) + '\n')

def map_remote(path: str) -> pathlib.Path:
    p = path.strip().strip('"').strip("'")
    if p.startswith('/'):
        p = p[1:]
    return root / p

def extract_cd(text: str) -> str:
    m = re.search(r"cd\s+((?:'[^']*')|(?:\"[^\"]*\")|\S+)", text)
    return shlex.split(m.group(0))[1] if m else ''

cmd = sys.argv[-1]
log({'tool': 'ssh', 'cmd': cmd})
if cmd.startswith('mkdir -p '):
    map_remote(shlex.split(cmd)[-1]).mkdir(parents=True, exist_ok=True)
    sys.exit(0)
if 'chmod +x' in cmd:
    base = extract_cd(cmd)
    files = shlex.split(cmd.split('chmod +x', 1)[1])
    for rel in files:
        target = map_remote(base) / rel
        marker = target.with_suffix(target.suffix + '.chmod_marker')
        marker.write_text('chmod +x\n', encoding='utf-8')
    sys.exit(0)
if 'REMOTE_DT_SCRIPT_CRLF' in cmd:
    base = extract_cd(cmd)
    remote_base = map_remote(base)
    for rel in ('build.sh', 'scripts/run.sh'):
        f = remote_base / rel
        if f.exists() and b'\r' in f.read_bytes()[:512]:
            print(f'REMOTE_DT_SCRIPT_CRLF:{rel}')
            sys.exit(21)
    sys.exit(0)
if 'dt_build.log' in cmd or 'dt_execute.log' in cmd or 'dt_coverage.log' in cmd:
    base = extract_cd(cmd)
    remote_base = map_remote(base)
    logs = remote_base / '.agent_workbench_remote_dt' / 'logs'
    results = remote_base / '.agent_workbench_remote_dt' / 'results'
    logs.mkdir(parents=True, exist_ok=True)
    results.mkdir(parents=True, exist_ok=True)
    step = 'build' if 'dt_build.log' in cmd else ('execute' if 'dt_execute.log' in cmd else 'coverage')
    (logs / f'dt_{step}.log').write_text(f'{step} ok\n', encoding='utf-8')
    (results / f'dt_{step}_result.json').write_text(json.dumps({'step': step, 'exit_code': 0}), encoding='utf-8')
    if step == 'coverage':
        cov = remote_base / 'coverage'
        cov.mkdir(parents=True, exist_ok=True)
        (cov / 'index.html').write_text('coverage ok', encoding='utf-8')
    sys.exit(0)
sys.exit(0)