"""Verify retained trials and return an allowlisted compact evidence bundle."""
from pathlib import Path
import hashlib
import json
import platform
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
TASK = Path('/data/sun/vla_mppi_20261009')


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024**2), b''):
            digest.update(block)
    return digest.hexdigest()


def main():
    assert platform.system() == 'Linux' and HERE.is_relative_to(TASK / 'repo')
    assert not subprocess.check_output(['docker', 'ps', '--format', '{{.Names}}'], text=True).strip()
    result = TASK / 'results'
    progress = json.loads((result / 'recovery_v131_repeats/progress.json').read_text())
    assert progress['state'] == 'completed' and len(progress['completed']) == 12
    output = result / 'recovery_return_v1'
    output.mkdir(exist_ok=False)
    names = ['recovery_original_v114', 'recovery_red01', 'recovery_red02',
             'recovery_origin_contract', 'recovery_stop_contract', 'recovery_retry_contract',
             'recovery_v128', 'recovery_v128_repeats', 'recovery_v129', 'recovery_v130',
             'recovery_v131', 'recovery_v131_repeats', 'recovery_foxy_reference',
             'recovery_route_diagnosis', 'recovery_v132', 'recovery_v133',
             'recovery_v133_pilots', 'recovery_refresh_contract']
    include_names = {'outcome.json', 'metrics.json', 'latency.csv', 'remote_artifacts.json',
                     'result.json', 'gateway.json', 'input.json', 'request.json', 'progress.json',
                     'summary.json', 'events.json', 'trials.csv', 'proofs.json', 'stop_windows.json',
                     'native_graph_preflight.json', 'output_ownership_test.json', 'host_tests.log',
                     'baseline_receipt.json', 'candidate_receipt.json', 'build_request.json',
                     'build.log', 'run.log', 'run.sh', 'tests.xml', 'pilot_events.json',
                     'pilot_proofs.json', 'fixture.xml', 'provenance.json', 'package.xml',
                     'first_failed_routes.json', 'posture.json', 'diagnosis.json', 'input_identity.json'}
    selected = []
    for name in names:
        for path in (result / name).rglob('*'):
            if not path.is_file() or any(p in ('build', 'ros_logs') for p in path.relative_to(result / name).parts):
                continue
            if path.name in include_names or path.name.endswith('_preflight.json') or path.suffix == '.xml':
                selected.append(path)
    verified_raw = []
    raw_seen = set()
    for path in selected:
        if path.name != 'remote_artifacts.json':
            continue
        data = json.loads(path.read_text())
        root = Path(data['root'])
        assert root.is_relative_to(TASK / 'trials')
        if root in raw_seen:
            continue
        raw_seen.add(root)
        total = 0
        for name, expected in data['files'].items():
            source = root / name
            assert source.is_relative_to(root) and source.is_file()
            assert source.stat().st_size == expected['bytes'] and sha(source) == expected['sha256'], str(source)
            total += source.stat().st_size
        verified_raw.append({'root': str(root), 'files': len(data['files']), 'bytes': total,
                             'artifact_index_sha256': sha(path)})
    versions = {}
    for version in ('v128', 'v129', 'v130', 'v131', 'v132', 'v133'):
        source = HERE.parents[1] / 'versions' / version
        check = subprocess.check_output([sys.executable, str(source / 'freeze_host.py'), 'verify'], text=True)
        receipt = json.loads((result / ('recovery_' + version) / 'candidate_receipt.json').read_text())
        for name, expected in receipt['files'].items():
            assert sha(TASK / Path(name).relative_to('/task')) == expected, name
        versions[version] = {'source_check': json.loads(check), 'manifest_sha256': sha(source / 'manifest.json'),
                             'quality_sha256': sha(source / 'quality.json'), 'native_receipt_verified': True}
    # The untouched original baseline receipt is verified separately.
    original = json.loads((result / 'baseline_receipt.json').read_text())
    for name, expected in original['files'].items():
        assert sha(TASK / Path(name).relative_to('/task')) == expected, name
    files = {}
    for path in selected:
        relative = path.relative_to(result)
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        files[str(relative)] = {'bytes': path.stat().st_size, 'sha256': sha(path)}
    report = {'passed': True, 'host': 'gpu5070ti', 'remote_root': str(TASK),
              'files': files, 'compact_bytes': sum(r['bytes'] for r in files.values()),
              'verified_raw_trials': verified_raw, 'versions': versions,
              'original_v114_receipt_verified': True,
              'collector_sha256': sha(Path(__file__))}
    (output / 'MANIFEST.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'passed': True, 'compact_files': len(files), 'compact_bytes': report['compact_bytes'],
                      'raw_trials': len(verified_raw), 'output': str(output)}), flush=True)


if __name__ == '__main__':
    main()
