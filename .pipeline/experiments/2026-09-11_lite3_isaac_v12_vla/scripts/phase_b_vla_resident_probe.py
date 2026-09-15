"""Phase B.2, last part: GPU memory and latency of InternVLA-N1 while it shares the GPU with Isaac.

Loads the pinned InternNav real-world agent (internvla_n1_agent_realworld.InternVLAN1AsyncAgent) exactly as upstream's
http_internvla_server.py does, warms it on a real rendered RGB-D frame from a Phase B run, writes a `vla_ready` marker,
then keeps calling agent.step() until a `stop` file appears or --max-seconds elapses. Every call records torch allocator
figures and device-wide free memory, so the peak with both processes resident is measured rather than added up.

The frame only has to be a realistic tensor: this measures memory and latency, not navigation quality.
Upstream's server omits plan_step_gap (AttributeError at construction) and the intrinsic argument of its warm-up call;
both are supplied here, plan_step_gap = 4 as in upstream's inference_only_demo notebook.
"""

import argparse
import hashlib
import json
import os
import sys
import time
import traceback
from pathlib import Path

import numpy as np


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--internnav-root', type=Path, required=True)
    parser.add_argument('--model-path', type=Path, required=True)
    parser.add_argument('--depth-anything', type=Path, required=True,
                        help='depth_anything_v2_metric_hypersim_vits.pth; the model loads it from ./checkpoints/')
    parser.add_argument('--rgb', type=Path, required=True, help='HxWx3 uint8 .npy')
    parser.add_argument('--depth', type=Path, required=True, help='HxW[x1] float32 metres .npy, same camera as --rgb')
    parser.add_argument('--hfov', type=float, required=True, help='horizontal FOV of the camera that produced the frame')
    parser.add_argument('--max-seconds', type=float, default=900.0)
    parser.add_argument('--device', default='cuda:0')
    parser.add_argument('--plan-step-gap', type=int, default=4)
    parser.add_argument('--input-size', default='640x480',
                        help='centre-crop to this aspect and resize before inference; empty keeps the source frame')
    args = parser.parse_args()

    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    os.chdir(out)  # the agent writes test_data/<timestamp>/ debug images relative to the working directory
    sys.path.insert(0, str(args.internnav_root))
    # internvla_n1_arch.build_depthanythingv2 reads checkpoints/depth_anything_v2_metric_hypersim_vits.pth relative to
    # the working directory (upstream's launch-dir convention). Link that one file; the link is removed at exit so a
    # recursive copy of this run cannot follow it into model bytes.
    link = out / 'checkpoints' / 'depth_anything_v2_metric_hypersim_vits.pth'
    link.parent.mkdir(exist_ok=True)
    if not link.is_symlink():
        link.symlink_to(args.depth_anything.resolve())

    import torch

    # InternVLAN1ForCausalLM.generate_traj runs its 10-step, 64-sample diffusion loop outside no_grad, and upstream's
    # http_internvla_server.py calls agent.step with autograd on. That kept the activation graph and took System 1 from
    # ~16 GiB to 23.5 GiB (OOM, phase_b_vla_resident_v3). The DualVLN fixture probe wrapped step in no_grad; so must
    # the Phase C client.
    torch.set_grad_enabled(False)

    record = {
        'python': sys.version,
        'torch': torch.__version__,
        'pytorch_cuda_alloc_conf': os.environ.get('PYTORCH_CUDA_ALLOC_CONF'),
        'grad_enabled': torch.is_grad_enabled(),
        'identity': {
            rel: sha256(args.internnav_root / rel)
            for rel in ('internnav/agent/internvla_n1_agent_realworld.py',
                        'internnav/model/basemodel/internvla_n1/internvla_n1.py')
        },
        'depth_anything_sha256': sha256(args.depth_anything),
        'model_path': str(args.model_path),
        'frame': {'rgb': str(args.rgb), 'depth': str(args.depth), 'hfov': args.hfov},
        'plan_step_gap': args.plan_step_gap,
        'calls': [],
        'error': None,
    }

    def device_mem():
        free, total = torch.cuda.mem_get_info()
        return {
            'allocated_mib': torch.cuda.memory_allocated() / 2**20,
            'reserved_mib': torch.cuda.memory_reserved() / 2**20,
            'max_allocated_mib': torch.cuda.max_memory_allocated() / 2**20,
            'max_reserved_mib': torch.cuda.max_memory_reserved() / 2**20,
            'device_used_mib': (total - free) / 2**20,
            'device_total_mib': total / 2**20,
        }

    def flush():
        (out / 'vla_resident_probe.json').write_text(json.dumps(record, indent=2) + '\n')

    from PIL import Image

    rgb = np.load(args.rgb)
    depth = np.load(args.depth).astype(np.float32)
    if depth.ndim == 3:
        depth = depth[..., 0]
    depth = np.where(np.isfinite(depth), depth, 0.0).astype(np.float32)  # sky and beyond-clip pixels carry inf
    record['frame']['source_shape'] = list(rgb.shape)
    hfov = args.hfov
    if args.input_size:
        # The Phase C input is a 640x480 camera, as in upstream's real-world server. Resolution matters here: in
        # look_down mode the agent passes the image to System 2 without resizing (phase_b_vla_resident_v3 fed 1280x720).
        out_w, out_h = (int(v) for v in args.input_size.split('x'))
        h, w = rgb.shape[:2]
        crop_w = min(w, round(h * out_w / out_h))
        x0 = (w - crop_w) // 2
        hfov = float(np.degrees(2 * np.arctan(np.tan(np.radians(args.hfov / 2)) * crop_w / w)))
        rgb = np.asarray(Image.fromarray(rgb[:, x0:x0 + crop_w, :3]).resize((out_w, out_h), Image.BILINEAR))
        depth = np.asarray(Image.fromarray(depth[:, x0:x0 + crop_w]).resize((out_w, out_h), Image.NEAREST))
    h, w = rgb.shape[:2]
    fx = (w / 2) / np.tan(np.radians(hfov / 2))
    intrinsic = np.array([[fx, 0, w / 2, 0], [0, fx, h / 2, 0], [0, 0, 1, 0], [0, 0, 0, 1]], dtype=np.float64)
    record['frame'].update(shape=list(rgb.shape), hfov_used=hfov, fx=float(fx))
    instruction = 'Walk forward along the floor tiles and stop after a few metres.'

    try:
        from internnav.agent.internvla_n1_agent_realworld import InternVLAN1AsyncAgent

        agent_args = argparse.Namespace(device=args.device, model_path=str(args.model_path), resize_w=384, resize_h=384,
                                        num_history=8, plan_step_gap=args.plan_step_gap)
        t0 = time.time()
        agent = InternVLAN1AsyncAgent(agent_args)
        torch.cuda.synchronize()
        record['load_seconds'] = time.time() - t0
        record['after_load'] = device_mem()
        agent.reset()

        t0 = time.time()
        agent.step(rgb, depth, np.eye(4), instruction, intrinsic)
        torch.cuda.synchronize()
        record['warmup_seconds'] = time.time() - t0
        record['after_warmup'] = device_mem()
        flush()
        (out / 'vla_ready').write_text(f'{time.time()}\n')

        started = time.time()
        while not (out / 'stop').exists() and time.time() - started < args.max_seconds:
            s2_before = agent.last_s2_idx
            t0 = time.time()
            result = agent.step(rgb, depth, np.eye(4), instruction, intrinsic)
            first_action = result.output_action
            looked_down = False
            if result.output_action is not None and result.output_action == [5]:
                # As upstream http_internvla_server.py does: a "look down" answer is followed by a look_down=True
                # query, which yields a pixel goal and a latent that System 1 turns into a trajectory. Without this
                # (phase_b_vla_resident_v2) every call stayed in System 2 and System 1 never ran.
                result = agent.step(rgb, depth, np.eye(4), instruction, intrinsic, look_down=True)
                looked_down = True
            torch.cuda.synchronize()
            call = {'unix_s': t0, 'seconds': time.time() - t0, 's2': agent.last_s2_idx != s2_before or looked_down,
                    'looked_down': looked_down, 'first_action': first_action,
                    'discrete_action': result.output_action, 'has_trajectory': result.output_trajectory is not None}
            call.update(device_mem())
            record['calls'].append(call)
            if len(record['calls']) % 10 == 0:
                flush()
            if len(agent.rgb_list) > 64:  # keep the episode short so history growth does not dominate
                agent.reset()
    except BaseException as error:  # noqa: BLE001 - an OOM is a result here, not a crash to hide
        record['error'] = {'type': type(error).__name__, 'message': str(error)[:2000],
                           'traceback': traceback.format_exc()[-4000:]}
        try:
            record['at_error'] = device_mem()
        except Exception:  # noqa: BLE001
            pass

    calls = record['calls']
    if calls:
        s2 = [c['seconds'] for c in calls if c['s2']]
        s1 = [c['seconds'] for c in calls if not c['s2']]
        s1_only = [c['seconds'] for c in calls if not c['s2'] and c['has_trajectory']]
        record['summary'] = {
            'calls': len(calls),
            's2_calls': len(s2), 's2_mean_s': float(np.mean(s2)) if s2 else None,
            'non_s2_calls': len(s1), 'non_s2_mean_s': float(np.mean(s1)) if s1 else None,
            's1_only_calls': len(s1_only), 's1_only_mean_s': float(np.mean(s1_only)) if s1_only else None,
            'look_down_calls': sum(c['looked_down'] for c in calls),
            'trajectories': sum(c['has_trajectory'] for c in calls),
            'peak_device_used_mib': max(c['device_used_mib'] for c in calls),
            'peak_max_reserved_mib': max(c['max_reserved_mib'] for c in calls),
            'peak_max_allocated_mib': max(c['max_allocated_mib'] for c in calls),
        }
    flush()
    link.unlink()
    link.parent.rmdir()
    return 1 if record['error'] else 0


if __name__ == '__main__':
    sys.exit(main())
