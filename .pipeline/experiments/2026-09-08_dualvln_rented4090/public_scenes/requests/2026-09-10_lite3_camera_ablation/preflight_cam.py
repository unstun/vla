"""Preflight one camera condition from the official launch directory.

Must run from work/InternNav inside official_r2r/official_env_024, once per
condition:

  CAM_YAML=<yaml> python public_scenes/requests/2026-09-10_lite3_camera_ablation/preflight_cam.py --cond c1_lite3_rig

Stops at the first failing stage and records the traceback. Stage 5 renders
the start frame of the first episode and checks, independently of any
assumption about Habitat's orientation convention, that (a) the sensor sits
at the configured height above the agent, (b) the sensor forward vector is
pitched down by the configured angle, and (c) the depth at the bottom image rows
matches the z-depth a flat floor returns for the configured height, pitch, and
vertical FOV (Habitat depth is measured along the optical axis, so this equals
the research note's h / tan(pitch + vfov/2) only for a level camera). Round 2 (2026-09-10): the floor sub-check bounds the implied agent-origin-to-floor
gap, h * (measured / expected - 1), instead of a 25 percent ratio, because round 1
measured a constant navmesh-to-floor gap of about 0.16 m at this start pose in all
four conditions while every direct sensor-state check passed. Stage 6 checks that look_down is a no-op when tilt_angle is 0 (pitch delta and
changed-pixel fraction bounded; round 2 showed a quaternion re-normalisation flips about
0.3 percent of edge pixels without moving the camera) and a 15-degree tilt otherwise. Stage 7 closes the preflight simulator before reading free memory.
"""
import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import traceback
from pathlib import Path

sys.path.append('.')
sys.path.append('./third_party/diffusion-policy')

REQ = 'public_scenes/requests/2026-09-10_lite3_camera_ablation'
BASELINE_INPUTS = 'public_scenes/runs/public_eval_v5/inputs.json'
RUN_SUMMARY = 'public_scenes/setup/run_summary.json'
REPORT = {'stages': []}
ENV_HOLDER = {}


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


def vfov_deg(hfov_deg, width, height):
    return math.degrees(2 * math.atan(math.tan(math.radians(hfov_deg) / 2) * height / width))


def close(a, b, tol):
    return all(abs(float(x) - float(y)) <= tol for x, y in zip(a, b)) and len(a) == len(b)


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
    if a.cond not in conds['conditions']:
        raise SystemExit(f'unknown condition {a.cond}; have {sorted(conds["conditions"])}')
    spec = conds['conditions'][a.cond]
    hab = spec['habitat']
    yaml_rel = spec['habitat_yaml']
    cfg_rel = conds['execution']['eval_config']
    pf = conds['preflight']
    W, H = conds['resolution']['width'], conds['resolution']['height']
    out = a.out or f'{REQ}/preflight/{a.cond}.json'
    if os.environ.get('CAM_YAML') != yaml_rel:
        raise SystemExit(f'CAM_YAML must equal {yaml_rel} for condition {a.cond}')

    def s_versions():
        import habitat, habitat_baselines, habitat_sim, torch, transformers, diffusers
        return {'python': sys.version.split()[0], 'habitat_lab': habitat.__version__,
                'habitat_baselines': habitat_baselines.__version__, 'habitat_sim': habitat_sim.__version__,
                'torch': torch.__version__, 'transformers': transformers.__version__,
                'diffusers': diffusers.__version__, 'cuda_available': torch.cuda.is_available(),
                'cuda_device': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}

    def s_paths():
        wanted = {
            'condition_yaml': yaml_rel, 'eval_config': cfg_rel,
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
        res['condition_yaml_sha256'] = sha256_file(yaml_rel)
        res['eval_config_sha256'] = sha256_file(cfg_rel)
        res['conditions_json_sha256'] = sha256_file(f'{REQ}/conditions.json')
        if bad:
            raise RuntimeError(f'pinned inputs differ from baseline public_eval_v5: {bad}')
        return res

    def s_eval_cfg():
        import importlib.util
        specm = importlib.util.spec_from_file_location('preflight_cam_eval_cfg', cfg_rel)
        mod = importlib.util.module_from_spec(specm)
        specm.loader.exec_module(mod)
        cfg = mod.eval_cfg
        ms = dict(cfg.agent.model_settings)
        if cfg.env.env_settings['config_path'] != yaml_rel:
            raise RuntimeError('eval config did not pick up CAM_YAML')
        if ms['mode'] != 'dual_system' or ms['model_path'] != 'checkpoints/InternVLA-N1-DualVLN':
            raise RuntimeError(f'unexpected model settings {ms}')
        return {'eval_type': cfg.eval_type, 'model_settings': ms,
                'env_settings': dict(cfg.env.env_settings), 'eval_settings': dict(cfg.eval_settings)}

    def s_habitat_config():
        from habitat_baselines.config.default import get_config as get_habitat_config
        cfg = get_habitat_config(yaml_rel)
        base_cfg = get_habitat_config(conds['baseline']['habitat_yaml'])
        sim = cfg.habitat.simulator
        ag = sim.agents.main_agent
        got = {}
        problems = []
        for s in ('rgb_sensor', 'depth_sensor'):
            sc = getattr(ag.sim_sensors, s)
            g = {'width': int(sc.width), 'height': int(sc.height), 'hfov': float(sc.hfov),
                 'position': [float(v) for v in sc.position],
                 'orientation': [float(v) for v in sc.orientation]}
            got[s] = g
            if (g['width'], g['height']) != (W, H):
                problems.append(f'{s} resolution {g["width"]}x{g["height"]}')
            if abs(g['hfov'] - hab['hfov']) > 1e-6:
                problems.append(f'{s} hfov {g["hfov"]} != {hab["hfov"]}')
            if not close(g['position'], hab['position'], 1e-6):
                problems.append(f'{s} position {g["position"]} != {hab["position"]}')
            if not close(g['orientation'], hab['orientation'], 1e-6):
                problems.append(f'{s} orientation {g["orientation"]} != {hab["orientation"]}')
        got['tilt_angle'] = float(sim.tilt_angle)
        if abs(got['tilt_angle'] - hab['tilt_angle']) > 1e-6:
            problems.append(f'tilt_angle {got["tilt_angle"]} != {hab["tilt_angle"]}')
        ds = ag.sim_sensors.depth_sensor
        got['depth_min_max'] = [float(ds.min_depth), float(ds.max_depth)]
        got['normalize_depth'] = bool(ds.normalize_depth)
        got['forward_step_size'] = float(sim.forward_step_size)
        got['turn_angle'] = float(sim.turn_angle)
        got['agent_height'] = float(ag.height)
        got['agent_radius'] = float(ag.radius)
        got['dataset'] = {'type': cfg.habitat.dataset.type, 'split': cfg.habitat.dataset.split,
                          'scenes_dir': cfg.habitat.dataset.scenes_dir, 'data_path': cfg.habitat.dataset.data_path}
        got['actions'] = sorted(cfg.habitat.task.actions.keys())
        got['measurements'] = sorted(cfg.habitat.task.measurements.keys())
        got['max_episode_steps'] = int(cfg.habitat.environment.max_episode_steps)
        bsim = base_cfg.habitat.simulator
        same = {
            'depth_min_max': [float(bsim.agents.main_agent.sim_sensors.depth_sensor.min_depth),
                              float(bsim.agents.main_agent.sim_sensors.depth_sensor.max_depth)],
            'forward_step_size': float(bsim.forward_step_size), 'turn_angle': float(bsim.turn_angle),
            'agent_height': float(bsim.agents.main_agent.height), 'agent_radius': float(bsim.agents.main_agent.radius),
            'dataset': {'type': base_cfg.habitat.dataset.type, 'split': base_cfg.habitat.dataset.split,
                        'scenes_dir': base_cfg.habitat.dataset.scenes_dir, 'data_path': base_cfg.habitat.dataset.data_path},
            'actions': sorted(base_cfg.habitat.task.actions.keys()),
            'measurements': sorted(base_cfg.habitat.task.measurements.keys()),
            'max_episode_steps': int(base_cfg.habitat.environment.max_episode_steps),
        }
        for k, v in same.items():
            if got[k] != v:
                problems.append(f'{k} differs from baseline: {got[k]} != {v}')
        if problems:
            raise RuntimeError('composed config mismatch: ' + '; '.join(problems))
        ENV_HOLDER['cfg'] = cfg
        return got

    def s_render():
        import numpy as np
        import quaternion  # numpy-quaternion, a habitat-sim dependency
        import habitat
        from PIL import Image
        import internnav.habitat_extensions.vln.measures  # noqa: F401
        cfg = ENV_HOLDER['cfg']
        env = habitat.Env(cfg)
        ENV_HOLDER['env'] = env
        obs = env.reset()
        ep = env.current_episode
        ds = cfg.habitat.simulator.agents.main_agent.sim_sensors.depth_sensor
        dmin, dmax = float(ds.min_depth), float(ds.max_depth)
        rgb = np.asarray(obs['rgb'])[:, :, :3]
        d = np.asarray(obs['depth']).squeeze()
        metres = d * (dmax - dmin) + dmin if bool(ds.normalize_depth) else d
        h_img, w_img = metres.shape
        c0, c1 = w_img // 2 - pf['central_columns'] // 2, w_img // 2 + pf['central_columns'] // 2
        bottom = metres[h_img - pf['bottom_rows']:, c0:c1]
        top = metres[:pf['bottom_rows'], c0:c1]
        floor_est = float(np.percentile(bottom, pf['floor_percentile']))
        top_med = float(np.median(top))
        vf = vfov_deg(hab['hfov'], w_img, h_img)
        pitch_cfg = -math.degrees(hab['orientation'][0])
        ang = pitch_cfg + vf / 2
        # Ground distance of the bottom-edge ray, d = h / tan(pitch + vfov/2): the research
        # note's figure, reported for reference only.
        ground_dist = spec['height_m'] / math.tan(math.radians(ang)) if 0 < ang < 89 else float('inf')
        # Habitat's depth sensor returns z-depth along the optical axis, not ground distance.
        # A flat floor at image row r therefore reads h / (sin(pitch) + tan(theta_r) cos(pitch)),
        # theta_r being that row's ray angle below the optical axis. Build the expectation on the
        # same rows-by-columns block and take the same percentile as the measurement. For a level
        # camera this equals d; for C1/C4 it is larger by cos(vfov/2) / cos(pitch + vfov/2).
        p_rad = math.radians(pitch_cfg)
        rows = np.arange(h_img - pf['bottom_rows'], h_img)
        tan_theta = ((rows + 0.5) - h_img / 2) / (h_img / 2) * math.tan(math.radians(vf / 2))
        denom = math.sin(p_rad) + tan_theta * math.cos(p_rad)
        if np.all(denom > 1e-6):
            z_rows = spec['height_m'] / denom
            expected = float(np.percentile(np.repeat(z_rows[:, None], c1 - c0, axis=1), pf['floor_percentile']))
        else:
            expected = float('inf')  # bottom rays never reach the floor

        st = env.sim.get_agent_state()
        sens = st.sensor_states['rgb']
        height_above_agent = float(sens.position[1] - st.position[1])
        rel = st.rotation.inverse() * sens.rotation
        fwd = quaternion.rotate_vectors(rel, np.array([0.0, 0.0, -1.0]))
        measured_pitch_down = math.degrees(math.asin(max(-1.0, min(1.0, -float(fwd[1])))))
        forward_offset = float(-(quaternion.rotate_vectors(st.rotation.inverse(),
                                                           np.asarray(sens.position) - np.asarray(st.position))[2]))

        outdir = Path(f'{REQ}/preflight')
        outdir.mkdir(parents=True, exist_ok=True)
        Image.fromarray(rgb.astype(np.uint8)).save(outdir / f'{a.cond}_start_rgb.png')
        Image.fromarray((metres * 1000.0).clip(0, 65535).astype(np.uint16)).save(outdir / f'{a.cond}_start_depth_mm.png')

        res = {
            'episode_id': ep.episode_id, 'scene_id': ep.scene_id,
            'start_position': [float(v) for v in ep.start_position],
            'rgb_shape': list(rgb.shape), 'depth_shape': list(metres.shape),
            'vfov_deg_from_hfov': round(vf, 3),
            'configured': {'height_m': spec['height_m'], 'pitch_down_deg': pitch_cfg,
                           'forward_offset_m': spec['forward_offset_m']},
            'measured_sensor_state': {'height_above_agent_m': round(height_above_agent, 4),
                                      'pitch_down_deg': round(measured_pitch_down, 3),
                                      'forward_offset_m': round(forward_offset, 4)},
            'bottom_rows_floor_zdepth_m_p90': round(floor_est, 3),
            'expected_bottom_rows_floor_zdepth_m_p90': round(expected, 3) if math.isfinite(expected) else None,
            'reference_ground_distance_m_h_over_tan': round(ground_dist, 3) if math.isfinite(ground_dist) else None,
            'top_rows_median_depth_m': round(top_med, 3),
            'rgb_png': str(outdir / f'{a.cond}_start_rgb.png'),
            'depth_png': str(outdir / f'{a.cond}_start_depth_mm.png'),
        }
        # For a flat floor at fixed pitch and rows, z-depth scales linearly with the
        # camera height above that floor, so measured / expected - 1 times the
        # configured height is the vertical gap between the agent origin (navmesh
        # point) and the rendered floor. Round 1 measured 0.158 to 0.163 m for all
        # four conditions at this start pose; the gap, not a ratio, is what is bounded.
        if math.isfinite(expected) and expected > 0:
            ratio = floor_est / expected
            implied_gap = (ratio - 1.0) * spec['height_m']
        else:
            ratio, implied_gap = None, None
        res['floor_zdepth_ratio_measured_over_expected'] = round(ratio, 4) if ratio is not None else None
        res['implied_agent_origin_to_floor_gap_m'] = round(implied_gap, 4) if implied_gap is not None else None
        res['floor_gap_bounds_m'] = pf['floor_gap_bounds_m']
        # Persist the numbers even when a check below fails (round 1 lost them).
        REPORT.setdefault('partial_details', {})['start frame renders with the specified height, pitch, and floor distance'] = res
        problems = []
        if abs(height_above_agent - spec['height_m']) > pf['height_tolerance_m']:
            problems.append(f'sensor height above agent {height_above_agent:.4f} != {spec["height_m"]}')
        if abs(measured_pitch_down - pitch_cfg) > pf['pitch_tolerance_deg']:
            problems.append(f'sensor pitch down {measured_pitch_down:.3f} != {pitch_cfg} (sign or units wrong?)')
        if abs(forward_offset - spec['forward_offset_m']) > pf['height_tolerance_m']:
            problems.append(f'sensor forward offset {forward_offset:.4f} != {spec["forward_offset_m"]}')
        if implied_gap is not None:
            lo, hi = pf['floor_gap_bounds_m']
            if not (lo <= implied_gap <= hi):
                problems.append(f'implied agent-origin-to-floor gap {implied_gap:.3f} m outside [{lo}, {hi}] m '
                                f'(floor z-depth p90 {floor_est:.3f} m vs flat-floor expectation {expected:.3f} m)')
        if problems:
            raise RuntimeError('render check failed: ' + '; '.join(problems))
        return res

    def s_tilt():
        import numpy as np
        import quaternion
        env = ENV_HOLDER['env']
        before = np.asarray(env.sim.get_sensor_observations()['rgb'])[:, :, :3].copy()

        def pitch_now():
            st = env.sim.get_agent_state()
            rel = st.rotation.inverse() * st.sensor_states['rgb'].rotation
            fwd = quaternion.rotate_vectors(rel, np.array([0.0, 0.0, -1.0]))
            return math.degrees(math.asin(max(-1.0, min(1.0, -float(fwd[1])))))

        p0 = pitch_now()
        obs = env.step({'action': 'look_down'})
        after = np.asarray(obs['rgb'])[:, :, :3]
        p1 = pitch_now()
        env.step({'action': 'look_up'})
        p2 = pitch_now()
        identical = bool(np.array_equal(before, after))
        diff = np.abs(before.astype(np.int16) - after.astype(np.int16))
        changed_fraction = float((diff.max(axis=2) > 0).mean())
        mean_abs_delta = float(diff.mean())
        res = {'tilt_angle': hab['tilt_angle'], 'pitch_before': round(p0, 3), 'pitch_after_look_down': round(p1, 3),
               'pitch_after_look_up': round(p2, 3), 'frame_identical_after_look_down': identical,
               'changed_pixel_fraction_after_look_down': round(changed_fraction, 6),
               'mean_abs_channel_delta_after_look_down': round(mean_abs_delta, 6),
               'pitch_delta_deg_after_look_down': round(p1 - p0, 6)}
        delta = p1 - p0
        if abs(delta - hab['tilt_angle']) > pf['pitch_tolerance_deg']:
            raise RuntimeError(f'look_down changed pitch by {delta:.3f}, expected {hab["tilt_angle"]}')
        # Round 2 showed that a zero-amount look_down re-normalises the sensor quaternion by
        # 1-2 ULP (pitch change 5.5e-7 deg), which flips about 0.3 percent of edge pixels while
        # the sensor position and pitch are unchanged. A bit-identical frame is therefore not
        # the right no-op criterion; bound the changed-pixel fraction and the pitch delta instead.
        if hab['tilt_angle'] == 0:
            if abs(delta) > pf['tilt_noop_max_pitch_delta_deg']:
                raise RuntimeError(f'tilt_angle 0 but look_down changed pitch by {delta:.6f} deg')
            if changed_fraction > pf['tilt_noop_max_changed_pixel_fraction']:
                raise RuntimeError(f'tilt_angle 0 but look_down changed {changed_fraction:.4%} of pixels '
                                   f'(limit {pf["tilt_noop_max_changed_pixel_fraction"]:.2%})')
        elif changed_fraction < pf['tilt_move_min_changed_pixel_fraction']:
            raise RuntimeError(f'tilt_angle non-zero but look_down changed only {changed_fraction:.4%} of pixels')
        if abs(p2 - p0) > pf['pitch_tolerance_deg']:
            raise RuntimeError('look_up did not restore the pitch')
        return res

    def s_gpu():
        # Release the preflight's own simulator first: the baseline peak sits within about
        # 2 GiB of the whole device, so its device memory must not count against the budget.
        env = ENV_HOLDER.pop('env', None)
        if env is not None:
            env.close()
        q = subprocess.run(['nvidia-smi', '--query-gpu=memory.total,memory.used,memory.free',
                            '--format=csv,noheader,nounits'], capture_output=True, text=True, check=True)
        total, used, free = [int(x.strip()) for x in q.stdout.strip().splitlines()[0].split(',')]
        apps = subprocess.run(['nvidia-smi', '--query-compute-apps=pid,process_name,used_memory',
                               '--format=csv,noheader'], capture_output=True, text=True).stdout.strip()
        rs = json.loads(Path(RUN_SUMMARY).read_text())
        mems = [r['device_memory_sampled_every_5s_MiB'] for r in rs['runs']
                if 'device_memory_sampled_every_5s_MiB' in r]
        footprint = max(m['max_used_whole_device'] - m['min_used_whole_device'] for m in mems)
        required = int(footprint)  # design rule: free >= max baseline memory.used delta
        res = {'total_MiB': total, 'used_MiB': used, 'free_MiB': free,
               'baseline_model_footprint_MiB_max_over_runs': footprint, 'required_free_MiB': required,
               'margin_MiB': free - required,
               'resident_compute_apps': apps.splitlines(), 'note': 'resident processes are recorded, never touched'}
        if free < required:
            raise RuntimeError(f'free GPU memory {free} MiB < required {required} MiB')
        return res

    try:
        stage('official env versions', s_versions)
        stage('all paths resolve from the launch directory', s_paths)
        stage('pinned inputs match baseline public_eval_v5', s_identity)
        stage('condition eval config loads with CAM_YAML', s_eval_cfg)
        stage('condition habitat config composes to the specified geometry', s_habitat_config)
        stage('start frame renders with the specified height, pitch, and floor distance', s_render)
        stage('look_down/look_up behave per tilt_angle', s_tilt)
        stage('GPU budget against the baseline footprint', s_gpu)
    finally:
        env = ENV_HOLDER.get('env')
        if env is not None:
            env.close()

    failed = [s for s in REPORT['stages'] if not s['ok']]
    REPORT['first_blocker'] = failed[0]['stage'] if failed else None
    REPORT['all_stages_passed'] = not failed
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(REPORT, indent=2, sort_keys=True) + '\n')
    for s in REPORT['stages']:
        print(('PASS  ' if s['ok'] else ('SKIP  ' if s.get('skipped') else 'FAIL  ')) + s['stage'])
    print('ALL_STAGES_PASSED' if REPORT['all_stages_passed'] else f"FIRST_BLOCKER: {REPORT['first_blocker']}")
    return 0 if REPORT['all_stages_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
