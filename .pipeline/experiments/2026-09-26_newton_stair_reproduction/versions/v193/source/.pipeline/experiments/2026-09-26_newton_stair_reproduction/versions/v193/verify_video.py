"""Validate exact causal timeline, visible curves and the finished MP4 for v192_mac_full_attempt01."""
from pathlib import Path
import hashlib
import json
import math
import numpy as np

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
TASK = Path('/private/tmp/vla_stop_audit_20261012')
OUT = TASK / 'video_v193/runs/full01'


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(4 * 1024**2), b''):
            digest.update(block)
    return digest.hexdigest()


def main():
    contract = json.loads((TASK / 'video_v193/display_contract.json').read_text())
    source = Path(contract['physical_source_root'])
    original = json.loads((source / 'video_states.json').read_text())
    route = json.loads(Path(contract['route_verification']).read_text())
    assert route['passed'] is False
    metrics = json.loads(Path(contract['analysis_metrics']).read_text())
    assert metrics['terminal']['backend_terminal_status'] == 'FAILED'
    proof = json.loads((source / 'initial_state.json').read_text())
    assert proof['passed'] and proof['physics_steps'] == 0 and proof['physics_time_s'] == 0.0
    assert original[0] == proof['frame'] and original[0]['physics_time_s'] == 0.0
    assert original[0]['recorded_before_first_physics_step']
    start = next(i for i, r in enumerate(original) if 'wall_monotonic_s' in r)
    startup = original[:start]
    nav = original[start:]
    sim = np.array([r['physics_time_s'] for r in startup])
    times = np.array([r['wall_monotonic_s'] for r in nav])
    assert json.loads((source / 'factory_video_states.json').read_text()) == startup
    ns = int(math.ceil((nav[0]['physics_time_s'] - sim[0]) * 30))
    nn = int(np.ceil((times[-1] - times[0]) * 30)) + 1
    n = ns + nn
    frames = json.loads((OUT / 'frames.json').read_text())
    curves = json.loads((OUT / 'curve_frames.json').read_text())
    cameras = json.loads((OUT / 'heading_camera.json').read_text())['cameras']
    assert len(frames) == len(curves) == len(cameras) == n
    expected_start = np.maximum(0, np.searchsorted(sim, sim[0] + np.arange(ns) / 30, side='right') - 1)
    expected_nav = np.maximum(0, np.searchsorted(times, times[0] + np.arange(nn) / 30, side='right') - 1) + start
    expected = np.concatenate([expected_start, expected_nav])
    assert int(expected[0]) == 0 and int(expected[-1]) == len(original) - 1
    visible = 0
    routes_visible = 0
    for i, (f, r) in enumerate(zip(frames, curves)):
        src = original[int(expected[i])]
        assert f['source_state_index'] == r['source_state_index'] == int(expected[i])
        assert f['physics_time_s'] == r['physics_time_s'] == src['physics_time_s']
        if i < ns:
            assert f['timeline_segment'] == 'startup sim'
            assert r['source_wall_s'] is None and r['trajectory_id'] is None and r['latest_completed_solve_ms'] is None
        else:
            assert f['timeline_segment'] == 'navigation wall 1:1'
            assert r['source_wall_s'] == src['wall_monotonic_s']
        assert abs(f['display_time_s'] - i / 30) < 1e-7
        if r['trajectory_id'] is not None:
            assert r['curve_event_wall_s'] <= r['source_wall_s'] and r['sampled_points'] == 150
            assert -1e-6 <= r['physics_time_s'] - r['curve_start_s']
            assert r['physics_time_s'] <= r['curve_end_s'] + .15
            assert -1e-6 <= r['source_wall_s'] - r['command_event_wall_s'] <= .15
            assert -1e-6 <= r['physics_time_s'] - r['command_clock_s'] <= .15
            visible += 1
        if r['route_points']:
            assert r['route_event_wall_s'] <= r['source_wall_s']
            assert r['route_clock_s'] <= r['physics_time_s'] + 1e-6
            routes_visible += 1
        if r['solve_finish_wall_s'] is not None:
            assert r['solve_finish_wall_s'] <= r['source_wall_s']
    assert visible > n // 2 and routes_visible > n // 2
    # Re-evaluate the original event stream against every delivered frame.
    from curve_overlay import Overlay
    from full_timeline import load_rows
    replay = Overlay(source, contract['latency_csv'])
    for row, actual in zip(load_rows(source), curves):
        _, wanted = replay.frame(row)
        assert actual == wanted
    assert curves[-1]['trajectory_id'] is None
    result = json.loads((OUT / 'result.json').read_text())
    verification = json.loads((OUT / 'video_verification.json').read_text())
    port = json.loads((OUT / 'host_port_verification.json').read_text())
    assert result['render_only_no_physics_steps'] and port['source_unchanged']
    assert port['render_only_no_physics_steps'] and verification['full_decode_passed']
    assert frames[-1]['navigation_status'].startswith('failed (nav2_failed)')
    for name, expected_sha in contract['input_files'].items():
        assert sha(Path(name)) == expected_sha, name
    master = OUT / 'newton_stair_recorded.mp4'
    assert sha(master) == result['video_sha256'] and master.stat().st_size < 80_000_000
    data = {
        'passed': True,
        'physical_source_run': contract['physical_source_run'],
        'physical_source_version': 'v192',
        'display_version': 'v193',
        'frames': n,
        'startup_frames': ns,
        'startup_original_frames': start,
        'first_physics_s': original[0]['physics_time_s'],
        'navigation_frames': nn,
        'startup_clock': 'original simulation timestamps; no wall stamps invented',
        'navigation_clock': 'original wall timestamps, 1:1',
        'fps': 30,
        'duration_s': n / 30,
        'curve_visible_frames': visible,
        'global_route_visible_frames': routes_visible,
        'last_physics_s': frames[-1]['physics_time_s'],
        'last_source_state_index': frames[-1]['source_state_index'],
        'complete_first_and_last_recorded_states': True,
        'causal_source_indices_checked': n,
        'no_future_curve_events': True,
        'terminal_frame': frames[-1]['navigation_status'],
        'full_route_gate_passed': False,
        'measured_path_m': metrics['measured_path_m'],
        'render_only_no_physics_steps': True,
        'full_decode_passed': True,
        'video_sha256': sha(master),
        'video_bytes': master.stat().st_size,
        'video_master': str(master),
        'source_contract_sha256': sha(TASK / 'video_v193/display_contract.json'),
        'checker_sha256': sha(Path(__file__)),
        'claim': ('Complete original-start Option B v192_mac_full_attempt01 episode, continuous recorded '
                  'physical state; FAILED/nav2_failed at 118.886s and 72.572m. No arrival or full-route acceptance.'),
    }
    (OUT / 'delivery_verification.json').write_text(json.dumps(data, indent=2) + '\n')
    quality = {
        'passed': True,
        'display_accepted': True,
        'overlay_unit_tests': 10,
        'timeline_unit_tests': 4,
        'input_source_unchanged': True,
        'physical_rerun': False,
        'physics_acceptance_from_this_render': False,
        'checks': {
            'delivery': {'path': str(OUT / 'delivery_verification.json'), 'sha256': sha(OUT / 'delivery_verification.json')},
            'stream': {'path': str(OUT / 'video_verification.json'), 'sha256': sha(OUT / 'video_verification.json')},
            'host': {'path': str(OUT / 'host_port_verification.json'), 'sha256': sha(OUT / 'host_port_verification.json')},
        },
    }
    (HERE / 'quality.json').write_text(json.dumps(quality, indent=2) + '\n')
    print(json.dumps(data))


if __name__ == '__main__':
    main()
