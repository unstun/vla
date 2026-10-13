"""Three unchanged pre-MPPI v114 diagnostic episodes on the verified v125 host."""
from pathlib import Path
import hashlib
import json
import socket
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
TASK = Path('/data/sun/vla_mppi_20261009')
OUT = TASK / 'results/recovery_original_v114'


def main():
    OUT.mkdir(exist_ok=False)
    progress = {'state': 'running', 'native': 'v114', 'completed': [],
                'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    for attempt in (2, 3, 4):
        tag = f'v125_baseline_attempt{attempt:02d}'
        assert not (TASK / 'trials' / tag).exists()
        assert not subprocess.check_output(['docker', 'ps', '-q'], text=True).strip()
        subprocess.run([sys.executable, str(BASE / 'versions/v125/freeze_host.py'), 'verify'], check=True)
        deadline = time.monotonic() + 180
        while True:
            try:
                for port in (46200, 46201, 46202, 46203, 8785):
                    with socket.socket() as sock:
                        sock.bind(('127.0.0.1', port))
                break
            except OSError:
                if time.monotonic() > deadline:
                    raise
                time.sleep(1)
        directory = OUT / tag
        directory.mkdir()
        print(json.dumps({'start': tag}), flush=True)
        with (directory / 'driver.log').open('w') as stream:
            subprocess.run([sys.executable, str(BASE / 'versions/v125/run_remote_corner.py'),
                            '--variant', 'baseline', '--attempt', str(attempt)],
                           stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=650)
        root = TASK / 'trials' / tag / 'runs' / tag
        with (directory / 'analysis.log').open('w') as stream:
            subprocess.run([sys.executable, str(BASE / 'versions/v125/analyze_remote.py'),
                            '--run-root', str(root), '--output', str(directory), '--metrics-only'],
                           stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=180)
        metrics = json.loads((directory / 'metrics.json').read_text())
        assert metrics['state_copyback_verified']
        assert json.loads((root / 'retention_result.json').read_text())['status'] == 'completed'
        row = {'run': tag, 'terminal': metrics['terminal'], 'fallen': metrics['fallen'],
               'path_m': metrics['measured_path_m'], 'end_sim_s': metrics['actual_physics_end_s']}
        progress['completed'].append(row)
        (OUT / 'progress.json').write_text(json.dumps(progress, indent=2) + '\n')
        print(json.dumps(row), flush=True)
    progress['state'] = 'completed'
    (OUT / 'progress.json').write_text(json.dumps(progress, indent=2) + '\n')


if __name__ == '__main__':
    main()
