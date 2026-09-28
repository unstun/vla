"""Continuous actual-physics control qualification, without planner commands."""
import json
import argparse
import os
from pathlib import Path

import numpy as np
import warp as wp
wp.config.kernel_cache_dir = os.environ["WARP_CACHE_PATH"]
wp.init()
wp.set_device("cpu")
from flat_scene import FlatSceneRobot


def main():
    out = Path(os.environ["NEWTON_RUN_DIR"])
    parser = argparse.ArgumentParser()
    parser.add_argument("--factory", action="store_true")
    parser.add_argument("--wait-for-hold", action="store_true")
    parser.add_argument("--native-cpu", action="store_true")
    args = parser.parse_args()
    robot = FlatSceneRobot(None, obstacle_kind="none", stance_hold=True,
                           startup_mode="factory_pd" if args.factory else "policy", native_cpu=args.native_cpu)
    if args.factory:
        from factory_navigation_startup import initialize
        initialize(robot, out)
    rows = []
    sequence, phase_started, hold_since = 0, robot.physics_time(), None
    max_steps = 4000 if args.wait_for_hold else 1500
    (out / "qualification_request.json").write_text(json.dumps({
        "factory": args.factory, "wait_for_hold": args.wait_for_hold,
        "physics_backend": "native" if args.native_cpu else "warp",
        "max_control_seconds": max_steps*.02, "walk_duration_s": 4., "pd_dwell_s": 2.}, indent=2)+"\n")
    with (out / "telemetry.jsonl").open("w") as stream:
        for i in range(max_steps):
            t = i * .02
            moving = sequence in (1,3) if args.wait_for_hold else (6 <= t < 10 or 18 <= t < 22)
            command = [.4, 0., 0.] if moving else [0., 0., 0.]
            robot.step(command)
            row = robot.telemetry()
            stream.write(json.dumps(row)+"\n")
            rows.append(row)
            if args.wait_for_hold:
                now = robot.physics_time()
                if moving and now-phase_started >= 4.:
                    sequence += 1
                    phase_started, hold_since = now, None
                elif not moving:
                    held = row["stance_mode"] == "FIXED_STAND"
                    hold_since = (now if hold_since is None else hold_since) if held else None
                    if hold_since is not None and now-hold_since >= 2.:
                        sequence += 1
                        phase_started, hold_since = now, None
                        if sequence == 5:
                            break
            if i % 100 == 0:
                print(t, row["stance_mode"], row["joint_q"][:3], row["foot_forces_n"], flush=True)
    hold = [r for r in rows if r["stance_mode"] == "FIXED_STAND"]
    status = robot.stance.status()
    checks = {
        "three_pd_holds": status["hold"]["counters"]["fixed_stand"] >= 3,
        "two_rejoins": status["hold"]["counters"]["rejoin_complete"] >= 2,
        "hold_owns_joints": bool(hold) and all(not r["policy_owns_joints"] for r in hold),
        "hold_gains": bool(hold) and all(np.all(np.asarray(r["motor_kp"]) == 60) and np.all(np.asarray(r["motor_kd"]) == 1) for r in hold),
        "positive_foot_support": bool(hold) and all(min(r["foot_forces_n"]) > 1 for r in hold),
        "actual_motion": rows[-1]["joint_q"][0] - rows[0]["joint_q"][0] > 2.,
        "upright": min(r["base_up_z"] for r in rows) > .95,
        "height": min(r["joint_q"][2] for r in rows) > .25,
        "applied_action_history": all(np.max(np.abs(np.asarray(b["observation"])[33:45] - np.asarray(a["action"]))) < 1e-6 for a,b in zip(rows, rows[1:])),
        "force_mapping": robot.max_applied_torque_error < 1e-4,
    }
    result = {"passed": all(checks.values()), "checks": checks, "stance": status,
              "physics_s": robot.physics_time(), "physics_steps": robot.steps}
    (out / "result.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result, indent=2), flush=True)
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
