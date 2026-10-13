"""Freeze v52-owned source and reference immutable inherited snapshots."""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
BASE = HERE.parents[1]
NATIVE = BASE / 'runtime/scan74_terrain_lookup_v52'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not (HERE / 'manifest.json').exists(), 'Frozen versions are immutable'
    parent_path = HERE.parent / 'v50/manifest.json'
    parent = json.loads(parent_path.read_text())
    selected = dict(parent['source_files'])
    for name, digest in selected.items():
        assert sha(ROOT / name) == digest, name
        assert sha(HERE.parent / 'v50/source' / name) == digest, name
    qualification = json.loads((HERE / 'component_qualification.json').read_text())
    for key in ('cache_geometry_and_contract_passed', 'warm_contract_passed',
                'goal_region_contract_passed', 'paired_replay_passed',
                'backend_contract_passed', 'terrain_lookup_contract_passed'):
        assert qualification[key], key
    runtime = json.loads((HERE / 'runtime_preparation.json').read_text())
    for name, row in runtime['files'].items():
        assert sha(HERE.parent / 'v50' / name) == row['parent_sha256']
        assert sha(HERE / name) == row['output_sha256']
    owned = []
    for name in ('PLAN.md', 'IMPLEMENTATION.md', 'changes.patch', 'preparation.json',
                 'materialize.py', 'runtime_preparation.json', 'freeze_source.py',
                 'component_qualification.json', 'remote_build.py', 'remote_test.py',
                 'remote_profile.py', 'remote_trial.py', 'analyze_trial.py',
                 'test_backend_contract.py', 'building_planner.yaml', 'controller.yaml'):
        owned.append(HERE / name)
    owned.extend(HERE / name for name in runtime['files'])
    for directory in (HERE / 'contract', HERE / 'profiling', HERE / 'backend_ros', NATIVE / 'src'):
        owned.extend(p for p in directory.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    owned.extend(NATIVE / name for name in ('source_sha256.json', 'install_sha256.json', 'build_result.json'))
    # Bind the existing managed storage entry point without copying its parent trees.
    owned.append(BASE / 'scripts/run_managed.py')
    v51 = HERE.parent / 'v51'
    v51_manifest = json.loads((v51 / 'manifest.json').read_text())
    for name in ('managed_run.py', 'artifacts.py'):
        path = v51 / name
        assert sha(path) == v51_manifest['source_files'][str(path.relative_to(ROOT))]
        owned.append(path)
    locations = {name: str((HERE.parent / 'v50/source' / name).relative_to(ROOT))
                 for name in selected}
    for path in sorted(set(owned)):
        name = str(path.relative_to(ROOT))
        selected[name] = sha(path)
        destination = HERE / 'source' / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        assert sha(destination) == selected[name]
        locations[name] = str(destination.relative_to(ROOT))
    manifest = dict(version='v52', parent='v50', native_source_parent='v50',
        parent_manifest_sha256=sha(parent_path),
        status='frozen_components_passed_physics_pending',
        source_files=dict(sorted(selected.items())),
        snapshot_locations=dict(sorted(locations.items())),
        snapshot_storage='Inherited bytes reference frozen v50/source; v52 owns only its selected delta',
        native_source_sha256=json.loads((NATIVE / 'source_sha256.json').read_text()),
        native_install_sha256=json.loads((NATIVE / 'install_sha256.json').read_text()),
        physics_run=False, full_stack_integrated=False, navigation_validated=False)
    (HERE / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(dict(version='v52', frozen_files=len(selected),
                         own_snapshot_files=len(set(owned)), validated=False)))


if __name__ == '__main__':
    main()
