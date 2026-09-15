"""Freeze the two public-scene evaluation episodes.

Everything written here is decided from pre-inference geometry and from the
rendered previews only. No model has been queried at this point, and the file
this produces is not regenerated after seeing any navigation outcome.

Episode selection rule, recorded and applied in this order:
  1. Only scenes that can host a non-degenerate episode are eligible. The test is
     in scene_feasibility.json: geodesic diameter > 2 x success radius (6 m) and
     fewer than half of navigable samples already inside the 3 m success radius
     of the far goal. van-gogh-room fails this (diameter 4.35 m, 82.9 % already
     inside the radius) and is excluded, so both routes are in skokloster-castle,
     which the package explicitly allows.
  2. Among the seeded candidates for the eligible scene, take the pair with the
     largest mutual start and goal separation, so the two routes are distinct.
  3. Instructions are written from the rendered previews of those routes, and the
     left/right wording is taken from route_orientation.json, which was measured
     by driving the simulator's own turn actions.
"""
import gzip
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPLIT = 'val_unseen'  # keeps the official config's `split` field unchanged

# preview index -> (episode_id, instruction)
CHOSEN = {
    0: (1, "Turn right and walk past the long dark wooden table. "
           "Go straight on into the next room with the tall bright windows. "
           "Stop near the high-backed chairs standing between the windows."),
    4: (2, "Turn left and walk into the large hall with the painted ceiling. "
           "Cross the checkered stone floor towards the big paintings of men on horseback. "
           "Stop in front of the row of striped chairs under those paintings."),
}
SCENE = 'skokloster-castle'


def tokenize(text):
    return [t for t in re.split(r"([^\w-]+)", text.lower()) if t.strip()]


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def main():
    setup = ROOT / 'public_scenes/setup'
    prev = json.loads((ROOT / 'public_scenes/previews/preview_summary.json').read_text())
    orient = {r['episode_id']: r for r in
              json.loads((ROOT / 'public_scenes/previews/orientation/orientation.json').read_text())}
    feas = json.loads((setup / 'scene_feasibility.json').read_text())
    by_index = {e['preview_index']: e for e in prev['episodes']}

    vocab = ['<pad>', '<unk>', '<s>', '</s>']
    for _, instr in CHOSEN.values():
        for t in tokenize(instr):
            if t not in vocab:
                vocab.append(t)
    stoi = {w: i for i, w in enumerate(vocab)}

    episodes, records = [], []
    for pidx in sorted(CHOSEN):
        ep_id, instr = CHOSEN[pidx]
        src = by_index[pidx]
        assert src['scene'] == SCENE, src['scene']
        ep = {
            'episode_id': ep_id,
            'trajectory_id': ep_id,
            'scene_id': f'{SCENE}/{SCENE}.glb',
            'start_position': src['start_position'],
            'start_rotation': src['start_rotation_xyzw'],
            'goals': [{'position': src['goal_position'], 'radius': 3.0}],
            'info': {'geodesic_distance': src['geodesic_distance']},
            'reference_path': src['reference_path'],
            'instruction': {
                'instruction_text': instr,
                'instruction_tokens': [stoi.get(t, 1) for t in tokenize(instr)],
            },
        }
        episodes.append(ep)
        records.append({
            'episode_id': ep_id,
            'preview_index': pidx,
            'preview_dir': f'public_scenes/previews/{SCENE}__cand{pidx:02d}',
            'instruction_text': instr,
            'start_position': src['start_position'],
            'start_rotation_xyzw': src['start_rotation_xyzw'],
            'goal_position': src['goal_position'],
            'success_radius_m': 3.0,
            'geodesic_distance_m': src['geodesic_distance'],
            'euclidean_distance_m': src['euclidean_distance'],
            'initial_goal_distance_exceeds_success_radius': src['geodesic_distance'] > 3.0,
            'measured_turn_direction_to_goal': orient[pidx]['turn_direction_towards_goal'],
            'measured_turn_steps_of_15deg': orient[pidx]['turn_steps_of_15deg_to_face_goal'],
            'initial_bearing_error_deg': orient[pidx]['initial_bearing_error_deg'],
            'executed': False,
        })

    payload = {'episodes': episodes, 'instruction_vocab': {'word_list': vocab}}
    out = ROOT / 'public_scenes/data/vln_ce/raw_data/public' / SPLIT / f'{SPLIT}.json.gz'
    out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.GzipFile(out, 'wb', mtime=0) as f:
        f.write(json.dumps(payload, sort_keys=True).encode('utf-8'))

    manifest = {
        'status': 'FROZEN_BEFORE_ANY_MODEL_QUERY',
        'scene': SCENE,
        'scene_files': json.loads((setup / 'public_scene_manifest.json').read_text())['files'],
        'split_field_unchanged_from_official_config': SPLIT,
        'selection_rule': [
            'scene eligible only if geodesic diameter > 2 x success radius and '
            '< 50 % of navigable samples already inside the success radius of the far goal',
            'among seeded candidates of the eligible scene, the pair with the largest '
            'mutual start and goal separation',
            'instructions written from the rendered previews; left/right wording measured '
            'by driving the simulator turn actions',
        ],
        'scene_feasibility': feas['scenes'],
        'excluded_scene': {
            'van-gogh-room': {
                'reason': ('navigable area 9.2 m2 and geodesic diameter 4.35 m against a 3.0 m '
                           'success radius: 82.9 % of navigable samples are already inside the '
                           'success radius of the farthest reachable goal, so the official '
                           'success measure cannot discriminate navigation from standing still'),
                'previewed': 'public_scenes/previews/van-gogh-room__cand06',
            }
        },
        'camera_geometry': prev['geometry'],
        'episodes': records,
        'dataset_path': str(out.relative_to(ROOT)),
        'dataset_sha256': sha256_file(out),
        'dataset_bytes': out.stat().st_size,
    }
    (setup / 'frozen_public_episodes.json').write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    print('frozen episodes:', [r['episode_id'] for r in records])
    print('dataset sha256:', manifest['dataset_sha256'])
    print('FREEZE_DONE')


if __name__ == '__main__':
    main()
