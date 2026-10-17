"""Run original factory algorithm against continuous Newton physics.

Newton supplies ideal absolute joint angles. Motor encoder ambiguity is absent;
the hardware caller's turn correction is diagnosed, never silently fabricated.
This test cannot validate physical factory calibration equivalence.
"""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys
import time
import xml.etree.ElementTree as ET

import numpy as np

from factory_process import FactoryProcess, ROOT

EXPERIMENTS = ROOT.parent
SCENE = EXPERIMENTS / "2026-09-26_newton_stair_reproduction"
sys.path.insert(0, str(SCENE / "scripts"))
from flat_scene import FlatSceneRobot
from robot_scene import QUALIFIED
from lite3_newton import EFFORT, JOINT_NAMES, SIM_DT, rotation_matrix


def gyro(robot):
    q, qd = robot.state.joint_q.numpy(), robot.state.joint_qd.numpy()
    matrix = rotation_matrix(q[[6, 3, 4, 5]])
    pitch = np.arcsin(np.clip(-matrix[2, 0], -1, 1))
    roll = np.arctan2(matrix[2, 1], matrix[2, 2])
    yaw = np.arctan2(matrix[1, 0], matrix[0, 0])
    angular = matrix.T @ qd[3:6]
    specific_force = matrix.T @ (robot.native_array("qacc")[:3] + [0., 0., 9.81])
    # Factory GyroDataProcess 0x108618 converts only the three angles from degrees.
    return np.r_[np.degrees([roll, pitch, yaw]), angular, specific_force]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--duration", type=float, default=12.0)
    args = parser.parse_args()
    if not args.run.replace("_", "").isalnum() or not 1 <= args.duration <= 14:
        raise ValueError("invalid bounded run")
    out = SCENE / "runs" / args.run
    out.mkdir(parents=True, exist_ok=False)
    source = SCENE / "inputs/sensor_rig/lite3_pro_sensor_rig_real_with_interface.urdf"
    code = [Path(__file__), ROOT / "factory_actor.cpp", ROOT / "factory_process.py",
            ROOT / "prepare_algorithm_inputs.py", QUALIFIED / "scripts/lite3_newton.py",
            SCENE / "scripts/flat_scene.py"]
    for path in code:
        shutil.copyfile(path, out / ("executed_" + path.name))
    request = {"scene": "flat_box", "startup_mode": "pd_stand", "startup_qualification": True,
               "factory_runtime": True, "duration_s": args.duration, "zero_request_s": 1.,
               "stand_request_s": 7.5, "encoder_model": "ideal_absolute",
               "factory_calibration_validated": False,
               "renderer_caption": "Factory algorithm | crouch > zero-return torque > stand",
               "renderer_footer": "Continuous Newton physics | ideal encoders | mechanical calibration unvalidated"}
    (out / "episode_request.json").write_text(json.dumps(request, indent=2) + "\n")
    (out / "backend_states.jsonl").write_text("")
    joints = {e.get("name"): e for e in ET.parse(source).getroot().findall("joint")}
    lower = np.array([float(joints[n].find("limit").get("lower")) for n in JOINT_NAMES])
    upper = np.array([float(joints[n].find("limit").get("upper")) for n in JOINT_NAMES])
    robot = FlatSceneRobot(None, obstacle_kind="box", startup_mode="pd_stand")
    phases = {1: "crouch", 17: "factory_zero_return", 4: "factory_prepare", 5: "factory_stand", 6: "factory_standing"}
    frames, events, records, reply_records = [], [], [], []
    last_event = None
    zero_measurements = []
    error = None
    phase = 1
    started = time.monotonic()

    def frame():
        return {"physics_time_s": robot.physics_time(), "body_q": robot.state.body_q.numpy().tolist(),
                "joint_q": robot.state.joint_q.numpy().tolist(), "command": [0., 0., 0.],
                "controller_phase": phases.get(phase, f"factory_state_{phase}"),
                "policy_calls": 0, "navigation_ready": False}

    frames.append(frame())
    try:
        with FactoryProcess(out / "factory_process", wall_limit=240) as actor:
            for i in range(round(args.duration / SIM_DT)):
                if time.monotonic() - started > 240:
                    raise TimeoutError("bounded Newton trial wall deadline")
                t = robot.physics_time()
                q, qd = robot.state.joint_q.numpy(), robot.state.joint_qd.numpy()
                measured = np.r_[q[robot.q_indices], qd[robot.qd_indices], robot.applied_torque(), gyro(robot)]
                command = bytearray(552)
                command[73] = int(t + 1e-8 >= request["zero_request_s"])
                command[0] = int(t + 1e-8 >= request["stand_request_s"])
                raw = actor.step(struct.pack("<47d552s", t, SIM_DT, *measured, bytes(command)))
                motor = np.frombuffer(raw, dtype="<f8", count=72, offset=288).copy().reshape(6, 12)
                basic, gait, policy = struct.unpack_from("<3i", raw, 1984)
                phase, cycle = struct.unpack_from("<iI", raw, 2192)
                zero = bool(raw[1984 + 0xbd])
                event = (phase, basic, zero)
                if event != last_event:
                    events.append({"time_s": t, "phase": phase, "basic_state": basic, "zero_flag": zero})
                    print(json.dumps(events[-1]), flush=True)
                    last_event = event
                if zero:
                    zero_measurements.append({"time_s": t, "joint_q": measured[:12].tolist()})
                robot.motor_kp, robot.motor_kd = motor[0], motor[1]
                robot.target, robot.target_velocity = motor[3], motor[4]
                robot._motor_substep(feedforward_torque=motor[2])
                after_q, after_qd = robot.state.joint_q.numpy(), robot.state.joint_qd.numpy()
                up = rotation_matrix(after_q[[6, 3, 4, 5]])[2, 2]
                records.append(np.r_[t, phase, int(zero), measured, motor.ravel(), robot.torque,
                                     after_q, after_qd, up])
                reply_records.append(np.frombuffer(raw, dtype=np.uint8))
                if robot.steps % 80 == 0:
                    frames.append(frame())
                if robot.steps % 1000 == 0:
                    print(json.dumps({"physics_s": robot.physics_time(), "phase": phase,
                                      "height_m": float(after_q[2]), "up": float(up)}), flush=True)
                if not np.isfinite(after_qd).all() or up < 0.35:
                    raise RuntimeError("robot lost upright posture in factory trial")
    except Exception as caught:
        error = repr(caught)
    finally:
        if frames[-1]["physics_time_s"] != robot.physics_time():
            frames.append(frame())
        (out / "video_states.json").write_text(json.dumps(frames) + "\n")
        (out / "factory_events.json").write_text(json.dumps(events, indent=2) + "\n")
        (out / "zero_measurements.json").write_text(json.dumps(zero_measurements, indent=2) + "\n")
        np.savez_compressed(out / "full_rate.npz", records=np.array(records),
                            factory_replies=np.array(reply_records), joint_lower=lower, joint_upper=upper)
    data = np.array(records)
    # Layout: t/phase/flag [0:3], input [3:48], motor [48:120], applied [120:132],
    # post-step q [132:151], qd [151:169], body up [169].
    standing = data[data[:, 0] >= 10] if len(data) else np.empty((0, 170))
    checks = {"no_runtime_error": error is None, "zero_phase_seen": any(e["phase"] == 17 for e in events),
              "zero_flag_seen": bool(zero_measurements), "stand_phase_seen": any(e["phase"] == 5 for e in events),
              "standing_two_seconds": bool(len(standing) >= 1900 and np.min(standing[:, 134]) > .25
                                           and np.min(standing[:, 169]) > .95),
              "standing_in_place": bool(len(standing) and np.max(np.linalg.norm(standing[:, 132:134], axis=1)) < .1),
              "standing_low_speed": bool(len(standing) and np.max(np.linalg.norm(standing[:, 151:154], axis=1)) < .1),
              "force_mapping": robot.max_applied_torque_error < 1e-4,
              "continuous_clock": abs(robot.physics_time() - robot.steps * SIM_DT) < 1e-7}
    result = {"algorithm_physics_checks": checks, "algorithm_physics_passed": all(checks.values()),
              "factory_calibration_validated": False, "error": error, "steps": robot.steps,
              "physics_time_s": robot.physics_time(), "events": events,
              "max_applied_force_error": robot.max_applied_torque_error,
              "final_position": robot.state.joint_q.numpy()[:3].tolist(),
              "original_urdf_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in code},
              "claim": "Original factory algorithm with Newton ideal absolute encoders; mechanical zero-reference equivalence unvalidated"}
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2), flush=True)
    if error:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
