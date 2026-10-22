"""Recover frozen v286 native bytes from local pinned snapshots only."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[2]
VERSIONS = EXP / 'versions'
REPO = next(p for p in HERE.parents if (p / 'AGENTS.md').is_file())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    version = VERSIONS / 'v286'
    manifest = json.loads((version / 'native_manifest.json').read_text())
    inventory_path = version / 'results/native_source_inventory.json'
    assert sha(inventory_path) == manifest['source_inventory_sha256']
    inventory = json.loads(inventory_path.read_text())
    snapshots = sorted((p for p in VERSIONS.iterdir() if p.name.startswith('v')
        and p.name[1:].isdigit() and int(p.name[1:]) <= 286),
        key=lambda p: int(p.name[1:]), reverse=True)
    candidates = snapshots + [EXP / 'audits/2026-09-30_native_local_profile/native_profile']
    mapping = {}
    for relative, expected in inventory.items():
        source = next((base / relative for base in candidates
            if (base / relative).is_file() and sha(base / relative) == expected), None)
        assert source is not None, ('Missing frozen source', relative, expected)
        mapping[relative] = dict(source=str(source.relative_to(REPO)), sha256=expected)
    assert len(mapping) == 329
    for relative, row in mapping.items():
        target = args.output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / row['source'], target)
        assert sha(target) == row['sha256']
    (args.output / 'source_inventory.json').write_bytes(inventory_path.read_bytes())
    report = dict(frozen_native_manifest_sha256=sha(version / 'native_manifest.json'),
        navigation_source_changed=False, files=mapping, source_files=len(mapping))
    (args.output / 'recovery.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(source_files=len(mapping), all_frozen_hashes_match=True)))


if __name__ == '__main__':
    main()
