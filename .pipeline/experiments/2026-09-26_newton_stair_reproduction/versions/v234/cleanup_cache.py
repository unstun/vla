"""User-authorized gpu40901 cleanup: pip download/wheel cache only."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

CACHE = Path('/home/ubuntu/.cache/pip')
PYTHON = '/home/ubuntu/miniconda3/bin/python'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    assert CACHE.is_dir() and not CACHE.is_symlink()
    reported = subprocess.check_output([PYTHON, '-m', 'pip', 'cache', 'dir'], text=True).strip()
    assert Path(reported) == CACHE, reported
    entries = [dict(path=str(p.relative_to(CACHE)), bytes=p.stat().st_size)
               for p in CACHE.rglob('*') if p.is_file() and not p.is_symlink()]
    active = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdecimal():
            continue
        try:
            for fd in (proc / 'fd').iterdir():
                try:
                    target = os.readlink(fd)
                    if target.startswith(str(CACHE) + '/'):
                        active.append(dict(pid=int(proc.name), file=target))
                except OSError:
                    continue
        except OSError:
            continue
    assert not active, f'Cache currently open: {active}'
    before = shutil.disk_usage(CACHE).free
    started = time.time_ns()
    result = subprocess.run([PYTHON, '-m', 'pip', 'cache', 'purge'],
                            capture_output=True, text=True, timeout=300)
    remaining = sum(p.stat().st_size for p in CACHE.rglob('*') if p.is_file())
    report = dict(authorized='Dr Sun: reasonable gpu40901 storage cleanup',
                  scope=str(CACHE), started_ns=started, completed_ns=time.time_ns(),
                  cache_bytes_before=sum(p['bytes'] for p in entries), cache_bytes_after=remaining,
                  disk_free_before=before, disk_free_after=shutil.disk_usage(CACHE).free,
                  result=dict(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr),
                  files_before=entries, models_or_experiments_removed=False,
                  shared_environments_changed=False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('scope', 'cache_bytes_before', 'cache_bytes_after',
                                           'disk_free_before', 'disk_free_after')}))
    result.check_returncode()


if __name__ == '__main__':
    main()
