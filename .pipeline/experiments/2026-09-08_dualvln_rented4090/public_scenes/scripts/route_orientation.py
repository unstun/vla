"""Determine, empirically and before any model query, which way the agent must
turn at the start of each chosen route, so the written instruction's left/right
wording matches what the simulator actually does.

Rather than reasoning about Habitat's quaternion conventions, this drives the
real `turn_left`/`turn_right` actions in the real environment and measures which
one reduces the bearing error to the goal.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.append('.')
sys.path.append('./third_party/diffusion-policy')

import habitat
from habitat_baselines.config.default import get_config as get_habitat_config

import internnav.habitat_extensions.vln.measures  # noqa: F401  # isort: skip

ROOT = Path(__file__).resolve().parents[2]


def bearing_error(sim, goal):
    st = sim.get_agent(0).get_state()
    q = st.rotation
    fwd = np.array([0.0, 0.0, -1.0])
    r = np.quaternion(q.w, q.x, q.y, q.z) if not isinstance(q, np.quaternion) else q
    import quaternion as qt
    fwd_w = qt.rotate_vectors(r, fwd)
    to_goal = np.array(goal) - np.array(st.position)
    a = math.atan2(fwd_w[0], fwd_w[2])
    b = math.atan2(to_goal[0], to_goal[2])
    d = math.degrees(b - a)
    return (d + 180.0) % 360.0 - 180.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', default='public_scenes/configs/vln_public_scenes.yaml')
    ap.add_argument('--split', default='preview')
    ap.add_argument('--episodes', nargs='+', type=int, required=True)
    ap.add_argument('--out', default='public_scenes/previews/orientation')
    a = ap.parse_args()

    config = get_habitat_config(a.config)
    with habitat.config.read_write(config):
        config.habitat.dataset.split = a.split

    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    report = []
    env = habitat.Env(config)
    try:
        for _ in range(64):
            obs = env.reset()
            ep = env.current_episode
            k = int(ep.episode_id)
            if k not in a.episodes:
                continue
            goal = [float(v) for v in ep.goals[0].position]
            sim = env.sim
            start_state = sim.get_agent(0).get_state()
            e0 = bearing_error(sim, goal)

            probe = {}
            for name, action in (('turn_left', 2), ('turn_right', 3)):
                st = sim.get_agent(0).get_state()
                st.position = start_state.position
                st.rotation = start_state.rotation
                sim.get_agent(0).set_state(st)
                sim.step(action)
                probe[name] = bearing_error(sim, goal)

            better = min(probe, key=lambda n: abs(probe[n]))
            # rotate all the way round to face the goal, then render that view
            st = sim.get_agent(0).get_state()
            st.position = start_state.position
            st.rotation = start_state.rotation
            sim.get_agent(0).set_state(st)
            n = 0
            while abs(bearing_error(sim, goal)) > 8.0 and n < 24:
                sim.step(2 if better == 'turn_left' else 3)
                n += 1
            o = sim.get_sensor_observations()
            Image.fromarray(np.asarray(o['rgb'])[:, :, :3]).save(out / f'ep{k:02d}_facing_goal_rgb.png')

            rec = {
                'episode_id': k,
                'initial_bearing_error_deg': round(e0, 2),
                'after_one_turn_left_deg': round(probe['turn_left'], 2),
                'after_one_turn_right_deg': round(probe['turn_right'], 2),
                'turn_direction_towards_goal': better.replace('turn_', ''),
                'turn_steps_of_15deg_to_face_goal': n,
                'residual_bearing_error_deg': round(bearing_error(sim, goal), 2),
            }
            report.append(rec)
            print(json.dumps(rec))
            if len(report) == len(a.episodes):
                break
    finally:
        env.close()

    (out / 'orientation.json').write_text(json.dumps(report, indent=2) + '\n')
    print('ORIENTATION_DONE')


if __name__ == '__main__':
    main()
