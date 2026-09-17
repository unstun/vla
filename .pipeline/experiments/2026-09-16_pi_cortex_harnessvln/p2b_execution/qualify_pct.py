"""Compute both pilot routes with real PCT; this is not motion evidence."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent


def inside(output):
    import numpy as np
    from pct_planner.config import Config
    from pct_planner.planner_wrapper import TomogramPlanner
    from pct_planner import planner_wrapper
    from pct_planner.lib import a_star, ele_planner, traj_opt
    manifest = json.loads((HERE / 'pct_runtime_manifest.json').read_text())
    for name, expected in manifest['files'].items():
        assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == expected, name
    input_manifest = json.loads((HERE / 'input_manifest.json').read_text())
    for item in input_manifest['files']:
        if item['path'] in ['inputs/new_building.pickle', 'inputs/pilot.json']:
            assert hashlib.sha256((HERE / item['path']).read_bytes()).hexdigest() == item['sha256']
    pilot = json.loads((HERE / 'inputs/pilot.json').read_text())
    planner = TomogramPlanner(Config(), str(HERE / 'inputs'))
    planner.loadTomogram(tomogram_path=str(HERE / 'inputs/new_building.pickle'))
    planner.planner.set_reference_height(pilot['nominal_body_height_m'])
    start = np.asarray(pilot['spawn_ground_xyz_m'], dtype=np.float64)
    output.mkdir(parents=True, exist_ok=False)
    records = []
    for goal in pilot['goals']:
        target = np.asarray(goal['ground_xyz_m'], dtype=np.float64)
        begin = time.monotonic()
        raw = planner.plan(start, target, start_layer=pilot['pct_layer'],
                           end_layer=pilot['pct_layer'], optimize=True)
        if raw is None:
            raise RuntimeError('Native PCT rejected ' + goal['goal_id'])
        opt = planner.planner.get_trajectory_optimizer_wnoj()
        xyz = np.asarray(raw, dtype=np.float64).copy()
        heights = np.asarray(opt.get_heights(), dtype=np.float64)
        assert xyz.ndim == 2 and xyz.shape[1] == 3 and len(xyz) >= 2 and np.isfinite(xyz).all()
        assert np.allclose(xyz[:, 2] - heights, 0.5, atol=1e-6)
        xyz[:, 2] = heights
        error = float(np.linalg.norm(xyz[-1, :2] - target[:2]))
        if error > pilot['goal_xy_tolerance_m']:
            raise RuntimeError('Native endpoint outside declared goal tolerance')
        record = {'goal_id': goal['goal_id'], 'start_ground_xyz_m': start.tolist(),
                  'target_ground_xyz_m': target.tolist(), 'elapsed_wall_s': time.monotonic() - begin,
                  'point_count': len(xyz), 'endpoint_error_xy_m': error,
                  'points_xyz_m': xyz.tolist(), 'semantics': 'body_reference_xyz_m',
                  'native_optimization': True, 'resampling': False}
        (output / (goal['goal_id'] + '.json')).write_text(json.dumps(record, indent=2) + '\n')
        records.append({k: v for k, v in record.items() if k != 'points_xyz_m'})
        start = target
    identity = {m.__name__: {'path': m.__file__, 'sha256': hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()}
                for m in [planner_wrapper, a_star, ele_planner, traj_opt]}
    result = {'passed': True, 'python': sys.version, 'modules': identity, 'routes': records,
              'claim': 'Native PCT planning at declared pilot endpoints only; second start is the first requested endpoint, not a measured robot pose. No motion/ROS/Isaac integration evidence.'}
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


def host():
    run_id = datetime.now(timezone.utc).strftime('pct_%Y%m%dT%H%M%SZ')
    out = HERE / 'qualification' / run_id
    out.mkdir(parents=True)
    runtime = json.loads((HERE / 'pct_runtime_manifest.json').read_text())
    files = list(runtime['files']) + ['qualify_pct.py', 'pct_runtime_manifest.json', 'input_manifest.json',
                                      'inputs/pilot.json', 'inputs/new_building.pickle']
    (out / 'files.txt').write_text('\n'.join(files) + '\n')
    expected = {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in files}
    (out / 'source_sha256.json').write_text(json.dumps(expected, indent=2) + '\n')
    remote = '/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/qualification/' + run_id
    ssh = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=20', 'gpu5070ti']
    commands = []

    def run(label, cmd, stdin=None):
        p = subprocess.run(cmd, input=stdin, capture_output=True, text=True, timeout=180)
        (out / (label + '.log')).write_text(p.stdout + p.stderr)
        commands.append({'label': label, 'command': cmd, 'exit_code': p.returncode})
        (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        print(label, p.returncode, flush=True)
        p.check_returncode()

    run('mkdir', ssh + [shlex.join(['mkdir', '-p', remote])])
    run('sync', ['rsync', '-a', '--files-from=' + str(out / 'files.txt'), str(HERE) + '/', 'gpu5070ti:' + remote + '/'])
    gate = ('import pathlib,hashlib,json\n' + f'root=pathlib.Path({remote!r});expected={expected!r}\n'
            'actual={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in expected}\n'
            'assert actual==expected\nprint(json.dumps({"matched":True,"files":len(actual)}))\n')
    run('source_gate', ssh + ['python3 -'], gate)
    inner = ('set -e\nsource /opt/ros/humble/setup.bash\n'
             'export PYTHONPATH=/qualification/pct_runtime/python:${PYTHONPATH:-}\n'
             'export LD_LIBRARY_PATH=/qualification/pct_runtime/lib:$LD_LIBRARY_PATH\n'
             'exec python3 /qualification/qualify_pct.py --inside --output /qualification/result')
    run('compute', ssh + [shlex.join(['podman', 'run', '--rm', '--pull=never', '--network=none',
                                     '-e', 'PYTHONDONTWRITEBYTECODE=1', '-e', 'OPENBLAS_NUM_THREADS=1',
                                     '-e', 'OMP_NUM_THREADS=2', '-v', remote + ':/qualification',
                                     runtime['image_id'], 'bash', '-lc', inner])])
    run('return', ['rsync', '-a', 'gpu5070ti:' + remote + '/result/', str(out / 'result') + '/'])
    remote_hash = 'import pathlib,hashlib,json\n' + f'r=pathlib.Path({remote!r})/"result"\n' + 'print(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in r.iterdir() if p.is_file()}))\n'
    run('return_hashes', ssh + ['python3 -'], remote_hash)
    returned = json.loads((out / 'return_hashes.log').read_text())
    assert returned == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (out / 'result').iterdir() if p.is_file()}
    (out / 'sync_verdict.json').write_text(json.dumps({'source_matched': True, 'returned_hashes_match': True,
                                                      'result_file': 'result/result.json'}, indent=2) + '\n')
    print(out)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--inside', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    inside(args.output) if args.inside else host()
