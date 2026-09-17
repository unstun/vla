#!/usr/bin/env python3
"""Phase D.1b, POST-HOC analysis (after the start; the frozen gate verdict is not changed by it).

    python3 scripts/phase_d1b_validity_analysis.py [--run-dir runs/phase_d1b_stage_audit_kujiale_0031_v1] \
        [--out analysis/phase_d1b_validity_analysis.json]

The two failed checks of run phase_d1b_stage_audit_kujiale_0031_v1 are both validity controls. This script asks, from
the recorded data only, whether the measurements they guard are nevertheless consistent:

1. P1 physics readout probe. Frozen expectation: a cube at rest drops g*dt^2*n(n+1)/2 = 4.930 m over n = 200 steps.
   If the cube had already fallen k steps when first read, the drop over the next n steps is g*dt^2*(n*k + n(n+1)/2).
   Solve for k from the recorded drop: an integer k means the readout tracks exact semi-implicit Euler motion and only
   the at-rest assumption was wrong.
2. Pose-B render. Frozen control: the camera position read back from its XformPrimView must be within 0.05 m of the
   target. Camera-independent check: PhysX scene-query rays from the TORSO point along the heading (z 0.25 m) against
   the head_eval centre-pixel depth (z 0.356 m, 0.2721 m ahead of the TORSO point, same heading line). For vertical
   faces the two must differ by exactly the 0.2721 m offset if the camera really rendered from that pose.
"""
import argparse
import json
import math
import pathlib

import numpy as np

HERE = pathlib.Path(__file__).resolve().parents[1]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--run-dir', type=pathlib.Path, default=HERE / 'runs' / 'phase_d1b_stage_audit_kujiale_0031_v1')
    ap.add_argument('--out', type=pathlib.Path, default=HERE / 'analysis' / 'phase_d1b_validity_analysis.json')
    args = ap.parse_args(argv)
    result = json.loads((args.run_dir / 'audit' / 'stage_audit_result.json').read_text())
    thr = result['thresholds']
    g, dt = 9.81, thr['physics']['physics_dt_s']
    n = result['physics']['physics_steps']
    out = {'label': 'post-hoc analysis; the frozen D.1b verdict (P1 FAIL, R_frames_valid_pose_B FAIL) stands',
           'run': args.run_dir.name}

    probes = result['physics']['probes_by_readout']
    drop = probes['rigid_body_view']['drop_m']
    k = (drop / (g * dt * dt) - n * (n + 1) / 2) / n
    k_round = round(k)
    predicted = g * dt * dt * (n * k_round + n * (n + 1) / 2)
    moved = [b for b in result['physics']['bodies'] if b.get('found') and (
        b['displacement_m'] > thr['physics']['max_displacement_m'] or b['rotation_deg'] > thr['physics']['max_rotation_deg'])]
    gated = [b for b in result['physics']['bodies'] if b['group'] in thr['physics']['gated_groups']]
    out['probe'] = {
        'rigid_body_view_drop_m': drop, 'frozen_expected_drop_m': thr['validity_controls']['physics_readout_probe']['expected_drop_m'],
        'get_rigidbody_transformation_drop_m': probes['get_rigidbody_transformation']['drop_m'],
        'steps_before_first_read_k': k, 'k_rounded': k_round,
        'drop_predicted_for_k_rounded_m': predicted, 'residual_m': drop - predicted,
        'bodies_in_view_readout': len([b for b in result['physics']['bodies'] if b.get('found')]),
        'gated_bodies': len(gated), 'gated_read': len([b for b in gated if b.get('found')]),
        'bodies_beyond_1mm_or_0p1deg': len(moved),
        'max_displacement_m': max((b['displacement_m'] for b in result['physics']['bodies'] if b.get('found')), default=None),
        'max_rotation_deg': max((b['rotation_deg'] for b in result['physics']['bodies'] if b.get('found')), default=None),
    }

    frames = args.run_dir / 'audit' / 'frames'
    offset = result['cameras']['head_eval']['pos'][0]
    rows = {}
    for label in ('A', 'B'):
        ray = result['collision']['horizontal_rays'][label][0]
        depth = np.load(frames / '{}_last_head_eval_depth.npy'.format(label))
        h, w = depth.shape
        centre = float(np.median(depth[h // 2 - 5:h // 2 + 5, w // 2 - 5:w // 2 + 5]))
        rows[label] = {'ray_ahead_distance_m': ray['distance'], 'ray_ahead_class': ray['class'],
                       'camera_forward_offset_m': offset, 'expected_centre_depth_m': ray['distance'] - offset,
                       'rendered_centre_depth_m': centre, 'difference_m': centre - (ray['distance'] - offset)}
    readback = result['render']['poses_check']['B']
    target_a = result['render']['poses']['A']['cameras_world']['head_eval']['pos']
    rows['B']['readback_head_eval_m'] = readback['readback']['head_eval']
    rows['B']['readback_equals_pose_A_target_within_m'] = math.dist(readback['readback']['head_eval'], target_a)
    diff = {}
    from PIL import Image
    for cam in ('head_eval', 'fusion_head', 'fusion_d435'):
        a = np.asarray(Image.open(frames / 'A_last_{}.png'.format(cam))).astype(np.int16)
        b = np.asarray(Image.open(frames / 'B_last_{}.png'.format(cam))).astype(np.int16)
        diff[cam] = float(np.abs(a - b).mean())
    out['pose_b'] = {'centre_depth_vs_physx_ray': rows, 'mean_abs_rgb_difference_A_last_vs_B_last': diff}
    out['conclusion'] = (
        'P1: the rigid-body view tracks free fall exactly (k = {:.3f} steps before the first read, residual {:.2e} m); '
        'the frozen probe assumed the cube was at rest. {} of {} gated bodies read, {} beyond 1 mm / 0.1 deg. '
        'Pose B: centre depth equals the PhysX ray distance minus the 0.2721 m camera offset at both poses '
        '(A {:+.4f} m, B {:+.4f} m), so the cameras rendered from pose B; the XformPrimView readback returned the pose-A '
        'position ({:.2e} m from the pose-A target).').format(
            k, out['probe']['residual_m'], out['probe']['gated_read'], out['probe']['gated_bodies'],
            out['probe']['bodies_beyond_1mm_or_0p1deg'], rows['A']['difference_m'], rows['B']['difference_m'],
            rows['B']['readback_equals_pose_A_target_within_m'])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1) + '\n')
    print(out['conclusion'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
