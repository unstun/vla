"""Preflight one FUSED camera condition (round 5) from the official launch directory.

Must run from work/InternNav inside official_r2r/official_env_024, once per condition:

  CAM_YAML=<yaml> python public_scenes/requests/2026-09-10_lite3_camera_ablation/preflight_fused.py --cond c7_fused_level

Same report shape as preflight_cam.py (run_matrix.sh gates on all_stages_passed). Stages:
 1 official env versions; 2 paths (plus plugin, fusion module, fused eval config);
 3 pinned inputs match baseline public_eval_v5; 4 fused eval config loads with CAM_YAML and the
 plugin registered its sensors; 5 composed config: virtual rgb/depth, the three rendered mounts and the
 fused_rgb_sensor task sensor have the geometry of conditions.json, everything else equals the baseline;
 6 start frame: env.reset() returns the FUSED image under key rgb (bit-identical to an offline recompute
 from the raw sensors, and different from the ideal sim rgb), the fused image matches the ideal virtual
 render inside the covered regions, coverage fractions are within bounds, and every sensor's measured
 height / pitch / forward offset equals its configuration (this independently checks Habitat's pitch
 sign for the +16.7 deg head camera); 7 look_down is a no-op for the fused rgb (tilt_angle 0);
 8 fusion cost per frame; 9 free GPU memory after closing the preflight simulator.
"""
import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

sys.path.append('.')
sys.path.append('./third_party/diffusion-policy')

REQ = 'public_scenes/requests/2026-09-10_lite3_camera_ablation'
BASELINE_INPUTS = 'public_scenes/runs/public_eval_v5/inputs.json'
RUN_SUMMARY = 'public_scenes/setup/run_summary.json'
REPORT = {'stages': []}
H = {}


def stage(name, fn):
    entry = {'stage': name}
    if REPORT['stages'] and not REPORT['stages'][-1]['ok']:
        entry.update(ok=False, skipped=True, detail='not attempted: an earlier stage failed')
        REPORT['stages'].append(entry)
        return None
    try:
        entry['detail'] = fn()
        entry['ok'] = True
    except Exception:
        entry['ok'] = False
        entry['traceback'] = traceback.format_exc()
    REPORT['stages'].append(entry)
    return entry.get('detail')


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def close(a, b, tol):
    return len(a) == len(b) and all(abs(float(x) - float(y)) <= tol for x, y in zip(a, b))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cond', required=True)
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    cwd = Path.cwd()
    REPORT['launch_directory'] = str(cwd)
    REPORT['condition'] = a.cond
    if cwd.name != 'InternNav':
        raise SystemExit(f'must run from the official launch directory work/InternNav, not {cwd}')
    conds = json.loads(Path(f'{REQ}/conditions.json').read_text())
    if a.cond not in conds['conditions'] or 'fused' not in conds['conditions'][a.cond]:
        raise SystemExit(f'{a.cond} is not a fused condition')
    spec = conds['conditions'][a.cond]
    F = spec['fused']
    yaml_rel = spec['habitat_yaml']
    cfg_rel = spec['eval_config']
    pf = conds['preflight']
    pff = pf['fused']
    out = a.out or f'{REQ}/preflight/{a.cond}.json'
    if os.environ.get('CAM_YAML') != yaml_rel:
        raise SystemExit(f'CAM_YAML must equal {yaml_rel} for condition {a.cond}')
    outdir = Path(f'{REQ}/preflight')
    outdir.mkdir(parents=True, exist_ok=True)

    def s_versions():
        import habitat, habitat_baselines, habitat_sim, torch, transformers, diffusers
        try:
            import cv2
            cv2v = cv2.__version__
        except Exception:
            cv2v = None
        return {'python': sys.version.split()[0], 'habitat_lab': habitat.__version__,
                'habitat_baselines': habitat_baselines.__version__, 'habitat_sim': habitat_sim.__version__,
                'torch': torch.__version__, 'transformers': transformers.__version__,
                'diffusers': diffusers.__version__, 'cuda_available': torch.cuda.is_available(),
                'cuda_device': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
                'cv2': cv2v}

    def s_paths():
        wanted = {
            'condition_yaml': yaml_rel, 'eval_config': cfg_rel,
            'fusion_module': F['fusion']['module'], 'fusion_plugin': F['fusion']['plugin'],
            'conditions_json': f'{REQ}/conditions.json',
            'annotations': 'public_scenes/data/vln_ce/raw_data/public/val_unseen/val_unseen.json.gz',
            'scene_glb': 'public_scenes/data/scene_data/public/skokloster-castle/skokloster-castle.glb',
            'scene_navmesh': 'public_scenes/data/scene_data/public/skokloster-castle/skokloster-castle.navmesh',
            'aux_depth_encoder': 'checkpoints/depth_anything_v2_metric_hypersim_vits.pth',
            'model_checkpoint_config': 'checkpoints/InternVLA-N1-DualVLN/config.json',
            'baseline_inputs': BASELINE_INPUTS, 'baseline_run_summary': RUN_SUMMARY,
        }
        res, missing = {}, []
        for k, rel in wanted.items():
            p = Path(rel)
            res[k] = {'relative_to_launch_dir': rel, 'exists': p.exists(),
                      'resolves_to': str(p.resolve()) if p.exists() else None}
            if not p.exists():
                missing.append(rel)
        if missing:
            raise RuntimeError(f'unresolvable from the launch directory: {missing}')
        return res

    def s_identity():
        base = json.loads(Path(BASELINE_INPUTS).read_text())['input_sha256']
        pinned = ['scripts/eval/eval.py',
                  'internnav/habitat_extensions/vln/habitat_vln_evaluator.py',
                  'internnav/model/utils/vln_utils.py',
                  'public_scenes/data/vln_ce/raw_data/public/val_unseen/val_unseen.json.gz',
                  'public_scenes/data/scene_data/public/skokloster-castle/skokloster-castle.glb',
                  'public_scenes/data/scene_data/public/skokloster-castle/skokloster-castle.navmesh']
        res, bad = {}, []
        for rel in pinned:
            got = sha256_file(rel)
            res[rel] = {'sha256': got, 'baseline_sha256': base.get(rel), 'matches_baseline': got == base.get(rel)}
            if got != base.get(rel):
                bad.append(rel)
        for k in ('condition_yaml', 'eval_config', 'conditions_json', 'fusion_module', 'fusion_plugin'):
            rel = {'condition_yaml': yaml_rel, 'eval_config': cfg_rel, 'conditions_json': f'{REQ}/conditions.json',
                   'fusion_module': F['fusion']['module'], 'fusion_plugin': F['fusion']['plugin']}[k]
            res[f'{k}_sha256'] = sha256_file(rel)
        if bad:
            raise RuntimeError(f'pinned inputs differ from baseline public_eval_v5: {bad}')
        return res

    def s_eval_cfg():
        import importlib.util
        specm = importlib.util.spec_from_file_location('preflight_fused_eval_cfg', cfg_rel)
        mod = importlib.util.module_from_spec(specm)
        specm.loader.exec_module(mod)
        cfg = mod.eval_cfg
        ms = dict(cfg.agent.model_settings)
        if cfg.env.env_settings['config_path'] != yaml_rel:
            raise RuntimeError('eval config did not pick up CAM_YAML')
        if ms['mode'] != 'dual_system' or ms['model_path'] != 'checkpoints/InternVLA-N1-DualVLN':
            raise RuntimeError(f'unexpected model settings {ms}')
        if 'fused_camera_plugin' not in sys.modules:
            raise RuntimeError('eval config did not import fused_camera_plugin')
        from habitat.core.registry import registry
        for t in ('FusedRGBSensor', 'FusedHeadRGBSensor', 'FusedD435RGBSensor', 'FusedD435DepthSensor'):
            if registry.get_sensor(t) is None:
                raise RuntimeError(f'sensor type {t} not registered')
        H['plugin'] = sys.modules['fused_camera_plugin']
        return {'eval_type': cfg.eval_type, 'model_settings': ms, 'env_settings': dict(cfg.env.env_settings),
                'eval_settings': dict(cfg.eval_settings), 'plugin_version': H['plugin'].PLUGIN_VERSION,
                'plugin_file': H['plugin'].__file__}

    def s_habitat_config():
        from habitat_baselines.config.default import get_config as get_habitat_config
        cfg = get_habitat_config(yaml_rel)
        base_cfg = get_habitat_config(conds['baseline']['habitat_yaml'])
        sim = cfg.habitat.simulator
        ag = sim.agents.main_agent
        got, problems = {}, []
        expect = {'rgb_sensor': F['virtual'], 'depth_sensor': F['depth_for_evaluator'],
                  'fused_head_rgb_sensor': F['head_rgb'], 'fused_d435_rgb_sensor': F['d435_rgb'],
                  'fused_d435_depth_sensor': F['d435_depth']}
        for key, e in expect.items():
            if key not in ag.sim_sensors:
                problems.append(f'{key} missing from sim_sensors'); continue
            sc = ag.sim_sensors[key]
            g = {'type': str(sc.type), 'width': int(sc.width), 'height': int(sc.height), 'hfov': float(sc.hfov),
                 'position': [float(v) for v in sc.position], 'orientation': [float(v) for v in sc.orientation],
                 'uuid': str(getattr(sc, 'uuid', {'rgb_sensor': 'rgb', 'depth_sensor': 'depth'}.get(key, '')))}
            if 'min_depth' in sc:
                g.update(min_depth=float(sc.min_depth), max_depth=float(sc.max_depth), normalize_depth=bool(sc.normalize_depth))
            got[key] = g
            if (g['width'], g['height']) != (int(e['width']), int(e['height'])):
                problems.append(f'{key} resolution {g["width"]}x{g["height"]}')
            if abs(g['hfov'] - float(e['hfov'])) > 1e-6:
                problems.append(f'{key} hfov {g["hfov"]} != {e["hfov"]}')
            if not close(g['position'], e['position'], 1e-6):
                problems.append(f'{key} position {g["position"]} != {e["position"]}')
            if not close(g['orientation'], e['orientation'], 1e-6):
                problems.append(f'{key} orientation {g["orientation"]} != {e["orientation"]}')
            if 'uuid' in e and g['uuid'] != e['uuid'] and key not in ('rgb_sensor', 'depth_sensor'):
                problems.append(f'{key} uuid {g["uuid"]} != {e["uuid"]}')
            if 'normalize_depth' in e and g.get('normalize_depth') != bool(e['normalize_depth']):
                problems.append(f'{key} normalize_depth {g.get("normalize_depth")} != {e["normalize_depth"]}')
        ls = cfg.habitat.task.lab_sensors
        if 'fused_rgb_sensor' not in ls:
            problems.append('fused_rgb_sensor missing from task.lab_sensors')
        else:
            fs = ls.fused_rgb_sensor
            got['fused_rgb_sensor'] = {k: (str(v) if isinstance(v, str) else v) for k, v in dict(fs).items()}
            if str(fs.type) != 'FusedRGBSensor' or str(fs.uuid) != F['virtual']['uuid']:
                problems.append(f'fused_rgb_sensor type/uuid {fs.type}/{fs.uuid}')
            if int(fs.feather_rows) != int(F['fusion']['feather_rows']) or abs(float(fs.depth_valid_max_m) - float(F['fusion']['depth_valid_max_m'])) > 1e-9:
                problems.append('fused_rgb_sensor fusion parameters differ from conditions.json')
        got['tilt_angle'] = float(sim.tilt_angle)
        if abs(got['tilt_angle'] - spec['habitat']['tilt_angle']) > 1e-6:
            problems.append(f'tilt_angle {got["tilt_angle"]}')
        got['forward_step_size'] = float(sim.forward_step_size); got['turn_angle'] = float(sim.turn_angle)
        got['agent_height'] = float(ag.height); got['agent_radius'] = float(ag.radius)
        got['dataset'] = {'type': cfg.habitat.dataset.type, 'split': cfg.habitat.dataset.split,
                          'scenes_dir': cfg.habitat.dataset.scenes_dir, 'data_path': cfg.habitat.dataset.data_path}
        got['actions'] = sorted(cfg.habitat.task.actions.keys()); got['measurements'] = sorted(cfg.habitat.task.measurements.keys())
        got['max_episode_steps'] = int(cfg.habitat.environment.max_episode_steps)
        got['lab_sensors'] = sorted(ls.keys())
        bsim = base_cfg.habitat.simulator
        same = {'forward_step_size': float(bsim.forward_step_size), 'turn_angle': float(bsim.turn_angle),
                'agent_height': float(bsim.agents.main_agent.height), 'agent_radius': float(bsim.agents.main_agent.radius),
                'dataset': {'type': base_cfg.habitat.dataset.type, 'split': base_cfg.habitat.dataset.split,
                            'scenes_dir': base_cfg.habitat.dataset.scenes_dir, 'data_path': base_cfg.habitat.dataset.data_path},
                'actions': sorted(base_cfg.habitat.task.actions.keys()),
                'measurements': sorted(base_cfg.habitat.task.measurements.keys()),
                'max_episode_steps': int(base_cfg.habitat.environment.max_episode_steps)}
        for k, v in same.items():
            if got[k] != v:
                problems.append(f'{k} differs from baseline: {got[k]} != {v}')
        if sorted(set(got['lab_sensors']) - {'fused_rgb_sensor'}) != sorted(base_cfg.habitat.task.lab_sensors.keys()):
            problems.append('lab sensors other than fused_rgb_sensor differ from baseline')
        if problems:
            raise RuntimeError('composed config mismatch: ' + '; '.join(problems))
        H['cfg'] = cfg
        return got

    def sensor_state(env, uuid):
        import numpy as np, quaternion
        st = env.sim.get_agent_state()
        s = st.sensor_states[uuid]
        rel = st.rotation.inverse() * s.rotation
        fwd = quaternion.rotate_vectors(rel, np.array([0.0, 0.0, -1.0]))
        pitch_down = math.degrees(math.asin(max(-1.0, min(1.0, -float(fwd[1])))))
        d = quaternion.rotate_vectors(st.rotation.inverse(), np.asarray(s.position) - np.asarray(st.position))
        return {'height_above_agent_m': round(float(d[1]), 4), 'pitch_down_deg': round(pitch_down, 3),
                'forward_offset_m': round(float(-d[2]), 4)}

    def s_render():
        import numpy as np
        import habitat
        from PIL import Image
        import internnav.habitat_extensions.vln.measures  # noqa: F401
        cfg = H['cfg']
        env = habitat.Env(cfg)
        H['env'] = env
        obs = env.reset()
        ep = env.current_episode
        need = {'rgb', 'depth', F['head_rgb']['uuid'], F['d435_rgb']['uuid'], F['d435_depth']['uuid'], 'gps', 'compass'}
        missing = sorted(need - set(obs.keys()))
        if missing:
            raise RuntimeError(f'observation keys missing: {missing}; have {sorted(obs.keys())}')
        fused = np.asarray(obs['rgb'])
        if fused.shape != (F['virtual']['height'], F['virtual']['width'], 3) or fused.dtype != np.uint8:
            raise RuntimeError(f'fused rgb shape/dtype {fused.shape} {fused.dtype}')
        raw = env.sim.get_sensor_observations()
        ideal = np.asarray(raw['rgb'])[:, :, :3]
        head = np.asarray(raw[F['head_rgb']['uuid']])[:, :, :3]
        d435 = np.asarray(raw[F['d435_rgb']['uuid']])[:, :, :3]
        d435z = np.clip(np.asarray(raw[F['d435_depth']['uuid']]).squeeze(), F['d435_depth']['min_depth'], F['d435_depth']['max_depth'])
        sensor = env.task.sensor_suite.sensors['rgb']
        if type(sensor).__name__ != 'FusedRGBSensor':
            raise RuntimeError(f'task sensor rgb is {type(sensor).__name__}, not FusedRGBSensor')
        re_img, re_cov = sensor.fuse_from({F['head_rgb']['uuid']: head, F['d435_rgb']['uuid']: d435,
                                           F['d435_depth']['uuid']: d435z[..., None]})
        identical = bool(np.array_equal(re_img, fused))
        differs_from_ideal = float((np.abs(fused.astype(np.int16) - ideal.astype(np.int16)).max(axis=2) > 0).mean())
        err = np.abs(fused.astype(np.float64) - ideal.astype(np.float64)).mean(axis=2)
        cov = re_cov
        from fused_camera import coverage_stats
        stats = coverage_stats(cov)
        def region(m):
            return {'pixels': int(m.sum()), 'mean_abs_err': (round(float(err[m].mean()), 3) if m.any() else None),
                    'psnr_db': (round(10 * math.log10(255 ** 2 / max(float((err[m] ** 2).mean()), 1e-9)), 2) if m.any() else None)}
        regions = {'head': region(cov == 1), 'd435': region(cov == 2), 'blend': region(cov == 3)}
        states = {u: sensor_state(env, u) for u in ('rgb', 'depth', F['head_rgb']['uuid'], F['d435_rgb']['uuid'], F['d435_depth']['uuid'])}
        # evaluator depth floor gap: expected z-depth of a flat floor on the bottom rows. Habitat depth is
        # z-depth along the optical axis, so a flat floor at row r reads h / (sin(pitch) + tan(theta_r) cos(pitch)),
        # theta_r being that row's angle below the optical axis. Rounds 5/5b used the level-only shortcut
        # h / tan(theta_r); that is the same expression at pitch 0 but wrong for the pitched virtual camera of
        # round 6 (C9), where it would under-report the implied gap by about 0.11 m. Ported from preflight_cam.py,
        # which has carried the general form since round 1 for the pitched conditions C1/C4/C6.
        ds = cfg.habitat.simulator.agents.main_agent.sim_sensors.depth_sensor
        dmin, dmax = float(ds.min_depth), float(ds.max_depth)
        d = np.asarray(obs['depth']).squeeze()
        metres = d * (dmax - dmin) + dmin if bool(ds.normalize_depth) else d
        h_img, w_img = metres.shape
        c0, c1 = w_img // 2 - pf['central_columns'] // 2, w_img // 2 + pf['central_columns'] // 2
        floor_est = float(np.percentile(metres[h_img - pf['bottom_rows']:, c0:c1], pf['floor_percentile']))
        vf = math.degrees(2 * math.atan(math.tan(math.radians(F['virtual']['hfov']) / 2) * h_img / w_img))
        rows = np.arange(h_img - pf['bottom_rows'], h_img)
        tan_theta = ((rows + 0.5) - h_img / 2) / (h_img / 2) * math.tan(math.radians(vf / 2))
        p_rad = -float(F['virtual']['orientation'][0])  # Habitat orientation[0] is radians, positive up
        denom = math.sin(p_rad) + tan_theta * math.cos(p_rad)
        if np.all(denom > 1e-6):
            expected = float(np.percentile(np.repeat((spec['height_m'] / denom)[:, None], c1 - c0, axis=1), pf['floor_percentile']))
        else:
            expected = float('inf')  # bottom rays never reach the floor
        implied_gap = ((floor_est / expected - 1.0) * spec['height_m']) if math.isfinite(expected) else float('nan')
        Image.fromarray(fused).save(outdir / f'{a.cond}_start_fused_rgb.png')
        Image.fromarray(ideal.astype(np.uint8)).save(outdir / f'{a.cond}_start_ideal_rgb.png')
        Image.fromarray(head.astype(np.uint8)).save(outdir / f'{a.cond}_start_head_rgb.png')
        Image.fromarray(d435.astype(np.uint8)).save(outdir / f'{a.cond}_start_d435_rgb.png')
        Image.fromarray((d435z * 1000.0).clip(0, 65535).astype(np.uint16)).save(outdir / f'{a.cond}_start_d435_depth_mm.png')
        Image.fromarray((metres * 1000.0).clip(0, 65535).astype(np.uint16)).save(outdir / f'{a.cond}_start_depth_mm.png')
        Image.fromarray((cov * 80).astype(np.uint8)).save(outdir / f'{a.cond}_start_coverage.png')
        res = {'episode_id': ep.episode_id, 'scene_id': ep.scene_id,
               'start_position': [float(v) for v in ep.start_position],
               'observation_keys': sorted(obs.keys()), 'fused_rgb_shape': list(fused.shape),
               'fused_equals_offline_recompute': identical,
               'fraction_of_pixels_differing_from_ideal': round(differs_from_ideal, 4),
               'coverage': stats, 'error_vs_ideal_by_region': regions,
               'fusion_ms_last_call': round(float(sensor.last_ms), 2) if sensor.last_ms else None,
               'measured_sensor_state': states,
               'evaluator_depth_bottom_rows_floor_zdepth_m_p90': round(floor_est, 3),
               'evaluator_depth_expected_flat_floor_m_p90': round(expected, 3),
               'implied_agent_origin_to_floor_gap_m': round(implied_gap, 4),
               'pngs': sorted(str(p) for p in outdir.glob(f'{a.cond}_start_*.png'))}
        REPORT.setdefault('partial_details', {})['start frame'] = res
        problems = []
        if not identical:
            problems.append('env rgb is not the plugin fusion of the raw sensors (override not in effect or non-deterministic)')
        if differs_from_ideal < 0.01:
            problems.append('env rgb equals the ideal sim rgb: the task sensor did not override it')
        if stats['none'] > pff['max_uncovered_fraction'][a.cond]:
            problems.append(f'uncovered fraction {stats["none"]:.4f} > {pff["max_uncovered_fraction"][a.cond]}')
        min_head = pff['min_fraction_from_head']
        if isinstance(min_head, dict):
            min_head = min_head[a.cond]
        if stats['head'] < min_head:
            problems.append(f'head fraction {stats["head"]:.3f} < {min_head}')
        if regions['head']['mean_abs_err'] is None or regions['head']['mean_abs_err'] > pff['max_mean_abs_err_head_region']:
            problems.append(f'head-region error {regions["head"]["mean_abs_err"]} > {pff["max_mean_abs_err_head_region"]}')
        if regions['d435']['mean_abs_err'] is None or regions['d435']['mean_abs_err'] > pff['max_mean_abs_err_d435_region']:
            problems.append(f'd435-region error {regions["d435"]["mean_abs_err"]} > {pff["max_mean_abs_err_d435_region"]}')
        exp_states = {'rgb': (F['virtual'], spec['height_m'], spec['forward_offset_m']),
                      'depth': (F['depth_for_evaluator'], spec['height_m'], spec['forward_offset_m']),
                      F['head_rgb']['uuid']: (F['head_rgb'], F['head_rgb']['position'][1], -F['head_rgb']['position'][2]),
                      F['d435_rgb']['uuid']: (F['d435_rgb'], F['d435_rgb']['position'][1], -F['d435_rgb']['position'][2]),
                      F['d435_depth']['uuid']: (F['d435_depth'], F['d435_depth']['position'][1], -F['d435_depth']['position'][2])}
        for u, (e, hgt, fwd) in exp_states.items():
            s = states[u]
            pitch_cfg = -math.degrees(e['orientation'][0])
            if abs(s['height_above_agent_m'] - hgt) > pf['height_tolerance_m']:
                problems.append(f'{u} height {s["height_above_agent_m"]} != {hgt}')
            if abs(s['pitch_down_deg'] - pitch_cfg) > pf['pitch_tolerance_deg']:
                problems.append(f'{u} pitch down {s["pitch_down_deg"]} != {pitch_cfg} (sign or units wrong?)')
            if abs(s['forward_offset_m'] - fwd) > pf['height_tolerance_m']:
                problems.append(f'{u} forward offset {s["forward_offset_m"]} != {fwd}')
        lo, hi = pf['floor_gap_bounds_m']
        if not math.isfinite(implied_gap) or not (lo <= implied_gap <= hi):
            problems.append(f'implied floor gap {implied_gap:.3f} outside [{lo}, {hi}]')
        if problems:
            raise RuntimeError('render check failed: ' + '; '.join(problems))
        return res

    def s_tilt():
        import numpy as np
        env = H['env']
        before = np.asarray(env.reset()['rgb']).copy()  # advances to the second frozen episode; recorded below
        p0 = {u: sensor_state(env, u)['pitch_down_deg'] for u in ('rgb', F['head_rgb']['uuid'], F['d435_rgb']['uuid'])}
        after = np.asarray(env.step({'action': 'look_down'})['rgb'])
        p1 = {u: sensor_state(env, u)['pitch_down_deg'] for u in p0}
        env.step({'action': 'look_up'})
        diff = np.abs(before.astype(np.int16) - after.astype(np.int16))
        changed = float((diff.max(axis=2) > 0).mean())
        res = {'tilt_angle': spec['habitat']['tilt_angle'], 'episode_id': env.current_episode.episode_id, 'pitch_before': p0, 'pitch_after_look_down': p1,
               'changed_pixel_fraction_after_look_down': round(changed, 6),
               'mean_abs_channel_delta_after_look_down': round(float(diff.mean()), 6)}
        for u in p0:
            if abs(p1[u] - p0[u]) > pf['tilt_noop_max_pitch_delta_deg']:
                raise RuntimeError(f'tilt_angle 0 but look_down changed {u} pitch by {p1[u] - p0[u]:.6f} deg')
        # resampling spreads the 1-2 ULP re-normalisation flicker seen in rounds 2-4 (0.3 percent of raw
        # pixels) over neighbouring fused pixels; bound the fraction at 5x the raw limit
        if changed > 5 * pf['tilt_noop_max_changed_pixel_fraction']:
            raise RuntimeError(f'tilt_angle 0 but look_down changed {changed:.4%} of fused pixels')
        return res

    def s_cost():
        import numpy as np
        env = H['env']
        raw = env.sim.get_sensor_observations()
        sensor = env.task.sensor_suite.sensors['rgb']
        obs = {F['head_rgb']['uuid']: np.asarray(raw[F['head_rgb']['uuid']])[:, :, :3],
               F['d435_rgb']['uuid']: np.asarray(raw[F['d435_rgb']['uuid']])[:, :, :3],
               F['d435_depth']['uuid']: np.clip(np.asarray(raw[F['d435_depth']['uuid']]).squeeze(), 0, 10)[..., None]}
        times = []
        for _ in range(10):
            t0 = time.perf_counter(); sensor.fuse_from(obs); times.append((time.perf_counter() - t0) * 1000)
        res = {'fusion_ms_mean': round(float(np.mean(times)), 2), 'fusion_ms_max': round(float(np.max(times)), 2), 'calls': 10}
        if res['fusion_ms_mean'] > pff['max_fusion_ms_per_frame']:
            raise RuntimeError(f'fusion {res["fusion_ms_mean"]} ms/frame > {pff["max_fusion_ms_per_frame"]}')
        return res

    def s_gpu():
        env = H.pop('env', None)
        if env is not None:
            env.close()
        q = subprocess.run(['nvidia-smi', '--query-gpu=memory.total,memory.used,memory.free', '--format=csv,noheader,nounits'],
                           capture_output=True, text=True, check=True)
        total, used, free = [int(x.strip()) for x in q.stdout.strip().splitlines()[0].split(',')]
        apps = subprocess.run(['nvidia-smi', '--query-compute-apps=pid,process_name,used_memory', '--format=csv,noheader'],
                              capture_output=True, text=True).stdout.strip()
        rs = json.loads(Path(RUN_SUMMARY).read_text())
        mems = [r['device_memory_sampled_every_5s_MiB'] for r in rs['runs'] if 'device_memory_sampled_every_5s_MiB' in r]
        footprint = max(m['max_used_whole_device'] - m['min_used_whole_device'] for m in mems)
        res = {'total_MiB': total, 'used_MiB': used, 'free_MiB': free, 'baseline_model_footprint_MiB_max_over_runs': footprint,
               'required_free_MiB': int(footprint), 'margin_MiB': free - int(footprint),
               'resident_compute_apps': apps.splitlines(), 'note': 'resident processes are recorded, never touched'}
        if free < int(footprint):
            raise RuntimeError(f'free GPU memory {free} MiB < required {footprint} MiB')
        return res

    try:
        stage('official env versions', s_versions)
        stage('all paths resolve from the launch directory', s_paths)
        stage('pinned inputs match baseline public_eval_v5', s_identity)
        stage('fused eval config loads with CAM_YAML and registers the plugin sensors', s_eval_cfg)
        stage('condition habitat config composes to the specified geometry', s_habitat_config)
        stage('start frame: fused rgb overrides sim rgb, matches the ideal render, sensors sit where configured', s_render)
        stage('look_down is a no-op for the fused rgb (tilt_angle 0)', s_tilt)
        stage('fusion cost per frame', s_cost)
        stage('free GPU memory after closing the preflight simulator', s_gpu)
    finally:
        env = H.pop('env', None)
        if env is not None:
            try:
                env.close()
            except Exception:
                pass
        REPORT['all_stages_passed'] = len(REPORT['stages']) == 9 and all(s.get('ok') for s in REPORT['stages'])
        REPORT['condition_yaml'] = yaml_rel
        REPORT['eval_config'] = cfg_rel
        REPORT['written_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        Path(out).write_text(json.dumps(REPORT, indent=2, default=str) + '\n')
        print(json.dumps({'condition': a.cond, 'all_stages_passed': REPORT['all_stages_passed'],
                          'stages': [(s['stage'], s.get('ok')) for s in REPORT['stages']]}, indent=1))
        print('ALL_STAGES_PASSED' if REPORT['all_stages_passed'] else 'PREFLIGHT_FAILED', out)
    return 0 if REPORT['all_stages_passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
