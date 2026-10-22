"""Own the resource observer and the once-only frozen physical dispatcher."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = Path('/home/sun/vla_exec/navigation_geometry_v283')
VERSION = HERE.parents[1] / 'versions/v283'


def main():
    assert hashlib.sha256((VERSION / 'manifest.json').read_bytes()).hexdigest() == '8d22f7e0ebeb90432b6811462d95dd175613bb3e4902d5b4634fe6b0ca38cc71'
    assert hashlib.sha256((VERSION / 'native_manifest.json').read_bytes()).hexdigest() == 'caeea41b0dbb99ca10ae74b1cf6239535d4c2c4d25327f53988d8afe7b1393f4'
    sys.path.insert(0, str(VERSION))
    from identity import verify_sources
    verify_sources()
    receipt = ROOT / 'physical02_coordinator.json'
    assert not receipt.exists()
    row = dict(pid=os.getpid(), started_utc_s=time.time(), source_verified=True)
    receipt.write_text(json.dumps(row, indent=2) + '\n')
    with (ROOT / 'resource_watch02.log').open('x') as observer_log:
        observer = subprocess.Popen([sys.executable, str(HERE / 'watch_resources.py')],
            stdout=observer_log, stderr=subprocess.STDOUT)
        try:
            code = subprocess.run([sys.executable, str(HERE / 'run_physical.py')]).returncode
            row.update(returncode=code, finished_utc_s=time.time())
            receipt.write_text(json.dumps(row, indent=2) + '\n')
        finally:
            (HERE / 'results/resource_watch/stop_requested').touch()
            observer.wait(timeout=65)
    raise SystemExit(code)


if __name__ == '__main__':
    main()
