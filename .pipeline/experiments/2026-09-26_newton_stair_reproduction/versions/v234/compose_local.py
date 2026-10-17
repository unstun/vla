"""Recover the exact frozen v232 source tree from existing local snapshots."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
VERSIONS = HERE.parent
ROOT = next(p for p in HERE.parents if (p / 'AGENTS.md').is_file())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    inventory = json.loads((VERSIONS / 'v232/results/source_inventory.json').read_text())
    snapshots = sorted((p for p in VERSIONS.iterdir() if p.name.startswith('v')
                        and p.name[1:].isdigit() and int(p.name[1:]) <= 232),
                       key=lambda p: int(p.name[1:]), reverse=True)
    audit = VERSIONS.parent / 'audits/2026-09-30_native_local_profile/native_profile'
    mapping = {}
    for rel, expected in inventory.items():
        source = next((base / rel for base in [*snapshots, audit]
                       if (base / rel).is_file() and sha(base / rel) == expected), None)
        assert source, f'No locally pinned source for {rel}'
        mapping[rel] = dict(source=str(source.relative_to(ROOT)), sha256=expected)
    assert len(mapping) == 317
    args.output.mkdir(parents=True)
    for rel, row in mapping.items():
        target = args.output / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / row['source'], target)
        assert sha(target) == row['sha256']
    (args.output / 'source_inventory.json').write_text(json.dumps(inventory, indent=2) + '\n')
    (args.output / 'local_source_mapping.json').write_text(json.dumps(mapping, indent=2) + '\n')
    print(json.dumps(dict(files=len(mapping), output=str(args.output), exact_frozen_source=True)))


if __name__ == '__main__':
    main()
