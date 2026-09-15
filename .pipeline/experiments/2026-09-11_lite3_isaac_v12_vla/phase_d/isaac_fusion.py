"""Phase D.0f: the Habitat c8 two-mount camera fusion, driven from the Isaac lockstep server.

The fusion itself is the camera ablation's `fused_camera.py`, loaded by path and refused unless its SHA-256 matches the
config. This module only adapts poses and records what happened:

- poses: the server mounts every camera on TORSO (x forward, y left, z up) with a `pitch_up` angle and no yaw or roll
  (`phase_b_camera_probe.camera_rotation`). `fused_camera` works in Habitat's agent frame (x right, y up, z backward)
  with a pitch about x, positive up. A TORSO position (x, y, z) is therefore (-y, z, -x) there, and the pitch carries
  over unchanged. Only positions relative to the virtual camera matter to the fusion.
- intrinsics: each rendered camera's K must be the pinhole the fusion assumes (fx = fy = (w/2)/tan(hfov/2), principal
  point at the image centre) within a tolerance. Isaac Lab itself sets fy = fx and the principal point at the centre, so
  in practice this checks the focal length and aperture; the render-level check is the fused-vs-ideal error.
- mounts: each camera's pose relative to TORSO as Isaac authored it on the camera prim (USD `xformOp:translate` /
  `xformOp:orient`, OpenGL camera convention) must equal the configured position and `camera_rotation(pitch_up)`,
  because the image error bounds are too loose to catch a few centimetres of D435i translation. The camera's reported
  world pose is only recorded: `data.pos_w` is the initialisation pose, and a Fabric refresh read cameras that share
  a parent and a translation 15.6 mm apart (runs phase_d_fused_scripted_preflight_v1/v2).
- virtual camera: the config's `virtual` block (the built-in camera's optical centre) replaces the episode camera's
  position; its size, HFOV and pitch must equal the episode camera's.
- per frame: fusion wall time, coverage fractions, mean absolute error against the ideal virtual render in each
  coverage region, and the share of D435i pixels nearer than `self_occlusion_max_depth_m` (the robot's own body, which
  Habitat never rendered).

numpy and PIL; cv2 through `fused_camera` when present.
"""

import hashlib
import importlib.util
import json
import math
import time
from pathlib import Path

import numpy as np

REGION_CODES = {'head': 1, 'd435': 2, 'blend': 3}


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def verify_module(tools_dir, config):
    """Hash check only (no import), so it can run before the simulator starts."""
    path = Path(tools_dir) / config['fused_camera_module']
    digest = sha256_file(path)
    if digest != config['fused_camera_sha256']:
        raise RuntimeError('{} sha256 {} is not the pinned {}'.format(path, digest, config['fused_camera_sha256']))
    return path, digest


def load_fused_camera(tools_dir, config):
    path, digest = verify_module(tools_dir, config)
    spec = importlib.util.spec_from_file_location('fused_camera', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, digest


def torso_to_fusion_frame(pos):
    x, y, z = (float(v) for v in pos)
    return (-y, z, -x)


def cam_from_spec(fused_camera, spec):
    return fused_camera.Cam(int(spec['width']), int(spec['height']), float(spec['hfov']),
                            torso_to_fusion_frame(spec['pos']), math.radians(float(spec['pitch_up'])))


def load_config(path, episode_camera):
    """Read the fusion config and refuse a virtual camera or head mount the fusion cannot serve."""
    config = json.loads(Path(path).read_text())
    virtual = config['virtual']
    for key in ('width', 'height', 'hfov', 'pitch_up'):
        if float(episode_camera[key]) != float(virtual[key]):
            raise ValueError('episode camera {}={} is not the fusion virtual camera {}'.format(
                key, episode_camera[key], virtual[key]))
    # fuse() maps the head camera by rotation only (a fixed lookup table), so it must share the optical centre.
    if [float(v) for v in config['head']['pos']] != [float(v) for v in virtual['pos']]:
        raise ValueError('the head camera must share the virtual camera optical centre')
    return config


def virtual_spec(config, episode_camera):
    """The head_eval camera for a fused run: the episode camera moved to the config's virtual position."""
    return dict(episode_camera, pos=[float(v) for v in config['virtual']['pos']])


def quat_wxyz_to_matrix(q):
    w, x, y, z = (float(v) for v in q)
    n = math.sqrt(w * w + x * x + y * y + z * z)
    w, x, y, z = w / n, x / n, y / n, z / n
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def depth_to_mm_png(depth_m):
    z = np.asarray(depth_m, dtype=np.float64)
    z = np.where(np.isfinite(z) & (z > 0), z, 0.0)
    return np.clip(np.rint(z * 1000.0), 0, 65535).astype(np.uint16)


class IsaacFusion:
    def __init__(self, config, virtual_spec, tools_dir):
        self.config = config
        self.fc, self.module_sha256 = load_fused_camera(tools_dir, config)
        self.virt = cam_from_spec(self.fc, virtual_spec)
        self.head = cam_from_spec(self.fc, config['head'])
        self.d435 = cam_from_spec(self.fc, config['d435'])
        self.lut = self.fc.head_lut(self.virt, self.head)
        self.bounds = config['preflight_bounds_from_habitat_c8']
        self.intrinsics = {}
        self.mounts = {}
        self.live_readback = {}

    def geometry_record(self):
        def cam(c):
            return {'width': c.w, 'height': c.h, 'f_px': c.f, 'vfov_deg': c.vfov_deg(),
                    'position_fusion_frame': c.p.tolist(),
                    'pitch_up_deg': math.degrees(math.atan2(c.R[2, 1], c.R[1, 1]))}
        return {'fused_camera_sha256': self.module_sha256, 'cv2_available': self.fc.cv2 is not None,
                'virtual': cam(self.virt), 'head': cam(self.head), 'd435': cam(self.d435),
                'head_lut_valid_fraction': float(self.lut[2].mean())}

    def check_intrinsics(self, name, cam, k):
        """Record one camera's measured K; return a list of mismatches against the fusion's pinhole."""
        k = np.asarray(k, dtype=np.float64)
        fx, fy, cx, cy = float(k[0, 0]), float(k[1, 1]), float(k[0, 2]), float(k[1, 2])
        tol = float(self.config['intrinsics_tolerance_px'])
        self.intrinsics[name] = {'fx': fx, 'fy': fy, 'cx': cx, 'cy': cy, 'expected_f': cam.f,
                                 'expected_cx': cam.w / 2.0, 'expected_cy': cam.h / 2.0}
        problems = []
        for label, measured, wanted in (('fx', fx, cam.f), ('fy', fy, cam.f), ('cx', cx, cam.w / 2.0),
                                        ('cy', cy, cam.h / 2.0)):
            if not abs(measured - wanted) <= tol + 1e-9:
                problems.append('{} {} {:.3f} != {:.3f}'.format(name, label, measured, wanted))
        return problems

    def check_authored_mount(self, name, spec, expected_opengl_quat_wxyz, local_pos, local_quat_wxyz):
        """Compare the camera prim's authored local pose (relative to TORSO) with its configuration; record it."""
        position_error_m = float(np.linalg.norm(np.asarray(local_pos, dtype=np.float64)
                                                - np.asarray(spec['pos'], dtype=np.float64)))
        R_rel = quat_wxyz_to_matrix(expected_opengl_quat_wxyz).T @ quat_wxyz_to_matrix(local_quat_wxyz)
        angle_deg = math.degrees(math.acos(max(-1.0, min(1.0, (float(np.trace(R_rel)) - 1.0) / 2.0))))
        self.mounts[name] = {'authored_position_m': [float(v) for v in local_pos],
                             'authored_quat_wxyz_opengl': [float(v) for v in local_quat_wxyz],
                             'configured_position_m': list(spec['pos']),
                             'configured_pitch_up_deg': float(spec['pitch_up']),
                             'position_error_m': position_error_m, 'rotation_error_deg': angle_deg}
        problems = []
        if not position_error_m <= float(self.config['authored_mount_tolerance_m']):
            problems.append('{} authored position error {:.6f} m'.format(name, position_error_m))
        if not angle_deg <= float(self.config['authored_mount_tolerance_deg']):
            problems.append('{} authored rotation error {:.4f} deg'.format(name, angle_deg))
        return problems

    def record_live_readback(self, phase, name, spec, expected_ros_quat_wxyz, torso_pos_w, torso_quat_wxyz,
                             cam_pos_w, cam_quat_ros_wxyz, refreshed):
        """Record only: the camera's reported world pose relative to the TORSO link at the same call."""
        R_torso = quat_wxyz_to_matrix(torso_quat_wxyz)
        rel_pos = R_torso.T @ (np.asarray(cam_pos_w, dtype=np.float64) - np.asarray(torso_pos_w, dtype=np.float64))
        rel_R = R_torso.T @ quat_wxyz_to_matrix(cam_quat_ros_wxyz)
        err_R = quat_wxyz_to_matrix(expected_ros_quat_wxyz).T @ rel_R
        self.live_readback.setdefault(phase, {})[name] = {
            'position_in_torso_m': rel_pos.tolist(), 'configured_position_m': list(spec['pos']),
            'position_error_m': float(np.linalg.norm(rel_pos - np.asarray(spec['pos'], dtype=np.float64))),
            'rotation_error_deg': math.degrees(math.acos(max(-1.0, min(1.0, (float(np.trace(err_R)) - 1.0) / 2.0)))),
            'measured_pitch_up_deg': math.degrees(math.asin(max(-1.0, min(1.0, float(rel_R[2, 2]))))),
            'refreshed_from_simulator': bool(refreshed)}

    def fuse(self, head_rgb, d435_rgb, d435_depth_m, ideal_rgb):
        start = time.perf_counter()
        fused, cov = self.fc.fuse(np.asarray(head_rgb)[..., :3], np.asarray(d435_rgb)[..., :3], d435_depth_m,
                                  self.virt, self.head, self.d435, feather_rows=int(self.config['feather_rows']),
                                  depth_valid_max=float(self.config['depth_valid_max_m']), lut=self.lut)
        fusion_ms = (time.perf_counter() - start) * 1000.0
        coverage = self.fc.coverage_stats(cov)
        err = np.abs(fused.astype(np.float64) - np.asarray(ideal_rgb)[..., :3].astype(np.float64)).mean(axis=2)
        regions = {}
        for name, code in REGION_CODES.items():
            mask = cov == code
            regions[name] = {'pixels': int(mask.sum()),
                             'mean_abs_err': round(float(err[mask].mean()), 3) if mask.any() else None}
        z = np.asarray(d435_depth_m, dtype=np.float64)
        finite = np.isfinite(z) & (z > 0)
        row = {
            'fusion_ms': round(fusion_ms, 2),
            'coverage': {key: round(value, 6) for key, value in coverage.items()},
            'error_vs_ideal': regions,
            'fused_differs_from_ideal_fraction': round(float((err > 0).mean()), 6),
            'd435_self_occlusion_fraction': round(float(
                (finite & (z < float(self.config['self_occlusion_max_depth_m']))).sum() / z.size), 6),
            'd435_finite_depth_fraction': round(float(finite.sum() / z.size), 6),
        }
        row['c8_bound_failures'] = self.bound_failures(row)
        return fused, cov, row

    def bound_failures(self, row):
        """The Habitat c8 preflight bounds (fusion time is reported separately: here it only pauses the simulator)."""
        b = self.bounds
        failures = []
        if row['coverage']['none'] > b['max_uncovered_fraction']:
            failures.append('uncovered {:.4f} > {}'.format(row['coverage']['none'], b['max_uncovered_fraction']))
        if row['coverage']['head'] < b['min_fraction_from_head']:
            failures.append('head share {:.4f} < {}'.format(row['coverage']['head'], b['min_fraction_from_head']))
        for region, key in (('head', 'max_mean_abs_err_head_region'), ('d435', 'max_mean_abs_err_d435_region')):
            value = row['error_vs_ideal'][region]['mean_abs_err']
            if value is None or value > b[key]:
                failures.append('{} region error {} > {}'.format(region, value, b[key]))
        return failures


def summarise(rows, bounds):
    def spread(values):
        values = sorted(v for v in values if v is not None)
        if not values:
            return None
        return {'min': values[0], 'median': values[len(values) // 2], 'p95': values[int(round(0.95 * (len(values) - 1)))],
                'max': values[-1], 'n': len(values)}
    decision = [r for r in rows if r.get('kind') == 'decision']
    return {
        'frames': len(rows), 'decision_frames': len(decision),
        'decision_frames_outside_c8_bounds': sum(1 for r in decision if r['c8_bound_failures']),
        'all_frames_outside_c8_bounds': sum(1 for r in rows if r['c8_bound_failures']),
        'fusion_ms': spread([r['fusion_ms'] for r in rows]),
        'fusion_ms_over_c8_bound': sum(1 for r in rows if r['fusion_ms'] > bounds['max_fusion_ms_per_frame']),
        'uncovered_fraction': spread([r['coverage']['none'] for r in rows]),
        'head_fraction': spread([r['coverage']['head'] for r in rows]),
        'head_region_mean_abs_err': spread([r['error_vs_ideal']['head']['mean_abs_err'] for r in rows]),
        'd435_region_mean_abs_err': spread([r['error_vs_ideal']['d435']['mean_abs_err'] for r in rows]),
        'd435_self_occlusion_fraction': spread([r['d435_self_occlusion_fraction'] for r in rows]),
    }
