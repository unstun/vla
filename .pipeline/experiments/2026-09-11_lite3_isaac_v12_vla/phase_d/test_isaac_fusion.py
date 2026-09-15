"""Phase D.0f local test: the Isaac-side fusion glue against an exact render made in Isaac's own conventions.

The three cameras are ray-traced here WITHOUT fused_camera: each is mounted on TORSO with the quaternion the server gives
Isaac (`phase_b_camera_probe.camera_rotation`, ROS optical frame: x right, y down, z forward) and Isaac's pinhole
(focal from `focal_for_hfov`, 20.955 mm aperture, square pixels, principal point at the centre). The scene is a room
with a different texture on every wall and an off-centre box, so a flipped axis, a wrong pitch sign or a wrong lateral
sign changes the picture. The fused image must match the ideal render inside the covered regions, the intrinsics check
must accept Isaac's K and reject a wrong one, the config loader must refuse a camera the fusion cannot serve, and
deliberately wrong fusions must fail (so the test can fail): a flipped head pitch and a 0.3 m D435i shift against the c8
bounds, and a flipped forward or lateral sign in the TORSO-to-fusion conversion against the tighter Habitat self-test
bounds (the c8 image bounds alone cannot see a few centimetres of D435i translation). The lateral case renders a copy of
the rig with the D435i 0.08 m to the left, since the configured rig has y = 0 everywhere.

    python3 phase_d/test_isaac_fusion.py --tools-dir SCRIPTS_DIR --fused-camera-dir DIR [--save DIR]
"""

import argparse
import copy
import json
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
TORSO_HEIGHT_M = 0.30   # floor at z = -0.30 in the TORSO frame


def quat_to_matrix(q):
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def isaac_k(probe, spec):
    """K as Isaac derives it from the USD pinhole: fx = focal * w / aperture, square pixels, centred."""
    focal = probe.focal_for_hfov(float(spec['hfov']))
    fx = focal * spec['width'] / 20.955
    return np.array([[fx, 0.0, spec['width'] / 2.0], [0.0, fx, spec['height'] / 2.0], [0.0, 0.0, 1.0]])


def texture(name, P):
    x, y, z = P[..., 0], P[..., 1], P[..., 2]
    if name == 'floor':
        chk = (np.floor(x / 0.25) + np.floor(y / 0.25)) % 2
        return np.stack([60 + 150 * chk, 80 + 100 * chk + 20 * np.sin(4 * x), 120 + 60 * (1 - chk)], -1)
    if name == 'ceiling':
        s = np.floor(y / 0.5) % 2
        return np.stack([200 + 40 * s, 200 + 40 * s, 210 - 40 * s], -1)
    if name == 'front':
        chk = (np.floor(y / 0.2) + np.floor(z / 0.2)) % 2
        return np.stack([40 + 50 * z + 40 * chk, 100 + 30 * y + 40 * chk, 180 - 30 * z], -1)
    if name == 'left':
        chk = (np.floor(x / 0.3) + np.floor(z / 0.3)) % 2
        return np.stack([150 + 60 * chk, 90 + 40 * chk, 60 + 30 * chk], -1)
    if name == 'right':
        s = np.floor(z / 0.15) % 2
        return np.stack([40 + 30 * s, 160 + 50 * s, 90 + 20 * np.sin(3 * x)], -1)
    if name == 'back':
        return np.stack([np.full_like(x, 90.0), np.full_like(x, 90.0), np.full_like(x, 90.0)], -1)
    # box: its own stripes
    s = (np.floor(z / 0.1) + np.floor((x + y) / 0.1)) % 2
    return np.stack([220 - 120 * s, 40 + 80 * s, 40 + 40 * s], -1)


PLANES = [  # (point, normal, texture) in TORSO coordinates
    (np.array([0.0, 0.0, -TORSO_HEIGHT_M]), np.array([0.0, 0.0, 1.0]), 'floor'),
    (np.array([0.0, 0.0, 2.4]), np.array([0.0, 0.0, -1.0]), 'ceiling'),
    (np.array([4.0, 0.0, 0.0]), np.array([-1.0, 0.0, 0.0]), 'front'),
    (np.array([0.0, 3.0, 0.0]), np.array([0.0, -1.0, 0.0]), 'left'),
    (np.array([0.0, -3.0, 0.0]), np.array([0.0, 1.0, 0.0]), 'right'),
    (np.array([-1.0, 0.0, 0.0]), np.array([1.0, 0.0, 0.0]), 'back'),
]
BOX = (np.array([1.4, 0.15, -TORSO_HEIGHT_M]), np.array([1.9, 0.75, 0.35]))   # min, max corners


def render(probe, spec, with_depth=False):
    w, h = int(spec['width']), int(spec['height'])
    K = isaac_k(probe, spec)
    quat, _ = probe.camera_rotation(float(spec['pitch_up']))
    R = quat_to_matrix(quat)                          # optical -> TORSO
    cols = (np.arange(w) + 0.5 - K[0, 2]) / K[0, 0]
    rows = (np.arange(h) + 0.5 - K[1, 2]) / K[1, 1]
    uu, vv = np.meshgrid(cols, rows)
    d_opt = np.stack([uu, vv, np.ones_like(uu)], -1)  # z = 1, so the ray parameter is the z-depth
    d = d_opt @ R.T
    o = np.asarray(spec['pos'], dtype=np.float64)
    best = np.full((h, w), np.inf)
    img = np.zeros((h, w, 3))
    for q, n, name in PLANES:
        denom = d @ n
        with np.errstate(divide='ignore', invalid='ignore'):
            t = ((q - o) @ n) / denom
        hit = np.isfinite(t) & (t > 1e-6) & (t < best)
        P = o + d * t[..., None]
        img[hit] = texture(name, P)[hit]
        best[hit] = t[hit]
    lo, hi = BOX
    with np.errstate(divide='ignore', invalid='ignore'):
        t1 = (lo - o) / d
        t2 = (hi - o) / d
    t_near = np.nanmax(np.minimum(t1, t2), axis=-1)
    t_far = np.nanmin(np.maximum(t1, t2), axis=-1)
    hit = (t_near <= t_far) & (t_near > 1e-6) & (t_near < best)
    P = o + d * t_near[..., None]
    img[hit] = texture('box', P)[hit]
    best[hit] = t_near[hit]
    img = np.clip(img + 0.5, 0, 255).astype(np.uint8)
    return (img, best) if with_depth else img


def self_test_failures(row):
    """The Habitat self-test bounds (test_fused_camera.py): head region < 6, D435i region < 12."""
    failures = []
    for region, bound in (('head', 6.0), ('d435', 12.0)):
        value = row['error_vs_ideal'][region]['mean_abs_err']
        if value is None or not value < bound:
            failures.append('{} region error {} >= {}'.format(region, value, bound))
    return failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tools-dir', type=Path, required=True, help='holds phase_b_camera_probe.py')
    parser.add_argument('--fused-camera-dir', type=Path, required=True, help='holds the pinned fused_camera.py')
    parser.add_argument('--config', type=Path, default=HERE / 'fusion_isaac_c8.json')
    parser.add_argument('--episode', type=Path, default=HERE.parent / 'phase_c' / 'episodes' / 'c_green_box_right_v1.json')
    parser.add_argument('--save', type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.tools_dir))
    sys.path.insert(0, str(HERE))
    import phase_b_camera_probe as probe
    import isaac_fusion

    episode_camera = json.loads(args.episode.read_text())['camera']
    config = isaac_fusion.load_config(args.config, episode_camera)
    virtual_spec = isaac_fusion.virtual_spec(config, episode_camera)
    fusion = isaac_fusion.IsaacFusion(config, virtual_spec, args.fused_camera_dir)
    results = {'virtual_spec': virtual_spec}
    results['geometry'] = fusion.geometry_record()
    checks = []

    # 0. The chosen geometry: D435i 0.02 m behind and 0.02 m above the built-in camera (c8), evaluation view at the
    # built-in camera's optical centre.
    offset = [round(h - d, 6) for h, d in zip(config['head']['pos'], config['d435']['pos'])]
    checks.append(('built-in camera 0.02 m ahead of and 0.02 m below the D435i (c8 offset)',
                   offset == [0.02, 0.0, -0.02], offset))
    checks.append(('evaluation view at the built-in camera optical centre',
                   virtual_spec['pos'] == config['head']['pos'], virtual_spec['pos']))

    # 1. Intrinsics: Isaac's K passes for all three cameras; a 2 px focal error is rejected.
    problems = []
    for name, spec, cam in (('head_eval', virtual_spec, fusion.virt), ('fusion_head', config['head'], fusion.head),
                            ('fusion_d435', config['d435'], fusion.d435)):
        problems += fusion.check_intrinsics(name, cam, isaac_k(probe, spec))
    bad_k = isaac_k(probe, config['d435'])
    bad_k[0, 0] += 2.0
    checks.append(('intrinsics accept Isaac K', not problems, problems))
    rejected = fusion.check_intrinsics('bad', fusion.d435, bad_k)
    checks.append(('intrinsics reject a 2 px focal error', bool(rejected), rejected))

    # 2. Config refusals.
    for label, mutate in (('episode camera pitch', lambda v, c: v.__setitem__('pitch_up', -9.0)),
                          ('episode camera HFOV', lambda v, c: v.__setitem__('hfov', 90.0)),
                          ('virtual camera off the head optical centre',
                           lambda v, c: c['virtual'].__setitem__('pos', [0.25, 0.0, 0.054])),
                          ('head off the optical centre', lambda v, c: c['head'].__setitem__('pos', [0.26, 0.0, 0.054]))):
        v, c = copy.deepcopy(episode_camera), json.loads(args.config.read_text())
        mutate(v, c)
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir) / 'fusion_config.json'
            tmp.write_text(json.dumps(c))
            try:
                isaac_fusion.load_config(tmp, v)
                refused = False
            except ValueError:
                refused = True
        checks.append(('config refuses ' + label, refused, None))

    # 3. Exact renders in Isaac's convention, fused by the pinned module.
    ideal = render(probe, virtual_spec)
    head = render(probe, config['head'])
    d_rgb, d_z = render(probe, config['d435'], with_depth=True)
    fused, cov, row = fusion.fuse(head, d_rgb, d_z, ideal)
    results['exact_render'] = row
    checks.append(('fused matches ideal within the c8 bounds', not row['c8_bound_failures'], row['c8_bound_failures']))
    checks.append(('fused matches ideal within the Habitat self-test bounds (head < 6, d435 < 12)',
                   not self_test_failures(row), self_test_failures(row)))
    checks.append(('fused differs from a black image', fused.mean() > 20, float(fused.mean())))

    # 4. Negative controls: the same renders with a mis-specified fusion must fail the bounds.
    for label, key, change in (('head pitch sign flipped', 'head', ('pitch_up', -16.7)),
                               ('d435 moved 0.3 m sideways', 'd435',
                                ('pos', [config['d435']['pos'][0], 0.3, config['d435']['pos'][2]]))):
        wrong = copy.deepcopy(config)
        wrong['head' if key == 'head' else 'd435'][change[0]] = change[1]
        broken = isaac_fusion.IsaacFusion.__new__(isaac_fusion.IsaacFusion)
        broken.__dict__.update(fusion.__dict__)
        broken.config = wrong
        if key == 'head':
            broken.head = isaac_fusion.cam_from_spec(fusion.fc, wrong['head'])
            broken.lut = fusion.fc.head_lut(fusion.virt, broken.head)
        else:
            broken.d435 = isaac_fusion.cam_from_spec(fusion.fc, wrong['d435'])
        _, _, bad_row = broken.fuse(head, d_rgb, d_z, ideal)
        results['negative_' + key] = bad_row
        checks.append(('negative control fails the bounds: ' + label, bool(bad_row['c8_bound_failures']),
                       bad_row['c8_bound_failures']))

    # 5. Sign of each axis in the TORSO-to-fusion conversion. Forward: the configured rig (the D435i sits 0.018 m behind
    # the head camera). Lateral: a rig copy with the D435i 0.08 m to the left, rendered and fused correctly first.
    lateral = copy.deepcopy(config)
    lateral['d435']['pos'] = [config['d435']['pos'][0], 0.08, config['d435']['pos'][2]]
    lat_rgb, lat_z = render(probe, lateral['d435'], with_depth=True)
    lat_fusion = isaac_fusion.IsaacFusion.__new__(isaac_fusion.IsaacFusion)
    lat_fusion.__dict__.update(fusion.__dict__)
    lat_fusion.config = lateral
    lat_fusion.d435 = isaac_fusion.cam_from_spec(fusion.fc, lateral['d435'])
    _, _, lat_row = lat_fusion.fuse(head, lat_rgb, lat_z, ideal)
    results['lateral_rig'] = lat_row
    checks.append(('lateral rig (d435 0.08 m left) matches ideal within the self-test bounds',
                   not self_test_failures(lat_row), self_test_failures(lat_row)))
    original = isaac_fusion.torso_to_fusion_frame
    for label, flipped, spec_used, d_img, d_depth in (
            ('forward sign flipped in the conversion', lambda p: (-float(p[1]), float(p[2]), float(p[0])), config,
             d_rgb, d_z),
            ('lateral sign flipped in the conversion', lambda p: (float(p[1]), float(p[2]), -float(p[0])), lateral,
             lat_rgb, lat_z)):
        isaac_fusion.torso_to_fusion_frame = flipped
        try:
            wrong = isaac_fusion.IsaacFusion.__new__(isaac_fusion.IsaacFusion)
            wrong.__dict__.update(fusion.__dict__)
            wrong.config = spec_used
            wrong.virt = isaac_fusion.cam_from_spec(fusion.fc, virtual_spec)
            wrong.head = isaac_fusion.cam_from_spec(fusion.fc, spec_used['head'])
            wrong.d435 = isaac_fusion.cam_from_spec(fusion.fc, spec_used['d435'])
            wrong.lut = fusion.fc.head_lut(wrong.virt, wrong.head)
            _, _, bad_row = wrong.fuse(head, d_img, d_depth, ideal)
        finally:
            isaac_fusion.torso_to_fusion_frame = original
        results['negative_' + label.split()[0]] = bad_row
        checks.append(('negative control fails the self-test bounds: ' + label, bool(self_test_failures(bad_row)),
                       bad_row['error_vs_ideal']))

    if args.save:
        from PIL import Image
        args.save.mkdir(parents=True, exist_ok=True)
        Image.fromarray(ideal).save(args.save / 'ideal.png')
        Image.fromarray(fused).save(args.save / 'fused.png')
        Image.fromarray((cov * 80).astype(np.uint8)).save(args.save / 'coverage.png')
        Image.fromarray(head).save(args.save / 'head.png')
        Image.fromarray(d_rgb).save(args.save / 'd435.png')
        Image.fromarray(isaac_fusion.depth_to_mm_png(d_z)).save(args.save / 'd435_depth_mm.png')
        (args.save / 'results.json').write_text(json.dumps({'results': results, 'checks': [
            {'check': c, 'ok': ok, 'detail': detail} for c, ok, detail in checks]}, indent=2, default=str) + '\n')

    print(json.dumps(results['exact_render'], indent=1))
    for check, ok, detail in checks:
        print('{} {}{}'.format('PASS' if ok else 'FAIL', check, '' if ok else ': {}'.format(detail)))
    passed = all(ok for _, ok, _ in checks)
    print('ISAAC_FUSION_TEST', 'PASSED' if passed else 'FAILED')
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
