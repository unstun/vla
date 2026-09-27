"""Bounded actual-physics startup qualification; no navigation or pose resets."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

import numpy as np

from flat_scene import FlatSceneRobot
from robot_scene import QUALIFIED
from lite3_newton import JOINT_NAMES, EFFORT, check_golden_policy


def main():
    out = Path(os.environ["NEWTON_RUN_DIR"])
    for path in [Path(__file__), Path(__file__).with_name("flat_scene.py"),
                 *[QUALIFIED / "scripts" / name for name in ("lite3_newton.py", "pd_startup.py", "build_sdk_spline.py")]]:
        shutil.copyfile(path, out / ("executed_" + path.name))
    shutil.copyfile(QUALIFIED / "runtime/lite3_sdk_spline/build_identity.json", out / "sdk_build_identity.json")
    (out / "episode_request.json").write_text(json.dumps({"scene": "flat_box", "startup_mode": "pd_stand",
        "startup_qualification": True, "duration_s": 8., "obstacle_used_for_control": False,
        "requested_early_command": [.3, 0., 0.], "early_command_until_s": 3.5}, indent=2) + "\n")
    (out / "backend_states.jsonl").write_text("")
    robot = FlatSceneRobot(None, obstacle_kind="box", startup_mode="pd_stand")
    source = Path(__file__).resolve().parents[1] / "inputs/sensor_rig/lite3_pro_sensor_rig_real_with_interface.urdf"
    joints = {j.get("name"): j for j in ET.parse(source).getroot().findall("joint")}
    lower = np.array([float(joints[n].find("limit").get("lower")) for n in JOINT_NAMES])
    upper = np.array([float(joints[n].find("limit").get("upper")) for n in JOINT_NAMES])
    maxima = {"joint_speed_radps": 0., "joint_limit_excursion_rad": 0., "effort_ratio": 0.,
              "target_step_rad": 0., "torque_step_nm": 0., "handoff_torque_step_nm": 0.}
    previous_target, previous_torque = None, None
    original_observer = robot.contact_observer

    def observe(state, contacts):
        nonlocal previous_target, previous_torque
        original_observer(state, contacts)
        q, qd = state.joint_q.numpy()[robot.q_indices], state.joint_qd.numpy()[robot.qd_indices]
        maxima["joint_speed_radps"] = max(maxima["joint_speed_radps"], float(np.max(np.abs(qd))))
        maxima["joint_limit_excursion_rad"] = max(maxima["joint_limit_excursion_rad"], float(np.max(np.r_[lower-q, q-upper, 0.])))
        maxima["effort_ratio"] = max(maxima["effort_ratio"], float(np.max(np.abs(robot.torque) / EFFORT)))
        if previous_target is not None:
            maxima["target_step_rad"] = max(maxima["target_step_rad"], float(np.max(np.abs(robot.target-previous_target))))
            delta = float(np.max(np.abs(robot.torque-previous_torque)))
            maxima["torque_step_nm"] = max(maxima["torque_step_nm"], delta)
            if robot.startup.phase == "handoff":
                maxima["handoff_torque_step_nm"] = max(maxima["handoff_torque_step_nm"], delta)
        substeps.write(json.dumps({"step": robot.steps, "time_s": robot.steps * .001,
            "phase": robot.startup.phase, "q": q.tolist(), "qd": qd.tolist(),
            "target": robot.target.tolist(), "target_velocity": robot.target_velocity.tolist(),
            "kp": robot.motor_kp, "kd": robot.motor_kd, "torque": robot.torque.tolist()}) + "\n")
        previous_target, previous_torque = robot.target.copy(), robot.torque.copy()

    def frame():
        return {"physics_time_s": robot.physics_time(), "body_q": robot.state.body_q.numpy().tolist(),
                "joint_q": robot.state.joint_q.numpy().tolist(), "command": robot.effective_command.tolist(),
                "controller_phase": robot.startup.phase, "policy_calls": robot.policy_calls,
                "navigation_ready": robot.navigation_ready}

    rows, frames, error = [], [frame()], None
    robot.contact_observer = observe
    try:
        with (out / "substeps.jsonl").open("w") as substeps, (out / "telemetry.jsonl").open("w") as stream:
            for i in range(400):
                requested = np.array([.3, 0., 0.]) if robot.steps < 3500 else np.zeros(3)
                robot.step(requested)
                row = robot.telemetry()
                row["requested_command"] = requested.tolist()
                rows.append(row)
                stream.write(json.dumps(row) + "\n")
                if (i + 1) % 4 == 0:
                    frames.append(frame())
                if (i + 1) % 50 == 0:
                    print(json.dumps({"t": row["physics_time_s"], "phase": row["controller_phase"],
                          "z": row["joint_q"][2], "up": row["base_up_z"], "policy_calls": row["policy_calls"]}), flush=True)
                if row["base_up_z"] < .5:
                    raise RuntimeError("Robot fell during startup qualification")
    except Exception as caught:
        error = repr(caught)
    finally:
        (out / "video_states.json").write_text(json.dumps(frames) + "\n")
        (out / "startup_events.json").write_text(json.dumps(robot.startup.events, indent=2) + "\n")
    initial_z = frames[0]["joint_q"][2]
    policy_rows = [r for r in rows if r["navigation_ready"]]
    checks = {
        "no_runtime_error": error is None,
        "all_phases": [v["phase"] for v in robot.startup.events] == ["crouch", "prepare", "stand", "settle", "handoff", "policy"],
        "base_rose_10cm": bool(policy_rows and min(r["joint_q"][2] for r in policy_rows) - initial_z >= .10),
        "upright_after_handoff": bool(policy_rows and min(r["base_up_z"] for r in policy_rows) >= .95),
        "three_seconds_policy": bool(policy_rows and policy_rows[-1]["physics_time_s"]-policy_rows[0]["physics_time_s"] >= 3.),
        "early_command_blocked": all(max(abs(v) for v in r["effective_command"]) == 0 for r in rows if r["physics_steps"] <= 3500),
        "no_early_inference": all(r["policy_calls"] == 0 for r in rows if r["controller_phase"] not in ("handoff", "policy")),
        "effort_limited": maxima["effort_ratio"] <= 1.000001,
        "full_contact_cadence": robot.contact_scoring["physics_substeps_checked"] == robot.steps,
        "no_obstacle_contact": robot.contact_scoring["touching_substeps"] == 0,
        "golden_policy": check_golden_policy()["passed"],
    }
    result = {"passed": all(checks.values()), "checks": checks, "error": error,
        "physics_steps": robot.steps, "initial_base_z": initial_z,
        "final_base_z": float(robot.state.joint_q.numpy()[2]), "phase_events": robot.startup.events,
        "maxima": maxima, "contact_scoring": robot.contact_scoring,
        "navigation_validated": False, "claim": "Bounded flat startup physics only; no SCAN navigation trial",
        "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob("executed_*.py")}}
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2), flush=True)
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
