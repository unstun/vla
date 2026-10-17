"""Freeze the Mac display source for v193 without promoting v192 navigation."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def verify():
    m = json.loads((HERE / 'manifest.json').read_text())
    for n, e in m['source_files'].items():
        assert sha(ROOT / n) == e and sha(ROOT / m['snapshot_locations'][n]) == e, n
    assert sha(HERE / 'quality.json') == m['quality_sha256']
    assert sha(BASE / 'versions/v192/manifest.json') == m['parent_manifest_sha256']
    assert sha(BASE / 'versions/v190/manifest.json') == m['display_parent_manifest_sha256']
    print(json.dumps({'passed': True, 'version': 'v193', 'source_pairs': len(m['source_files']), 'display_only': True}))


def freeze():
    assert not (HERE / 'manifest.json').exists()
    p = json.loads((BASE / 'versions/v192/manifest.json').read_text())
    files = dict(p['source_files'])
    locations = dict(p['snapshot_locations'])
    q = json.loads((HERE / 'quality.json').read_text())
    assert q['passed'] and q['display_accepted']
    for path in sorted(HERE.iterdir()):
        if path.is_file() and (path.suffix in ('.py', '.md') or path.name == 'source_identity.json'):
            n = str(path.relative_to(ROOT))
            e = sha(path)
            s = HERE / 'source' / n
            s.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, s)
            files[n] = e
            locations[n] = str(s.relative_to(ROOT))
    m = {
        'version': 'v193',
        'parent': 'v192',
        'display_parent': 'v190',
        'physical_source': 'v192_mac_full_attempt01',
        'parent_manifest_sha256': sha(BASE / 'versions/v192/manifest.json'),
        'display_parent_manifest_sha256': sha(BASE / 'versions/v190/manifest.json'),
        'status': 'frozen_display_review_v192_mac_full_attempt01_failed_nav2_route',
        'platform': 'Mac ARM64 Cocoa ViewerGL replay, CPU model construction, no physics steps',
        'source_files': files,
        'snapshot_locations': locations,
        'quality_sha256': sha(HERE / 'quality.json'),
    }
    (HERE / 'manifest.json').write_text(json.dumps(m, indent=2) + '\n')
    verify()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['freeze', 'verify'])
    args = parser.parse_args()
    (freeze if args.action == 'freeze' else verify)()
