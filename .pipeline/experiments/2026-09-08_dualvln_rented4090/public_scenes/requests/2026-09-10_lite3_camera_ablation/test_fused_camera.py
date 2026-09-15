"""Synthetic self-test of fused_camera.py: an analytic room (floor at y=0, ceiling at y=3,
front wall 4 m ahead, side walls +/-3 m) with procedural textures is rendered exactly for the head
camera, the D435i (colour + z-depth) and the ideal virtual camera; the fused image must match
the ideal render closely inside the covered regions. Run: python3 test_fused_camera.py [--save DIR]"""
import argparse, json, math, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fused_camera import Cam, fuse, coverage_stats

PLANES = [  # (point on plane, normal pointing into the room, texture id)
    (np.array([0, 0.0, 0]), np.array([0, 1.0, 0]), 0),     # floor
    (np.array([0, 3.0, 0]), np.array([0, -1.0, 0]), 1),    # ceiling
    (np.array([0, 0, -4.0]), np.array([0, 0, 1.0]), 2),    # front wall
    (np.array([-3.0, 0, 0]), np.array([1.0, 0, 0]), 3),    # left wall
    (np.array([3.0, 0, 0]), np.array([-1.0, 0, 0]), 3),    # right wall
    (np.array([0, 0, 1.0]), np.array([0, 0, -1.0]), 1),    # back wall 1 m behind
]

def texture(tid, P):
    x, y, z = P[..., 0], P[..., 1], P[..., 2]
    if tid == 0:   # floor: 0.25 m checker + slow colour gradient
        chk = ((np.floor(x / 0.25) + np.floor(z / 0.25)) % 2)
        return np.stack([60 + 150 * chk, 80 + 100 * chk + 20 * np.sin(4 * x), 120 + 60 * (1 - chk)], -1)
    if tid == 1:   # ceiling: stripes
        s = (np.floor(x / 0.5) % 2)
        return np.stack([200 + 40 * s, 200 + 40 * s, 210 - 40 * s], -1)
    if tid == 2:   # front wall: gradient + fine checker
        chk = ((np.floor(x / 0.2) + np.floor(y / 0.2)) % 2)
        return np.stack([40 + 50 * y + 40 * chk, 100 + 30 * x + 40 * chk, 180 - 30 * y], -1)
    chk = ((np.floor(y / 0.3) + np.floor(z / 0.3)) % 2)  # side walls
    return np.stack([150 + 60 * chk, 90 + 40 * chk, 60 + 30 * chk], -1)

def render(cam: Cam, with_depth=False):
    d = cam.rays() @ cam.R.T                           # agent-frame directions
    o = cam.p
    best_t = np.full(d.shape[:2], np.inf); img = np.zeros(d.shape[:2] + (3,))
    for q, n, tid in PLANES:
        denom = d @ n
        t = ((q - o) @ n) / np.where(np.abs(denom) < 1e-9, np.nan, denom)
        hit = np.isfinite(t) & (t > 1e-6) & (t < best_t)
        P = o + d * t[..., None]
        col = texture(tid, P)
        img[hit] = col[hit]; best_t[hit] = t[hit]
    img = np.clip(img, 0, 255).astype(np.uint8)
    if not with_depth:
        return img
    # z-depth along the optical axis = t * (-d_sensor.z) = t * 1, since rays have z = -1 in the sensor frame
    return img, best_t.copy()

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--save', default=None); a = ap.parse_args()
    deg = math.radians
    head = Cam(1280, 720, 105.0, [0, 0.40, -0.27], deg(16.7))
    def virt_at(pitch_down_deg):
        return Cam(640, 480, 79.0, [0, 0.40, -0.27], deg(-pitch_down_deg))
    d435_c7 = Cam(640, 480, 55.0, [0, 0.42, -0.25], deg(-20))
    d435_c8 = Cam(1280, 720, 69.0, [0, 0.42, -0.25], deg(-20))
    results = {}
    # Round 6 adds c9: same sensors as c8, virtual camera pitched 9 deg down. The fusion maths is
    # pose-general, so this case exists to prove it against an exact render rather than by inspection.
    for name, virt, d435 in (('c7_d435_640x480_hfov55', virt_at(0), d435_c7),
                             ('c8_d435_1280x720_hfov69', virt_at(0), d435_c8),
                             ('c9_virt_down9_d435_1280x720', virt_at(9), d435_c8)):
        head_img = render(head)
        d_img, d_z = render(d435, with_depth=True)
        ideal = render(virt).astype(np.float64)
        fused, cov = fuse(head_img, d_img, d_z, virt, head, d435)
        st = coverage_stats(cov)
        err = np.abs(fused.astype(np.float64) - ideal).mean(axis=2)
        def region(mask):
            m = float(err[mask].mean()) if mask.any() else None
            mse = float((err[mask] ** 2).mean()) if mask.any() else None
            return {'mean_abs_err': m, 'psnr_db': (10 * math.log10(255 ** 2 / mse) if mse else None)}
        r = {'coverage': st, 'head_region': region(cov == 1), 'd435_region': region(cov == 2),
             'blend_region': region(cov == 3), 'vfov_head_deg': head.vfov_deg(), 'vfov_d435_deg': d435.vfov_deg(),
             'vfov_virt_deg': virt.vfov_deg(), 'virt_pitch_down_deg': round(math.degrees(math.asin(virt.R[1, 2])), 3)}
        # expected uncovered fraction: rows below the head's bottom edge that the D435i does not reach horizontally
        results[name] = r
        print(name, json.dumps(r, indent=1))
        if a.save:
            os.makedirs(a.save, exist_ok=True)
            from PIL import Image
            Image.fromarray(fused).save(f'{a.save}/{name}_fused.png')
            Image.fromarray(ideal.astype(np.uint8)).save(f'{a.save}/{name}_ideal.png')
            Image.fromarray((cov * 80).astype(np.uint8)).save(f'{a.save}/{name}_coverage.png')
            Image.fromarray(head_img).save(f'{a.save}/{name}_head.png'); Image.fromarray(d_img).save(f'{a.save}/{name}_d435.png')
    ok = all(r['head_region']['mean_abs_err'] < 6 and r['d435_region']['mean_abs_err'] < 12 and r['coverage']['none'] < 0.10
             for r in results.values())
    print('SELF_TEST', 'PASSED' if ok else 'FAILED')
    return 0 if ok else 1

if __name__ == '__main__':
    sys.exit(main())
