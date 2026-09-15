"""Freeze three R2R val_unseen episodes by a deterministic, outcome-independent rule.

Rule (fixed before any model trial, and independent of any model output):
  1. Group val_unseen episodes by `scene_id`.
  2. Keep scenes with at least three episodes.
  3. Sort those scene_ids lexicographically (byte order) and take the FIRST.
  4. Within that scene, sort episodes by int(episode_id) ascending and take the
     first three.

The selected episode objects are copied through unchanged, and the dataset
metadata (`instruction_vocab`) is preserved, so the derived annotation file is a
strict subset of the source in the same schema.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', required=True, help='original val_unseen.json.gz')
    ap.add_argument('--out-annotation', required=True)
    ap.add_argument('--out-manifest', required=True)
    ap.add_argument('--n', type=int, default=3)
    a = ap.parse_args()

    src = Path(a.source)
    source_sha = sha256(src)
    data = json.loads(gzip.open(src, 'rt', encoding='utf-8').read())
    episodes = data['episodes']

    by_scene = {}
    for e in episodes:
        by_scene.setdefault(e['scene_id'], []).append(e)

    eligible = sorted(s for s, v in by_scene.items() if len(v) >= a.n)
    if not eligible:
        raise SystemExit('no scene has at least %d episodes' % a.n)
    scene = eligible[0]
    picked = sorted(by_scene[scene], key=lambda e: int(e['episode_id']))[:a.n]

    derived = {k: v for k, v in data.items() if k != 'episodes'}
    derived['episodes'] = picked

    out = Path(a.out_annotation)
    out.parent.mkdir(parents=True, exist_ok=True)
    # mtime=0 so the gzip container is byte-reproducible across runs.
    with gzip.GzipFile(out, 'wb', mtime=0) as f:
        f.write(json.dumps(derived, sort_keys=True).encode('utf-8'))

    manifest = {
        'selection_rule': ('group val_unseen by scene_id; keep scenes with >= %d '
                           'episodes; sort those scene_ids lexicographically and take '
                           'the first; within it sort by int(episode_id) ascending and '
                           'take the first %d' % (a.n, a.n)),
        'rule_is_outcome_independent': True,
        'frozen_before_any_model_trial': True,
        'source_annotation': str(src),
        'source_sha256': source_sha,
        'source_episode_count': len(episodes),
        'source_scene_count': len(by_scene),
        'eligible_scene_count': len(eligible),
        'eligible_scenes_sorted': eligible,
        'selected_scene_id': scene,
        'selected_scene_episode_count': len(by_scene[scene]),
        'derived_annotation': str(out),
        'derived_sha256': sha256(out),
        'derived_bytes': out.stat().st_size,
        'preserved_metadata_keys': sorted(k for k in data if k != 'episodes'),
        'episodes': [{
            'episode_id': e['episode_id'],
            'trajectory_id': e.get('trajectory_id'),
            'scene_id': e['scene_id'],
            'instruction_text': e['instruction']['instruction_text'],
            'instruction_id': e['instruction'].get('instruction_id'),
            'start_position': e['start_position'],
            'start_rotation': e['start_rotation'],
            'goals': e['goals'],
            'reference_path_points': len(e.get('reference_path', [])),
            'reference_path': e.get('reference_path'),
            'info': e.get('info'),
            'episode_object_sha256': hashlib.sha256(
                json.dumps(e, sort_keys=True).encode('utf-8')).hexdigest(),
        } for e in picked],
    }
    Path(a.out_manifest).write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'scene': scene,
                      'episode_ids': [e['episode_id'] for e in picked],
                      'derived_sha256': manifest['derived_sha256']}, indent=2))


if __name__ == '__main__':
    main()
