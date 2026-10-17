"""Read compact state for the authorized v35 trial; never change runtime files."""
from pathlib import Path
import json

base = Path('/home/sun/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction')
run = base / 'runs/v35_historical_full01'
host = base / 'versions/v35/host'


def tail(path, size=2400):
    if not path.exists():
        return ''
    with path.open('rb') as stream:
        stream.seek(max(0, path.stat().st_size - size))
        return stream.read().decode(errors='replace')


latest = run / 'backend_latest.json'
state = json.loads(latest.read_text()) if latest.exists() else {}
owner = state.get('service', {}).get('active_owner') or {}
body = state.get('measurement_body_pose') or {}
manifest = tail(host / 'v35_historical_full01_manifest.log')
result = {
    'sim_s': state.get('scan_port', {}).get('sim_clock_s'),
    'body_xyz_m': body.get('position_world_m'),
    'horizontal_speed_mps': body.get('horizontal_speed_mps'),
    'status': owner.get('status'),
    'terminal_cause': owner.get('terminal_cause'),
    'stop_flow_present': state.get('stop_flow') is not None,
    'process_complete': (run / 'process.json').exists(),
    'result_present': (run / 'result.json').exists(),
    'runner_manifest_verified': 'manifest self-check passed' in manifest,
    'run_log_tail': tail(run / 'run.log', 900),
}
if (run / 'process.json').exists():
    process = json.loads((run / 'process.json').read_text())
    result['process'] = {key: process.get(key) for key in ('exit_code', 'timed_out', 'wall_seconds')}
print(json.dumps(result, indent=2))
