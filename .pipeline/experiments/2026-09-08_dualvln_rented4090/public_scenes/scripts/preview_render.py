"""Render candidate routes through the official habitat.Env before writing any
instruction and before the first model query.

This deliberately uses habitat.Env composed from the derived official YAML, not a
hand-built habitat_sim Simulator, so the previewed camera geometry, resolution,
hfov, depth range and agent height are exactly the ones the evaluation will use.
The agent is teleported along the geodesic path only to look at the route; no
policy is involved.
"""
import argparse
import gzip
import json
import math
import sys
from pathlib import Path

# scripts/eval/eval.py does exactly this; the launch directory must be work/InternNav.
sys.path.append('.')
sys.path.append('./third_party/diffusion-policy')

import numpy as np
from PIL import Image

import habitat
from habitat_baselines.config.default import get_config as get_habitat_config

# Same registry side-effect import the official evaluator performs; OracleSuccess
# and OracleNavigationError are InternNav measures, not habitat-lab ones.
import internnav.habitat_extensions.vln.measures  # noqa: F401  # isort: skip

ROOT = Path(__file__).resolve().parents[2]
PREVIEW_SPLIT = 'preview'


def yaw_quat_xyzw(dx, dz):
    """Quaternion [x, y, z, w] that points the agent's -Z forward axis at (dx, dz)."""
    theta = math.atan2(-dx, -dz)
    return [0.0, math.sin(theta / 2.0), 0.0, math.cos(theta / 2.0)]


def build_bootstrap(entries):
    episodes = []
    for k, e in enumerate(entries):
        s = e['start_position']
        p1 = e['path_points'][1] if len(e['path_points']) > 1 else e['goal_position']
        episodes.append({
            'episode_id': k,
            'trajectory_id': k,
            'scene_id': f"{e['scene']}/{e['scene']}.glb",
            'start_position': s,
            'start_rotation': yaw_quat_xyzw(p1[0] - s[0], p1[2] - s[2]),
            'goals': [{'position': e['goal_position'], 'radius': 3.0}],
            'info': {'geodesic_distance': e['geodesic_distance']},
            'reference_path': e['path_points'],
            'instruction': {'instruction_text': 'PREVIEW ONLY - no instruction written yet.',
                            'instruction_tokens': []},
        })
    return {'episodes': episodes,
            'instruction_vocab': {'word_list': ['<pad>', '<unk>', '<s>', '</s>']}}


def save_obs(obs, out_dir, tag, cfg_depth):
    out_dir.mkdir(parents=True, exist_ok=True)
    Image.fromarray(obs['rgb'][:, :, :3]).save(out_dir / f'{tag}_rgb.png')
    d = np.asarray(obs['depth']).squeeze()
    metres = d * (cfg_depth['max'] - cfg_depth['min']) + cfg_depth['min']
    Image.fromarray((metres * 1000.0).clip(0, 65535).astype(np.uint16)).save(
        out_dir / f'{tag}_depth_mm.png')
    return float(np.nanmean(metres)), float(np.nanmin(metres)), float(np.nanmax(metres))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', default='public_scenes/configs/vln_public_scenes.yaml')
    ap.add_argument('--scene-take', nargs='+', required=True,
                    help='scene:count pairs, e.g. skokloster-castle:6 van-gogh-room:1')
    ap.add_argument('--out', default='public_scenes/previews')
    a = ap.parse_args()

    entries = []
    for spec in a.scene_take:
        scene, n = spec.rsplit(':', 1)
        data = json.loads((ROOT / 'public_scenes/setup' / f'candidates_{scene}.json').read_text())
        for c in data['candidates'][: int(n)]:
            c = dict(c)
            c['scene'] = scene
            entries.append(c)

    boot = build_bootstrap(entries)
    boot_path = ROOT / 'public_scenes/data/vln_ce/raw_data/public' / PREVIEW_SPLIT / f'{PREVIEW_SPLIT}.json.gz'
    boot_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.GzipFile(boot_path, 'wb', mtime=0) as f:
        f.write(json.dumps(boot, sort_keys=True).encode('utf-8'))
    print('bootstrap episodes:', len(boot['episodes']), '->', boot_path.relative_to(ROOT))

    config = get_habitat_config(a.config)
    with habitat.config.read_write(config):
        config.habitat.dataset.split = PREVIEW_SPLIT
    ds = config.habitat.simulator.agents.main_agent.sim_sensors.depth_sensor
    cfg_depth = {'min': float(ds.min_depth), 'max': float(ds.max_depth)}
    rgb = config.habitat.simulator.agents.main_agent.sim_sensors.rgb_sensor
    geometry = {
        'rgb': {'width': int(rgb.width), 'height': int(rgb.height), 'hfov': int(rgb.hfov),
                'position': [float(v) for v in rgb.position]},
        'depth': {'width': int(ds.width), 'height': int(ds.height), 'hfov': int(ds.hfov),
                  'position': [float(v) for v in ds.position],
                  'min_depth': cfg_depth['min'], 'max_depth': cfg_depth['max'],
                  'normalize_depth': bool(ds.normalize_depth)},
        'forward_step_size': float(config.habitat.simulator.forward_step_size),
        'turn_angle': int(config.habitat.simulator.turn_angle),
        'tilt_angle': int(config.habitat.simulator.tilt_angle),
        'action_space_config': str(config.habitat.simulator.action_space_config),
        'success_distance': float(config.habitat.task.measurements.success.success_distance),
        'agent_height': float(config.habitat.simulator.agents.main_agent.height),
        'agent_radius': float(config.habitat.simulator.agents.main_agent.radius),
    }
    print('camera geometry:', json.dumps(geometry))

    out_root = ROOT / a.out
    summary = {'geometry': geometry, 'episodes': []}

    env = habitat.Env(config)
    try:
        for _ in range(len(boot['episodes'])):
            obs = env.reset()
            ep = env.current_episode
            k = int(ep.episode_id)
            src = entries[k]
            tagdir = out_root / f"{src['scene']}__cand{k:02d}"
            rec = {
                'preview_index': k,
                'scene': src['scene'],
                'start_position': [float(v) for v in ep.start_position],
                'start_rotation_xyzw': [float(v) for v in ep.start_rotation],
                'goal_position': [float(v) for v in ep.goals[0].position],
                'geodesic_distance': src['geodesic_distance'],
                'euclidean_distance': src['euclidean_distance'],
                'reference_path': src['path_points'],
                'frames': [],
            }
            stats = save_obs(obs, tagdir, 'f00_start', cfg_depth)
            rec['frames'].append({'tag': 'f00_start', 'depth_mean_min_max_m': stats,
                                  'position': rec['start_position']})

            # look along the route by teleporting to each waypoint
            sim = env.sim
            pts = src['path_points']
            for wi in range(1, len(pts)):
                cur, nxt = pts[wi], pts[min(wi + 1, len(pts) - 1)]
                look = nxt if wi < len(pts) - 1 else pts[wi - 1]
                if wi == len(pts) - 1:
                    dx, dz = cur[0] - pts[wi - 1][0], cur[2] - pts[wi - 1][2]
                else:
                    dx, dz = look[0] - cur[0], look[2] - cur[2]
                q = yaw_quat_xyzw(dx, dz)
                st = sim.get_agent(0).get_state()
                st.position = np.array(cur, dtype=np.float32)
                st.rotation = np.quaternion(q[3], q[0], q[1], q[2])
                sim.get_agent(0).set_state(st)
                o = sim.get_sensor_observations()
                o = {'rgb': o['rgb'], 'depth': np.asarray(o['depth'])[..., None] / cfg_depth['max']}
                tag = f'f{wi:02d}_wp'
                stats = save_obs(o, tagdir, tag, cfg_depth)
                rec['frames'].append({'tag': tag, 'depth_mean_min_max_m': stats,
                                      'position': [float(v) for v in cur]})
            summary['episodes'].append(rec)
            print(f"  previewed {src['scene']} cand{k:02d} geo={src['geodesic_distance']:.2f} "
                  f"frames={len(rec['frames'])}")
    finally:
        env.close()

    (out_root / 'preview_summary.json').write_text(
        json.dumps(summary, indent=2, sort_keys=True) + '\n')
    print('PREVIEW_DONE')


if __name__ == '__main__':
    main()
