"""Bounded offline diagnosis; never modify the frozen planner or run physics."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[2]
NATIVE=BASE/'runtime/scan79_goal_endpoint_evidence_v58'
IMAGE='sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb'


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(4*1024**2),b''):h.update(block)
    return h.hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--attempt',type=int,default=1);a=p.parse_args()
    os.environ['PATH']='/home/sun/vla_exec/bin:'+os.environ['PATH']
    assert not subprocess.check_output(['docker','ps','-q'],text=True).strip()
    assert shutil.disk_usage(HERE).free>4*1024**3
    native=json.loads((NATIVE/'source_sha256.json').read_text())
    assert all(sha(NATIVE/n)==h for n,h in native.items())
    out=HERE/f'attempt{a.attempt:02d}';out.mkdir()
    owned='vla-v58-goal-paired'
    sources={p.name:sha(p) for p in HERE.iterdir() if p.is_file() and p.suffix in ('.py','.cpp','.sh','.txt','.json','.md')}
    (out/'source_identity.json').write_text(json.dumps(sources,indent=2)+'\n')
    cmd=['docker','run','--rm','--pull=never','--platform=linux/amd64','--network=none','--name',owned,'--cpus=3','--memory=6g',
         '-e','ROS_DOMAIN_ID=220','-e','ROS_LOCALHOST_ONLY=1','-e','OMP_NUM_THREADS=1','-e','OPENBLAS_NUM_THREADS=1',
         '-v',str(NATIVE)+':/workspace:ro','-v',str(BASE)+':/archive:ro','-v',str(BASE/'versions/v57')+':/version:ro',
         '-v',str(HERE)+':/profile:ro','-v',str(out)+':/attempt:rw','--entrypoint','/bin/bash',IMAGE,'/profile/inside.sh']
    (out/'request.json').write_text(json.dumps(dict(command=cmd,external_bound_s=300,physics=False,local_return='Compact report/probe/source provenance only; events and build remain remote'),indent=2)+'\n')
    start=time.monotonic();error=None;code=127
    try:
        with (out/'execution.log').open('w') as f:code=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=300).returncode
    except (OSError,subprocess.TimeoutExpired) as e:error=repr(e)
    finally:subprocess.run(['docker','rm','-f',owned],capture_output=True,timeout=20)
    rows={p.stem:[json.loads(s) for s in p.read_text().splitlines()] for p in out.glob('*_native.jsonl')}
    result=dict(exit_code=code,error=error,wall_s=time.monotonic()-start,source_unchanged=all(sha(NATIVE/n)==h for n,h in native.items()),
                rows=rows,scope='Same fixed-clock inputs; alternating v58 evidence switch, original native validation unchanged; not live timings.')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    manifest={str(p.relative_to(out)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in out.rglob('*') if p.is_file() and 'build' not in p.parts}
    (out/'remote_artifacts.json').write_text(json.dumps(dict(host='gpu5070ti',absolute_root=str(out),files=manifest),indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'}),flush=True)
    raise SystemExit(code)


if __name__=='__main__':main()
