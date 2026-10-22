"""Start one scored53 batch and record the shared-host load without retiming."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import time

R=Path('/home/ubuntu/sun/vla_v290_20261021')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    proof=json.loads((R/'evidence/local_source_return01.json').read_text())
    assert proof['passed'] and proof['manifest_sha256']==sha(R/'source/native_manifest.json')
    assert not (R/'benchmark/native_ledger.json').exists()
    assert not (R/'evidence/offline_matrix01_closed.json').exists()
    script=R/'migration/benchmark.py'
    subprocess.run([sys.executable,str(script),'verify'],check=True)
    command=[sys.executable,str(script),'matrix']
    began=time.monotonic()
    with (R/'evidence/offline_matrix01.log').open('x') as log, (R/'evidence/offline_host_load01.jsonl').open('x') as resources:
        process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
        while True:
            resources.write(json.dumps(dict(time_s=time.time(),load=Path('/proc/loadavg').read_text().strip(),
                meminfo=Path('/proc/meminfo').read_text(),cpu=Path('/proc/stat').read_text().splitlines()[0]))+'\n')
            resources.flush()
            try:code=process.wait(timeout=5);break
            except subprocess.TimeoutExpired:pass
    gate=R/'benchmark/offline_gate.json'
    result=dict(returncode=code,execution_complete=(R/'benchmark/complete.json').exists(),
        wall_s=time.monotonic()-began,command=command,source_manifest_sha256=sha(R/'source/native_manifest.json'),
        adapter_sha256=sha(script),launcher_sha256=sha(Path(__file__)),physics_steps=0,
        log_sha256=sha(R/'evidence/offline_matrix01.log'),gate=json.loads(gate.read_text()) if gate.exists() else None,
        claim='Original2CPU native timing under observed shared-host load. No quiet-host or timing-exception claim.')
    (R/'evidence/offline_matrix01_closed.json').write_text(json.dumps(result,indent=2)+'\n')
    raise SystemExit(code)


if __name__=='__main__':main()
