"""Verify unchanged installations, retained trials and compact return identities."""
from pathlib import Path
import csv
import hashlib
import json
import statistics
import subprocess
import sys

TASK = Path('/data/sun/vla_mppi_20261009')
HERE = Path(__file__).resolve().parent
RESULT = TASK / 'results/step3_repeats'
VERSION = HERE.parents[1] / 'versions/v127'


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024**2), b''):
            digest.update(chunk)
    return digest.hexdigest()


def identity(path):
    return {'remote': str(path), 'bytes': path.stat().st_size, 'sha256': sha(path)}


def main():
    progress = json.loads((RESULT / 'progress.json').read_text())
    assert progress['state'] == 'completed' and len(progress['completed']) == 12
    subprocess.run([sys.executable, str(VERSION / 'freeze_host.py'), 'verify'], check=True)
    receipts = {}
    for variant in ('baseline', 'candidate'):
        receipt = json.loads((TASK / 'results/step3_v127' / f'{variant}_receipt.json').read_text())
        for name, expected in receipt['files'].items():
            assert sha(TASK / Path(name).relative_to('/task')) == expected, name
        receipts[variant] = len(receipt['files'])
    containers = subprocess.check_output(['docker', 'ps', '--format', '{{.Names}}'], text=True).strip()
    assert not containers, containers
    for path in Path('/proc').glob('[0-9]*/cmdline'):
        try:
            command = path.read_bytes().replace(b'\0', b' ').decode(errors='replace')
        except OSError:
            continue
        assert not any(tag in command for tag in ('v127_baseline_attempt', 'v127_candidate_attempt')), command
    mapping = {}
    retained = {}
    for trial in progress['completed']:
        tag = trial['tag']
        compact = TASK / 'results/step3_v127/comparison' / tag
        original = json.loads((compact / 'remote_artifacts.json').read_text())
        count = 0
        size = 0
        for name, expected in original['files'].items():
            path = Path(original['root']) / name
            assert path.stat().st_size == expected['bytes'] and sha(path) == expected['sha256'], str(path)
            count += 1
            size += expected['bytes']
        retained[tag] = {'root': original['root'], 'verified_files': count, 'bytes': size}
        for path in compact.iterdir():
            if path.is_file() and path.suffix in ('.json', '.csv', '.log'):
                mapping['physical/' + tag + '/' + path.name] = path
    inputs = TASK / 'step3_repeats_replay/input'
    input_manifest = {'files': {str(p.relative_to(inputs)): identity(p)
                               for p in sorted(inputs.rglob('*')) if p.is_file()}}
    (RESULT / 'replay_input_manifest.json').write_text(json.dumps(input_manifest, indent=2) + '\n')
    replay = RESULT / 'replay01'
    replay_result = json.loads((replay / 'result.json').read_text())
    assert replay_result['passed']
    timing = []
    for directory in sorted(replay.glob('numeric_*')):
        if not directory.is_dir():
            continue
        with (directory / 'timing.csv').open() as stream:
            values = sorted(float(row['validation_us']) for row in csv.DictReader(stream))
        def quantile(fraction):
            index = (len(values) - 1) * fraction
            lo = int(index)
            hi = min(lo + 1, len(values) - 1)
            return values[lo] + (index - lo) * (values[hi] - values[lo])
        timing.append({'run': directory.name, 'samples': len(values),
                       'mean_us': statistics.mean(values), 'p95_us': quantile(.95),
                       'p99_us': quantile(.99), 'max_us': max(values),
                       'source': identity(directory / 'timing.csv')})
        mapping['replay/' + directory.name + '/numeric.json'] = directory / 'numeric.json'
    (RESULT / 'numeric_timing_summary.json').write_text(json.dumps(timing, indent=2) + '\n')
    for path in RESULT.iterdir():
        if path.is_file() and path.name != 'closeout_manifest.json' and path.suffix in ('.json', '.log'):
            mapping['batch/' + path.name] = path
    for path in (RESULT / 'analysis').iterdir():
        if path.is_file():
            mapping['analysis/' + path.name] = path
    for path in replay.iterdir():
        if path.is_file() and path.suffix in ('.json', '.log'):
            mapping['replay/' + path.name] = path
    for variant in ('baseline', 'candidate'):
        mapping['replay/map_' + variant + '/maps.tsv'] = replay / ('map_' + variant) / 'maps.tsv'
    for name in ('curves.csv', 'epochs.csv'):
        mapping['replay/canonical_verdicts/' + name] = replay / 'numeric_0_baseline' / name
    mapping['replay/input_identity.json'] = inputs / 'identity.json'
    record = {'passed': True, 'host': 'gpu5070ti', 'closed_trials': 12,
              'source_pairs': len(json.loads((VERSION / 'manifest.json').read_text())['source_files']),
              'runtime_inputs': len(json.loads((VERSION / 'runtime_sync_manifest.json').read_text())['files']),
              'native_receipt_files': receipts, 'owned_containers': [], 'owned_trial_processes': [],
              'retained_trials': retained, 'replay_input_files': len(input_manifest['files']),
              'files': {name: identity(path) for name, path in mapping.items()},
              'script_sha256': sha(Path(__file__))}
    record['total_return_bytes'] = sum(item['bytes'] for item in record['files'].values())
    (RESULT / 'closeout_manifest.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({key: value for key, value in record.items() if key not in ('files', 'retained_trials')}, indent=2))


if __name__ == '__main__':
    main()
