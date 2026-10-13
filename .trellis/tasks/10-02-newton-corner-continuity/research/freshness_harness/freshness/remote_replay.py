"""Bounded unchanged-native replay; bulk evidence remains on gpu5070ti."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[2]
ROOT = BASE.parents[2]
NATIVE = BASE / 'runtime/scan75_reference_continuity_v53'
IMAGE = 'sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb'

def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()

def main():
    global NATIVE
    assert str(ROOT) == '/home/sun/vla_exec/vla'
    os.environ['PATH'] = '/home/sun/vla_exec/bin:' + os.environ['PATH']
    assert not subprocess.check_output(['docker', 'ps', '-q'], text=True).strip(), 'Host has active containers'
    parser = __import__('argparse').ArgumentParser(); parser.add_argument('--parent-red',action='store_true');parser.add_argument('--attempt',type=int,default=1);args=parser.parse_args()
    NATIVE = BASE/'runtime/scan75_reference_continuity_v53'
    expected = json.loads((NATIVE/'source_sha256.json').read_text())
    assert all(sha(NATIVE/n) == h for n,h in expected.items()), 'Native source mismatch'
    assert shutil.disk_usage(HERE).free > 4*1024**3
    out = HERE/f'red{args.attempt:02d}'
    out.mkdir()
    source = {p.name: sha(p) for p in HERE.iterdir() if p.is_file() and p.suffix in ('.py','.cpp','.sh','.txt','.json','.md')}
    (out/'source_identity.json').write_text(json.dumps({'audit_sources': source, 'native_sources': expected}, indent=2)+'\n')
    name = 'vla-v54-corner-20261002'
    cmd = ['docker','run','--rm','--pull=never','--platform=linux/amd64','--network=none','--name',name,'--cpus=3','--memory=6g',
           '-e','ROS_DOMAIN_ID=219','-e','ROS_LOCALHOST_ONLY=1','-e','OPENBLAS_NUM_THREADS=1','-e','OMP_NUM_THREADS=1',
           '-v',str(NATIVE)+':/workspace:ro','-v',str(BASE)+':/archive:ro','-v',str(BASE/'versions/v54')+':/version:ro',
           '-v',str(HERE)+':/profile:ro','-v',str(out)+':/attempt:rw','--entrypoint','/bin/bash',IMAGE,'/profile/inside.sh']
    (out/'request.json').write_text(json.dumps({'command':cmd, 'supervisor_deadline_s':900,
       'scope':'Offline unchanged-v52 native corner replay, no physics or planner deadline change'},indent=2)+'\n')
    started=time.monotonic()
    code=127
    error=None
    try:
        with (out/'execution.log').open('w') as log:
            code=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=900).returncode
    except (OSError,subprocess.TimeoutExpired) as exc:
        error=repr(exc)
    finally:
        subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=20)
    log=(out/'replay.log').read_text() if (out/'replay.log').exists() else ''
    probes=[json.loads(x) for x in (out/'probes.jsonl').read_text().splitlines()] if (out/'probes.jsonl').exists() else []
    compact=[];current=None
    markers=('CORNER_CASE','CORNER_ROUND','V48_WARM_SEED','reactive_stair_seed_search_failed','reference_prefix_proposal','prefix_candidate','First three control points','rebound_no_valid_new_constraints','initial_spline_collision','V47_WINDOW_HINT','spline_seed_capture')
    for number,line in enumerate(log.splitlines(),1):
        if any(k in line for k in markers): compact.append(dict(line=number,text=line))
    unchanged=all(sha(NATIVE/n)==h for n,h in expected.items())
    retained=next((bool(p['retained']) for p in probes if p.get('kind')=='refresh_binding'),False)
    result=dict(expected_refresh_binding=retained, parent_red=args.parent_red, exit_code=code,error=error,wall_s=time.monotonic()-started,
        completed=code==0 and 'V54_PARENT_RED_REPRODUCED' in log,
        native_source_unchanged=unchanged,probes=probes,evidence=compact,
        limitations='Fixed-clock observer-order reconstruction with documented first-route ordering correction; no live mid-solve input progression. Contended host, diagnostic timings only.')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    records={str(p.relative_to(out)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in out.rglob('*') if p.is_file() and not p.is_symlink() and 'probe_build' not in p.parts}
    exe=out/'probe_build/tail_replay'
    if exe.is_file(): records['probe_build/tail_replay']=dict(bytes=exe.stat().st_size,sha256=sha(exe))
    (out/'remote_artifacts.json').write_text(json.dumps(dict(host='gpu5070ti',absolute_root=str(out),files=records),indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('probes','evidence')},indent=2),flush=True)
    raise SystemExit(0 if result['completed'] and unchanged  else 1)

if __name__ == '__main__': main()
