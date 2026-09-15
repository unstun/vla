#!/usr/bin/env python3
"""Phase B: attach a robot-mounted RTX camera to the V12 Lite3 and measure what rendering costs.

The pinned adapter has no robot-mounted colour camera: its only on-robot sensor is a ray-cast depth
camera, and every RGB path is a third-person chase view used for video. This script adds the missing
camera WITHOUT editing the pinned bytes - it imports `run_isaac_v12_fallback` as a library, reuses its
own `_configure_environment` so the scene is the one Phase A measured, and only then inserts cameras.

    --config none        no RTX camera at all; the honest baseline (enable_cameras stays False)
    --config single_640  one 640x480 HFOV 79 camera at the head pose, level (design.md Decision 3, step 1)
    --config dual_720    the real two-mount rig: head 1280x720 HFOV 105 at +16.7 deg up, plus a D435i
                         1280x720 HFOV 69 colour + aligned depth at 20 deg down (step 2)

Inference only. No training, no optimiser, no checkpoint write.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import statistics
import subprocess
import sys
import time

# ---------------------------------------------------------------------------------------------
# Geometry helpers. Everything here is asserted against the rendered axes below, never trusted.
# ---------------------------------------------------------------------------------------------

def _matrix_to_quat_wxyz(R):
    """Rotation matrix -> (w, x, y, z). Only used for the well-conditioned camera rotations here."""
    trace = R[0][0] + R[1][1] + R[2][2]
    w = math.sqrt(max(0.0, 1.0 + trace)) / 2.0
    if w < 1e-6:
        raise ValueError('degenerate rotation for this simple conversion')
    x = (R[2][1] - R[1][2]) / (4.0 * w)
    y = (R[0][2] - R[2][0]) / (4.0 * w)
    z = (R[1][0] - R[0][1]) / (4.0 * w)
    return (w, x, y, z)


def _matmul(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def camera_rotation(pitch_up_deg: float):
    """ROS optical-frame quaternion for a camera on a body frame that is x-forward, y-left, z-up.

    Positive pitch_up_deg tilts the optical axis UP. Returns (quat_wxyz, forward_axis_in_body).
    """
    # Level: optical X(right) = body -Y, optical Y(down) = body -Z, optical Z(forward) = body +X.
    level = [[0.0, 0.0, 1.0],
             [-1.0, 0.0, 0.0],
             [0.0, -1.0, 0.0]]
    phi = math.radians(-pitch_up_deg)          # right-hand rule about body +Y sends +X toward -Z
    pitch = [[math.cos(phi), 0.0, math.sin(phi)],
             [0.0, 1.0, 0.0],
             [-math.sin(phi), 0.0, math.cos(phi)]]
    R = _matmul(pitch, level)
    forward = (R[0][2], R[1][2], R[2][2])      # third column is the optical Z axis, in body coords
    expected_z = math.sin(math.radians(pitch_up_deg))
    if abs(forward[2] - expected_z) > 1e-9 or forward[0] < 0.0:
        raise AssertionError(f'camera rotation is wrong: forward={forward} for pitch_up={pitch_up_deg}')
    return _matrix_to_quat_wxyz(R), forward


def focal_for_hfov(hfov_deg: float, horizontal_aperture_mm: float = 20.955) -> float:
    """Isaac's pinhole takes focal length and aperture in mm, not a field of view."""
    return horizontal_aperture_mm / (2.0 * math.tan(math.radians(hfov_deg) / 2.0))


# Head-camera pose relative to the Lite3 TORSO frame. The ablation measured the head camera at roughly
# 0.40 m above ground and 0.27 m forward; the V12 torso sits near 0.31 m, so +0.09 m in the body frame.
HEAD_POS = (0.27, 0.0, 0.09)
# The D435i mount, taken from the adapter's own default --sensor-translation.
D435I_POS = (0.182399336, 0.0, 0.108541081)

CAMERA_SETS = {
    'none': [],
    'single_640': [
        dict(name='head_eval', width=640, height=480, hfov=79.0, pitch_up=0.0,
             pos=HEAD_POS, data_types=['rgb']),
    ],
    'dual_720': [
        dict(name='head_wide', width=1280, height=720, hfov=105.0, pitch_up=16.7,
             pos=HEAD_POS, data_types=['rgb']),
        dict(name='d435i', width=1280, height=720, hfov=69.0, pitch_up=-20.0,
             pos=D435I_POS, data_types=['rgb', 'distance_to_image_plane']),
    ],
}


def gpu_used_mib() -> float:
    out = subprocess.run(['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'],
                         capture_output=True, text=True, check=True)
    return float(out.stdout.strip().splitlines()[0])


# PhysX GPU buffers are preallocated. The V12 Lite3 task config (robot_lab/tasks/lite3/env_cfg.py:497-498) sets a
# 512 MiB collision stack and a 1M patch count, and Isaac Lab defaults to 2**23 rigid contacts (a 640 MiB contact-pair
# tensor): sized for thousands of training robots. With InternVLA-N1 resident those exact allocations failed
# (phase_b_vla_resident_v2_isaac). One robot on flat ground needs a few hundred contacts; one_env is still ~100x that.
PHYSX_BUFFER_PRESETS = {
    'v12': {},
    'one_env': {
        'gpu_collision_stack_size': 2**26,
        'gpu_max_rigid_contact_count': 2**16,
        'gpu_max_rigid_patch_count': 2**15,
        'gpu_found_lost_pairs_capacity': 2**16,
        'gpu_found_lost_aggregate_pairs_capacity': 2**16,
        'gpu_total_aggregate_pairs_capacity': 2**16,
        'gpu_max_soft_body_contacts': 2**10,
        'gpu_max_particle_contacts': 2**10,
    },
}
PHYSX_GPU_FIELDS = ('gpu_collision_stack_size', 'gpu_max_rigid_contact_count', 'gpu_max_rigid_patch_count',
                    'gpu_found_lost_pairs_capacity', 'gpu_found_lost_aggregate_pairs_capacity',
                    'gpu_total_aggregate_pairs_capacity', 'gpu_heap_capacity', 'gpu_temp_buffer_capacity',
                    'gpu_max_soft_body_contacts', 'gpu_max_particle_contacts')


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=pathlib.Path, required=True)
    parser.add_argument('--checkpoint', type=pathlib.Path, required=True)
    parser.add_argument('--vendored-rsl-rl', type=pathlib.Path, required=True)
    parser.add_argument('--config', choices=sorted(CAMERA_SETS), default='single_640')
    parser.add_argument('--steps', type=int, default=200, help='timed policy steps (50 Hz)')
    parser.add_argument('--warmup-steps', type=int, default=50)
    parser.add_argument('--camera-hz', type=float, default=0.0,
                        help='0 renders every policy step (worst case); 5 matches the expected VLA rate')
    parser.add_argument('--device', default='cuda:0')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--physx-buffers', choices=sorted(PHYSX_BUFFER_PRESETS), default='v12',
                        help='v12 keeps the task config (sized for training); one_env sizes GPU buffers for one robot')
    parser.add_argument('--rendering-mode', choices=['default', 'performance', 'balanced', 'quality'],
                        default='default')
    args = parser.parse_args(argv)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    cameras = CAMERA_SETS[args.config]
    want_cameras = bool(cameras)

    from lite3_sim_bridge import run_isaac_v12_fallback as v12

    v12._activate_vendored_rsl_rl(args.vendored_rsl_rl)

    from isaaclab.app import AppLauncher
    launcher = AppLauncher(headless=True, enable_cameras=want_cameras, device=args.device)
    simulation_app = launcher.app

    import gymnasium as gym                                         # noqa: E402
    import numpy as np                                              # noqa: E402
    import torch                                                    # noqa: E402
    from isaaclab.sensors import CameraCfg                          # noqa: E402
    import isaaclab.sim as sim_utils                                # noqa: E402
    from isaaclab_tasks.utils.parse_cfg import load_cfg_from_registry  # noqa: E402
    from isaaclab_rl.rsl_rl import RslRlVecEnvWrapper               # noqa: E402

    __import__('robot_lab.tasks')

    # Reuse the adapter's OWN scene composition, so any render cost we measure is a delta against the
    # exact environment Phase A ran in rather than against a scene of our own invention.
    v12_args = v12._parser().parse_args([
        '--mode', 'qualification',
        '--course', 'flat',
        '--output-dir', str(args.output_dir),
        '--checkpoint', str(args.checkpoint),
        '--vendored-rsl-rl', str(args.vendored_rsl_rl),
        '--device', args.device,
        '--seed', str(args.seed),
    ])
    v12_args.mid360_pattern_table = None

    env_cfg = load_cfg_from_registry(v12_args.task, 'env_cfg_entry_point')
    agent_cfg = load_cfg_from_registry(v12_args.task, 'rsl_rl_cfg_entry_point')
    v12._configure_environment(env_cfg, v12_args)
    agent_cfg.seed = args.seed
    agent_cfg.device = args.device
    for field, value in PHYSX_BUFFER_PRESETS[args.physx_buffers].items():
        setattr(env_cfg.sim.physx, field, value)
    physx_record = {field: getattr(env_cfg.sim.physx, field, None) for field in PHYSX_GPU_FIELDS}
    if args.rendering_mode != 'default':
        env_cfg.sim.render.rendering_mode = args.rendering_mode

    camera_record = []
    for spec in cameras:
        quat, forward = camera_rotation(spec['pitch_up'])
        focal = focal_for_hfov(spec['hfov'])
        cfg = CameraCfg(
            prim_path='{ENV_REGEX_NS}/Robot/TORSO/' + spec['name'],
            update_period=0.0 if args.camera_hz <= 0 else 1.0 / args.camera_hz,
            height=spec['height'],
            width=spec['width'],
            data_types=list(spec['data_types']),
            spawn=sim_utils.PinholeCameraCfg(
                focal_length=focal, horizontal_aperture=20.955,
                clipping_range=(0.05, 30.0),
            ),
            offset=CameraCfg.OffsetCfg(pos=spec['pos'], rot=quat, convention='ros'),
        )
        setattr(env_cfg.scene, spec['name'], cfg)
        camera_record.append({**spec, 'focal_length_mm': focal, 'quat_wxyz': quat,
                              'optical_forward_in_body': forward})

    raw_env = gym.make(v12_args.task, cfg=env_cfg)
    base_env = raw_env.unwrapped
    wrapped_env = RslRlVecEnvWrapper(raw_env, clip_actions=agent_cfg.clip_actions)
    policy, _, observation, _ = v12._load_inference_policy(
        wrapped_env, agent_cfg, v12_args.checkpoint, agent_cfg.device)

    command_term = base_env.command_manager.get_term('base_velocity')
    step_dt = float(base_env.step_dt)
    robot = base_env.scene['robot']
    locomotion = {'resets': 0, 'root_height': [], 'vx_body': []}

    def drive(n, record=False):
        nonlocal observation
        for _ in range(n):
            command_term.commands[:, 0] = 0.3
            command_term.commands[:, 1] = 0.0
            command_term.commands[:, 2] = 0.0
            with torch.inference_mode():
                actions = policy(observation)
            observation, _, dones, _ = wrapped_env.step(actions)
            if record:
                # Shrunken PhysX buffers drop contacts silently; a robot that sinks, stalls or resets shows it.
                locomotion['resets'] += int(dones.sum().item())
                locomotion['root_height'].append(float(robot.data.root_pos_w[0, 2]))
                locomotion['vx_body'].append(float(robot.data.root_lin_vel_b[0, 0]))

    gpu_before = gpu_used_mib()
    drive(args.warmup_steps)          # shaders, Warp kernels and CUDA graphs all compile on first use
    torch.cuda.reset_peak_memory_stats()
    gpu_after_warmup = gpu_used_mib()

    step_times, sensor_times = [], []
    for index in range(args.steps):
        started = time.perf_counter()
        drive(1, record=True)
        step_times.append(time.perf_counter() - started)
        if cameras:
            started = time.perf_counter()
            for spec in cameras:
                sensor = base_env.scene[spec['name']]
                for data_type in spec['data_types']:
                    _ = sensor.data.output[data_type]
            sensor_times.append(time.perf_counter() - started)

    frames = {}
    for spec in cameras:
        sensor = base_env.scene[spec['name']]
        for data_type in spec['data_types']:
            tensor = sensor.data.output[data_type][0]
            array = tensor.detach().cpu().numpy()
            path = args.output_dir / f"frame_{spec['name']}_{data_type}.npy"
            np.save(path, array)
            frames[f"{spec['name']}/{data_type}"] = {
                'file': path.name, 'shape': list(array.shape), 'dtype': str(array.dtype),
                'finite_fraction': float(np.isfinite(array).mean()),
                'mean': float(np.nanmean(array.astype('float64'))),
                'std': float(np.nanstd(array.astype('float64'))),
            }
            if data_type == 'rgb':
                try:
                    from PIL import Image
                    Image.fromarray(array[..., :3].astype('uint8')).save(
                        args.output_dir / f"frame_{spec['name']}.png")
                    frames[f"{spec['name']}/{data_type}"]['png'] = f"frame_{spec['name']}.png"
                except Exception as error:               # noqa: BLE001 - a missing PIL is not a failure
                    frames[f"{spec['name']}/{data_type}"]['png_error'] = str(error)

    total = sum(step_times)
    result = {
        'config': args.config,
        'camera_hz': args.camera_hz if args.camera_hz > 0 else 1.0 / step_dt,
        'enable_cameras': want_cameras,
        'physx_buffers': args.physx_buffers,
        'physx_gpu_cfg': physx_record,
        'rendering_mode': args.rendering_mode,
        'locomotion': {
            'resets': locomotion['resets'],
            'root_height_min': min(locomotion['root_height']),
            'root_height_mean': statistics.mean(locomotion['root_height']),
            'vx_body_mean_last_100': statistics.mean(locomotion['vx_body'][-100:]),
            'commanded_vx': 0.3,
        },
        'cameras': camera_record,
        'timed_steps': args.steps,
        'warmup_steps': args.warmup_steps,
        'step_dt_s': step_dt,
        'physics_hz': 1.0 / float(base_env.physics_dt),
        'policy_hz': 1.0 / step_dt,
        'wall_seconds': total,
        'sim_seconds': args.steps * step_dt,
        'real_time_factor': (args.steps * step_dt) / total,
        'step_ms': {
            'mean': 1000 * statistics.mean(step_times),
            'median': 1000 * statistics.median(step_times),
            'p95': 1000 * sorted(step_times)[int(0.95 * len(step_times)) - 1],
            'max': 1000 * max(step_times),
        },
        'sensor_read_ms': ({
            'mean': 1000 * statistics.mean(sensor_times),
            'median': 1000 * statistics.median(sensor_times),
        } if sensor_times else None),
        'gpu_mib': {
            'before_warmup': gpu_before,
            'after_warmup': gpu_after_warmup,
            'after_timing': gpu_used_mib(),
            'torch_peak_allocated_mib': torch.cuda.max_memory_allocated() / (1024 ** 2),
        },
        'frames': frames,
    }
    (args.output_dir / 'camera_probe.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))

    # Close the environment before the app, as the adapter does (run_isaac_v12_fallback.py:5594-5597).
    # Without it SimulationApp.close() hung until the wall limit in phase_b_none_v2.
    wrapped_env.close()
    simulation_app.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
