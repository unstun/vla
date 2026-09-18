"""Run the pinned Lite3 policy with PhysX, ray-cast LiDAR and TCP bridge.

Isaac imports intentionally happen only after ``AppLauncher`` starts. This
module can therefore be imported by ordinary unit tests without an Isaac kit
runtime.
"""

import argparse
import hashlib
import json
from pathlib import Path
import threading
import time
from typing import Dict, Optional, Sequence

from .command_state import CommandLimits, LatestCommandState
from .isaac_adapter_core import (
    DEFAULT_QUALIFICATION_SCHEDULE,
    assert_command_visible_in_critic,
    canonical_config_sha256,
    quaternion_wxyz_to_xyzw,
    schedule_duration,
    schedule_state,
    world_hits_to_sensor_points,
)
from .protocol import (
    CommandV1,
    MessageType,
    SensorFrameV1,
    StatusFlag,
    StatusV1,
    decode_sensor_payload,
    decode_status_payload,
    encode_frame,
    encode_sensor_payload,
    encode_status_payload,
    pack_xyz_points,
)
from .transport import (
    CommandClient,
    CommandReceiverServer,
    FrameStreamClient,
    TelemetryPublisherServer,
)


PINNED_SOURCE_COMMIT = "2cd9211830becc7a76a7d2182cb46d18dea44a1c"
PINNED_CHECKPOINT_SHA256 = (
    "366aa0579a1a35e70595ab816dab0a8970e797e6175e858071ec968f31453050"
)
PINNED_POLICY_SHA256 = (
    "0141c49a3eb981e4d717008ac41e2d869b5ffb6cc07e9e11ba07a5b670bdd412"
)
DEFAULT_TASK = "Wave-C-Stairs-V17a4-Expert-Lite3-v0"
DEFAULT_SENSOR_TEMPLATE_TASK = "Wave-C-Stairs-V17a4-MED-Lite3-v0"


class AdapterFailure(RuntimeError):
    """A fail-closed qualification or runtime invariant failed."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class _QualificationSender:
    """Drive the command server through its real TCP boundary."""

    def __init__(
        self,
        port: int,
        rate_hz: float,
        limits: CommandLimits,
        schedule=DEFAULT_QUALIFICATION_SCHEDULE,
    ) -> None:
        self._port = port
        self._period = 1.0 / rate_hz
        self._limits = limits
        self._schedule = tuple(schedule)
        if not self._schedule:
            raise ValueError("qualification schedule must not be empty")
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._run, name="lite3-qualification-command-source", daemon=True
        )
        self._started = False
        self.error = None  # type: Optional[BaseException]
        self.started_monotonic = None  # type: Optional[float]

    def start(self) -> None:
        self._started = True
        self._thread.start()

    def _run(self) -> None:
        client = CommandClient("127.0.0.1", self._port, limits=self._limits)
        try:
            deadline = time.monotonic() + 5.0
            while not self._stop.is_set():
                try:
                    client.connect()
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise AdapterFailure("qualification command client could not connect")
                    self._stop.wait(0.05)
            self.started_monotonic = time.monotonic()
            while not self._stop.is_set():
                loop_start = time.monotonic()
                elapsed = loop_start - self.started_monotonic
                if elapsed >= schedule_duration(self._schedule):
                    break
                segment, _ = schedule_state(elapsed, self._schedule)
                if not segment.connected:
                    client.close()
                    self._stop.wait(schedule_duration(self._schedule) - elapsed)
                    break
                client.send_command(CommandV1(*segment.command))
                self._stop.wait(max(0.0, self._period - (time.monotonic() - loop_start)))
        except BaseException as error:  # preserved in the run report
            self.error = error
        finally:
            client.close()

    def stop(self) -> None:
        self._stop.set()
        if self._started:
            self._thread.join(timeout=2.0)


class _TelemetrySink:
    """Exercise and validate telemetry during standalone qualification."""

    def __init__(self, port: int, expected_config_sha256: bytes) -> None:
        self._port = port
        self._expected_config_sha256 = expected_config_sha256
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._run, name="lite3-qualification-telemetry-sink", daemon=True
        )
        self._started = False
        self._lock = threading.Lock()
        self.sensor_frames = 0
        self.status_frames = 0
        self.nonempty_sensor_frames = 0
        self.error = None  # type: Optional[BaseException]

    def start(self) -> None:
        self._started = True
        self._thread.start()

    def _run(self) -> None:
        client = FrameStreamClient("127.0.0.1", self._port, timeout_seconds=1.0)
        try:
            deadline = time.monotonic() + 5.0
            while not self._stop.is_set():
                try:
                    client.connect()
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise AdapterFailure("qualification telemetry sink could not connect")
                    self._stop.wait(0.05)
            while not self._stop.is_set():
                try:
                    frame = client.receive()
                except TimeoutError:
                    continue
                if frame.header.message_type == MessageType.SENSOR_FRAME_V1:
                    sensor = decode_sensor_payload(frame.payload)
                    if sensor.config_sha256 != self._expected_config_sha256:
                        raise AdapterFailure("telemetry config hash changed during run")
                    with self._lock:
                        self.sensor_frames += 1
                        self.nonempty_sensor_frames += int(sensor.point_count > 0)
                elif frame.header.message_type == MessageType.STATUS_V1:
                    decode_status_payload(frame.payload)
                    with self._lock:
                        self.status_frames += 1
        except (EOFError, OSError):
            if not self._stop.is_set():
                self.error = AdapterFailure("telemetry stream ended unexpectedly")
        except BaseException as error:  # preserved in the run report
            self.error = error
        finally:
            client.close()

    def snapshot(self) -> Dict[str, int]:
        with self._lock:
            return {
                "sensor_frames": self.sensor_frames,
                "status_frames": self.status_frames,
                "nonempty_sensor_frames": self.nonempty_sensor_frames,
            }

    def stop(self) -> None:
        self._stop.set()
        if self._started:
            self._thread.join(timeout=2.0)


def _configure_deterministic_runtime(env_cfg) -> None:
    events = getattr(env_cfg, "events", None)
    if events is not None:
        for name in (
            "randomize_rigid_body_mass_base",
            "randomize_rigid_body_mass_others",
            "randomize_com_positions",
            "randomize_actuator_gains",
            "randomize_motor_zero_offset",
            "randomize_push_robot",
            "randomize_apply_external_force_torque",
            "randomize_rigid_body_material",
        ):
            if hasattr(events, name):
                setattr(events, name, None)
        if getattr(events, "reset_robot_joints", None) is not None:
            events.reset_robot_joints.params["position_range"] = (1.0, 1.0)
            events.reset_robot_joints.params["velocity_range"] = (0.0, 0.0)
        if getattr(events, "reset_base", None) is not None:
            events.reset_base.params["pose_range"] = {
                "x": (0.0, 0.0),
                "y": (0.0, 0.0),
                "z": (0.0, 0.0),
                "yaw": (0.0, 0.0),
            }
            events.reset_base.params["velocity_range"] = {
                axis: (0.0, 0.0)
                for axis in ("x", "y", "z", "roll", "pitch", "yaw")
            }
    curriculum = getattr(env_cfg, "curriculum", None)
    if curriculum is not None:
        for name in (
            "terrain_levels",
            "command_levels_lin_vel",
            "command_levels_ang_vel",
            "base_linear_velocity",
            "base_height_l2",
        ):
            if hasattr(curriculum, name):
                setattr(curriculum, name, None)
    command_cfg = env_cfg.commands.base_velocity
    command_cfg.dynamic_resample_commands = False
    command_cfg.command_range_curriculum = []
    command_cfg.zero_command_curriculum = None
    command_cfg.limit_vel_prob = 0.0
    command_cfg.limit_ang_vel_at_zero_command_prob = 0.0
    command_cfg.resampling_time = 1000.0
    command_cfg.resampling_time_range = (1000.0, 1000.0)
    command_cfg.ranges.lin_vel_x = (0.0, 0.0)
    command_cfg.ranges.lin_vel_y = (0.0, 0.0)
    command_cfg.ranges.ang_vel_yaw = (0.0, 0.0)


def _make_environment(args):
    import copy
    import gymnasium as gym
    from isaaclab.sensors import MultiMeshRayCasterCfg, patterns
    from isaaclab_tasks.utils.parse_cfg import load_cfg_from_registry

    __import__("robot_lab.tasks")
    env_cfg = load_cfg_from_registry(args.task, "env_cfg_entry_point")
    sensor_template_cfg = load_cfg_from_registry(
        args.sensor_template_task, "env_cfg_entry_point"
    )
    env_cfg.scene.num_envs = 1
    env_cfg.sim.device = args.device
    env_cfg.seed = args.seed
    env_cfg.sim.enable_scene_query_support = True
    env_cfg.scene.terrain.terrain_generator.bind_teacher(args.expert_index)
    _configure_deterministic_runtime(env_cfg)

    lidar_cfg = copy.deepcopy(sensor_template_cfg.scene.lidar_height_scanner)
    if not isinstance(lidar_cfg, MultiMeshRayCasterCfg):
        raise AdapterFailure("navigation LiDAR requires MultiMeshRayCasterCfg")
    lidar_cfg.prim_path = "{ENV_REGEX_NS}/Robot/mid360_scan_frame"
    lidar_cfg.offset.pos = (0.0, 0.0, 0.0)
    lidar_cfg.offset.rot = (1.0, 0.0, 0.0, 0.0)
    lidar_cfg.ray_alignment = "base"
    lidar_cfg.update_period = args.sensor_period
    lidar_cfg.pattern_cfg = patterns.LidarPatternCfg(
        channels=args.lidar_channels,
        vertical_fov_range=(args.lidar_vertical_min, args.lidar_vertical_max),
        horizontal_fov_range=(-180.0, 180.0),
        horizontal_res=args.lidar_horizontal_resolution,
    )
    lidar_cfg.max_distance = args.lidar_max_range
    lidar_cfg.update_mesh_ids = False
    lidar_cfg.mesh_prim_paths = ["/World/ground"]
    setattr(env_cfg.scene, "navigation_lidar", lidar_cfg)

    env = gym.make(args.task, cfg=env_cfg, render_mode=None).unwrapped
    observations, _ = env.reset()
    return env, observations


def _tensor_list(tensor) -> Sequence[float]:
    return [float(value) for value in tensor.detach().cpu().flatten().tolist()]


def _qualification_report(records, sink, command_stats, telemetry_stats) -> Dict[str, object]:
    checks = {}
    checks["records_present"] = bool(records)
    checks["no_termination"] = bool(records) and not any(row["done"] for row in records)
    checks["finite_policy"] = bool(records) and all(row["finite"] for row in records)
    checks["command_visible"] = bool(records) and max(
        row["command_observation_max_error"] for row in records
    ) <= 1.0e-5
    supported_fraction = (
        sum(row["contact_count"] >= 2 for row in records) / len(records)
        if records
        else 0.0
    )
    minimum_root_height = (
        min(row["root_pos_w"][2] for row in records) if records else None
    )
    checks["supported_sample_fraction_value"] = supported_fraction
    checks["minimum_root_height_m_value"] = minimum_root_height
    checks["support"] = (
        bool(records)
        and supported_fraction >= 0.90
        and minimum_root_height is not None
        and minimum_root_height >= 0.20
    )
    checks["watchdog_zero"] = any(
        row["command_reason"] in ("disconnected", "watchdog_timeout")
        and row["applied_command"] == [0.0, 0.0, 0.0]
        for row in records
    )
    directional = {
        "forward": ("root_lin_vel_b", 0),
        "lateral": ("root_lin_vel_b", 1),
        "yaw": ("root_ang_vel_b", 2),
    }
    for name, (field, index) in directional.items():
        samples = [
            row[field][index]
            for row in records
            if row["schedule_segment"] == name
            and row["schedule_segment_elapsed_seconds"] >= 0.75
        ]
        mean = sum(samples) / len(samples) if samples else None
        checks[name + "_response"] = bool(samples) and mean > 0.03
        checks[name + "_mean"] = mean
    checks["telemetry_nonempty"] = (
        sink.get("sensor_frames", 0) > 0
        and sink.get("nonempty_sensor_frames", 0) == sink.get("sensor_frames", 0)
        and sink.get("status_frames", 0) > 0
    )
    required_checks = (
        "records_present",
        "no_termination",
        "finite_policy",
        "command_visible",
        "support",
        "watchdog_zero",
        "forward_response",
        "lateral_response",
        "yaw_response",
        "telemetry_nonempty",
    )
    passed = all(bool(checks[key]) for key in required_checks)
    return {
        "schema_version": 1,
        "status": "PASS" if passed else "FAIL",
        "claim": "locomotion qualification only; not SCAN closed-loop validation",
        "checks": checks,
        "telemetry_sink": sink,
        "command_transport": command_stats.__dict__,
        "telemetry_transport": telemetry_stats.__dict__,
        "record_count": len(records),
    }


def _run(args) -> int:
    import torch

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_sha = _sha256(args.teacher_checkpoint)
    policy_sha = _sha256(args.teacher_policy)
    if args.source_commit != PINNED_SOURCE_COMMIT:
        raise AdapterFailure("source commit is not the reviewed V17.4 pin")
    if checkpoint_sha != PINNED_CHECKPOINT_SHA256:
        raise AdapterFailure("teacher checkpoint hash mismatch")
    if policy_sha != PINNED_POLICY_SHA256:
        raise AdapterFailure("exported teacher policy hash mismatch")
    if args.command_host != "127.0.0.1" or args.telemetry_host != "127.0.0.1":
        raise AdapterFailure("v1 endpoints must bind to 127.0.0.1")

    config_identity = {
        "schema_version": 1,
        "source_commit": args.source_commit,
        "checkpoint_sha256": checkpoint_sha,
        "policy_sha256": policy_sha,
        "task": args.task,
        "sensor_template_task": args.sensor_template_task,
        "expert_index": args.expert_index,
        "seed": args.seed,
        "device": args.device,
        "command_limits": [args.max_vx, args.max_vy, args.max_wz],
        "watchdog_seconds": args.watchdog_seconds,
        "sensor": {
            "backend": "IsaacLab MultiMeshRayCaster LidarPatternCfg",
            "truth_pose": True,
            "channels": args.lidar_channels,
            "vertical_fov_degrees": [args.lidar_vertical_min, args.lidar_vertical_max],
            "horizontal_fov_degrees": [-180.0, 180.0],
            "horizontal_resolution_degrees": args.lidar_horizontal_resolution,
            "minimum_range_m": args.lidar_min_range,
            "maximum_range_m": args.lidar_max_range,
            "period_seconds": args.sensor_period,
            "frame": "mid360_scan_frame",
        },
    }
    config_sha256 = canonical_config_sha256(config_identity)
    config_identity["config_sha256"] = config_sha256.hex()
    _write_json(output_dir / "run_identity.json", config_identity)

    limits = CommandLimits(args.max_vx, args.max_vy, args.max_wz)
    command_state = LatestCommandState(
        limits,
        timeout_ns=int(args.watchdog_seconds * 1.0e9),
        max_source_age_ns=int(args.watchdog_seconds * 1.0e9),
        max_future_skew_ns=25_000_000,
    )
    command_server = CommandReceiverServer(command_state, args.command_host, args.command_port)
    telemetry_server = TelemetryPublisherServer(args.telemetry_host, args.telemetry_port)
    command_server.start()
    telemetry_server.start()
    qualification_sender = None
    telemetry_sink = None
    if args.mode == "qualification":
        telemetry_sink = _TelemetrySink(args.telemetry_port, config_sha256)
        qualification_sender = _QualificationSender(args.command_port, 50.0, limits)

    env = None
    records = []
    telemetry_sequence = 0
    dropped_frames = 0
    runtime_error = None
    metrics_path = output_dir / "metrics.jsonl"
    start_wall = None
    schedule_start = None
    try:
        env, _ = _make_environment(args)
        policy = torch.jit.load(str(args.teacher_policy), map_location=args.device)
        policy.eval()
        robot = env.scene["robot"]
        lidar = env.scene.sensors["navigation_lidar"]
        contact = env.scene.sensors["contact_forces"]
        _, foot_names = robot.find_bodies(
            ["FL_FOOT", "FR_FOOT", "HL_FOOT", "HR_FOOT"], preserve_order=True
        )
        contact_foot_ids, contact_names = contact.find_bodies(
            ["FL_FOOT", "FR_FOOT", "HL_FOOT", "HR_FOOT"], preserve_order=True
        )
        if len(foot_names) != 4 or len(contact_foot_ids) != 4:
            raise AdapterFailure(
                f"foot binding mismatch: robot={foot_names}, contact={contact_names}"
            )
        if telemetry_sink is not None:
            telemetry_sink.start()
        if qualification_sender is not None:
            qualification_sender.start()
        previous_actions = torch.zeros((1, 12), device=env.device)
        sensor_stride = max(1, int(round(args.sensor_period / float(env.step_dt))))
        run_seconds = schedule_duration() + 0.25 if args.mode == "qualification" else args.duration_seconds
        start_wall = time.monotonic()
        next_tick = time.monotonic()
        with metrics_path.open("w", encoding="utf-8") as metrics_file:
            step = 0
            while time.monotonic() - start_wall < run_seconds:
                tick_started = time.monotonic()
                if qualification_sender is not None:
                    if qualification_sender.error is not None:
                        raise AdapterFailure(
                            f"qualification sender failed: {qualification_sender.error}"
                        )
                    if qualification_sender.started_monotonic is not None:
                        schedule_start = qualification_sender.started_monotonic
                snapshot = command_server.snapshot(time.monotonic_ns())
                command_values = (
                    snapshot.command.vx,
                    snapshot.command.vy,
                    snapshot.command.wz,
                )
                command_term = env.command_manager.get_term("base_velocity")
                _, _, terminated, truncated, _ = env.step(previous_actions)
                # V17's route command term is expected to update during
                # env.step(). Navigation owns the next policy command, so
                # reassert it after physics and recompute the history-free
                # teacher critic observation before inference.
                command_term.commands[:, 0] = command_values[0]
                command_term.commands[:, 1] = command_values[1]
                command_term.commands[:, 2] = command_values[2]
                actor_obs = env.observation_manager.compute_group(
                    "critic", update_history=False
                )
                if tuple(actor_obs.shape) != (1, 275):
                    raise AdapterFailure(
                        f"teacher observation shape {tuple(actor_obs.shape)} != (1, 275)"
                    )
                observed_command = assert_command_visible_in_critic(
                    _tensor_list(actor_obs[0]), command_values
                )
                with torch.inference_mode():
                    actions = policy(actor_obs)
                if tuple(actions.shape) != (1, 12):
                    raise AdapterFailure(
                        f"teacher action shape {tuple(actions.shape)} != (1, 12)"
                    )
                previous_actions = actions

                force_norm = torch.linalg.vector_norm(contact.data.net_forces_w[0], dim=-1)
                contact_count = int(
                    (force_norm[contact_foot_ids] >= args.contact_force_threshold).sum().item()
                )
                nonfoot_ids = [
                    index for index in range(force_norm.shape[0]) if index not in contact_foot_ids
                ]
                nonfoot_max = float(force_norm[nonfoot_ids].max().item()) if nonfoot_ids else 0.0
                done = bool((terminated | truncated).any().item())
                finite = bool(
                    torch.isfinite(actor_obs).all().item()
                    and torch.isfinite(actions).all().item()
                    and torch.isfinite(robot.data.root_state_w).all().item()
                )
                now = time.monotonic()
                elapsed_schedule = max(0.0, now - schedule_start) if schedule_start is not None else 0.0
                segment, segment_elapsed = schedule_state(elapsed_schedule)
                row = {
                    "step": step,
                    "wall_elapsed_seconds": now - start_wall,
                    "sim_time_seconds": float(env.sim.current_time),
                    "schedule_segment": segment.name if args.mode == "qualification" else "external",
                    "schedule_segment_elapsed_seconds": segment_elapsed,
                    "applied_command": list(command_values),
                    "command_sequence": snapshot.sequence,
                    "command_reason": snapshot.reason,
                    "command_stale": snapshot.stale,
                    "command_observation": list(observed_command),
                    "command_observation_max_error": max(
                        abs(left - right) for left, right in zip(observed_command, command_values)
                    ),
                    "command_transition_priming_steps": 0,
                    "root_pos_w": _tensor_list(robot.data.root_pos_w[0]),
                    "root_quat_wxyz": _tensor_list(robot.data.root_quat_w[0]),
                    "root_lin_vel_w": _tensor_list(robot.data.root_lin_vel_w[0]),
                    "root_ang_vel_w": _tensor_list(robot.data.root_ang_vel_w[0]),
                    "root_lin_vel_b": _tensor_list(robot.data.root_lin_vel_b[0]),
                    "root_ang_vel_b": _tensor_list(robot.data.root_ang_vel_b[0]),
                    "actions": _tensor_list(actions[0]),
                    "joint_position": _tensor_list(robot.data.joint_pos[0]),
                    "joint_velocity": _tensor_list(robot.data.joint_vel[0]),
                    "applied_torque": _tensor_list(robot.data.applied_torque[0]),
                    "contact_count": contact_count,
                    "nonfoot_contact_max_n": nonfoot_max,
                    "done": done,
                    "finite": finite,
                    "watchdog_events": snapshot.watchdog_events,
                    "sequence_gaps": snapshot.sequence_gaps,
                }
                records.append(row)
                metrics_file.write(json.dumps(row, sort_keys=True) + "\n")
                metrics_file.flush()

                if step % sensor_stride == 0:
                    lidar.update(dt=0.0, force_recompute=True)
                    sensor_position = _tensor_list(lidar.data.pos_w[0])
                    sensor_quaternion_wxyz = _tensor_list(lidar.data.quat_w[0])
                    points = world_hits_to_sensor_points(
                        lidar.data.ray_hits_w[0].detach().cpu().tolist(),
                        sensor_position,
                        sensor_quaternion_wxyz,
                        args.lidar_min_range,
                        args.lidar_max_range,
                    )
                    point_count, point_bytes = pack_xyz_points(points)
                    sensor_payload = encode_sensor_payload(
                        SensorFrameV1(
                            body_position=tuple(_tensor_list(robot.data.root_pos_w[0])),
                            body_quaternion_xyzw=quaternion_wxyz_to_xyzw(
                                _tensor_list(robot.data.root_quat_w[0])
                            ),
                            sensor_position=tuple(sensor_position),
                            sensor_quaternion_xyzw=quaternion_wxyz_to_xyzw(sensor_quaternion_wxyz),
                            config_sha256=config_sha256,
                            point_count=point_count,
                            points_xyz_f32_be=point_bytes,
                        )
                    )
                    telemetry_sequence += 1
                    sensor_sent = telemetry_server.publish(
                        encode_frame(
                            MessageType.SENSOR_FRAME_V1,
                            telemetry_sequence,
                            int(float(env.sim.current_time) * 1.0e9),
                            sensor_payload,
                        )
                    )
                    dropped_frames += int(not sensor_sent)
                    flags = 0
                    if contact_count >= 2:
                        flags |= int(StatusFlag.CONTACT_SUPPORTED)
                    if nonfoot_max >= args.collision_force_threshold:
                        flags |= int(StatusFlag.COLLISION)
                    if done:
                        flags |= int(StatusFlag.TERMINATED)
                    if not finite:
                        flags |= int(StatusFlag.NAN_DETECTED)
                    latency_ms = (
                        0.0
                        if snapshot.received_monotonic_ns is None
                        else max(
                            0.0,
                            (time.monotonic_ns() - snapshot.received_monotonic_ns) / 1.0e6,
                        )
                    )
                    telemetry_sequence += 1
                    status_sent = telemetry_server.publish(
                        encode_frame(
                            MessageType.STATUS_V1,
                            telemetry_sequence,
                            int(float(env.sim.current_time) * 1.0e9),
                            encode_status_payload(
                                StatusV1(
                                    physics_hz=1.0 / float(env.physics_dt),
                                    policy_hz=1.0 / float(env.step_dt),
                                    sensor_hz=1.0 / args.sensor_period,
                                    bridge_latency_ms=latency_ms,
                                    contact_count=contact_count,
                                    dropped_frames=dropped_frames,
                                    watchdog_events=snapshot.watchdog_events,
                                    flags=flags,
                                    termination_code=1 if done else 0,
                                )
                            ),
                        )
                    )
                    dropped_frames += int(not status_sent)
                if done or not finite:
                    raise AdapterFailure("termination or non-finite state during qualification")
                step += 1
                next_tick += float(env.step_dt)
                time.sleep(max(0.0, next_tick - time.monotonic()))
                if time.monotonic() - tick_started > args.max_step_wall_seconds:
                    raise AdapterFailure("simulation step exceeded wall-time safety limit")
    except BaseException as error:
        runtime_error = error
    finally:
        if qualification_sender is not None:
            qualification_sender.stop()
        if env is not None:
            env.close()
        if telemetry_sink is not None:
            telemetry_sink.stop()
        command_server.stop()
        telemetry_server.stop()

    sink_snapshot = telemetry_sink.snapshot() if telemetry_sink is not None else {}
    if telemetry_sink is not None and telemetry_sink.error is not None and runtime_error is None:
        runtime_error = telemetry_sink.error
    report = _qualification_report(
        records, sink_snapshot, command_server.stats(), telemetry_server.stats()
    )
    report["runtime_error"] = None if runtime_error is None else {
        "type": type(runtime_error).__name__,
        "message": str(runtime_error),
    }
    if runtime_error is not None:
        report["status"] = "INSTRUMENTATION_ERROR"
    _write_json(output_dir / "qualification_report.json", report)
    print(json.dumps({"status": report["status"], "output_dir": str(output_dir)}), flush=True)
    return 0 if report["status"] == "PASS" else 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("qualification", "external"), default="qualification")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--teacher-checkpoint", type=Path, required=True)
    parser.add_argument("--teacher-policy", type=Path, required=True)
    parser.add_argument("--source-commit", default=PINNED_SOURCE_COMMIT)
    parser.add_argument("--task", default=DEFAULT_TASK)
    parser.add_argument("--sensor-template-task", default=DEFAULT_SENSOR_TEMPLATE_TASK)
    parser.add_argument("--expert-index", type=int, default=3)
    parser.add_argument("--seed", type=int, default=47)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--duration-seconds", type=float, default=10.0)
    parser.add_argument("--command-host", default="127.0.0.1")
    parser.add_argument("--command-port", type=int, default=46001)
    parser.add_argument("--telemetry-host", default="127.0.0.1")
    parser.add_argument("--telemetry-port", type=int, default=46000)
    parser.add_argument("--max-vx", type=float, default=0.75)
    parser.add_argument("--max-vy", type=float, default=0.35)
    parser.add_argument("--max-wz", type=float, default=1.0)
    parser.add_argument("--watchdog-seconds", type=float, default=0.25)
    parser.add_argument("--sensor-period", type=float, default=0.10)
    parser.add_argument("--lidar-channels", type=int, default=16)
    parser.add_argument("--lidar-vertical-min", type=float, default=-7.0)
    parser.add_argument("--lidar-vertical-max", type=float, default=52.0)
    parser.add_argument("--lidar-horizontal-resolution", type=float, default=2.0)
    parser.add_argument("--lidar-min-range", type=float, default=0.10)
    parser.add_argument("--lidar-max-range", type=float, default=12.0)
    parser.add_argument("--contact-force-threshold", type=float, default=5.0)
    parser.add_argument("--collision-force-threshold", type=float, default=75.0)
    parser.add_argument("--max-step-wall-seconds", type=float, default=5.0)
    return parser


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    for path in (args.teacher_checkpoint, args.teacher_policy):
        if not path.is_file():
            raise SystemExit(f"required immutable payload file is missing: {path}")
    from isaaclab.app import AppLauncher

    simulation_app = AppLauncher(headless=True, enable_cameras=False, device=args.device).app
    try:
        return _run(args)
    finally:
        simulation_app.close()


if __name__ == "__main__":
    raise SystemExit(main())
