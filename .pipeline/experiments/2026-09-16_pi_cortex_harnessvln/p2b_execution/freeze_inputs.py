"""Freeze hash-identified Building inputs; never copy an uncommitted code tree."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
NAV = ROOT.parent / 'machine-dog-nav'
BASELINE = NAV / '.pipeline/experiments/2026-09-11_pct_scan_upstream_baseline'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    scope_path = BASELINE / 'contracts/native_nominal_scope.json'
    scope = json.loads(scope_path.read_text())
    files = []

    def freeze(source, destination, expected=None):
        data = source.read_bytes()
        actual = digest(data)
        if expected is not None and actual != expected:
            raise RuntimeError('Input hash differs from recorded baseline: ' + str(source))
        target = HERE / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_bytes() != data:
            raise RuntimeError('Refusing to overwrite frozen input: ' + str(target))
        target.write_bytes(data)
        files.append({'source': str(source), 'path': destination,
                      'sha256': actual, 'bytes': len(data)})

    for name, field in [('building.usda', 'building_usda'), ('new_building.pickle', 'pct_tomogram')]:
        item = scope['frozen_assets'][field]
        freeze(NAV / item['path'], 'inputs/' + name, item['sha256'])
    for name in ['bridge.yaml', 'controller.yaml', 'planner.yaml']:
        freeze(BASELINE / 'config' / name, 'baseline_config/' + name,
               scope['config_sha256'][name])
    freeze(scope_path, 'baseline_config/native_nominal_scope.json')
    freeze(BASELINE / 'inputs/pct_inputs.json', 'baseline_config/pct_inputs.json')
    flat_path = NAV / '.pipeline/experiments/2026-09-09_pct_scan_lite3_building/inputs/flat_segment.json'
    flat = json.loads(flat_path.read_text())
    freeze(flat_path, 'inputs/flat_segment.original.json')
    assert flat['building_usda']['sha256'] == scope['frozen_assets']['building_usda']['sha256']
    assert flat['tomogram']['sha256'] == scope['frozen_assets']['pct_tomogram']['sha256']
    points = flat['segment_ground_xyz_m']
    pilot = {
        'schema_version': 1,
        'profile': 'diagnostic_simulator_truth_known_map',
        'frame_id': 'world', 'units': 'm', 'pct_layer': 1,
        'nominal_body_height_m': 0.35,
        'spawn_ground_xyz_m': points[0],
        'spawn_yaw_rad': flat['segment']['start_tangent_yaw_radians'],
        'goals': [{'goal_id': 'goal-a', 'ground_xyz_m': points[80]},
                  {'goal_id': 'goal-b', 'ground_xyz_m': points[160]}],
        'selection': 'Endpoints selected on the previously geometry-audited flat platform; every execution route must be freshly computed by native PCT from measured pose.',
        'no_reference_route_replay': True,
        'max_sim_seconds': 45.0, 'max_wall_seconds': 1200.0,
        'goal_xy_tolerance_m': 0.25, 'goal_z_tolerance_m': 0.20,
        'stop_dwell_sim_seconds': 1.0, 'stop_speed_mps': 0.10,
        'stop_yaw_rate_radps': 0.15, 'stop_command_norm': 0.01,
        'required_arrivals': 2, 'initialization_only_reset': True,
        'cancellation_test': 'Cancel the first attempt of goal-a after at least 0.4 m measured displacement; require confirmed stop before resubmitting goal-a, then execute goal-b.',
        'provisional': 'Resource/deadline bounds are fixed for the first pilot; changes require a new declared run configuration and preserve failed attempts.',
    }
    pilot_data = (json.dumps(pilot, indent=2) + '\n').encode()
    pilot_path = HERE / 'inputs/pilot.json'
    if pilot_path.exists() and pilot_path.read_bytes() != pilot_data:
        raise RuntimeError('Pilot already frozen with different settings')
    pilot_path.write_bytes(pilot_data)
    files.append({'source': 'derived by freeze_inputs.py from flat_segment.original.json endpoint selection',
                  'path': 'inputs/pilot.json', 'sha256': digest(pilot_data), 'bytes': len(pilot_data)})
    result = {'files': files, 'locomotion_source': 'references/upstream/2026-09-11_lite3_v12_locomotion',
              'checkpoint_sha256': scope['frozen_assets']['checkpoint']['sha256'],
              'source_selection': 'Only data/configuration artifacts copied from the baseline; executable source comes from already imported pinned snapshots.',
              'regeneration': 'python3 ' + str(Path(__file__).relative_to(ROOT))}
    (HERE / 'input_manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'input_count': len(files), 'pilot': pilot}, indent=2))


if __name__ == '__main__':
    main()
