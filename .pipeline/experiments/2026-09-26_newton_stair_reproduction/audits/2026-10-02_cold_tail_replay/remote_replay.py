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
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
NATIVE = BASE / 'runtime/scan73_v48_continuity_v50'
IMAGE = 'sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb'

def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()

def main():
    assert str(ROOT) == '/home/sun/vla_exec/vla'
    os.environ['PATH'] = '/home/sun/vla_exec/bin:' + os.environ['PATH']
    assert not subprocess.check_output(['docker', 'ps', '-q'], text=True).strip(), 'Host has active containers'
    expected = json.loads((NATIVE/'source_sha256.json').read_text())
    assert all(sha(NATIVE/n) == h for n,h in expected.items()), 'Native source mismatch'
    assert shutil.disk_usage(HERE).free > 4*1024**3
    out = HERE/'attempt01'
    out.mkdir()
    source = {p.name: sha(p) for p in HERE.iterdir() if p.is_file() and p.suffix in ('.py','.cpp','.sh','.txt','.json','.md')}
    (out/'source_identity.json').write_text(json.dumps({'audit_sources': source, 'native_sources': expected}, indent=2)+'\n')
    name = 'vla-cold-tail-replay-20261002'
    cmd = ['docker','run','--rm','--pull=never','--platform=linux/amd64','--network=none','--name',name,'--cpus=3','--memory=6g',
           '-e','ROS_DOMAIN_ID=219','-e','ROS_LOCALHOST_ONLY=1','-e','OPENBLAS_NUM_THREADS=1','-e','OMP_NUM_THREADS=1',
           '-v',str(NATIVE)+':/workspace:ro','-v',str(BASE)+':/archive:ro','-v',str(BASE/'versions/v50')+':/version:ro',
           '-v',str(HERE)+':/profile:ro','-v',str(out)+':/attempt:rw','--entrypoint','/bin/bash',IMAGE,'/profile/inside.sh']
    (out/'request.json').write_text(json.dumps({'command':cmd, 'supervisor_deadline_s':900,
       'scope':'Offline unchanged-v50 native replay, no physics or planner deadline change'},indent=2)+'\n')
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
    pairs=[json.loads(line) for line in (out/'tail_pairs.jsonl').read_text().splitlines()] if (out/'tail_pairs.jsonl').exists() else []
    diagnostics=[]
    current=None
    for line in log.splitlines():
        if 'COLD_REPLAY_CASE ' in line:
            current={'header':line, 'first_seed':None, 'blocked_first_controls':0, 'no_rebound_constraints':0}
            diagnostics.append(current)
        if current is None: continue
        if 'spline_seed_capture ' in line and current['first_seed'] is None:
            seed=json.loads(line.split('spline_seed_capture ',1)[1])
            current['first_seed']={'sha256':hashlib.sha256(json.dumps(seed,sort_keys=True).encode()).hexdigest(),
                                   'start':seed['points'][0], 'target':seed['points'][-1], 'derivatives':seed['derivatives']}
        current['blocked_first_controls'] += 'First three control points' in line
        current['no_rebound_constraints'] += 'rebound_no_valid_new_constraints' in line
    result={'exit_code':code,'error':error,'wall_s':time.monotonic()-started,
            'determinism_passed':code==0 and 'COLD_REPLAY_DETERMINISM_PASSED' in log and len(pairs)==18 and all(x['same_geometry'] for x in pairs),
            'native_source_unchanged':all(sha(NATIVE/n)==h for n,h in expected.items()),
            'diagnostics':diagnostics, 'pairs':pairs,
            'scope':'Observer-order fixed-clock reconstruction, not exact live DDS batching or full native-state replay.'}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    records={str(p.relative_to(out)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.rglob('*') if p.is_file() and not p.is_symlink() and 'probe_build' not in p.parts}
    exe=out/'probe_build/tail_replay'
    if exe.is_file(): records['probe_build/tail_replay']={'bytes':exe.stat().st_size,'sha256':sha(exe)}
    (out/'remote_artifacts.json').write_text(json.dumps({'host':'gpu5070ti','absolute_root':str(out),'files':records},indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('diagnostics','pairs')},indent=2),flush=True)
    raise SystemExit(0 if result['determinism_passed'] and result['native_source_unchanged'] else 1)

if __name__ == '__main__': main()
