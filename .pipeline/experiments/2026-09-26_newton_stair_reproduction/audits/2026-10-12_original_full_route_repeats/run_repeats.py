"""Six declared fresh v147 full-route trials; retain and count all outcomes."""
from pathlib import Path
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
VERSION = BASE / 'versions/v147'
TASK = Path('/data/sun/vla_mppi_20261009')
OUTPUT = TASK / 'results/full_route_repeats_20261012'
ATTEMPTS = tuple(range(2, 8))


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024**2), b''):
            digest.update(block)
    return digest.hexdigest()


def save(path, value):
    temporary = path.with_suffix('.pending')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def identities():
    checked = subprocess.run([sys.executable, str(VERSION / 'freeze_host.py'), 'verify'],
                             check=True, capture_output=True, text=True)
    receipt_path = TASK / 'results/recovery_v147/candidate_receipt.json'
    quality = json.loads((VERSION / 'quality.json').read_text())
    assert sha(receipt_path) == quality['runtime_receipts']['candidate']
    receipt = json.loads(receipt_path.read_text())
    assert receipt['native_version'] == 'v147' and receipt['passed']
    for name, digest in receipt['files'].items():
        assert sha(TASK / Path(name).relative_to('/task')) == digest, name
    profile = BASE / 'inputs/historical_full_building.json'
    assert sha(profile) == '6afa0e573c268aca641f7d176f55bbf720b6521db8e5ce8153e2baece1b5b621'
    return {'frozen': json.loads(checked.stdout), 'version_manifest_sha256': sha(VERSION / 'manifest.json'),
            'candidate_receipt_sha256': sha(receipt_path), 'installed_files_verified': len(receipt['files']),
            'original_profile_sha256': sha(profile), 'plan_sha256': sha(HERE / 'PLAN.md'),
            'runner_sha256': sha(Path(__file__))}


def resources():
    gpu = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.used,utilization.gpu',
                          '--format=csv,noheader'], capture_output=True, text=True, timeout=20)
    containers = subprocess.check_output(['docker', 'ps', '--format', '{{.Names}}'], text=True).strip()
    return {'unix_s': time.time(), 'load': os.getloadavg(), 'cpu_count': os.cpu_count(),
            'free_bytes': shutil.disk_usage(TASK).free, 'containers': containers,
            'gpu': gpu.stdout.strip(), 'gpu_query_exit': gpu.returncode,
            'memory': Path('/proc/meminfo').read_text().splitlines()[:3]}


def main():
    assert platform.system() == 'Linux' and HERE.is_relative_to(TASK / 'repo')
    tags = [f'v147_full_candidate_attempt{a:02d}' for a in ATTEMPTS]
    for tag in tags:
        assert not (TASK / 'trials' / tag).exists(), tag
        assert not (TASK / 'results/recording_v147' / tag).exists(), tag
    OUTPUT.mkdir(exist_ok=False)
    before = identities()
    save(OUTPUT / 'identities_before.json', before)
    save(OUTPUT / 'request.json', {'host': 'gpu5070ti', 'pid': os.getpid(),
                                 'started_unix_s': time.time(), 'stage': 'experiment + analysis',
                                 'tags': tags, 'excluded_pilot': 'v147_full_candidate_attempt01',
                                 'identities': before, 'navigation_failure_early_stop': False})
    progress = {'state': 'running', 'completed': [], 'active': None}
    try:
        for index, attempt in enumerate(ATTEMPTS, 1):
            tag = tags[index - 1]
            preflight = resources()
            assert preflight['free_bytes'] > 15 * 1024**3, 'Insufficient disk margin'
            assert not preflight['containers'], 'Existing host container; inspect ownership'
            save(OUTPUT / f'{tag}_preflight.json', preflight)
            progress['active'] = tag
            save(OUTPUT / 'progress.json', progress)
            print(json.dumps({'event': 'start', 'index': index, 'tag': tag, **preflight}), flush=True)
            with (OUTPUT / f'{tag}_driver.log').open('w') as stream:
                process = subprocess.run([sys.executable, str(VERSION / 'run_recording.py'),
                                          '--variant', 'candidate', '--attempt', str(attempt)],
                                         stdout=stream, stderr=subprocess.STDOUT, timeout=1400)
            result_dir = TASK / 'results/recording_v147' / tag
            path = result_dir / 'outcome.json'
            assert path.exists(), f'{tag}: missing outcome; runner exit {process.returncode}'
            outcome = json.loads(path.read_text())
            metrics = outcome.get('metrics', {})
            terminal = metrics.get('terminal') or {}
            root = TASK / 'trials' / tag / 'runs' / tag
            route_file = root / 'full_route_verification.json'
            route = json.loads(route_file.read_text()) if route_file.exists() else {}
            row = {'index': index, 'tag': tag, 'runner_exit': process.returncode,
                   'execution_exit': outcome.get('execution_exit'),
                   'terminal': terminal.get('backend_terminal_status'), 'terminal_note': terminal.get('note'),
                   'fallen': metrics.get('fallen'), 'copyback': metrics.get('state_copyback_verified'),
                   'retention': outcome.get('retention'), 'path_m': metrics.get('measured_path_m'),
                   'end_sim_s': metrics.get('actual_physics_end_s'), 'full_route_passed': route.get('passed', False),
                   'planning': metrics.get('planning'), 'outcome_sha256': sha(path)}
            progress['completed'].append(row)
            progress['active'] = None
            save(OUTPUT / 'progress.json', progress)
            print(json.dumps({'event': 'end', **row}), flush=True)
            # A FAILED terminal normally makes the original route checker exit1.
            # Keep that actual failure in the denominator and continue the batch.
            assert outcome.get('execution_exit') == 0, f'{tag}: execution failure'
            assert outcome.get('retention') == 'completed', f'{tag}: retention failure'
            assert metrics.get('state_copyback_verified'), f'{tag}: copyback failure'
            assert route_file.exists(), f'{tag}: missing route check'
            assert not (root / '.artifact-active').exists(), f'{tag}: active writer marker'
            assert process.returncode == 0 or (process.returncode == 1 and route['passed'] is False), \
                f'{tag}: unexpected runner failure'
        after = identities()
        assert after == before, 'Frozen or installed identity changed during the batch'
        save(OUTPUT / 'identities_after.json', after)
        save(OUTPUT / 'resources_after.json', resources())
        progress['state'] = 'completed'
    except BaseException as error:
        progress['state'] = 'interrupted'
        progress['error'] = repr(error)
        raise
    finally:
        progress['updated_unix_s'] = time.time()
        save(OUTPUT / 'progress.json', progress)
        print(json.dumps({'event': 'batch_state', **progress}), flush=True)


if __name__ == '__main__':
    main()
