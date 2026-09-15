"""Run one offline diagnostic with a 300-second wall deadline."""

import hashlib
import json
import os
import signal
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def main():
    here = Path(__file__).resolve().parent
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out = here / 'executions' / run_id
    out.mkdir(parents=True, exist_ok=False)
    snapshot = out / 'source_snapshot'
    snapshot.mkdir()
    for source in [*here.glob('*.py'), here / 'plan.json', here / 'package_sha256.json']:
        shutil.copy2(source, snapshot / source.name)
    command = [sys.executable, str(here / 'replay.py'), '--output',
               str(out / 'results')]
    started = time.monotonic()
    meta = {'run_id': run_id, 'command': command, 'deadline_seconds': 300,
            'started_at': datetime.now(timezone.utc).isoformat()}
    timed_out = False
    with (out / 'stdout.log').open('w') as stdout, (out / 'stderr.log').open('w') as stderr:
        proc = subprocess.Popen(command, stdout=stdout, stderr=stderr, start_new_session=True)
        meta['process_group'] = proc.pid
        (out / 'meta.json').write_text(json.dumps(meta, indent=2) + '\n')
        try:
            code = proc.wait(timeout=300)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                code = proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                code = proc.wait()
    meta.update(exit_code=code, timed_out=timed_out, wall_seconds=time.monotonic() - started)
    (out / 'meta.json').write_text(json.dumps(meta, indent=2) + '\n')
    inventory = [{'path': str(p.relative_to(out)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                 for p in sorted(out.rglob('*')) if p.is_file()]
    (out / 'artifact_sha256.json').write_text(json.dumps(inventory, indent=2) + '\n')
    print(json.dumps(meta), flush=True)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
