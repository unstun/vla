"""Closed-loop InternVLA-N1-DualVLN episode in headless Habitat-Sim.

The model (Torch/CUDA, Python 3.10 venv) runs here; Habitat-Sim runs in a
separate Python 3.9 process (`scripts/sim_worker.py`) and is driven over a
sentinel-tagged JSON line protocol. Observations are real rendered RGB-D.

Control semantics follow the upstream Habitat evaluator
(`internnav/habitat_extensions/vln/habitat_vln_evaluator.py`):
  * S2 text output containing digits -> pixel goal -> S1 diffusion trajectory
    -> `traj_to_actions` -> 0.25 m forward / 15 deg turn discrete actions.
  * S2 text output without digits -> parsed arrow/STOP action sequence, drained
    one action per frame; STOP here is a *learned stop* and ends the episode.
  * A STOP appearing inside an S1 action list is NOT a learned stop upstream:
    it invalidates the current pixel goal and forces a re-plan.
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
INTERNNAV = ROOT / 'work' / 'InternNav'
sys.path.insert(0, str(INTERNNAV))
sys.path.insert(0, str(INTERNNAV / 'src' / 'diffusion-policy'))

SENTINEL = '@@SIMJSON@@'
STOP, FORWARD, LEFT, RIGHT, LOOKUP, LOOKDOWN = 0, 1, 2, 3, 4, 5
ACTION_NAME = {STOP: 'stop', FORWARD: 'move_forward', LEFT: 'turn_left',
               RIGHT: 'turn_right', LOOKUP: 'look_up', LOOKDOWN: 'look_down'}
MAX_STEPS = 8          # upstream pad length for an S1 action list
MAX_LOCAL_STEPS = 4    # upstream truncation of an S1 action list


class SimClient:
    def __init__(self, cmd, log_path):
        self.log = open(log_path, 'wb')
        self.p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=self.log, cwd=str(ROOT), text=True, bufsize=1)
        first = self.read()
        assert first.get('event') == 'ready', first

    def read(self):
        for line in self.p.stdout:
            if line.startswith(SENTINEL):
                return json.loads(line[len(SENTINEL):])
        raise RuntimeError('sim worker closed stdout unexpectedly')

    def call(self, **req):
        self.p.stdin.write(json.dumps(req) + '\n')
        self.p.stdin.flush()
        r = self.read()
        if not r.get('ok'):
            raise RuntimeError('sim worker error: %s' % r)
        return r

    def close(self):
        try:
            self.call(cmd='close')
        except Exception:
            pass
        self.p.terminate()
        self.log.close()


def load_obs(reply, max_depth_for_model, exposure_target=0.0, exposure_max_gain=4.0):
    """Load one rendered observation.

    ``exposure_target`` emulates the auto-exposure of a real RGB-D camera. The
    habitat_test_scenes GLB has dark baked lighting (mean luma ~40) while the
    released real-world fixtures this checkpoint was demonstrated on sit near
    ~119, so the raw render is far out of distribution. The gain is applied to
    the MODEL INPUT ONLY; the PNG written by the sim worker stays untouched.
    """
    rgb = np.asarray(Image.open(reply['rgb_path']).convert('RGB'), dtype=np.uint8)
    gain = 1.0
    if exposure_target > 0:
        luma = float((0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1]
                      + 0.114 * rgb[:, :, 2]).mean())
        if luma > 1e-3:
            gain = float(min(max(exposure_target / luma, 1.0), exposure_max_gain))
            rgb = np.clip(rgb.astype(np.float32) * gain, 0, 255).astype(np.uint8)
    depth_mm = np.asarray(Image.open(reply['depth_path']), dtype=np.uint16)
    depth_m = depth_mm.astype(np.float32) / 1000.0
    # Upstream Habitat evaluator clamps the S1 depth input at 5 m.
    depth_m = np.clip(depth_m, 0.0, max_depth_for_model)
    return rgb, depth_m, gain


def pose_matrix(position, yaw):
    c, s = np.cos(yaw), np.sin(yaw)
    T = np.eye(4)
    T[:3, :3] = np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])
    T[:3, 3] = np.asarray(position, dtype=np.float64)
    return T


def smi():
    try:
        out = subprocess.run(['nvidia-smi', '--query-gpu=memory.used,memory.total',
                              '--format=csv,noheader,nounits'],
                             capture_output=True, text=True, timeout=20, check=True)
        used, total = out.stdout.strip().splitlines()[0].split(',')
        return {'used_mib': int(used), 'total_mib': int(total)}
    except Exception as exc:
        return {'error': str(exc)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--episode', required=True, help='frozen episode spec JSON')
    ap.add_argument('--model-path', required=True)
    ap.add_argument('--sim-python', default='sim_env/bin/python')
    ap.add_argument('--out', required=True)
    ap.add_argument('--max-steps', type=int, default=200)
    ap.add_argument('--max-seconds', type=float, default=1700.0)
    ap.add_argument('--seed', type=int, default=0)
    a = ap.parse_args()

    spec = json.loads(Path(a.episode).read_text())
    out_dir = Path(a.out)
    (out_dir / 'obs').mkdir(parents=True, exist_ok=True)
    torch.manual_seed(a.seed)
    np.random.seed(a.seed)

    from internnav.model.utils.vln_utils import traj_to_actions
    from internnav.agent.internvla_n1_agent_realworld import InternVLAN1AsyncAgent

    class RecordingAgent(InternVLAN1AsyncAgent):
        """Keeps the raw (un-normalised) S1 output so it can be converted twice.

        ``traj_to_actions`` divides ``dp_actions[:, :, :2]`` by 4 IN PLACE, so the
        tensor the base agent hands to it is already consumed. Clone before it.
        """
        last_raw_traj = None
        ran_s2 = False

        def step(self, *a, **kw):
            self.ran_s2 = False
            return super().step(*a, **kw)

        def step_s2(self, *a, **kw):
            self.ran_s2 = True
            return super().step_s2(*a, **kw)

        def step_s1(self, latent, rgb, depth):
            trajs = super().step_s1(latent, rgb, depth)
            self.last_raw_traj = trajs.detach().clone()
            return trajs

    class Args:
        device = 'cuda:0'
        model_path = a.model_path
        resize_w = 384
        resize_h = 384
        num_history = 8
        plan_step_gap = spec.get('plan_step_gap', 4)
        camera_intrinsic = np.asarray(spec['intrinsic'], dtype=np.float64)

    sim = SimClient([a.sim_python, 'scripts/sim_worker.py',
                     '--scene', spec['scene'], '--navmesh', spec['navmesh'],
                     '--out', str(out_dir / 'obs'),
                     '--width', str(spec['width']), '--height', str(spec['height']),
                     '--hfov', str(spec['hfov']),
                     '--sensor-height', str(spec['sensor_height']),
                     '--forward', str(spec['forward_step']),
                     '--turn', str(spec['turn_angle']), '--tilt', str(spec['tilt_angle']),
                     '--max-depth', str(spec['sim_max_depth']),
                     '--lighting', spec.get('lighting', 'scene'),
                     '--seed', str(a.seed)],
                    out_dir / 'sim_worker.log')

    info = sim.call(cmd='info')
    smi_before = smi()
    torch.cuda.reset_peak_memory_stats()
    t_load = time.time()
    agent = RecordingAgent(Args())
    load_seconds = time.time() - t_load
    vram_after_load = {'torch_allocated_mib': torch.cuda.memory_allocated() / 2**20,
                       'torch_reserved_mib': torch.cuda.memory_reserved() / 2**20,
                       'smi': smi()}
    agent.reset()

    exposure_target = float(spec.get('exposure_target_luma', 0.0))
    instruction = spec['instruction']
    target = spec['target']
    start_pos, start_yaw = spec['start_position'], spec['start_yaw_rad']

    obs = sim.call(cmd='reset', position=start_pos, yaw_rad=start_yaw, tag='ep')
    geo_start = sim.call(cmd='geodesic', **{'from': start_pos, 'to': target})['geodesic']

    record = {
        'phase': 'closed_loop_habitat_episode',
        'episode_spec': spec,
        'sim_info': info,
        'geodesic_start_m': geo_start,
        'model_load_seconds': load_seconds,
        'vram_before_model_load': smi_before,
        'vram_after_model_load': vram_after_load,
        'seed': a.seed,
        'caps': {'max_steps': a.max_steps, 'max_seconds': a.max_seconds},
        'exposure_target_luma': exposure_target,
        'steps': [],
    }

    pending = []           # drained S2 text action sequence
    pending_source = None
    termination = 'step_cap'
    t_episode = time.time()
    frames = []

    for step_id in range(a.max_steps):
        if time.time() - t_episode > a.max_seconds:
            termination = 'wall_clock_cap'
            break

        rgb, depth, gain = load_obs(obs, spec['model_max_depth'], exposure_target)
        pose = pose_matrix(obs['position'], obs['yaw_rad'])
        entry = {'step': step_id, 'uid': obs['uid'],
                 'rgb_path': obs['rgb_path'], 'depth_path': obs['depth_path'],
                 'position': obs['position'], 'yaw_rad': obs['yaw_rad'],
                 'collided_on_entry': obs['collided'],
                 'depth_valid_fraction': obs['depth_valid_fraction'],
                 'depth_max_m_raw_sim': obs['depth_max_m'],
                 'exposure_gain_applied_to_model_input': gain}

        torch.cuda.reset_peak_memory_stats()
        t0 = time.time()
        if pending:
            # Draining an S2 text action sequence: keep history in sync without
            # inference, exactly like the base agent's non-inference branch.
            agent.step_no_infer(rgb, depth, pose)
            entry['inference'] = 'none_draining_queue'
            proposed = list(pending)
        else:
            with torch.no_grad():
                out = agent.step(rgb, depth, pose, instruction,
                                 intrinsic=Args.camera_intrinsic, look_down=False)
            entry['inference'] = 's2' if agent.ran_s2 else 's1'
            entry['llm_output_raw'] = agent.llm_output
            entry['output_pixel'] = (list(map(int, out.output_pixel))
                                     if out.output_pixel is not None else None)
            if out.output_action:
                pending = list(map(int, out.output_action))
                pending_source = 's2_text'
                proposed = list(pending)
                entry['s2_action_sequence'] = proposed
            elif out.output_trajectory is not None:
                raw = agent.last_raw_traj.clone()
                acts = [int(x) for x in traj_to_actions(raw, use_discrate_action=True)]
                if len(acts) < MAX_STEPS:
                    acts = acts + [STOP] * (MAX_STEPS - len(acts))
                traj = np.asarray(out.output_trajectory, dtype=np.float64)
                entry['s1_trajectory_xy'] = traj.tolist()
                entry['s1_trajectory_finite'] = bool(np.isfinite(traj).all())
                entry['s1_path_length_m'] = float(
                    np.linalg.norm(np.diff(traj, axis=0), axis=1).sum())
                entry['s1_proposed_actions_full'] = acts
                pending = acts[:MAX_LOCAL_STEPS]
                pending_source = 's1_traj'
                proposed = list(pending)
            else:
                pending = [STOP]
                pending_source = 'empty'
                proposed = [STOP]
        entry['inference_seconds'] = time.time() - t0
        entry['peak_torch_allocated_mib'] = torch.cuda.max_memory_allocated() / 2**20
        entry['proposed_actions'] = proposed
        entry['pending_source'] = pending_source

        action = pending.pop(0)
        entry['action_from_model'] = action

        # A STOP inside an S1 action list is a re-plan trigger upstream, not a
        # learned stop; substitute a turn and force System-2 on the next frame.
        if action == STOP and pending_source == 's1_traj':
            entry['s1_stop_replan'] = True
            action = LEFT
            pending = []
            agent.last_s2_idx = -100
        elif action == STOP:
            entry['applied_action'] = 'stop'
            entry['learned_stop'] = True
            record['steps'].append(entry)
            termination = 'learned_stop'
            break

        if action == LOOKDOWN:
            # Real camera change: tilt down 2 x tilt_angle, re-query, tilt back.
            sim.call(cmd='step', action='look_down', tag='ep')
            down = sim.call(cmd='step', action='look_down', tag='ep')
            rgb_d, depth_d, gain_d = load_obs(down, spec['model_max_depth'], exposure_target)
            t0 = time.time()
            with torch.no_grad():
                out = agent.step(rgb_d, depth_d, pose_matrix(down['position'], down['yaw_rad']),
                                 instruction, intrinsic=Args.camera_intrinsic, look_down=True)
            entry['look_down_seconds'] = time.time() - t0
            entry['look_down_llm_output_raw'] = agent.llm_output
            entry['look_down_rgb_path'] = down['rgb_path']
            entry['look_down_exposure_gain'] = gain_d
            entry['look_down_output_pixel'] = (list(map(int, out.output_pixel))
                                               if out.output_pixel is not None else None)
            sim.call(cmd='step', action='look_up', tag='ep')
            obs = sim.call(cmd='step', action='look_up', tag='ep')
            entry['applied_action'] = 'look_down_excursion'
            if out.output_action:
                pending = list(map(int, out.output_action))
                pending_source = 's2_text'
            elif out.output_trajectory is not None:
                raw = agent.last_raw_traj.clone()
                acts = [int(x) for x in traj_to_actions(raw, use_discrate_action=True)]
                pending = acts[:MAX_LOCAL_STEPS]
                pending_source = 's1_traj'
        else:
            obs = sim.call(cmd='step', action=ACTION_NAME[action], tag='ep')
            entry['applied_action'] = ACTION_NAME[action]
            entry['collided'] = obs['collided']

        entry['position_after'] = obs['position']
        entry['yaw_rad_after'] = obs['yaw_rad']
        entry['geodesic_to_target_m'] = sim.call(
            cmd='geodesic', **{'from': obs['position'], 'to': target})['geodesic']
        frames.append({'rgb_path': entry['rgb_path'], 'step': step_id,
                       'action': entry.get('applied_action'),
                       'llm': entry.get('llm_output_raw', ''),
                       'pixel': entry.get('output_pixel'),
                       'traj': entry.get('s1_trajectory_xy'),
                       'geo': entry['geodesic_to_target_m'],
                       'collided': entry.get('collided', False)})
        record['steps'].append(entry)
        print(json.dumps({'step': step_id, 'inf': entry['inference'],
                          'act': entry.get('applied_action'),
                          'geo': round(entry['geodesic_to_target_m'], 3)
                          if entry['geodesic_to_target_m'] else None,
                          'sec': round(entry['inference_seconds'], 2),
                          'llm': (entry.get('llm_output_raw') or '')[:80]}), flush=True)

    final_pos = obs['position']
    geo_end = sim.call(cmd='geodesic', **{'from': final_pos, 'to': target})['geodesic']
    record['termination'] = termination
    record['final_position'] = final_pos
    record['geodesic_end_m'] = geo_end
    record['navigation_error_m'] = geo_end
    record['success_threshold_m'] = spec['success_distance']
    # Distance test only. Upstream habitat VLN Success also requires the agent
    # to have called STOP itself -- see scripts/analyze_episode.py.
    record['success_final_distance_only'] = bool(
        geo_end is not None and geo_end < spec['success_distance'])
    record['learned_stop_emitted'] = (termination == 'learned_stop')
    record['success_upstream_stop_based'] = bool(
        record['success_final_distance_only'] and record['learned_stop_emitted'])
    record['success'] = record['success_upstream_stop_based']
    record['collisions'] = sum(1 for s in record['steps'] if s.get('collided'))
    record['applied_action_counts'] = {}
    for s in record['steps']:
        k = s.get('applied_action', 'none')
        record['applied_action_counts'][k] = record['applied_action_counts'].get(k, 0) + 1
    record['episode_seconds'] = time.time() - t_episode
    record['vram_peak'] = {'torch_max_allocated_mib': torch.cuda.max_memory_allocated() / 2**20,
                           'torch_max_reserved_mib': torch.cuda.max_memory_reserved() / 2**20,
                           'smi': smi()}
    s2 = [s['inference_seconds'] for s in record['steps'] if s.get('inference') == 's2']
    s1 = [s['inference_seconds'] for s in record['steps'] if s.get('inference') == 's1']
    record['latency'] = {
        's2_calls': len(s2), 's2_mean_s': float(np.mean(s2)) if s2 else None,
        's2_max_s': float(np.max(s2)) if s2 else None,
        's1_calls': len(s1), 's1_mean_s': float(np.mean(s1)) if s1 else None,
        's1_max_s': float(np.max(s1)) if s1 else None}

    (out_dir / 'episode_record.json').write_text(json.dumps(record, indent=2) + '\n')
    (out_dir / 'frames_index.json').write_text(json.dumps(frames, indent=2) + '\n')
    sim.close()
    print('EPISODE_COMPLETE ' + json.dumps({
        'termination': termination, 'steps': len(record['steps']),
        'geodesic_start_m': geo_start, 'geodesic_end_m': geo_end,
        'success': record['success'], 'collisions': record['collisions']}), flush=True)


if __name__ == '__main__':
    main()
