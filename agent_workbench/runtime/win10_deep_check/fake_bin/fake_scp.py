from __future__ import annotations
import glob, json, os, pathlib, shutil, sys
root = pathlib.Path(os.environ['FAKE_REMOTE_ROOT'])
log_path = pathlib.Path(os.environ['FAKE_CALL_LOG'])

def log(item):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open('a', encoding='utf-8') as fp:
        fp.write(json.dumps(item, ensure_ascii=False) + '\n')

def split_remote(spec: str):
    if '@' not in spec or ':' not in spec:
        return None
    _, path = spec.split(':', 1)
    return path.strip().strip('"').strip("'")

def map_remote(path: str) -> pathlib.Path:
    p = path.strip().strip('"').strip("'")
    if p.startswith('/'):
        p = p[1:]
    return root / p

def copy_tree_contents(src: pathlib.Path, dest: pathlib.Path):
    dest.mkdir(parents=True, exist_ok=True)
    for child in src.iterdir():
        target = dest / child.name
        if child.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(child, target)
        else:
            shutil.copy2(child, target)

src_arg = sys.argv[-2]
dst_arg = sys.argv[-1]
log({'tool': 'scp', 'src': src_arg, 'dst': dst_arg})
remote_dst = split_remote(dst_arg)
remote_src = split_remote(src_arg)
if remote_dst is not None:
    src = pathlib.Path(src_arg[:-2] if src_arg.endswith('/.') else src_arg.strip('"'))
    copy_tree_contents(src, map_remote(remote_dst))
    sys.exit(0)
if remote_src is not None:
    dest = pathlib.Path(dst_arg)
    dest.mkdir(parents=True, exist_ok=True)
    pattern = map_remote(remote_src)
    matches = glob.glob(str(pattern)) if any(ch in str(pattern) for ch in '*?[') else [str(pattern)]
    for match in matches:
        p = pathlib.Path(match)
        if not p.exists():
            continue
        target = dest / p.name
        if p.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(p, target)
        else:
            shutil.copy2(p, target)
    sys.exit(0)
sys.exit(0)