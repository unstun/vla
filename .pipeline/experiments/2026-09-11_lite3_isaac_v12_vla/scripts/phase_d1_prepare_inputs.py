#!/usr/bin/env python3
"""Phase D.1a, local: turn the pinned Hugging Face listings into the two text inputs the host needs.

    python3 scripts/phase_d1_prepare_inputs.py --tree HF_TREE.json --episodes val_unseen.json.gz

Writes into setup/phase_d1_interioragent/:
  kujiale_0031_hf_tree.json            one entry per file of the scene at the pinned revision (path, size, LFS sha256
                                       or git blob sha1). The host fetch script re-lists the revision and refuses to
                                       download if the live listing differs from this file.
  kujiale_0031_val_unseen_episodes.json the 33 kujiale_0031 episodes, unchanged, from the pinned InteriorAgent_Nav file.

HF_TREE.json is the output of the HF API `tree/<revision>?recursive=true` (paginated, concatenated) for
spatialverse/InteriorAgent. No scene bytes are read or written here.
"""
import argparse
import gzip
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parents[1]
THRESHOLDS = HERE / 'phase_d' / 'stage_audit_thresholds_d1b.json'
OUT = HERE / 'setup' / 'phase_d1_interioragent'


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--tree', type=pathlib.Path, required=True)
    ap.add_argument('--episodes', type=pathlib.Path, required=True)
    args = ap.parse_args(argv)
    frozen = json.loads(THRESHOLDS.read_text())
    scene, eps_pin = frozen['scene'], frozen['episodes']
    prefix = scene['scene'] + '/'

    entries = json.loads(args.tree.read_text())
    files = []
    for e in entries:
        if e.get('type') != 'file' or not e['path'].startswith(prefix):
            continue
        lfs = e.get('lfs') or {}
        if lfs and int(lfs['size']) != int(e['size']):
            sys.exit('listing inconsistent for {}: lfs size {} != size {}'.format(e['path'], lfs['size'], e['size']))
        files.append({'path': e['path'], 'size': int(e['size']), 'lfs_sha256': lfs.get('oid'), 'git_oid': e['oid']})
    files.sort(key=lambda f: f['path'])
    total = sum(f['size'] for f in files)
    if len(files) != scene['files'] or total != scene['bytes']:
        sys.exit('listing gives {} files / {} bytes; the frozen thresholds say {} / {}'.format(
            len(files), total, scene['files'], scene['bytes']))
    if not any(f['path'] == scene['top_level_layer'] for f in files):
        sys.exit('top-level layer missing from listing: ' + scene['top_level_layer'])

    raw = args.episodes.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if len(raw) != eps_pin['bytes'] or digest != eps_pin['sha256']:
        sys.exit('episode file is not the pinned one: {} bytes, sha256 {}'.format(len(raw), digest))
    episodes = [e for e in json.loads(gzip.decompress(raw))['episodes'] if e['scan'] == scene['scene']]
    if len(episodes) != eps_pin['scan_episodes']:
        sys.exit('expected {} episodes for {}, found {}'.format(eps_pin['scan_episodes'], scene['scene'], len(episodes)))

    OUT.mkdir(parents=True, exist_ok=True)
    tree_doc = {
        'repo': scene['repo'], 'revision': scene['revision'], 'scene': scene['scene'],
        'listing': 'https://huggingface.co/api/datasets/{}/tree/{}?recursive=true (paginated)'.format(
            scene['repo'], scene['revision']),
        'resolve_url_template': 'https://huggingface.co/datasets/{}/resolve/{}/{{path}}'.format(
            scene['repo'], scene['revision']),
        'licence': 'InteriorAgent Terms of Use (PDF sha256 e7db118650cf4426d7a463686588719a3fceb985b718e2bea00b6d8e824dd1ef): '
                   'non-commercial research only, no redistribution. Bytes stay on the execution host, never in git.',
        'files': len(files), 'bytes': total,
        'lfs_files': sum(1 for f in files if f['lfs_sha256']), 'entries': files,
    }
    episodes_doc = {
        'repo': eps_pin['repo'], 'revision': eps_pin['revision'], 'file': eps_pin['file'],
        'file_bytes': eps_pin['bytes'], 'file_sha256': digest, 'licence': 'CC BY-NC 4.0',
        'scan': scene['scene'], 'episodes': episodes,
    }
    (OUT / 'kujiale_0031_hf_tree.json').write_text(json.dumps(tree_doc, indent=1) + '\n')
    (OUT / 'kujiale_0031_val_unseen_episodes.json').write_text(json.dumps(episodes_doc, indent=1) + '\n')
    print('wrote {} files / {} bytes listing and {} episodes into {}'.format(len(files), total, len(episodes), OUT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
