"""Local launcher: verify frozen bytes, send stdlib analysis via stdin, retain every receipt."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    frozen_bytes = (ROOT / 'frozen.json').read_bytes()
    frozen = json.loads(frozen_bytes)
    for name, identity in frozen['files'].items():
        data = (ROOT / name).read_bytes()
        assert sha(data) == identity['sha256'] and len(data) == identity['bytes'], name
    source = (ROOT / 'source/audit.py').read_text()
    request = (ROOT / 'request.json').read_text()
    payload = ('REQUEST=__import__("json").loads(' + repr(request) + ')\nSOURCE_SHA256=' + repr(sha(source.encode())) +
               '\nFROZEN_SHA256=' + repr(sha(frozen_bytes)) + '\n' + source)
    cmd = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', 'ultra9',
           'nice -n 19 /home/ubuntu/sun/vla_v234_20261017/env/newton_worker/bin/python -B -']
    started = time.time()
    receipt = dict(command=cmd, started_epoch_s=started, source_sha256=sha(source.encode()),
                   frozen_sha256=sha(frozen_bytes), payload_sha256=sha(payload.encode()),
                   new_physics_steps=0, remote_files_written=0)
    with (ROOT / 'results/extract01.started.json').open('x') as f:
        json.dump(receipt, f, indent=2)
    code = None
    try:
        with (ROOT / 'results/extract01.jsonl').open('x') as output, (ROOT / 'results/extract01.stderr.txt').open('x') as errors:
            result = subprocess.run(cmd, input=payload, text=True, stdout=output, stderr=errors, timeout=1800)
            code = result.returncode
    except Exception as error:
        receipt['launcher_error'] = repr(error)
        raise
    finally:
        receipt.update(returncode=code, ended_epoch_s=time.time())
        for name in ('extract01.jsonl', 'extract01.stderr.txt'):
            p = ROOT / 'results' / name
            if p.exists():
                data = p.read_bytes()
                receipt[name] = dict(bytes=len(data), sha256=sha(data))
        with (ROOT / 'results/extract01.receipt.json').open('x') as f:
            json.dump(receipt, f, indent=2)
    print(json.dumps(receipt, indent=2))
    return code


if __name__ == '__main__':
    sys.exit(main())
