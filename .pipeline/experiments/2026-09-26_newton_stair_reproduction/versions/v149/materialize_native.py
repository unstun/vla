"""Rebuild the executed v147 export from matching frozen local source bytes."""
from collections import defaultdict
from pathlib import Path
import argparse
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task-root', type=Path, required=True)
    args = parser.parse_args()
    task = args.task_root.resolve()
    assert task.parent == Path('/private/tmp') and task.name.startswith('vla_newton_v149_')
    identity = task / 'evidence/v147_source_identity.json'
    exported = json.loads(identity.read_text())
    assert exported['version'] == 'v147'
    manifest = json.loads((HERE.parent / 'v147/manifest.json').read_text())
    lookup = defaultdict(list)
    for name, digest in manifest['source_files'].items():
        lookup[digest].append(name)
    inputs = json.loads((HERE.parent / 'v147/runtime_sync_manifest.json').read_text())
    for name, entry in inputs['files'].items():
        lookup[entry['sha256']].append(name)
    workspace = task / 'recovery_v147'
    workspace.mkdir(exist_ok=False)
    mappings, metadata = {}, []
    for name, digest in exported['files'].items():
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        options = sorted(set(lookup[digest]))
        if not options:
            assert '/' not in name and (name.endswith('_parent_source_identity.json')
                                        or name == 'v89_parent_materialization.json'), name
            metadata.append(name)
            continue
        source = ROOT / options[0]
        assert sha(source) == digest, source
        if options[0] in manifest['snapshot_locations']:
            assert sha(ROOT / manifest['snapshot_locations'][options[0]]) == digest
        destination = workspace / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        assert sha(destination) == digest
        mappings[name] = {'local_source': options[0], 'sha256': digest}
    assert len(mappings) == 631 and len(metadata) == 15
    (task / 'evidence/native_metadata_allowlist.txt').write_text('\n'.join(metadata) + '\n')
    (task / 'evidence/local_source_materialization.json').write_text(json.dumps({
        'native_version': 'v147', 'parent_manifest_sha256': sha(HERE.parent / 'v147/manifest.json'),
        'executed_source_identity_sha256': sha(identity), 'files': mappings,
        'non_build_historical_metadata': metadata,
        'claim': 'All source, configuration, third-party and license bytes originate in frozen local files. Only historical export receipts require remote return.'}, indent=2) + '\n')
    shutil.copyfile(identity, workspace / 'source_identity.json')
    print(json.dumps({'local_files_verified': len(mappings), 'historical_metadata_pending': metadata}))


if __name__ == '__main__':
    main()
