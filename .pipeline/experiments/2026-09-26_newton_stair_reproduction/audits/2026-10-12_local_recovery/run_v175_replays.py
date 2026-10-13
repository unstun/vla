"""Run isolated native diagnostics on the closed v175 captures; no physics."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

BASE = Path(__file__).resolve().parents[2]
TASK = Path('/data/sun/vla_mppi_20261009')
sys.path.insert(0, str(BASE / 'versions/v175'))
from resource_gate import admit

admission = admit()
out = TASK / 'results/v175_native_replays'
out.mkdir(exist_ok=False)
image = json.loads((TASK / 'results/recovery_v175/candidate_receipt.json').read_text())['image_id']
build = '''set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/recovery_v175/install/setup.bash
cmake -S /task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v167 -B /task/replay_v175_native_build -DVERSIONS_ROOT=/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions
cmake --build /task/replay_v175_native_build -j2
'''
(out / 'build.sh').write_text(build)
docker = ['docker', 'run', '--rm', '--network=none', '--memory=6g', '--cpus=4',
          '-e', 'OPENBLAS_NUM_THREADS=1', '-e', 'OMP_NUM_THREADS=1',
          '-v', f'{TASK}:/task:rw', '--entrypoint', '/bin/bash', image]
with (out / 'build.log').open('w') as stream:
    subprocess.run(docker + ['/task/results/v175_native_replays/build.sh'],
                   stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=180)
results = []
for case in ['02', '03_stopped', '05']:
    inputs = TASK / f'replay_v175_attempt{case}_input'
    identity = json.loads((inputs / 'identity.json').read_text())
    for name, expected in identity['files'].items():
        assert hashlib.sha256((inputs / name).read_bytes()).hexdigest() == expected, name
    command = f'''ulimit -c 0
source /opt/ros/foxy/setup.bash
source /task/recovery_v175/install/setup.bash
REPLAY_INPUT=/task/replay_v175_attempt{case}_input PREFIX_BUDGET=6 /task/replay_v175_native_build/steering_probe --ros-args --params-file /task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v175/building_planner.yaml
'''
    path = out / f'case_{case}.log'
    with path.open('w') as stream:
        result = subprocess.run(docker + ['-c', command], stdout=stream,
                                stderr=subprocess.STDOUT, timeout=240)
    text = path.read_text()
    row = {'case': case, 'return_code': result.returncode,
           'input_identity_sha256': hashlib.sha256((inputs / 'identity.json').read_bytes()).hexdigest(),
           'input_root': str(inputs), 'log_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
           'summary': [line for line in text.splitlines() if any(key in line for key in
                       ('FULL_ROUTE_MAP', 'FULL_ROUTE_HEADING', 'V156_DIRECTION_COUNTS',
                        'FULL_ROUTE_REFERENCE', 'FULL_ROUTE_PREFIX', 'V167_REVERSE_VALIDATED',
                        'V167_PUBLISHED_INTENT', 'V158_GUARDS_PASS', 'what():'))]}
    results.append(row)
    print(json.dumps(row), flush=True)
(out / 'outcomes.json').write_text(json.dumps({'resource_admission': admission,
    'runs': results, 'scope': 'Ordered recorded sensor-prefix diagnostics with a frozen clock; '
                            'neither exact DDS scheduling nor physical execution is reconstructed.'}, indent=2) + '\n')
