"""Model-disconnected Lite3 contract and physical locomotion smoke."""
from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import mujoco
import numpy as np
from PIL import Image

from vln_mujoco.robots.lite3 import History, Lite3Backend, Q0, rotation_matrix


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pkg", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    checks = {}
    history = History()
    frame = np.arange(45, dtype=np.float32)
    first = history.push(frame)
    boundaries = (0, 3, 6, 9, 21, 33, 45)
    expected = np.concatenate([np.tile(frame[a:b], 10)
                               for a, b in zip(boundaries, boundaries[1:])])[None, :]
    checks["term_major_history_first_frame"] = bool(np.array_equal(first, expected))
    latest = history.push(frame + 100)
    checks["history_order"] = bool(np.array_equal(latest[0, :27], np.tile(frame[:3], 9))
                                   and np.array_equal(latest[0, 27:30], frame[:3] + 100))
    history.reset()
    checks["history_reset"] = bool(np.array_equal(history.push(frame), first))
    try:
        history.push(np.full(45, np.nan))
        checks["nonfinite_observation_rejected"] = False
    except ValueError:
        checks["nonfinite_observation_rejected"] = True
    yaw90 = rotation_matrix(np.array([math.sqrt(0.5), 0, 0, math.sqrt(0.5)]))
    checks["body_world_orientation"] = bool(np.allclose(yaw90 @ [1, 0, 0], [0, 1, 0]))
    checks["yaw_preserves_gravity"] = bool(np.allclose(yaw90.T @ [0, 0, -1], [0, 0, -1]))

    robot = Lite3Backend(args.pkg / "assets/lite3/lite3.xml",
                         args.pkg / "policy/policy_stateless_h10.onnx")
    foot = robot.model.geom("lite3/FL_FOOT_collision").id
    floor = np.flatnonzero(robot.model.geom_contype == 8)
    checks["robot_floor_collision_mask"] = bool(len(floor) and any(
        (robot.model.geom_contype[foot] & robot.model.geom_conaffinity[g])
        or (robot.model.geom_contype[g] & robot.model.geom_conaffinity[foot]) for g in floor))
    checks["robot_self_collision_stays_disabled"] = not bool(
        robot.model.geom_contype[foot] & robot.model.geom_conaffinity[foot])
    initial = robot.data.qpos.copy()
    robot.step((0.0, 0.0))
    checks["real_policy_called"] = robot.inferences == 1
    checks["first_previous_action_zero"] = bool(np.array_equal(robot.last_observation[-12:], np.zeros(12)))
    checks["action_target_mapping"] = bool(np.allclose(robot.target, Q0 + 0.25 * robot.last_action))
    robot.reset()
    checks["physical_reset"] = bool(np.array_equal(robot.data.qpos, initial)
                                    and robot.inferences == 0 and robot.history.values is None)
    if not all(checks.values()):
        raise RuntimeError(f"Contract failed: {checks}")

    renderer = mujoco.Renderer(robot.model, height=270, width=480)
    cam = mujoco.MjvCamera()
    rows = []
    stage_last = {}
    started = time.monotonic()
    with (args.out / "states.jsonl").open("w") as log:
        for index in range(2800):
            if index < 600:
                stage, command = "stand", (0., 0.)
            elif index < 1400:
                stage, command = "forward", (0.4, 0.)
            elif index < 2000:
                stage, command = "turn", (0., 0.6)
            else:
                stage, command = "stop", (0., 0.)
            robot.step(command)
            state = robot.state()
            if index % 10 == 0:
                row = {"step": index, "sim_time": robot.data.time, "stage": stage,
                       "requested": command, "pose": state.pose, "velocity": state.velocity,
                       **state.telemetry}
                log.write(json.dumps(row) + "\n")
                rows.append(row)
                if state.pose[2] < 0.15 or state.telemetry["tilt_rad"] > 0.9:
                    (args.out / "failure.json").write_text(json.dumps(row, indent=2))
                    renderer.close()
                    raise RuntimeError(f"Lite3 locomotion failure at {row}")
                if index % 100 == 0:
                    print(json.dumps(row), flush=True)
                renderer.update_scene(robot.data, camera=robot.camera_name)
                Image.fromarray(renderer.render()).save(args.out / f"front_{index:06d}.jpg", quality=82)
                renderer.update_scene(robot.data, camera=robot.third_person_camera(cam))
                Image.fromarray(renderer.render()).save(args.out / f"chase_{index:06d}.jpg", quality=82)
            stage_last[stage] = state
    renderer.close()
    forward_delta = stage_last["forward"].pose[0] - stage_last["stand"].pose[0]
    a, b = stage_last["turn"].pose[3], stage_last["forward"].pose[3]
    turned = math.atan2(math.sin(a-b), math.cos(a-b))
    last = [r for r in rows if r["sim_time"] >= 12]
    checks["forward_displacement"] = forward_delta > 0.5
    checks["left_turn"] = turned > 0.5
    checks["upright_finite"] = all(r["pose"][2] >= 0.15 and r["tilt_rad"] < 0.9 for r in rows)
    checks["zero_command_applied_after_stop"] = all(r["policy_command"] == [0., 0., 0.] for r in last)
    result = {"checks": checks, "passed": all(checks.values()), "sim_seconds": robot.data.time,
              "wall_seconds": time.monotonic()-started, "forward_dx_m": forward_delta,
              "turn_yaw_rad": turned, "min_height_m": min(r["pose"][2] for r in rows),
              "max_tilt_rad": max(r["tilt_rad"] for r in rows),
              "stop_last_2s_max_abs_forward": max(abs(r["velocity"][0]) for r in last),
              "stop_last_2s_max_abs_yaw": max(abs(r["velocity"][1]) for r in last),
              "stop_last_2s_xy_drift": math.dist(last[0]["pose"][:2], last[-1]["pose"][:2]),
              "model_inference": False, "walking_inferences": robot.inferences,
              "runtime": {"mujoco": mujoco.__version__}, "final_pose": stage_last["stop"].pose}
    (args.out / "result.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result, indent=2), flush=True)
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
