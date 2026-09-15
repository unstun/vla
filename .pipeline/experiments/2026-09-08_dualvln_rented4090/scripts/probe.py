"""Bounded open-loop fixture probe for InternVLA-N1-DualVLN.

Replays the released real-world RGB sequence through the original
``InternVLAN1AsyncAgent`` and records verbatim instruction, input hashes, raw
S2 text, parsed actions, S1 trajectories, per-call latency and VRAM.

Depth and pose are the dummy constants used by the upstream notebook, so this
phase is explicitly OPEN-LOOP and is not a navigation result.
"""
import argparse
import glob
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
INTERNNAV = ROOT / 'work' / 'InternNav'
sys.path.insert(0, str(INTERNNAV))
sys.path.insert(0, str(INTERNNAV / 'src' / 'diffusion-policy'))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def smi_total_used_mib():
    """Total device VRAM in use, including the protected Isaac Sim process."""
    try:
        out = subprocess.run(
            ['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=20, check=True)
        return int(out.stdout.strip().splitlines()[0])
    except Exception as exc:  # pragma: no cover - diagnostic only
        return {'error': str(exc)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scene-dir', required=True)
    ap.add_argument('--model-path', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--max-frames', type=int, default=24)
    ap.add_argument('--plan-step-gap', type=int, default=4)
    ap.add_argument('--num-history', type=int, default=8)
    ap.add_argument('--seed', type=int, default=0)
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    scene = Path(args.scene_dir)
    # The released fixtures ship both spellings of the instruction file name.
    inst_path = next((scene / n for n in ('instruction.txt', 'insturction.txt')
                      if (scene / n).exists()), None)
    if inst_path is None:
        raise SystemExit(f'no instruction file in {scene}')
    instruction_raw = inst_path.read_text()
    instruction = instruction_raw.strip()

    rgb_paths = sorted(glob.glob(str(scene / 'debug_raw_*.jpg')))[:args.max_frames]
    if not rgb_paths:
        raise SystemExit(f'no debug_raw_*.jpg in {scene}')

    inputs_manifest = [{'index': i, 'path': os.path.basename(p),
                        'bytes': os.path.getsize(p), 'sha256': sha256_file(p)}
                       for i, p in enumerate(rgb_paths)]

    class Args:
        device = 'cuda:0'
        model_path = args.model_path
        resize_w = 384
        resize_h = 384
        num_history = args.num_history
        plan_step_gap = args.plan_step_gap
        # Upstream notebook intrinsic (RealSense D455 on a Unitree Go2).
        camera_intrinsic = np.array([[386.5, 0.0, 328.9, 0.0],
                                     [0.0, 386.5, 244.0, 0.0],
                                     [0.0, 0.0, 1.0, 0.0],
                                     [0.0, 0.0, 0.0, 1.0]])

    from internnav.model.basemodel.internvla_n1.internvla_n1 import InternVLAN1ForCausalLM

    record = {
        'phase': 'open_loop_fixture_probe',
        'depth_source': 'dummy_constant_10m_upstream_notebook',
        'pose_source': 'dummy_identity_upstream_notebook',
        'instruction_verbatim': instruction_raw,
        'instruction_used': instruction,
        'instruction_sha256': hashlib.sha256(instruction_raw.encode()).hexdigest(),
        'scene_dir': str(scene),
        'model_path': args.model_path,
        'seed': args.seed,
        'plan_step_gap': args.plan_step_gap,
        'num_history': args.num_history,
        'torch': torch.__version__,
        'cuda': torch.version.cuda,
        'inputs': inputs_manifest,
        'steps': [],
    }

    torch.cuda.reset_peak_memory_stats()
    smi_before = smi_total_used_mib()

    # Capture missing/unexpected key info during the agent's own single load
    # instead of paying for a second 16.9 GB read.
    captured = {}
    _orig_from_pretrained = InternVLAN1ForCausalLM.from_pretrained.__func__

    @classmethod
    def _from_pretrained_capturing(cls, *a, **kw):
        kw['output_loading_info'] = True
        model, info = _orig_from_pretrained(cls, *a, **kw)
        captured.update({k: (v if isinstance(v, list) else list(v))
                         for k, v in info.items()})
        return model

    InternVLAN1ForCausalLM.from_pretrained = _from_pretrained_capturing

    from internnav.agent.internvla_n1_agent_realworld import InternVLAN1AsyncAgent

    class RecordingAgent(InternVLAN1AsyncAgent):
        """Flags whether System 2 actually ran on this frame.

        `last_s2_idx`/`episode_idx` cannot distinguish this reliably because a
        look-down S2 call does not advance `episode_idx`.
        """
        ran_s2 = False

        def step(self, *a, **kw):
            self.ran_s2 = False
            return super().step(*a, **kw)

        def step_s2(self, *a, **kw):
            self.ran_s2 = True
            return super().step_s2(*a, **kw)

    t0 = time.time()
    agent = RecordingAgent(Args())
    record['agent_init_seconds'] = time.time() - t0
    InternVLAN1ForCausalLM.from_pretrained = classmethod(_orig_from_pretrained)
    record['checkpoint_loading_info'] = captured or {'note': 'from_pretrained shim not hit'}

    dtypes = {}
    for n, p in agent.model.named_parameters():
        dtypes[str(p.dtype)] = dtypes.get(str(p.dtype), 0) + p.numel()
    record['parameter_dtype_counts'] = dtypes
    record['parameter_total'] = sum(dtypes.values())
    record['vram_after_load'] = {
        'torch_allocated_mib': torch.cuda.memory_allocated() / 2**20,
        'torch_reserved_mib': torch.cuda.memory_reserved() / 2**20,
        'smi_total_used_mib': smi_total_used_mib(),
        'smi_total_used_mib_before_load': smi_before,
    }

    agent.reset()
    record['agent_save_dir'] = agent.save_dir

    for i, rgb_path in enumerate(rgb_paths):
        look_down = 'look_down' in rgb_path
        rgb = np.asarray(Image.open(rgb_path).convert('RGB'))
        # Upstream notebook dummies: depth is a constant 10 m plane, pose identity.
        depth = 10 * np.ones((rgb.shape[0], rgb.shape[1]), dtype=np.float32)
        pose = np.eye(4)

        torch.cuda.reset_peak_memory_stats()
        t0 = time.time()
        with torch.no_grad():
            out = agent.step(rgb, depth, pose, instruction,
                             intrinsic=Args.camera_intrinsic, look_down=look_down)
        dt = time.time() - t0

        step = {
            'index': i,
            'frame': os.path.basename(rgb_path),
            'look_down': look_down,
            'rgb_shape': list(rgb.shape),
            'seconds': dt,
            'ran_s2': agent.ran_s2,
            'llm_output_raw': agent.llm_output,
            'output_pixel': (list(map(int, out.output_pixel))
                             if out.output_pixel is not None else None),
            'output_action': (list(map(int, out.output_action))
                              if out.output_action is not None else None),
            'peak_torch_allocated_mib': torch.cuda.max_memory_allocated() / 2**20,
        }
        if out.output_trajectory is not None:
            traj = np.asarray(out.output_trajectory, dtype=np.float64)
            step['trajectory_shape'] = list(traj.shape)
            step['trajectory_finite'] = bool(np.isfinite(traj).all())
            step['trajectory_xy'] = traj.tolist()
            step['trajectory_endpoint'] = traj[-1].tolist()
            step['trajectory_path_length_m'] = float(
                np.linalg.norm(np.diff(traj, axis=0), axis=1).sum())
        record['steps'].append(step)
        print(json.dumps({'step': i, 'frame': step['frame'],
                          'seconds': round(dt, 3),
                          'llm': step['llm_output_raw'][:120],
                          'pixel': step['output_pixel'],
                          'action': step['output_action'],
                          'traj_end': step.get('trajectory_endpoint')}), flush=True)

    record['vram_peak'] = {
        'torch_max_allocated_mib': torch.cuda.max_memory_allocated() / 2**20,
        'torch_max_reserved_mib': torch.cuda.max_memory_reserved() / 2**20,
        'smi_total_used_mib': smi_total_used_mib(),
    }
    s2 = [s['seconds'] for s in record['steps'] if s['ran_s2']]
    s1 = [s['seconds'] for s in record['steps'] if not s['ran_s2']]
    record['latency'] = {
        's2_calls': len(s2), 's2_mean_s': float(np.mean(s2)) if s2 else None,
        's2_max_s': float(np.max(s2)) if s2 else None,
        's1_calls': len(s1), 's1_mean_s': float(np.mean(s1)) if s1 else None,
        's1_max_s': float(np.max(s1)) if s1 else None,
    }
    (out_dir / 'probe_record.json').write_text(json.dumps(record, indent=2) + '\n')
    print('PROBE_COMPLETE', flush=True)


if __name__ == '__main__':
    main()
