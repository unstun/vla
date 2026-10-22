"""Observe the unchanged resource gate once a minute, without touching jobs."""
from pathlib import Path
import fcntl
import hashlib
import importlib.util
import json
import os
import time

HERE = Path(__file__).resolve().parent
VERSION = HERE.parents[1] / 'versions/v285'
OUT = HERE / 'results/resource_watch'


def sample():
    path = VERSION / 'resource_admission.py'
    spec = importlib.util.spec_from_file_location('v285_resource_gate', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = dict(utc_epoch_s=time.time(), pid=os.getpid(), physics_steps=0,
                  jobs_changed=0, gate_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    try:
        result.update(passed=True, resources=module.admit())
    except RuntimeError as error:
        result.update(passed=False, reason=str(error))
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / 'watch.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        previous = None
        while not (OUT / 'stop_requested').exists():
            try:
                row = sample()
            except Exception as error:
                row = dict(utc_epoch_s=time.time(), pid=os.getpid(), passed=False,
                           probe_error=repr(error), physics_steps=0, jobs_changed=0)
            temporary = OUT / 'latest.tmp'
            temporary.write_text(json.dumps(row, indent=2) + '\n')
            temporary.replace(OUT / 'latest.json')
            with (OUT / 'samples.jsonl').open('a') as history:
                history.write(json.dumps(row) + '\n')
            state = (row['passed'], row.get('probe_error'))
            if state != previous:
                print(json.dumps(row), flush=True)
            previous = state
            time.sleep(60)


if __name__ == '__main__':
    main()
