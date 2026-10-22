"""One owned physical dispatcher and resource observer, bound to the final freeze."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=Path('/home/sun/vla_exec/static_continuity_v284')
VERSION=HERE.parents[1]/'versions/v284'


def main():
    sys.path.insert(0,str(VERSION))
    from identity import verify_sources
    verify_sources()
    freeze=json.loads((VERSION/'manifest.json').read_text())
    assert freeze['frozen'] and freeze['authorized_attempts_per_case']==1
    receipt=ROOT/'physical02_coordinator.json'
    assert not receipt.exists()
    row=dict(pid=os.getpid(),started_utc_s=time.time(),source_verified=True,
        execution_manifest_sha256=hashlib.sha256((VERSION/'manifest.json').read_bytes()).hexdigest())
    receipt.write_text(json.dumps(row,indent=2)+'\n')
    with (ROOT/'resource_watch01.log').open('x') as log:
        observer=subprocess.Popen([sys.executable,str(HERE/'watch_resources.py')],stdout=log,stderr=subprocess.STDOUT)
        try:
            code=subprocess.run([sys.executable,str(HERE/'run_physical.py')]).returncode
            row.update(returncode=code,finished_utc_s=time.time())
            receipt.write_text(json.dumps(row,indent=2)+'\n')
        finally:
            (HERE/'results/resource_watch/stop_requested').touch()
            observer.wait(timeout=65)
    raise SystemExit(code)


if __name__=='__main__':
    main()
