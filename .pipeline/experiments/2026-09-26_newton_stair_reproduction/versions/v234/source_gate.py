"""Direct immutable source/install gate, without historical launch dependencies."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
VERSIONS = HERE.parent
ROOT = next(p for p in HERE.parents if (p / 'AGENTS.md').is_file())


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def verify_map(root, mapping):
    for rel, expected in mapping.items():
        assert sha(root / rel) == expected, str(root / rel)
    return len(mapping)


def verify_source(work):
    own_identity = HERE / 'source_identity.json'
    if own_identity.is_file():
        verify_map(HERE, json.loads(own_identity.read_text())['files'])
    baseline = VERSIONS / 'v232'
    execution = VERSIONS / 'v233'
    frozen = json.loads((baseline / 'manifest.json').read_text())
    count = verify_map(baseline, frozen['files'])
    manifest = json.loads((execution / 'manifest.json').read_text())
    verify_map(execution, manifest['source_files'])
    verify_map(execution, json.loads((execution / 'source_identity.json').read_text())['files'])
    inventory = json.loads((work / 'source_inventory.json').read_text())
    assert inventory == json.loads((baseline / 'results/source_inventory.json').read_text())
    assert len(inventory) == 317
    verify_map(work, inventory)
    binding = json.loads((HERE / 'binding.json').read_text())
    policy = ROOT / '.pipeline/experiments/2026-09-26_newton_macos_policy/policy/policy_stateless_h10.onnx'
    assert sha(policy) == binding['policy_sha256']
    return dict(passed=True, physics_steps=0, frozen_v232_files=count, source_files=317,
                v232_manifest_sha256=sha(baseline / 'manifest.json'),
                v233_manifest_sha256=sha(execution / 'manifest.json'), policy_sha256=sha(policy))


def verify(work):
    report = verify_source(work)
    baseline = VERSIONS / 'v232'
    inventory = json.loads((work / 'source_inventory.json').read_text())
    receipt = json.loads((work / 'native_rebuild_receipt.json').read_text())
    assert receipt['passed'] and receipt['unique_test_cases'] == 165 and receipt['colcon_records'] == 186
    assert receipt['physics_steps'] == 0 and receipt['source_inventory'] == inventory
    assert receipt['source_identity_sha256'] == sha(baseline / 'source_identity.json')
    old_receipt = json.loads((baseline / 'results/offline_gate.json').read_text())
    assert set(old_receipt['installed_files']).issubset(receipt['installed_files'])
    verify_map(work, receipt['installed_files'])
    binding = json.loads((HERE / 'binding.json').read_text())
    assert receipt['native_image'] == binding['native_image']
    assert receipt['native_packages'] == 14 and receipt['all_package_prefixes_current']
    assert receipt['original_install_byte_identity'] is False
    assert sha(work / 'fixtures/building/environment225.env') == binding['environment_sha256']
    report.update(host_tests_rerun=True, installed_files=len(receipt['installed_files']),
                  original_607_paths_present=True, original_install_byte_identity=False,
                  native_image=binding['native_image'], historical_dynamic_replay_rerun=False,
                  full_offline_acceptance=False)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    report = verify(args.work)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
