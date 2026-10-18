"""Read-only final execution-copy and frozen-evidence audit on gpu5070ti."""
from pathlib import Path
import datetime
import hashlib
import json

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
VERSIONS = HERE.parent.parent/'versions'
TASK = Path('/data/sun/vla_mppi_20261009')
WORK = TASK/'cooperative_search_v240'
def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()
def inventory(root, values):
    for rel, expected in values.items():
        assert sha(root/rel) == expected, str(root/rel)

for name in ('v238', 'v239', 'v240'):
    folder = VERSIONS/name
    manifest = json.loads((folder/'manifest.json').read_text())
    inventory(folder, manifest['files'])
    inventory(folder, manifest.get('result_files', {}))
    inventory(REPO, manifest.get('supporting_sources', {}))
manifest = json.loads((VERSIONS/'v240/manifest.json').read_text())
gate = json.loads((VERSIONS/'v240/results/offline_gate.json').read_text())
assert gate['passed'] and manifest['offline_continuity_acceptance_passed']
for name in ('source_inventory', 'installed_files'):
    inventory(WORK, json.loads((VERSIONS/f'v240/results/{name}.json').read_text()))
parent = json.loads((TASK/'callback_failure_v232/offline_gate.json').read_text())
for name in ('source_inventory', 'installed_files'):
    inventory(TASK/'callback_failure_v232', parent[name])
inventory(TASK/'terminal_approach_v238', json.loads((VERSIONS/'v238/results/installed_files.json').read_text()))
inventory(TASK/'cooperative_search_v239', json.loads((VERSIONS/'v239/results/source_inventory.json').read_text()))
logs = gate['bulk_artifacts']+[r['full_log'] for r in gate['live_runs'].values()]
logs.append(gate['loaded_native_library'])
for receipt in logs:
    path = Path(receipt['path'])
    assert path.stat().st_size == receipt['bytes'] and sha(path) == receipt['sha256'], str(path)
archive = TASK/'trials/v237_linux_full_attempt01/runs/v237_linux_full_attempt01/raw_capture.zip'
assert sha(archive) == manifest['raw_v237_archive_sha256']
print(json.dumps(dict(passed=True, checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    version='v240', manifest_sha256=sha(VERSIONS/'v240/manifest.json'),
    candidate_source_files=gate['candidate_source_files_verified'], candidate_installed_files=gate['candidate_installed_files'],
    parent_source_files_unchanged=len(parent['source_inventory']), parent_install_files_unchanged=len(parent['installed_files']),
    verified_full_log_and_library_receipts=len(logs), raw_v237_archive_unchanged=True,
    physical_attempts=0, selected_physical_baseline='v232/v233', verifier_sha256=sha(Path(__file__))), indent=2))
