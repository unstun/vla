"""Reuse the audited factory algorithm, then hand a measured stand to PD."""
import json
from pathlib import Path
import struct
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2] / "2026-09-27_lite3_factory_runtime_audit"
sys.path.insert(0, str(ROOT))
from factory_process import FactoryProcess
from run_newton_factory import gyro
from lite3_newton import SIM_DT, EFFORT, SPEED, rotation_matrix
from newton_stance import hold_module


def initialize(robot, out):
    if robot.startup_mode != "factory_pd" or robot.stance is None:
        raise ValueError("Factory navigation startup requires its explicit controller profile")
    records, frames, events = [], [], []
    stable_since = None
    last_phase = None
    phases = {1: "crouch", 17: "factory_zero_return", 4: "factory_prepare", 5: "factory_stand", 6: "factory_standing"}
    try:
        with FactoryProcess(out / "factory_process", wall_limit=240) as actor:
            while robot.physics_time() < 14.:
                t = robot.physics_time()
                q, qd = robot.state.joint_q.numpy(), robot.state.joint_qd.numpy()
                measured = np.r_[q[robot.q_indices], qd[robot.qd_indices], robot.applied_torque(), gyro(robot)]
                command = bytearray(552)
                command[73], command[0] = int(t >= 1.), int(t >= 7.5)
                raw = actor.step(struct.pack("<47d552s", t, SIM_DT, *measured, bytes(command)))
                motor = np.frombuffer(raw, dtype="<f8", count=72, offset=288).copy().reshape(6, 12)
                phase, _ = struct.unpack_from("<iI", raw, 2192)
                zero = bool(raw[1984 + 0xbd])
                if (phase, zero) != last_phase:
                    last_phase = (phase, zero)
                    events.append({"time_s": t, "phase": phase, "zero_flag": zero})
                    print(json.dumps(events[-1]), flush=True)
                robot.motor_kp, robot.motor_kd = motor[0], motor[1]
                robot.target, robot.target_velocity = motor[3], motor[4]
                robot._motor_substep(feedforward_torque=motor[2])
                q, qd = robot.state.joint_q.numpy(), robot.state.joint_qd.numpy()
                up = float(rotation_matrix(q[[6, 3, 4, 5]])[2, 2])
                records.append(np.r_[t, phase, zero, measured, motor.ravel(), robot.torque, q, qd, up])
                if up < .5:
                    raise RuntimeError("Factory startup lost upright posture")
                if robot.steps % 80 == 0:
                    frames.append({"physics_time_s": robot.physics_time(), "body_q": robot.state.body_q.numpy().tolist(),
                        "joint_q": q.tolist(), "command": [0., 0., 0.], "controller_phase": phases.get(phase, str(phase)),
                        "stance_mode": "FACTORY", "policy_owns_joints": False, "policy_calls": 0,
                        "navigation_ready": False})
                if robot.steps % 20:
                    continue
                forces = robot.stance.measure()
                stable = (t >= 10.5 and phase == 6 and q[2] >= .25 and up >= .98
                    and np.linalg.norm(qd[:3]) <= .10 and np.linalg.norm(qd[3:6]) <= .5
                    and np.all(forces >= hold_module.ENTRY_FOOT_FORCE_N))
                stable_since = (t if stable_since is None else stable_since) if stable else None
                if stable_since is None or t - stable_since < .5:
                    continue
                joints, velocities = q[robot.q_indices], qd[robot.qd_indices]
                current_force = motor[0] * (motor[3] - joints) + motor[1] * (motor[4] - velocities) + motor[2]
                current_force = np.clip(current_force,
                    np.clip(EFFORT * (-1. - velocities / SPEED), -EFFORT, 0.),
                    np.clip(EFFORT * (1. - velocities / SPEED), 0., EFFORT))
                seed = joints + (current_force + hold_module.HOLD_KD * velocities) / hold_module.HOLD_KP
                robot.stance.boot_standing(seed)
                robot.factory_startup_complete = True
                (out / "factory_handoff.json").write_text(json.dumps({
                    "physics_time_s": robot.physics_time(), "stable_since_s": stable_since,
                    "foot_forces_n": forces.tolist(), "joint_q": joints.tolist(), "joint_qd": velocities.tolist(),
                    "factory_force_nm": current_force.tolist(), "hold_target": seed.tolist(),
                    "new_force_nm": (hold_module.HOLD_KP*(seed-joints)-hold_module.HOLD_KD*velocities).tolist(),
                    "factory_calibration_validated": False, "encoder_model": "ideal_absolute"}, indent=2)+"\n")
                return frames
            raise TimeoutError("No measured factory-to-PD standing gate within 14 seconds")
    finally:
        np.savez_compressed(out / "factory_full_rate.npz", records=np.asarray(records))
        (out / "factory_events.json").write_text(json.dumps(events, indent=2)+"\n")
        (out / "factory_video_states.json").write_text(json.dumps(frames)+"\n")
