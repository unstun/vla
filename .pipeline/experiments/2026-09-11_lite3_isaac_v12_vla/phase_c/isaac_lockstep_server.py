"""Phase C, Isaac side: the V12 Lite3 on the flat course with landmarks, advanced only when the VLA client asks.

Runs inside the e01-walking-isaaclab container (Isaac Sim Python 3.11). Composition, all without editing pinned code:

- scene: the pinned adapter's own `_configure_environment` on the flat course (as the Phase B probe), one-robot PhysX
  GPU buffers (Phase B F1), a robot-mounted head RTX camera with aligned depth, a chase camera for video, and coloured
  landmark boxes placed like the adapter's `single_box` course;
- commands: every CMD_VEL_V1 goes through the bridge's `LatestCommandState` (clamp, sequence and freshness checks,
  250 ms watchdog) driven by the simulated clock, then into `command_manager` 'base_velocity' like Phase A;
- contact: the bridge's `SubstepContactMonitor` samples every physics substep and latches a case failure on a non-foot
  contact at the adapter's collision threshold;
- wire: `lockstep_protocol` (the pinned protocol plus IMAGE_FRAME_V1 and STEP_REQUEST_V1).

One request = one command + a duration; the reply is STATUS_V1, BODY_STATE_V2 and optionally IMAGE_FRAME_V1.

Phase D.0c (`--lidar-cloud`, off by default so Phase C behaviour is unchanged): the pinned adapter's own 360-degree
`navigation_lidar` (MultiMeshRayCaster, MID-360-like pattern) also ray-casts the landmark boxes, and every reply ends with
a SENSOR_FRAME_V1 built exactly as the adapter builds it (`world_hits_to_sensor_points`, floor filter, `pack_xyz_points`).

Phase D.0f (`--fusion-config`, off by default): the stock head camera and the D435i are also rendered, and IMAGE_FRAME_V1
carries their fusion by the camera ablation's unmodified `fused_camera.py` (via `phase_d/isaac_fusion.py`) in place of
the ideal head_eval render. Depth stays the ideal head_eval depth, as in the Habitat c8 condition. Every fused frame is
logged against the ideal render in `fusion_frames.jsonl`.
"""

import argparse
import json
import math
import pathlib
import socket
import sys
import time
import traceback

HERE = pathlib.Path(__file__).resolve().parent


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--episode', type=pathlib.Path, required=True)
    parser.add_argument('--output-dir', type=pathlib.Path, required=True)
    parser.add_argument('--checkpoint', type=pathlib.Path, required=True)
    parser.add_argument('--vendored-rsl-rl', type=pathlib.Path, required=True)
    parser.add_argument('--tools-dir', type=pathlib.Path, required=True, help='holds phase_b_camera_probe.py')
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--device', default='cuda:0')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--settle-steps', type=int, default=50, help='zero-command policy steps before the episode')
    parser.add_argument('--video-every-steps', type=int, default=5, help='policy steps between saved video frames')
    parser.add_argument('--accept-timeout-s', type=float, default=1200.0)
    parser.add_argument('--client-timeout-s', type=float, default=300.0, help='wall time a paused simulator waits')
    parser.add_argument('--lidar-cloud', action='store_true',
                        help='Phase D.0c: add landmarks to the navigation LiDAR and send SENSOR_FRAME_V1 every reply')
    parser.add_argument('--fusion-config', type=pathlib.Path,
                        help='Phase D.0f: send the two-mount fused image instead of the ideal head_eval render')
    args = parser.parse_args(argv)

    sys.path.insert(0, str(args.tools_dir))
    sys.path.insert(0, str(HERE))
    import phase_b_camera_probe as probe
    import lockstep_protocol as lp
    from lockstep_common import TERMINATION_CODES, horizontal_distance, landmark, load_episode

    episode = load_episode(args.episode)
    out = args.output_dir
    frames_dir = out / 'frames'
    frames_dir.mkdir(parents=True, exist_ok=True)
    fusion = fusion_config = None
    eval_camera = episode['camera']
    if args.fusion_config is not None:
        # Config and module hash are checked before Kit starts, so a bad input cannot leave a half-started app behind.
        sys.path.insert(0, str(HERE.parent / 'phase_d'))
        import isaac_fusion
        fusion_config = isaac_fusion.load_config(args.fusion_config, episode['camera'])
        isaac_fusion.verify_module(args.tools_dir, fusion_config)
        # The evaluation view moves to the built-in camera's optical centre (fusion config `virtual`).
        eval_camera = isaac_fusion.virtual_spec(fusion_config, episode['camera'])

    from lite3_sim_bridge import run_isaac_v12_fallback as v12
    from lite3_sim_bridge.command_state import CommandLimits, LatestCommandState
    from lite3_sim_bridge.contact_guard import ContactHistoryError, SubstepContactMonitor, SubstepContactStop

    v12._activate_vendored_rsl_rl(args.vendored_rsl_rl)
    from isaaclab.app import AppLauncher
    simulation_app = AppLauncher(headless=True, enable_cameras=True, device=args.device).app

    import gymnasium as gym                                          # noqa: E402
    import numpy as np                                               # noqa: E402
    import torch                                                     # noqa: E402
    from PIL import Image                                            # noqa: E402
    import isaaclab.sim as sim_utils                                 # noqa: E402
    from isaaclab.assets import AssetBaseCfg                         # noqa: E402
    from isaaclab.sensors import CameraCfg                           # noqa: E402
    from isaaclab_rl.rsl_rl import RslRlVecEnvWrapper                # noqa: E402
    from isaaclab_tasks.utils.parse_cfg import load_cfg_from_registry  # noqa: E402

    __import__('robot_lab.tasks')

    v12_args = v12._parser().parse_args([
        '--mode', 'qualification', '--course', 'flat',
        '--output-dir', str(out), '--checkpoint', str(args.checkpoint),
        '--vendored-rsl-rl', str(args.vendored_rsl_rl), '--device', args.device, '--seed', str(args.seed),
    ])
    v12_args.mid360_pattern_table = None
    env_cfg = load_cfg_from_registry(v12_args.task, 'env_cfg_entry_point')
    agent_cfg = load_cfg_from_registry(v12_args.task, 'rsl_rl_cfg_entry_point')
    v12._configure_environment(env_cfg, v12_args)
    agent_cfg.seed = args.seed
    agent_cfg.device = args.device
    for field, value in probe.PHYSX_BUFFER_PRESETS['one_env'].items():
        setattr(env_cfg.sim.physx, field, value)
    # No auto-reset inside an episode: a V12 termination ends the episode instead (external mode does the same).
    env_cfg.episode_length_s = max(float(env_cfg.episode_length_s), float(episode['max_sim_seconds']) + 30.0)

    def add_camera(name, spec, data_types):
        quat, forward = probe.camera_rotation(float(spec['pitch_up']))
        focal = probe.focal_for_hfov(float(spec['hfov']))
        setattr(env_cfg.scene, name, CameraCfg(
            prim_path='{ENV_REGEX_NS}/Robot/TORSO/' + name,
            update_period=0.0,
            height=int(spec['height']), width=int(spec['width']),
            data_types=list(data_types),
            spawn=sim_utils.PinholeCameraCfg(focal_length=focal, horizontal_aperture=20.955,
                                             clipping_range=(0.05, 30.0)),
            offset=CameraCfg.OffsetCfg(pos=tuple(spec['pos']), rot=quat, convention='ros'),
        ))
        return {**spec, 'data_types': list(data_types), 'focal_length_mm': focal, 'quat_wxyz': quat,
                'optical_forward_in_body': forward}

    camera_record = {
        'head_eval': add_camera('head_eval', eval_camera, ['rgb', 'distance_to_image_plane']),
        'chase': add_camera('chase', episode['chase_camera'], ['rgb']),
    }
    if fusion_config is not None:
        # The fusion needs the stock head camera (same optical centre as head_eval, pitched up) and the D435i colour
        # plus colour-aligned z-depth; head_eval stays for the depth sent and as the ideal reference.
        try:
            fusion = isaac_fusion.IsaacFusion(fusion_config, eval_camera, args.tools_dir)
        except Exception:  # noqa: BLE001 - close Kit instead of leaving it running without a server
            (out / 'FUSION_SETUP_ERROR').write_text(traceback.format_exc())
            print('FUSION_SETUP_ERROR\n' + traceback.format_exc(), flush=True)
            simulation_app.close()
            return 4
        camera_record[fusion_config['head']['name']] = add_camera(
            fusion_config['head']['name'], fusion_config['head'], ['rgb'])
        camera_record[fusion_config['d435']['name']] = add_camera(
            fusion_config['d435']['name'], fusion_config['d435'], ['rgb', 'distance_to_image_plane'])
    for item in episode['landmarks']:
        setattr(env_cfg.scene, 'landmark_' + item['name'], AssetBaseCfg(
            prim_path='/World/ground/landmark_' + item['name'],
            spawn=sim_utils.CuboidCfg(
                size=tuple(item['size']),
                collision_props=sim_utils.CollisionPropertiesCfg(),
                visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=tuple(item['color'])),
            ),
            init_state=AssetBaseCfg.InitialStateCfg(pos=tuple(item['center'])),
        ))
    lidar_record = None
    if args.lidar_cloud:
        # The adapter keeps each box as a distinct ray-cast target (the terrain scanner has already cached
        # /World/ground, so the parent path alone would miss children); do the same for every landmark.
        lidar_cfg = env_cfg.scene.navigation_lidar
        lidar_cfg.mesh_prim_paths = list(lidar_cfg.mesh_prim_paths) + [
            '/World/ground/landmark_' + item['name'] for item in episode['landmarks']]
        lidar_record = {
            'prim_path': lidar_cfg.prim_path, 'offset_pos': list(lidar_cfg.offset.pos),
            'offset_rot_wxyz': list(lidar_cfg.offset.rot), 'mesh_prim_paths': [str(t) for t in lidar_cfg.mesh_prim_paths],
            'channels': v12_args.lidar_channels,
            'vertical_fov_deg': [v12_args.lidar_vertical_min, v12_args.lidar_vertical_max],
            'horizontal_res_deg': v12_args.lidar_horizontal_resolution,
            'range_m': [v12_args.lidar_min_range, v12_args.lidar_max_range],
            'floor_filter_max_world_z_m': v12_args.planner_floor_filter_max_z,
        }

    raw_env = gym.make(v12_args.task, cfg=env_cfg)
    base_env = raw_env.unwrapped
    wrapped_env = RslRlVecEnvWrapper(raw_env, clip_actions=agent_cfg.clip_actions)
    policy, _, observation, _ = v12._load_inference_policy(wrapped_env, agent_cfg, v12_args.checkpoint,
                                                           agent_cfg.device)

    robot = base_env.scene['robot']
    contact = base_env.scene.sensors['contact_forces']
    head = base_env.scene['head_eval']
    chase = base_env.scene['chase']
    fusion_head = base_env.scene[fusion_config['head']['name']] if fusion is not None else None
    fusion_d435 = base_env.scene[fusion_config['d435']['name']] if fusion is not None else None
    lidar = base_env.scene.sensors['navigation_lidar'] if args.lidar_cloud else None
    if lidar is not None:
        import hashlib
        from lite3_sim_bridge.isaac_adapter_core import world_hits_to_sensor_points
        lidar_config_sha256 = hashlib.sha256(json.dumps(lidar_record, sort_keys=True).encode()).digest()
    command_term = base_env.command_manager.get_term('base_velocity')
    foot_ids, foot_names = contact.find_bodies(['FL_FOOT', 'FR_FOOT', 'HL_FOOT', 'HR_FOOT'], preserve_order=True)
    if len(foot_ids) != 4:
        raise RuntimeError('V12 contact foot binding mismatch: {}'.format(foot_names))
    body_names = list(contact.body_names)
    nonfoot_ids = [index for index in range(len(body_names)) if index not in foot_ids]
    policy_dt_ns = int(round(float(base_env.step_dt) * 1e9))
    physics_dt_s = float(base_env.physics_dt)
    physics_dt_ns = int(round(physics_dt_s * 1e9))
    decimation = int(base_env.cfg.decimation)
    max_sim_ns = int(float(episode['max_sim_seconds']) * 1e9)

    limits = CommandLimits(v12_args.max_vx, v12_args.max_vy, v12_args.max_wz)
    state = LatestCommandState(limits, timeout_ns=int(round(v12_args.watchdog_seconds * 1e9)))
    clock = {'sim_ns': 0}
    monitor = SubstepContactMonitor(
        read_forces=lambda: torch.linalg.vector_norm(contact.data.net_forces_w[0], dim=-1).tolist(),
        # clock['sim_ns'] only advances after the policy step; the sample for this substep is already appended when
        # the monitor reads the clock, so this is the end time of the substep being inspected.
        clock=lambda: (clock['sim_ns'] + len(monitor.samples) * physics_dt_ns) / 1e9,
        on_failure=lambda reason: state.latch_case_failure(reason),
        required_substeps=decimation,
        stop_on_contact=True,
        threshold_n=float(v12_args.collision_force_threshold),
        nonfoot_indices=nonfoot_ids,
        body_names=body_names,
        physics_dt_s=physics_dt_s,
    )
    monitor.install(base_env.scene)

    def set_command(vx, vy, wz):
        command_term.commands[:, 0] = vx
        command_term.commands[:, 1] = vy
        command_term.commands[:, 2] = wz

    def policy_step():
        nonlocal observation
        with torch.inference_mode():
            actions = policy(observation)
        observation, _, dones, _ = wrapped_env.step(actions)
        return bool(dones.any().item())

    for _ in range(args.settle_steps):
        set_command(0.0, 0.0, 0.0)
        policy_step()

    fusion_rows = []
    fusion_log = None
    fusion_dir = out / 'fusion'
    fusion_cameras = []
    if fusion is not None:
        from isaaclab.utils.math import convert_camera_frame_orientation_convention  # noqa: E402
        fusion_cameras = [('head_eval', head, fusion.virt, eval_camera),
                          (fusion_config['head']['name'], fusion_head, fusion.head, fusion_config['head']),
                          (fusion_config['d435']['name'], fusion_d435, fusion.d435, fusion_config['d435'])]

    def record_live_readback(phase):
        """Record only. CameraCfg.update_latest_camera_pose is False, so data.pos_w still holds the initialisation pose;
        refresh through Isaac Lab's Fabric world-pose path, record against the TORSO link, then restore the buffers so
        IMAGE_FRAME_V1 metadata stays as in Phase C/D. Preflights v1/v2 showed this readback cannot validate mounts."""
        torso_id = robot.find_bodies(['TORSO'])[0][0]
        torso_pos = robot.data.body_pos_w[0, torso_id].cpu().numpy()
        torso_quat = robot.data.body_quat_w[0, torso_id].cpu().numpy()
        for name, camera, _, spec in fusion_cameras:
            stale_pos, stale_quat = camera.data.pos_w.clone(), camera.data.quat_w_world.clone()
            camera._update_poses(camera._ALL_INDICES)
            refreshed = not (torch.equal(stale_pos, camera.data.pos_w)
                             and torch.equal(stale_quat, camera.data.quat_w_world))
            fusion.record_live_readback(phase, name, spec, probe.camera_rotation(float(spec['pitch_up']))[0],
                                        torso_pos, torso_quat, camera.data.pos_w[0].cpu().numpy(),
                                        camera.data.quat_w_ros[0].cpu().numpy(), refreshed)
            camera.data.pos_w[:] = stale_pos
            camera.data.quat_w_world[:] = stale_quat

    if fusion is not None:
        # The fusion assumes ideal pinholes at the configured poses. Check both against what Isaac actually built: each
        # camera's K, and the local pose authored on each camera prim relative to TORSO (USD xformOp translate/orient,
        # OpenGL camera convention). Refuse to serve images if either disagrees.
        problems = []
        try:
            for name, camera, cam, spec in fusion_cameras:
                problems += fusion.check_intrinsics(name, cam, camera.data.intrinsic_matrices[0].cpu().numpy())
                local_pos, local_quat = camera._view.get_local_poses()
                # Same conversion, dtype and device as Camera.__init__ uses when it authors the offset.
                expected_gl = convert_camera_frame_orientation_convention(
                    torch.tensor(probe.camera_rotation(float(spec['pitch_up']))[0], dtype=torch.float32,
                                 device='cpu').unsqueeze(0), origin='ros', target='opengl')[0]
                problems += fusion.check_authored_mount(name, spec, expected_gl.numpy(), local_pos[0].cpu().numpy(),
                                                        local_quat[0].cpu().numpy())
        except Exception:  # noqa: BLE001 - a check that cannot run must not leave Kit up without a server
            (out / 'FUSION_SETUP_ERROR').write_text(traceback.format_exc())
            print('FUSION_SETUP_ERROR\n' + traceback.format_exc(), flush=True)
            monitor.restore()
            wrapped_env.close()
            simulation_app.close()
            return 4
        try:
            record_live_readback('start')
        except Exception:  # noqa: BLE001 - record only
            fusion.live_readback['start_error'] = traceback.format_exc()
        if problems:
            (out / 'FUSION_GEOMETRY_MISMATCH').write_text(json.dumps(
                {'problems': problems, 'intrinsics': fusion.intrinsics, 'mounts_authored': fusion.mounts,
                 'live_camera_pose_readback_record_only': fusion.live_readback}, indent=2) + '\n')
            print('FUSION_GEOMETRY_MISMATCH ' + '; '.join(problems), flush=True)
            monitor.restore()
            wrapped_env.close()
            simulation_app.close()
            return 3
        fusion_dir.mkdir(parents=True, exist_ok=True)
        fusion_log = open(out / 'fusion_frames.jsonl', 'w')

    def tensor3(value):
        return tuple(float(v) for v in value[:3])

    def body_state(sequence, epoch):
        qw, qx, qy, qz = (float(v) for v in robot.data.root_quat_w[0])
        return lp.BodyStateV2(
            position_world=tensor3(robot.data.root_pos_w[0]),
            orientation_world_xyzw=(qx, qy, qz, qw),
            linear_velocity_world=tensor3(robot.data.root_lin_vel_w[0]),
            angular_velocity_world=tensor3(robot.data.root_ang_vel_w[0]),
            linear_velocity_body=tensor3(robot.data.root_lin_vel_b[0]),
            angular_velocity_body=tensor3(robot.data.root_ang_vel_b[0]),
            simulation_time_ns=clock['sim_ns'], state_sequence=sequence, run_epoch_ns=epoch,
        )

    def read_rgb(camera):
        return camera.data.output['rgb'][0][..., :3].to(torch.uint8).contiguous().cpu().numpy()

    fusion_cache = {}

    def fused_view(kind, index):
        """Fuse the current head and D435i renders into the head_eval view; log it against the ideal render.

        The renders only change when the simulator steps, so a video frame and a decision image at the same simulated
        time share one fusion (the decision row is marked `reused_fusion`).
        """
        key = (step_index, clock['sim_ns'])
        if fusion_cache.get('key') == key:
            ideal, head_rgb, d435_rgb, d435_depth, fused, coverage, base_row = fusion_cache['value']
            row = dict(base_row, reused_fusion=True)
        else:
            ideal = read_rgb(head)
            head_rgb = read_rgb(fusion_head)
            d435_rgb = read_rgb(fusion_d435)
            d435_depth = fusion_d435.data.output['distance_to_image_plane'][0][..., 0].to(
                torch.float32).contiguous().cpu().numpy()
            fused, coverage, base_row = fusion.fuse(head_rgb, d435_rgb, d435_depth, ideal)
            fusion_cache.update(key=key, value=(ideal, head_rgb, d435_rgb, d435_depth, fused, coverage, base_row))
            row = dict(base_row, reused_fusion=False)
        row.update({'kind': kind, 'index': index, 'sim_ns': clock['sim_ns'], 'policy_step': step_index})
        fusion_rows.append(row)
        fusion_log.write(json.dumps(row) + '\n')
        fusion_log.flush()
        if kind == 'decision' and (index <= int(fusion_config['save_first_images'])
                                   or index % int(fusion_config['save_every_images']) == 0):
            # Lossless inputs and outputs, so fusion_recompute_check.py can reproduce the fused image bit for bit.
            stem = fusion_dir / 'image_{:04d}'.format(index)
            try:
                Image.fromarray(ideal).save(str(stem) + '_ideal.png')
                Image.fromarray(fused).save(str(stem) + '_fused.png')
                Image.fromarray(coverage).save(str(stem) + '_coverage.png')
                Image.fromarray(head_rgb).save(str(stem) + '_head.png')
                Image.fromarray(d435_rgb).save(str(stem) + '_d435.png')
                np.save(str(stem) + '_d435_depth_m.npy', d435_depth)
            except OSError as error:  # not a client failure: surface it as a server error
                raise RuntimeError('fusion evidence save failed: {!r}'.format(error)) from error
        return fused

    def image_frame(frame_id):
        rgb = fused_view('decision', frame_id) if fusion is not None else read_rgb(head)
        depth = head.data.output['distance_to_image_plane'][0][..., 0].to(torch.float32).contiguous().cpu().numpy()
        k = head.data.intrinsic_matrices[0].cpu().numpy()
        qw, qx, qy, qz = (float(v) for v in head.data.quat_w_ros[0])
        return lp.ImageFrameV1(
            frame_id=frame_id, simulation_time_ns=clock['sim_ns'],
            width=int(rgb.shape[1]), height=int(rgb.shape[0]),
            intrinsics_fx_fy_cx_cy=(float(k[0, 0]), float(k[1, 1]), float(k[0, 2]), float(k[1, 2])),
            camera_position_world=tensor3(head.data.pos_w[0]),
            camera_orientation_world_xyzw=(qx, qy, qz, qw),
            rgb=rgb.tobytes(), depth=depth.astype('<f4').tobytes(),
        )

    def lidar_frame():
        # Same sequence as the adapter's sensor branch: force a recompute at the current pose, read world hits and the
        # sensor pose, keep finite hits in range and above the floor, express them in the sensor frame.
        # update(force_recompute=True) only refreshes a sensor already marked outdated, and the float32 timestamp can
        # leave it 1e-6 short of update_period, which reuses the previous tick's scan. reset() sets the outdated bit
        # first, as the adapter's _set_mid360_scan_window does; the ray caster has zero drift, so geometry is unchanged.
        lidar.reset()
        lidar.update(dt=0.0, force_recompute=True)
        qw, qx, qy, qz = (float(v) for v in lidar.data.quat_w[0])
        bw, bx, by, bz = (float(v) for v in robot.data.root_quat_w[0])
        points = world_hits_to_sensor_points(
            lidar.data.ray_hits_w[0].detach().cpu().tolist(), tensor3(lidar.data.pos_w[0]), (qw, qx, qy, qz),
            v12_args.lidar_min_range, v12_args.lidar_max_range, minimum_world_z=v12_args.planner_floor_filter_max_z)
        count, data = lp.pack_xyz_points(points)
        return lp.SensorFrameV1(
            body_position=tensor3(robot.data.root_pos_w[0]), body_quaternion_xyzw=(bx, by, bz, bw),
            sensor_position=tensor3(lidar.data.pos_w[0]), sensor_quaternion_xyzw=(qx, qy, qz, qw),
            config_sha256=lidar_config_sha256, point_count=count, points_xyz_f32_be=data)

    def save_video_frames(step_index):
        stem = '{:06d}'.format(step_index)
        Image.fromarray(chase.data.output['rgb'][0][..., :3].to(torch.uint8).cpu().numpy()).save(
            frames_dir / 'chase_{}.jpg'.format(stem), quality=90)
        Image.fromarray(head.data.output['rgb'][0][..., :3].to(torch.uint8).cpu().numpy()).save(
            frames_dir / 'head_{}.jpg'.format(stem), quality=90)
        if fusion is not None:
            Image.fromarray(fused_view('video', step_index)).save(frames_dir / 'fused_{}.jpg'.format(stem), quality=90)

    start_xy = tensor3(robot.data.root_pos_w[0])[:2]
    target = landmark(episode, episode['target_landmark'])
    record = {
        'episode': episode, 'cameras': camera_record, 'physx_gpu': probe.PHYSX_BUFFER_PRESETS['one_env'],
        'policy_dt_ns': policy_dt_ns, 'physics_dt_s': physics_dt_s, 'decimation': decimation,
        'limits': {'max_vx': limits.max_vx, 'max_vy': limits.max_vy, 'max_wz': limits.max_wz},
        'watchdog_seconds': v12_args.watchdog_seconds,
        'collision_force_threshold_n': v12_args.collision_force_threshold,
        'lidar': lidar_record,
        'fusion': None if fusion is None else {
            'config_path': str(args.fusion_config), 'config': fusion_config, 'geometry': fusion.geometry_record(),
            'virtual_camera': eval_camera, 'intrinsics_measured': fusion.intrinsics,
            'mounts_authored': fusion.mounts, 'live_camera_pose_readback_record_only': fusion.live_readback,
        },
        'start_pose': {'xyz': tensor3(robot.data.root_pos_w[0]),
                       'quat_wxyz': [float(v) for v in robot.data.root_quat_w[0]]},
        'landmark_distance_at_start_m': {item['name']: horizontal_distance(start_xy, item['center'])
                                         for item in episode['landmarks']},
    }

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('127.0.0.1', args.port))
    server.listen(1)
    server.settimeout(args.accept_timeout_s)
    (out / 'LISTENING').write_text(json.dumps({'port': args.port, 'unix_s': time.time()}) + '\n')
    print('LOCKSTEP_LISTENING port={}'.format(args.port), flush=True)

    termination = None
    detail = None
    requests = images = clouds = step_index = state_sequence = out_sequence = 0
    clamp_policy_steps = 0
    min_target_distance = horizontal_distance(start_xy, target['center'])
    last_received = None
    run_epoch_ns = time.time_ns()
    steps_log = open(out / 'isaac_steps.jsonl', 'w')
    try:
        connection, _ = server.accept()
    except socket.timeout:
        termination, detail = 'client_timeout', 'no client connected'
        connection = None
    if connection is not None:
        connection.settimeout(args.client_timeout_s)
        connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    def send(message_type, payload):
        nonlocal out_sequence
        out_sequence += 1
        lp.send_frame(connection, lp.encode_frame(message_type, out_sequence, clock['sim_ns'], payload))

    # A V12 termination resets the robot inside the same env.step, so the pose read after that step is the reset
    # pose, not where the episode ended. The pose from just before that step is kept for the metrics instead.
    pose_before_reset = None
    server_error = None
    try:
        while connection is not None:
            try:
                command_frame = lp.recv_frame(connection)
                request_frame = lp.recv_frame(connection)
            except (socket.timeout, TimeoutError):
                state.mark_disconnected()
                termination, detail = 'client_timeout', 'no request within {} s wall'.format(args.client_timeout_s)
                break
            except (EOFError, ConnectionError) as error:
                state.mark_disconnected()
                termination, detail = 'client_lost', repr(error)
                break
            except lp.ProtocolError as error:
                termination, detail = 'protocol_error', repr(error)
                break
            if (command_frame.header.message_type != lp.MessageType.CMD_VEL_V1
                    or request_frame.header.message_type != lp.MessageType.STEP_REQUEST_V1):
                termination, detail = 'protocol_error', 'expected CMD_VEL_V1 then STEP_REQUEST_V1'
                break
            requests += 1
            try:
                command = lp.decode_command_payload(command_frame.payload)
                request = lp.decode_step_request_payload(request_frame.payload)
            except lp.ProtocolError as error:
                termination, detail = 'protocol_error', repr(error)
                break
            try:
                # Both timestamps are simulated time: the client stamps the command with the sim time of the last
                # state it received, and the simulator receives it at the current sim time. Freshness and the
                # watchdog therefore measure simulated seconds, which is what the robot experiences.
                state.update(command, command_frame.header.sequence, command_frame.header.timestamp_ns,
                             clock['sim_ns'])
            except Exception as error:  # noqa: BLE001 - the pinned module raises its own ProtocolError class
                termination, detail = 'command_rejected', repr(error)
            last_received = command
            if termination is None and request.duration_ns % policy_dt_ns != 0:
                termination, detail = 'protocol_error', 'duration {} ns is not a multiple of {}'.format(
                    request.duration_ns, policy_dt_ns)
            steps = 0 if termination else request.duration_ns // policy_dt_ns
            for _ in range(steps):
                snapshot = state.snapshot(clock['sim_ns'])
                applied = snapshot.command
                if last_received is not None and not snapshot.stale and (
                        abs(applied.vx - last_received.vx) > 1e-9 or abs(applied.vy - last_received.vy) > 1e-9
                        or abs(applied.wz - last_received.wz) > 1e-9):
                    clamp_policy_steps += 1
                set_command(applied.vx, applied.vy, applied.wz)
                position_before_step = tensor3(robot.data.root_pos_w[0])
                try:
                    monitor.begin(step_index)
                    done = policy_step()
                    monitor.end()
                except SubstepContactStop as stop:
                    termination, detail = 'nonfoot_contact', repr(stop.failure.as_record() if stop.failure else stop)
                    done = False
                except ContactHistoryError as error:
                    termination, detail = 'contact_monitor_error', repr(error)
                    done = False
                clock['sim_ns'] += policy_dt_ns
                step_index += 1
                position = tensor3(robot.data.root_pos_w[0])
                if done:
                    pose_before_reset = position_before_step
                metric_position = position_before_step if done else position
                forces = torch.linalg.vector_norm(contact.data.net_forces_w[0], dim=-1)
                # Substep rows were sampled inside the step, before any reset, so they still show what ended it.
                substep_nonfoot = [(row[index], body_names[index]) for row in monitor.samples for index in nonfoot_ids]
                substep_max_n, substep_max_body = max(substep_nonfoot, default=(0.0, None))
                target_distance = horizontal_distance(metric_position[:2], target['center'])
                min_target_distance = min(min_target_distance, target_distance)
                qw, qx, qy, qz = (float(v) for v in robot.data.root_quat_w[0])
                steps_log.write(json.dumps({
                    'step': step_index, 'sim_ns': clock['sim_ns'], 'request': requests,
                    'received': [last_received.vx, last_received.vy, last_received.wz],
                    'applied': [applied.vx, applied.vy, applied.wz], 'stale': snapshot.stale,
                    'reason': snapshot.reason, 'watchdog_events': snapshot.watchdog_events,
                    'xyz': position, 'xyz_before_step': position_before_step,
                    'yaw': math.atan2(2 * (qw * qz + qx * qy), 1 - 2 * (qy * qy + qz * qz)),
                    'vel_body': tensor3(robot.data.root_lin_vel_b[0]),
                    'wz_body': float(robot.data.root_ang_vel_b[0][2]),
                    'feet_in_contact': int((forces[foot_ids] >= v12_args.contact_force_threshold).sum().item()),
                    'nonfoot_max_n': float(forces[nonfoot_ids].max().item()) if nonfoot_ids else 0.0,
                    'nonfoot_substep_max_n': float(substep_max_n), 'nonfoot_substep_max_body': substep_max_body,
                    'target_distance_m': target_distance, 'done': done,
                }) + '\n')
                if step_index % args.video_every_steps == 0:
                    save_video_frames(step_index)
                if termination is None and done:
                    termination, detail = 'env_done', 'V12 termination or reset'
                if termination is None and clock['sim_ns'] >= max_sim_ns:
                    termination, detail = 'max_sim_time', None
                if termination is not None:
                    break
            if termination is None and request.end_episode:
                termination, detail = 'client_end', None

            snapshot = state.snapshot(clock['sim_ns'])
            flags = 0
            if termination is not None:
                flags |= int(lp.StatusFlag.TERMINATED)
            if termination == 'nonfoot_contact':
                flags |= int(lp.StatusFlag.COLLISION)
            if termination == 'env_done':
                flags |= int(lp.StatusFlag.RESET_OCCURRED)
            forces = torch.linalg.vector_norm(contact.data.net_forces_w[0], dim=-1)
            try:
                state_sequence += 1
                send(lp.MessageType.STATUS_V1, lp.encode_status_payload(lp.StatusV1(
                    physics_hz=1.0 / physics_dt_s, policy_hz=1e9 / policy_dt_ns, sensor_hz=0.0, bridge_latency_ms=0.0,
                    contact_count=int((forces[foot_ids] >= v12_args.contact_force_threshold).sum().item()),
                    dropped_frames=0, watchdog_events=snapshot.watchdog_events, flags=flags,
                    termination_code=TERMINATION_CODES[termination] if termination else 0)))
                send(lp.MessageType.BODY_STATE_V2,
                     lp.encode_body_state_v2_payload(body_state(state_sequence, run_epoch_ns)))
                if request.want_image and termination is None:
                    images += 1
                    send(lp.MessageType.IMAGE_FRAME_V1, lp.encode_image_frame_payload(image_frame(images)))
                if lidar is not None and termination is None:
                    clouds += 1
                    send(lp.MessageType.SENSOR_FRAME_V1, lp.encode_sensor_payload(lidar_frame()))
            except (OSError, lp.ProtocolError) as error:
                termination, detail = termination or 'client_lost', repr(error)
            if termination is not None:
                break
    except Exception:  # noqa: BLE001 - a server-side failure must still release the client and leave a record
        server_error = traceback.format_exc()
        print(server_error, flush=True)
        termination = termination or 'server_error'

    # Release the client first: it must never wait on a simulator that has stopped serving, whatever happens below.
    for closable in (connection, server):
        try:
            if closable is not None:
                closable.close()
        except OSError:
            pass
    steps_log.close()
    if fusion_log is not None:
        fusion_log.close()
        try:
            record_live_readback('end')
        except Exception:  # noqa: BLE001 - record only
            record['fusion']['live_readback_end_error'] = traceback.format_exc()
        try:
            record['fusion']['summary'] = isaac_fusion.summarise(
                fusion_rows, fusion_config['preflight_bounds_from_habitat_c8'])
        except Exception:  # noqa: BLE001 - the episode record must still be written
            record['fusion']['summary_error'] = traceback.format_exc()
    final_xyz = pose_before_reset if pose_before_reset is not None else tensor3(robot.data.root_pos_w[0])
    final_xy = final_xyz[:2]
    snapshot = state.snapshot(clock['sim_ns'])
    record.update({
        'termination': termination, 'termination_detail': detail, 'server_error': server_error,
        'sim_seconds': clock['sim_ns'] / 1e9, 'policy_steps': step_index, 'requests': requests, 'images_sent': images, 'clouds_sent': clouds,
        'final_xy': list(final_xy),
        'final_pose_source': 'before_v12_reset' if pose_before_reset is not None else 'current',
        'final_distance_to_target_m': horizontal_distance(final_xy, target['center']),
        'min_distance_to_target_m': min_target_distance,
        'landmark_distance_at_end_m': {item['name']: horizontal_distance(final_xy, item['center'])
                                       for item in episode['landmarks']},
        'watchdog_events': snapshot.watchdog_events, 'sequence_gaps': snapshot.sequence_gaps,
        'case_failed': snapshot.case_failed, 'case_failure_reason': snapshot.case_failure_reason,
        'clamp_policy_steps': clamp_policy_steps, 'contact_monitor': monitor.as_record(),
        'gpu_used_mib_at_end': probe.gpu_used_mib(),
    })
    (out / 'isaac_episode.json').write_text(json.dumps(record, indent=2, default=str) + '\n')
    print('LOCKSTEP_EPISODE_DONE termination={} sim_s={:.2f}'.format(termination, clock['sim_ns'] / 1e9), flush=True)

    monitor.restore()
    wrapped_env.close()   # before the app, or SimulationApp.close() hangs (Phase B phase_b_none_v2)
    simulation_app.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
