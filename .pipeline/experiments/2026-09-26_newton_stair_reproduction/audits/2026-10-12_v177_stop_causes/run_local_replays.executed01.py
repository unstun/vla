"""Local bounded native replay after remote physical-run admission was held."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
TASK=Path('/private/tmp/vla_stop_audit_20261012')
OUT=HERE/'native_replays';OUT.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
image='sha256:a6326521265b857c85799c5d24eb8d9a78cbb19a25d2b1e5e1d01943cea3524e'
docker=['docker','run','--rm','--network=none','--cpus=2','--memory=4g','-e','OPENBLAS_NUM_THREADS=1',
        '-v',f'{TASK}:/task:rw','-v',f'{ROOT}:/task/repo:ro','--entrypoint','/bin/bash',image]
rows=[]
for inputs in sorted((TASK/'replay_v177_stop_inputs').glob('a*')):
    identity=json.loads((inputs/'identity.json').read_text())
    for n,h in identity['files'].items():assert sha(inputs/n)==h
    command=f'''set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/recovery_v174/install/setup.bash
REPLAY_INPUT=/task/replay_v177_stop_inputs/{inputs.name} /task/stop_build/stop_replay --ros-args --params-file /task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v177/building_planner.yaml
'''
    log=OUT/f'{inputs.name}.log'
    with log.open('w') as f:r=subprocess.run(docker+['-c',command],stdout=f,stderr=subprocess.STDOUT,timeout=180)
    row={'case':inputs.name,'return_code':r.returncode,'source_identity_sha256':sha(inputs/'identity.json'),
         'input_root':str(inputs),'log_sha256':sha(log),
         'summary':[l for l in log.read_text().splitlines() if l.startswith('STOP_')]}
    rows.append(row)
    (OUT/'outcomes.json').write_text(json.dumps({'rows':rows,'host':'local Mac ARM64',
        'scope':'Original native map checks on ordered Linux sensor data. Neither original asynchronous map state nor physical execution is reconstructed.',
        'image':image,'binary_sha256':sha(TASK/'stop_build/stop_replay'),
        'source_sha256':sha(HERE/'stop_replay.cpp'),'runner_sha256':sha(Path(__file__))},indent=2)+'\n')
    print(json.dumps(row),flush=True)
files={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in OUT.iterdir() if p.is_file()}
(OUT/'manifest.json').write_text(json.dumps({'files':files},indent=2)+'\n')
