"""Phase C, VLA side: InternVLA-N1 plus upstream's real-robot controllers, driving the lockstep simulator.

This reproduces upstream's quadruped client (`InternNav/scripts/realworld/http_internvla_client.py`, a Unitree Go2
node) on the simulated clock (design Decisions 5 and 6):

- planning thread -> one decision: the newest RGB-D frame goes through the same encoding upstream applies (JPEG colour;
  depth in metres scaled by 10000 into uint16, so clipped at 6.5535 m, invalid pixels 0), then `agent.step`, with the
  server's look-down follow-up (`http_internvla_server.py`). A trajectory is transformed into the world with the
  odometry captured with that image, skipping its first three points, and handed to `Mpc_controller`; arrow actions
  move an incremental goal (0.25 m / 15 deg) that `PID_controller` tracks.
- control thread -> 0.1 s ticks: while the VLA was thinking the simulator was paused; afterwards the PREVIOUS plan's
  controller is played for the measured inference time L, the new plan takes over (when a real robot would have
  received it), and it runs until the next image, captured max(L + 0.05, 0.3) s after the last one as upstream's
  planning loop does.

`controllers.py` is imported from the pinned InternNav tree, unmodified. Deviations, each forced by the simulator and
logged: the robot holds (0, 0) before the first plan (upstream publishes nothing), and a failed MPC solve sends (0, 0)
for that tick (upstream's control thread would die and the robot's own command timeout would stop it).
`trajectory_tovw` is evaluated on every trajectory and logged, never used; on the shipped (T+1, 2) trajectory it raises
IndexError because it reads `subgoal[2]`, which is itself evidence that it is dead code upstream.
"""

import argparse
import atexit
import io
import json
import math
import signal
import socket
import statistics
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lockstep_protocol as lp                                          # noqa: E402
from lockstep_common import (CONTROL_TICK_NS, TERMINATION_NAMES, horizontal_distance, landmark,  # noqa: E402
                             load_episode, yaw_from_quaternion_xyzw)

UPSTREAM_PLANNING_SLEEP_NS = 50_000_000     # planning_thread: time.sleep(0.05) before each request
UPSTREAM_PLANNING_PERIOD_NS = 300_000_000   # planning_thread: DESIRED_TIME = 0.3
STOP_HOLD_S = 1.0                   # after STOP, keep the PD hold this long before ending the episode


class ScriptedAgent:
    """Stand-in for InternVLAN1AsyncAgent in local tests: same call shape, canned outputs, no model."""

    class Output:
        def __init__(self, action=None, trajectory=None, pixel=None):
            self.output_action, self.output_trajectory, self.output_pixel = action, trajectory, pixel

    def __init__(self, script, latency_s=0.0):
        self.script, self.calls, self.llm_output, self.last_s2_idx = list(script), 0, '', -100
        self.latency_s = latency_s

    def reset(self):
        self.calls = 0

    def step_s2(self, *args, **kwargs):
        return None

    def step(self, rgb, depth, pose, instruction, intrinsic, look_down=False):
        assert rgb.dtype == np.uint8 and rgb.ndim == 3 and depth.ndim == 2
        if not look_down:
            time.sleep(self.latency_s)
        entry = self.script[min(self.calls, len(self.script) - 1)]
        if not look_down:
            self.calls += 1
        self.last_s2_idx += 1
        self.step_s2()
        if entry == 'look_down' and not look_down:
            self.llm_output = '↓'
            return self.Output(action=[5])
        if entry in ('look_down', 'straight'):
            self.llm_output = '320 400'
            xs = np.linspace(0.0, 1.6, 33)
            return self.Output(trajectory=np.stack([xs, np.zeros_like(xs)], axis=1), pixel=[400, 320])
        if entry == 'left':
            self.llm_output = '←←'
            return self.Output(action=[2, 2])
        if entry == 'stop':
            self.llm_output = 'STOP'
            return self.Output(action=[0])
        raise ValueError(entry)


def upstream_rgb(rgb):
    buffer = io.BytesIO()
    from PIL import Image
    Image.fromarray(rgb).save(buffer, format='JPEG')   # http_internvla_client.py: image.save(..., format='JPEG')
    buffer.seek(0)
    return np.asarray(Image.open(buffer).convert('RGB'))


def upstream_depth(depth_m):
    depth = np.where(np.isfinite(depth_m), depth_m, 0.0)
    depth[depth < 0] = 0
    quantised = np.clip(depth * 10000.0, 0, 65535).astype(np.uint16)   # client: *10000 -> uint16 PNG
    return quantised.astype(np.float32) / 10000.0                      # server: / 10000.0


def incremental_change_goal(homo_odom, actions):
    """Verbatim logic of Go2Manager.incremental_change_goal (http_internvla_client.py), without the ROS node."""
    homo_goal = homo_odom.copy()
    for each_action in actions:
        if each_action == 1:
            yaw = math.atan2(homo_goal[1, 0], homo_goal[0, 0])
            homo_goal[0, 3] += 0.25 * np.cos(yaw)
            homo_goal[1, 3] += 0.25 * np.sin(yaw)
        elif each_action in (2, 3):
            angle = math.radians(15) if each_action == 2 else -math.radians(15.0)
            rotation = np.array([[math.cos(angle), -math.sin(angle), 0], [math.sin(angle), math.cos(angle), 0],
                                 [0, 0, 1]])
            homo_goal[:3, :3] = np.dot(rotation, homo_goal[:3, :3])
    return homo_goal


def trajectory_tovw_probe(agent, trajectory):
    try:
        return {'value': [float(v) for v in agent.trajectory_tovw(np.asarray(trajectory))]}
    except Exception as error:  # noqa: BLE001 - recorded, never used for control
        return {'error': repr(error)}


class LockstepLink:
    def __init__(self, host, port, connect_timeout_s):
        deadline = time.time() + connect_timeout_s
        while True:
            try:
                self.sock = socket.create_connection((host, port), timeout=10)
                break
            except OSError:
                if time.time() > deadline:
                    raise
                time.sleep(2.0)
        self.sock.settimeout(600)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.sequence = 0
        self.sim_ns = 0
        self.epoch = None

    def step(self, v, w, duration_ns, want_image, end_episode=False):
        self.sequence += 1
        command = lp.encode_frame(lp.MessageType.CMD_VEL_V1, self.sequence, self.sim_ns,
                                  lp.encode_command_payload(lp.CommandV1(float(v), 0.0, float(w))))
        request = lp.encode_frame(lp.MessageType.STEP_REQUEST_V1, self.sequence, self.sim_ns,
                                  lp.encode_step_request_payload(lp.StepRequestV1(
                                      duration_ns, self.sequence, want_image, end_episode)))
        lp.send_frame(self.sock, command)
        lp.send_frame(self.sock, request)
        status_frame = lp.recv_frame(self.sock)
        body_frame = lp.recv_frame(self.sock)
        if (status_frame.header.message_type != lp.MessageType.STATUS_V1
                or body_frame.header.message_type != lp.MessageType.BODY_STATE_V2):
            raise lp.ProtocolError('expected STATUS_V1 then BODY_STATE_V2')
        status = lp.decode_status_payload(status_frame.payload)
        body = lp.decode_body_state_v2_payload(body_frame.payload)
        if self.epoch is None:
            self.epoch = body.run_epoch_ns
        elif body.run_epoch_ns != self.epoch:
            raise lp.ProtocolError('run epoch changed')
        if body.simulation_time_ns < self.sim_ns:
            raise lp.ProtocolError('simulation time went backwards')
        self.sim_ns = body.simulation_time_ns
        image = None
        if want_image and status.termination_code == 0:
            image_frame = lp.recv_frame(self.sock)
            if image_frame.header.message_type != lp.MessageType.IMAGE_FRAME_V1:
                raise lp.ProtocolError('expected IMAGE_FRAME_V1')
            image = lp.decode_image_frame_payload(image_frame.payload)
            if image.simulation_time_ns != body.simulation_time_ns:
                raise lp.ProtocolError('image and body state come from different simulation times')
        return status, body, image


def odom_of(body):
    x, y = body.position_world[0], body.position_world[1]
    yaw = yaw_from_quaternion_xyzw(body.orientation_world_xyzw)
    homo = np.eye(4)
    homo[:2, :2] = [[math.cos(yaw), -math.sin(yaw)], [math.sin(yaw), math.cos(yaw)]]
    homo[:2, 3] = [x, y]
    return [x, y, yaw], homo, [body.linear_velocity_body[0], body.angular_velocity_body[2]]


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--episode', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--agent', choices=['internvla', 'scripted'], default='internvla')
    parser.add_argument('--script', default='look_down,straight,straight,left,straight,stop')
    parser.add_argument('--scripted-latency-s', type=float, default=0.0, help='scripted agent: sleep per decision')
    parser.add_argument('--internnav-root', type=Path)
    parser.add_argument('--model-path', type=Path)
    parser.add_argument('--depth-anything', type=Path)
    parser.add_argument('--controllers-dir', type=Path, required=True, help='InternNav scripts/realworld')
    parser.add_argument('--connect-timeout-s', type=float, default=1200.0)
    parser.add_argument('--max-decisions', type=int, default=400)
    parser.add_argument('--plan-step-gap', type=int, default=4)
    args = parser.parse_args(argv)
    if args.agent == 'internvla':
        missing = [flag for flag, value in (('--internnav-root', args.internnav_root), ('--model-path', args.model_path),
                                            ('--depth-anything', args.depth_anything)) if value is None]
        if missing:
            parser.error('--agent internvla needs {}'.format(', '.join(missing)))
    # The internvla branch changes the working directory, so every local path must be absolute before that happens.
    for name in ('episode', 'output_dir', 'internnav_root', 'depth_anything', 'controllers_dir'):
        if getattr(args, name) is not None:
            setattr(args, name, getattr(args, name).resolve())
    if args.model_path is not None and args.model_path.exists():
        args.model_path = args.model_path.resolve()
    # SIGTERM (the run script's timeout and kill) becomes a normal exit, so the atexit cleanup below still runs.
    signal.signal(signal.SIGTERM, lambda signum, _frame: sys.exit(128 + signum))

    episode = load_episode(args.episode)
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    (out / 'decision_frames').mkdir(exist_ok=True)
    sys.path.insert(0, str(args.controllers_dir))
    from controllers import Mpc_controller, PID_controller  # pinned upstream, unmodified

    record = {'episode': episode, 'agent': args.agent, 'argv': sys.argv, 'python': sys.version}
    if args.agent == 'internvla':
        import os
        import torch
        torch.set_grad_enabled(False)   # Phase B v3: generate_traj builds an autograd graph otherwise (OOM)
        sys.path.insert(0, str(args.internnav_root))
        link_path = out / 'checkpoints' / 'depth_anything_v2_metric_hypersim_vits.pth'
        link_path.parent.mkdir(exist_ok=True)
        if not link_path.is_symlink():
            link_path.symlink_to(args.depth_anything)

        def remove_depth_anything_link():
            # Registered right after creation: runs on normal exit, on an exception and on SIGTERM alike.
            if link_path.is_symlink():
                link_path.unlink()
            if link_path.parent.is_dir() and not any(link_path.parent.iterdir()):
                link_path.parent.rmdir()
        atexit.register(remove_depth_anything_link)
        os.chdir(out)   # the agent writes test_data/ and loads checkpoints/ relative to the working directory
        from internnav.agent.internvla_n1_agent_realworld import InternVLAN1AsyncAgent
        started = time.time()
        agent = InternVLAN1AsyncAgent(argparse.Namespace(
            device='cuda:0', model_path=str(args.model_path), resize_w=384, resize_h=384, num_history=8,
            plan_step_gap=args.plan_step_gap))
        record.update(load_seconds=time.time() - started, torch=torch.__version__,
                      pytorch_cuda_alloc_conf=os.environ.get('PYTORCH_CUDA_ALLOC_CONF'))
        # Upstream's server warms the model once before serving; without it decision 1's latency includes CUDA and
        # flash-attention start-up. (Its own call passes float64 zeros and no intrinsic, which would raise.)
        started = time.time()
        agent.reset()
        agent.step(np.zeros((480, 640, 3), dtype=np.uint8), np.zeros((480, 640), dtype=np.float32), np.eye(4),
                   'hello', np.eye(4))
        record['warmup_seconds'] = time.time() - started
    else:
        agent = ScriptedAgent(args.script.split(','), args.scripted_latency_s)
        agent.trajectory_tovw = lambda trajectory: (_ for _ in ()).throw(IndexError('scripted agent has no tovw'))
    agent.reset()
    # phase_c_red_box_v1 inferred System 2 calls from last_s2_idx and missed decision 1 (the warm-up had already left
    # last_s2_idx at 0). Count the calls themselves instead; step() looks these up on the instance.
    calls = {'s2': 0, 's1': 0}
    for name in ('step_s2', 'step_s1'):
        original = getattr(agent, name, None)
        if original is not None:
            def counted(*a, _original=original, _key=name[-2:], **k):
                calls[_key] += 1
                return _original(*a, **k)
            setattr(agent, name, counted)

    pid = PID_controller(Kp_trans=2.0, Kd_trans=0.0, Kp_yaw=1.5, Kd_yaw=0.0, max_v=0.6, max_w=0.5)  # upstream globals
    mpc = None
    mode = None           # upstream starts in MPC mode with no MPC, which publishes nothing; we hold (0, 0) instead
    homo_goal = None
    target = landmark(episode, episode['target_landmark'])
    link = LockstepLink(args.host, args.port, args.connect_timeout_s)
    decisions_log = open(out / 'decisions.jsonl', 'w')
    ticks_log = open(out / 'ticks.jsonl', 'w')
    atexit.register(ticks_log.close)       # close() is idempotent; this covers exits through an exception
    atexit.register(decisions_log.close)

    status, body, image = link.step(0.0, 0.0, 0, want_image=True)
    odom, homo_odom, vel = odom_of(body)
    homo_goal = homo_odom.copy()       # upstream: first odometry initialises homo_goal
    termination = TERMINATION_NAMES.get(status.termination_code) if status.termination_code else None
    stop_sim_ns = None
    latencies, s2_cycles, trajectories, discrete = [], 0, 0, 0
    commands = []

    mpc_failures = []

    def control():
        if mode == 'mpc' and mpc is not None:
            try:
                opt_u_controls, _ = mpc.solve(np.array(odom))
            except RuntimeError as error:   # IPOPT did not converge
                mpc_failures.append({'sim_ns': body.simulation_time_ns, 'error': str(error)[-300:]})
                return 0.0, 0.0
            return float(opt_u_controls[0, 0]), float(opt_u_controls[0, 1])
        if mode == 'pid':
            v, w, _, _ = pid.solve(homo_odom, homo_goal, np.array(vel))
            return max(float(v), 0.0), float(w)
        return 0.0, 0.0

    def tick(want_image):
        nonlocal status, body, image, odom, homo_odom, vel, termination
        v, w = control()
        commands.append((v, w))
        status, body, new_image = link.step(v, w, CONTROL_TICK_NS, want_image=want_image)
        if new_image is not None:
            image = new_image
        odom, homo_odom, vel = odom_of(body)
        ticks_log.write(json.dumps({
            'sim_ns': body.simulation_time_ns, 'mode': mode, 'v': v, 'w': w, 'odom': odom, 'vel': vel,
            'watchdog_events': status.watchdog_events, 'flags': status.flags,
            'termination_code': status.termination_code,
            'target_distance_m': horizontal_distance(odom[:2], target['center']),
        }) + '\n')
        if status.termination_code:
            termination = TERMINATION_NAMES.get(status.termination_code, str(status.termination_code))

    decision = 0
    while termination is None and decision < args.max_decisions:
        decision += 1
        frame_odom = list(odom)   # odometry from the same reply as the image, used for the trajectory transform
        height, width = image.height, image.width
        rgb = upstream_rgb(np.frombuffer(image.rgb, dtype=np.uint8).reshape(height, width, 3))
        depth = upstream_depth(np.frombuffer(image.depth, dtype='<f4').reshape(height, width).copy())
        fx, fy, cx, cy = image.intrinsics_fx_fy_cx_cy
        intrinsic = np.array([[fx, 0, cx, 0], [0, fy, cy, 0], [0, 0, 1, 0], [0, 0, 0, 1]], dtype=np.float64)
        camera_pose = np.eye(4)
        qx, qy, qz, qw = image.camera_orientation_world_xyzw
        camera_pose[:3, :3] = [[1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy - qz * qw), 2 * (qx * qz + qy * qw)],
                               [2 * (qx * qy + qz * qw), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz - qx * qw)],
                               [2 * (qx * qz - qy * qw), 2 * (qy * qz + qx * qw), 1 - 2 * (qx * qx + qy * qy)]]
        camera_pose[:3, 3] = image.camera_position_world
        if decision <= 3 or decision % 5 == 0:
            from PIL import Image
            Image.fromarray(rgb).save(out / 'decision_frames' / 'decision_{:04d}.jpg'.format(decision))

        s2_before, s1_before = calls['s2'], calls['s1']
        started = time.perf_counter()
        result = agent.step(rgb, depth, camera_pose, episode['instruction'], intrinsic)
        first_action = result.output_action
        looked_down = False
        if result.output_action is not None and result.output_action == [5]:
            looked_down = True   # http_internvla_server.py follow-up
            result = agent.step(rgb, depth, camera_pose, episode['instruction'], intrinsic, look_down=True)
        latency = time.perf_counter() - started
        s2_calls, s1_calls = calls['s2'] - s2_before, calls['s1'] - s1_before
        s2_called = s2_calls > 0
        s2_cycles += int(s2_called)
        latencies.append(latency)
        # Upstream planning_thread, measured from the image capture: the response is applied after the inference
        # latency L, and the next image is captured max(L + 0.05, 0.3) s after this one. On the 0.1 s tick grid both
        # round up, so a plan is never applied before it could have arrived.
        latency_ns = int(latency * 1e9)
        apply_ticks = -(-latency_ns // CONTROL_TICK_NS)
        image_interval_ns = max(latency_ns + UPSTREAM_PLANNING_SLEEP_NS, UPSTREAM_PLANNING_PERIOD_NS)
        total_ticks = max(1, apply_ticks, -(-image_interval_ns // CONTROL_TICK_NS))
        image_sim_ns = image.simulation_time_ns

        # The robot keeps executing the previous plan while this decision is being made ...
        for index in range(apply_ticks):
            tick(want_image=index == total_ticks - 1)
            if termination is not None:
                break
        applied_at_sim_ns = body.simulation_time_ns

        trajectory = result.output_trajectory
        entry = {
            'decision': decision, 'image_sim_ns': image_sim_ns,
            'frame_odom': frame_odom, 'instruction': episode['instruction'],
            'llm_output': agent.llm_output if s2_called else None, 's2_called': s2_called,
            's2_calls': s2_calls, 's1_calls': s1_calls,
            'first_action': first_action, 'looked_down': looked_down, 'discrete_action': result.output_action,
            'pixel_goal': result.output_pixel, 'latency_s': latency, 'apply_ticks': apply_ticks,
            'ticks': total_ticks, 'applied_at_sim_ns': applied_at_sim_ns,
        }
        if termination is not None:
            entry['not_applied'] = 'episode ended during the latency'
        elif trajectory is not None:
            trajectories += 1
            trajectory = np.asarray(trajectory, dtype=np.float64)
            entry['trajectory'] = trajectory.tolist()
            entry['trajectory_tovw'] = trajectory_tovw_probe(agent, trajectory)
            trajs_in_world = []
            for i, point in enumerate(trajectory):
                if i < 3:
                    continue
                x_, y_, yaw_ = frame_odom
                w_T_b = np.array([[np.cos(yaw_), -np.sin(yaw_), 0, x_], [np.sin(yaw_), np.cos(yaw_), 0, y_],
                                  [0.0, 0.0, 1.0, 0], [0.0, 0.0, 0.0, 1.0]])
                trajs_in_world.append((w_T_b @ (np.array([point[0], point[1], 0.0, 1.0])).T)[:2])
            trajs_in_world = np.array(trajs_in_world)
            entry['trajectory_world'] = trajs_in_world.tolist()
            if mpc is None:
                mpc = Mpc_controller(np.array(trajs_in_world))
            else:
                mpc.update_ref_traj(np.array(trajs_in_world))
            mode = 'mpc'
        elif result.output_action is not None:
            discrete += 1
            actions = result.output_action
            if actions != [5] and actions != [9]:
                homo_goal = incremental_change_goal(homo_odom, actions)
                mode = 'pid'
            if actions == [0] and stop_sim_ns is None:
                stop_sim_ns = body.simulation_time_ns
        entry['mode_after'] = mode

        # ... and the new plan runs until the next image is captured.
        for index in range(apply_ticks, total_ticks):
            if termination is not None:
                break
            tick(want_image=index == total_ticks - 1)
        entry['next_image_sim_ns'] = body.simulation_time_ns
        decisions_log.write(json.dumps(entry, default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o)) + '\n')
        decisions_log.flush()

        if stop_sim_ns is not None and termination is None:
            for _ in range(int(round(STOP_HOLD_S * 1e9 / CONTROL_TICK_NS))):
                tick(want_image=False)
                if termination is not None:
                    break
            break

    if termination is None:
        status, body, _ = link.step(0.0, 0.0, 0, want_image=False, end_episode=True)
        termination = TERMINATION_NAMES.get(status.termination_code, 'client_end')
        if decision >= args.max_decisions:
            termination = 'max_decisions'
    decisions_log.close()
    ticks_log.close()

    final_xy = body.position_world[:2]
    final_distance = horizontal_distance(final_xy, target['center'])
    # After a V12 termination the body state is the reset pose, not where the robot ended; never score it.
    reset_occurred = bool(status.flags & int(lp.StatusFlag.RESET_OCCURRED))
    record.update({
        'termination': termination, 'decisions': decision, 's2_cycles': s2_cycles,
        'trajectories': trajectories, 'discrete_decisions': discrete,
        'stopped_by_model': stop_sim_ns is not None,
        'stop_sim_s': None if stop_sim_ns is None else stop_sim_ns / 1e9,
        'sim_seconds': body.simulation_time_ns / 1e9,
        'final_xy': list(final_xy), 'final_distance_to_target_m': final_distance,
        'final_pose_is_reset_pose': reset_occurred,
        'success': (stop_sim_ns is not None and not reset_occurred
                    and final_distance <= float(episode['success_radius_m'])),
        'latency_s': {'mean': statistics.mean(latencies), 'median': statistics.median(latencies),
                      'max': max(latencies)} if latencies else None,
        'command_abs_max': {'v': max((abs(c[0]) for c in commands), default=0.0),
                            'w': max((abs(c[1]) for c in commands), default=0.0)},
        'watchdog_events_at_end': status.watchdog_events,
        'mpc_solve_failures': len(mpc_failures), 'mpc_solve_failure_samples': mpc_failures[:5],
    })
    (out / 'client_episode.json').write_text(json.dumps(record, indent=2, default=str) + '\n')
    print('LOCKSTEP_CLIENT_DONE termination={} success={} final_distance_m={:.2f}'.format(
        termination, record['success'], final_distance), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
