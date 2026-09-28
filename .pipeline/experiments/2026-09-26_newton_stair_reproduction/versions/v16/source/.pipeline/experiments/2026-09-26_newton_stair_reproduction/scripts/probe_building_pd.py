"""Bounded factory/PD qualification in the complete archived Building."""
import json
import os
from pathlib import Path

import numpy as np
import warp as wp

wp.config.kernel_cache_dir = os.environ["WARP_CACHE_PATH"]
wp.init()
wp.set_device("cpu")

from robot_scene import StairRobot
from scene_assets import BASE, verify_inputs
from factory_navigation_startup import initialize
from run_local_episode import verify_integration_version


def main():
    out = Path(os.environ["NEWTON_RUN_DIR"])
    version = verify_integration_version(out)
    verify_inputs()
    scenario = json.loads((BASE / "inputs/stair_scenario.json").read_text())
    (out / "inputs").mkdir()
    (out / "inputs/stair_scenario.json").write_text(json.dumps(scenario, indent=2) + "\n")
    request = {"scene": "building_full", "startup_mode": "factory_pd", "stance_hold": True,
               "physics_backend": "warp", "geometry_obstacles": True,
               "integration_version": version, "control_qualification": True}
    (out / "episode_request.json").write_text(json.dumps(request, indent=2) + "\n")
    (out / "backend_states.jsonl").write_text("")
    robot = StairRobot(startup_mode="factory_pd", stance_hold=True,
                       automatic_contact_capacity=True, scenario=scenario)
    rows, frames = [], []
    result = {"passed": False, "version": version, "scope": "Factory and PD only; no navigation"}
    try:
        frames.extend(initialize(robot, out))
        for _ in range(110):
            robot.step([0., 0., 0.])
            row = robot.telemetry()
            rows.append(row)
            if robot.steps % 80 == 0:
                frames.append({"physics_time_s": robot.physics_time(), "body_q": robot.state.body_q.numpy().tolist(),
                               "joint_q": row["joint_q"], "command": [0., 0., 0.],
                               "controller_phase": row["controller_phase"], "stance_mode": row["stance_mode"],
                               "policy_owns_joints": row["policy_owns_joints"], "policy_calls": robot.policy_calls})
        checks = {
            "final_pd_dwell_over_two_seconds": rows[-1]["physics_time_s"]-rows[0]["physics_time_s"] >= 2.,
            "pd_owns_joints": all(r["stance_mode"] == "FIXED_STAND" and not r["policy_owns_joints"] for r in rows),
            "original_hold_gains": all(np.all(np.asarray(r["motor_kp"]) == 60) and np.all(np.asarray(r["motor_kd"]) == 1) for r in rows),
            "measured_foot_support": all(min(r["foot_forces_n"]) >= 10. for r in rows),
            "upright": all(r["base_up_z"] >= .98 for r in rows),
            "ground_relative_body_height": all(r["joint_q"][2]-scenario["spawn_ground_xyz_m"][2] >= .25 for r in rows),
            "motor_force_mapping": robot.max_applied_torque_error < 1e-4,
        }
        result.update(checks={k:bool(v) for k,v in checks.items()}, passed=all(checks.values()),
                      physics_s=robot.physics_time(), physics_steps=robot.steps,
                      building_vertices=len(robot.building_vertices), building_triangles=len(robot.building_faces),
                      building_bounds_m=[robot.building_vertices.min(axis=0).tolist(), robot.building_vertices.max(axis=0).tolist()],
                      final_position=rows[-1]["joint_q"][:3], factory_calibration_validated=False)
        if not result["passed"]:
            raise RuntimeError("Building factory/PD qualification did not pass")
    except BaseException as error:
        result["error"] = repr(error)
        raise
    finally:
        if not frames and (out / "factory_video_states.json").exists():
            frames = json.loads((out / "factory_video_states.json").read_text())
        (out / "video_states.json").write_text(json.dumps(frames) + "\n")
        (out / "telemetry.jsonl").write_text("".join(json.dumps(r)+"\n" for r in rows))
        (out / "stance_status.json").write_text(json.dumps(robot.stance.status(), indent=2) + "\n")
        (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
