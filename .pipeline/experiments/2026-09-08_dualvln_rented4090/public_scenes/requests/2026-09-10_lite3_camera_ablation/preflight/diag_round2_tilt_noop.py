"""Read-only diagnostic for the round-2 C1 preflight stage-6 blocker.

Stage 6 of preflight_cam.py raised `tilt_angle 0 but look_down changed the
frame` for c1_lite3_rig, while c4_raised_mount -- the other tilt_angle 0
condition -- passed the identical check in round 1. This script reproduces the
comparison and reports HOW MUCH the frame changed and what the sensor rotation
did, so the lead can tell a real camera movement from a floating-point
re-normalisation. It changes no geometry, no sign, and no criterion, writes
nothing outside REQ/preflight, and runs no evaluator.

  cd work/InternNav
  CAM_YAML=public_scenes/configs/vln_cam_c1_lite3_rig.yaml \
    ../../official_r2r/official_env_024/bin/python \
    public_scenes/requests/2026-09-10_lite3_camera_ablation/preflight/diag_round2_tilt_noop.py --cond c1_lite3_rig
"""
import argparse
import json
import math
import os
import sys
from pathlib import Path

sys.path.append('.')
sys.path.append('./third_party/diffusion-policy')

REQ = 'public_scenes/requests/2026-09-10_lite3_camera_ablation'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cond', required=True)
    a = ap.parse_args()

    import numpy as np
    import quaternion
    import habitat
    from habitat_baselines.config.default import get_config as get_habitat_config
    import internnav.habitat_extensions.vln.measures  # noqa: F401

    conds = json.loads(Path(f'{REQ}/conditions.json').read_text())
    hab = conds['conditions'][a.cond]['habitat']
    yaml_rel = os.environ['CAM_YAML']
    cfg = get_habitat_config(yaml_rel)
    env = habitat.Env(cfg)
    try:
        env.reset()

        def sensor_rot():
            st = env.sim.get_agent_state()
            q = st.sensor_states['rgb'].rotation
            rel = st.rotation.inverse() * q
            fwd = quaternion.rotate_vectors(rel, np.array([0.0, 0.0, -1.0]))
            pitch = math.degrees(math.asin(max(-1.0, min(1.0, -float(fwd[1])))))
            return {'quat_wxyz': [float(q.w), float(q.x), float(q.y), float(q.z)],
                    'quat_norm': float(math.sqrt(q.w * q.w + q.x * q.x + q.y * q.y + q.z * q.z)),
                    'pitch_down_deg': pitch,
                    'sensor_position': [float(v) for v in st.sensor_states['rgb'].position],
                    'agent_position': [float(v) for v in st.position]}

        def rgb_raw():
            return np.asarray(env.sim.get_sensor_observations()['rgb'])[:, :, :3].copy()

        def diff(x, y):
            d = np.abs(x.astype(np.int16) - y.astype(np.int16))
            npix = int((d.max(axis=2) > 0).sum())
            return {'identical': bool(np.array_equal(x, y)),
                    'differing_pixels': npix,
                    'total_pixels': int(d.shape[0] * d.shape[1]),
                    'differing_fraction': round(npix / (d.shape[0] * d.shape[1]), 8),
                    'max_abs_channel_delta': int(d.max()),
                    'mean_abs_channel_delta': round(float(d.mean()), 8)}

        out = {'condition': a.cond, 'cam_yaml': yaml_rel, 'tilt_angle': hab['tilt_angle'],
               'configured_pitch_down_deg': -math.degrees(hab['orientation'][0])}

        # 1. Pure render determinism: two consecutive reads, no action in between.
        r1 = rgb_raw()
        r2 = rgb_raw()
        out['render_determinism_no_action'] = diff(r1, r2)

        # 2. The preflight's own comparison: raw read, then env.step('look_down').
        before = rgb_raw()
        out['rotation_before'] = sensor_rot()
        obs = env.step({'action': 'look_down'})
        after_step = np.asarray(obs['rgb'])[:, :, :3].copy()
        out['rotation_after_look_down'] = sensor_rot()
        out['preflight_comparison_before_vs_step_obs'] = diff(before, after_step)

        # 3. Isolate the observation pathway from the action: raw read after the step.
        after_raw = rgb_raw()
        out['before_vs_raw_after_look_down'] = diff(before, after_raw)
        out['step_obs_vs_raw_after_look_down'] = diff(after_step, after_raw)

        # 4. Does a second identical look_down keep changing the frame?
        obs2 = env.step({'action': 'look_down'})
        after_step2 = np.asarray(obs2['rgb'])[:, :, :3].copy()
        out['rotation_after_second_look_down'] = sensor_rot()
        out['first_step_obs_vs_second_step_obs'] = diff(after_step, after_step2)

        # 5. look_up, as the preflight does, and compare with the original frame.
        obs3 = env.step({'action': 'look_up'})
        out['rotation_after_look_up'] = sensor_rot()
        out['before_vs_after_look_up'] = diff(before, np.asarray(obs3['rgb'])[:, :, :3].copy())

        outdir = Path(f'{REQ}/preflight')
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / f'diag_round2_tilt_noop_{a.cond}.json').write_text(
            json.dumps(out, indent=2, sort_keys=True) + '\n')
        print(json.dumps(out, indent=2, sort_keys=True))
    finally:
        env.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
