"""Build the same-input probe against the two exact tested native installs."""
from pathlib import Path
import hashlib
import json
import subprocess

TASK = Path('/data/sun/vla_mppi_20261009')
HERE = Path(__file__).resolve().parent
source = '/repo/'+str(HERE.relative_to(TASK/'repo'))
image = json.loads((TASK/'results/baseline_receipt.json').read_text())['image_id']
output = TASK/'results/curve_parity03'
output.mkdir(exist_ok=False)
(output/'ros_logs').mkdir()
curves = {}
for variant in ('baseline', 'candidate'):
    script = '\n'.join(['set -e', 'source /opt/ros/foxy/setup.bash',
        f'source /task/{variant}/install/setup.bash',
        f'cmake -S {source} -B /task/curve_probe_{variant} -DCMAKE_BUILD_TYPE=Release '
        f'-DCANDIDATE={"ON" if variant == "candidate" else "OFF"}',
        f'cmake --build /task/curve_probe_{variant} -j2',
        f'exec /task/curve_probe_{variant}/curve_probe --ros-args --params-file '
        '/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v114/building_planner.yaml '
        '-p grid_map.asynchronous_mapping:=false'])
    command = ['docker', 'run', '--rm', '--network', 'none', '--cpus', '4', '--memory', '8g',
               '-e', 'ROS_DOMAIN_ID=195', '-e', 'ROS_LOCALHOST_ONLY=1',
               '-e', 'ROS_LOG_DIR=/task/results/curve_parity03/ros_logs',
               '-e', 'V114_INPUT=/task/fixed_curve_input',
               '-v', f'{TASK}:/task:rw', '-v', f'{TASK}/repo:/repo:ro',
               '--entrypoint', '/bin/bash', image, '-c', script]
    with (output/f'{variant}.log').open('w') as stream:
        subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=180)
    text = (output/f'{variant}.log').read_text()
    assert 'V114_PUBLICATION_PROOF_PASS' in text, variant
    records = [json.loads(line.split('MPPI_CURVE ', 1)[1]) for line in text.splitlines() if 'MPPI_CURVE ' in line]
    assert len(records) == 1, variant
    assert min(records[0]['rows'], records[0]['cols']) == 3 and max(records[0]['rows'], records[0]['cols']) > 3, variant
    curves[variant] = records[0]
if curves['baseline'] != curves['candidate']:
    raise ValueError('Fixed-input native curve differs')
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
result = {'passed': True, 'control_points_knots_duration_bit_identical': True,
          'control_values': len(curves['baseline']['control_bits']),
          'knot_values': len(curves['baseline']['knot_bits']),
          'actual_native_success_and_stale_rejection_passed_both': True,
          'candidate_diagnostics_active': True, 'fixture': str(TASK/'fixed_curve_input'),
          'fixture_identity_sha256': sha(TASK/'fixed_curve_input/identity.json'),
          'source_sha256': {p.name: sha(p) for p in HERE.iterdir() if p.is_file()},
          'log_sha256': {name: sha(output/f'{name}.log') for name in curves},
          'image_id': image, 'curves': curves}
(output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k != 'curves'}))
