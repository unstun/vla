"""Run serial bounded native checks on recorded v177 inputs, without physics."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys

HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1]
TASK=Path('/data/sun/vla_mppi_20261009')
sys.path.insert(0,str(BASE/'versions/v177'))
from resource_gate import admit
out=TASK/'results/v177_stop_replays01';out.mkdir(exist_ok=False)
admission=admit()
env=dict(os.environ,PYTHONPATH=str(TASK/'host_python'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
with (out/'prepare.log').open('w') as f:
    subprocess.run([sys.executable,str(HERE/'prepare_replays.py')],env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=360)
image=json.loads((TASK/'results/recovery_v177/candidate_receipt.json').read_text())['image_id']
docker=['docker','run','--rm','--network=none','--memory=4g','--cpus=2','-e','OPENBLAS_NUM_THREADS=1','-e','OMP_NUM_THREADS=1',
        '-v',f'{TASK}:/task:rw','--entrypoint','/bin/bash',image]
rel=str(HERE.relative_to(TASK))
build=f'''set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/recovery_v175/install/setup.bash
cmake -S /task/{rel} -B /task/replay_v177_stop_build -DVERSIONS_ROOT=/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions
cmake --build /task/replay_v177_stop_build -j2
'''
(out/'build.sh').write_text(build)
with (out/'build.log').open('w') as f:
    subprocess.run(docker+['/task/results/v177_stop_replays01/build.sh'],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=180)
rows=[]
for inputs in sorted((TASK/'replay_v177_stop_inputs').glob('a*')):
    identity=json.loads((inputs/'identity.json').read_text())
    for name,h in identity['files'].items():assert hashlib.sha256((inputs/name).read_bytes()).hexdigest()==h
    command=f'''set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/recovery_v175/install/setup.bash
REPLAY_INPUT=/task/replay_v177_stop_inputs/{inputs.name} /task/replay_v177_stop_build/stop_replay --ros-args --params-file /task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v177/building_planner.yaml
'''
    log=out/f'{inputs.name}.log'
    with log.open('w') as f:result=subprocess.run(docker+['-c',command],stdout=f,stderr=subprocess.STDOUT,timeout=180)
    row={'case':inputs.name,'return_code':result.returncode,'source_identity_sha256':hashlib.sha256((inputs/'identity.json').read_bytes()).hexdigest(),
         'input_root':str(inputs),'summary':[l for l in log.read_text().splitlines() if l.startswith('STOP_')],
         'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()}
    rows.append(row);(out/'outcomes.json').write_text(json.dumps({'admission':admission,'rows':rows,'scope':'Native ordered sensor reconstruction, not exact asynchronous state or physics.'},indent=2)+'\n')
    print(json.dumps(row),flush=True)
files={p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in out.iterdir() if p.is_file()}
(out/'manifest.json').write_text(json.dumps({'files':files,'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2)+'\n')
