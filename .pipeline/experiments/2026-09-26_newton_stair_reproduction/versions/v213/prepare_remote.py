"""Bind the recorded v212_linux_full_attempt01 episode to a full causal review video."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
TASK = Path('/data/sun/vla_mppi_20261009/trials/v212_linux_full_attempt01')


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(4 * 1024**2), b''):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    tag = 'v212_linux_full_attempt01'
    source = TASK / 'runs' / tag
    analysis = BASE / 'versions/v212/results'
    outcome = analysis / 'outcome.json'
    route = analysis / 'full_route_verification.json'
    outcome_data = json.loads(outcome.read_text())
    route_data = json.loads(route.read_text())
    assert outcome_data['run'] == tag
    assert outcome_data['terminal_status'] in ('FINISHED','FAILED')
    assert outcome_data['full_route_gate_passed'] == route_data['passed']
    proof = json.loads((source / 'initial_state.json').read_text())
    assert proof['passed'] and proof['physics_time_s'] == 0.0 and proof['physics_steps'] == 0
    assert json.loads((source / 'video_states.json').read_text())[0] == proof['frame']
    metrics = json.loads((analysis / 'metrics.json').read_text())
    assert metrics['terminal']['backend_terminal_status'] == outcome_data['terminal_status']
    assert metrics['shared_state_verified']
    root = TASK / 'video_v213'
    root.mkdir(exist_ok=False)
    (root / 'runs').mkdir()
    (root / 'cache').mkdir()
    for name in ('test_overlay.py', 'test_timeline.py'):
        subprocess.run([sys.executable, str(HERE / name)], check=True)
    inputs = [route, outcome, analysis / 'metrics.json', analysis / 'latency.csv',
              BASE / 'versions/v212/execution_request.json']
    inputs += [source / name for name in (
        'initial_state.json', 'video_states.json', 'factory_video_states.json',
        'startup_pacing.json', 'raw_capture.zip', 'clock_samples.jsonl',
        'backend_states.jsonl', 'episode_request.json', 'inputs/stair_scenario.json', 'result.json')]
    identity = json.loads((HERE / 'source_identity.json').read_text())
    for name, expected in identity['files'].items():
        assert sha(HERE / name) == expected, name
    contract = {
        'physical_source_root': str(source),
        'physical_source_run': tag,
        'physical_parent': 'v212',
        'display_parent': 'v211',
        'native_implementation': 'v212 event planning + v206 navigation core + v208 locomotion',
        'source_outcome': str(outcome),
        'route_verification': str(route),
        'analysis_metrics': str(analysis / 'metrics.json'),
        'latency_csv': str(analysis / 'latency.csv'),
        'parent_manifests': {v: sha(BASE / 'versions' / v / 'manifest.json') for v in ('v211', 'v212')},
        'input_files': {str(p): sha(p) for p in inputs},
        'display_source_identity_sha256': sha(HERE / 'source_identity.json'),
        'source_outcome_sha256': sha(outcome),
        'claim': ('Display only. Entire recorded original-start v212_linux_full_attempt01 attempt, '
                  f"all pauses retained. {outcome_data['terminal_status']} at {metrics['actual_physics_end_s']:.9f}s physics; "
                  f"full-route gate passed={route_data['passed']}. "
                  'One recorded trial only. Zero new physics steps.'),
    }
    (root / 'display_contract.json').write_text(json.dumps(contract, indent=2) + '\n')
    print(json.dumps({
        'prepared': True,
        'root': str(root),
        'source': tag,
        'inputs': len(inputs),
        'contract_sha256': sha(root / 'display_contract.json'),
    }))


if __name__ == '__main__':
    main()
