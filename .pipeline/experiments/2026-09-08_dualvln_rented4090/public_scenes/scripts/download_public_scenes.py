"""Acquire the public Habitat test scenes named by OPUS_PUBLIC_SCENES_PACKAGE.

Downloads skokloster-castle and van-gogh-room (mesh + navmesh) from the pinned
ai-habitat/habitat_test_scenes revision, verifies byte size against the pinned
manifest, verifies SHA-256 against the upstream LFS oid where the manifest has
one, and records SHA-256 for every acquired file.

Unlike scripts/download_scene.py this does not assume anything is cached.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WANT = [
    'skokloster-castle.glb',
    'skokloster-castle.navmesh',
    'van-gogh-room.glb',
    'van-gogh-room.navmesh',
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    meta = json.loads((ROOT / 'setup/habitat_scene_source.json').read_text())
    by_path = {item['path']: item for item in meta['files'] if item['type'] == 'file'}
    # One directory per scene so that the evaluator's `scene_id.split('/')[-2]`
    # yields a distinct scene name, and so habitat-sim finds `<stem>.navmesh`
    # next to `<stem>.glb` exactly as in the mp3d layout.
    base = ROOT / 'public_scenes/data/scene_data/public'

    rows = []
    for name in WANT:
        item = by_path.get(name)
        if item is None:
            print(f'MISSING_IN_MANIFEST {name}', file=sys.stderr)
            return 2
        stem = name.split('.')[0]
        dest = base / stem
        dest.mkdir(parents=True, exist_ok=True)
        target = dest / name
        url = (
            f'https://huggingface.co/datasets/{meta["repo"]}'
            f'/resolve/{meta["revision"]}/{name}'
        )
        if not (target.exists() and target.stat().st_size == item['size']):
            subprocess.run(
                ['curl', '-fL', '--retry', '3', '--connect-timeout', '15',
                 '--max-time', '900', '-C', '-', '-o', str(target), url],
                check=True,
            )
        actual_size = target.stat().st_size
        if actual_size != item['size']:
            print(f'SIZE_MISMATCH {name} {actual_size} != {item["size"]}', file=sys.stderr)
            return 3
        digest = sha256(target)
        expected = item.get('lfs', {}).get('oid')
        if expected and digest != expected:
            print(f'SHA_MISMATCH {name} {digest} != {expected}', file=sys.stderr)
            return 4
        rows.append({
            'path': str(target.relative_to(ROOT)),
            'source_url': url,
            'bytes': actual_size,
            'sha256': digest,
            'upstream_lfs_sha256': expected,
            'sha256_verified_against_upstream': bool(expected),
            'git_blob_oid': item['oid'],
        })
        print(f'OK {name} {actual_size} {digest}')

    out = ROOT / 'public_scenes/setup/public_scene_manifest.json'
    out.write_text(json.dumps({
        'repo': meta['repo'],
        'revision': meta['revision'],
        'license': meta['cardData']['license'],
        'note': ('navmesh files are plain git blobs upstream (no LFS oid), so their '
                 'SHA-256 is recorded here but not cross-checked against an upstream digest; '
                 'byte size is checked against the pinned manifest.'),
        'files': rows,
    }, indent=2) + '\n')
    print('PUBLIC_SCENES_VERIFIED')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
