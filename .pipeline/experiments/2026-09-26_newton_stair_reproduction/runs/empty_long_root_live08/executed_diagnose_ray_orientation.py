"""Isolate ray-origin/orientation sensitivity without changing the robot state."""
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil

from diagnose_ray_coverage import (
    BASE, SOURCE, CloudFrame, GeometricLidar, OfficialHuman, PoseObservation,
    Rotation, StairRobot, TrackerParameters, inputs, load_building_background,
    newton, np, trace_candidates,
)


def main():
    out = Path(os.environ["NEWTON_RUN_DIR"])
    shutil.copyfile(__file__, out / "executed_script.py")
    sensors, _, _, _, _, terrain = inputs()
    telemetry = {
        row["state_sequence"]: row
        for row in (json.loads(line) for line in (SOURCE / "telemetry.jsonl").open())
    }
    robot = StairRobot()
    human = OfficialHuman(out)
    lidar = GeometricLidar(robot, human, emitter_self_exclusion=True)
    background = load_building_background(BASE / "inputs/static_background/building2_9.pcd")
    parameters = TrackerParameters()
    previous = sensors[127]["body_sensor"]
    previous_quat = np.asarray(previous["sensor_quaternion"])[[1, 2, 3, 0]]
    previous_rpy = Rotation.from_quat(previous_quat).as_euler("xyz")
    rows = []
    conditions = ("recorded", "previous_position_only", "previous_orientation_only",
                  "previous_roll_only", "previous_pitch_only", "previous_yaw_only")
    for index in (128, 129):
        sensor = sensors[index]
        state = telemetry[(index + 1) * 5]
        robot.state.joint_q.assign(np.asarray(state["joint_q"], dtype=np.float32))
        robot.state.joint_qd.assign(np.asarray(state["joint_qd"], dtype=np.float32))
        newton.eval_fk(robot.model, robot.state.joint_q, robot.state.joint_qd, robot.state)
        for condition in conditions:
            pose = deepcopy(sensor["body_sensor"])
            if condition == "previous_position_only":
                pose["sensor_position"] = previous["sensor_position"]
            elif condition == "previous_orientation_only":
                pose["sensor_quaternion"] = previous["sensor_quaternion"]
            elif condition != "recorded":
                axis = ("roll", "pitch", "yaw").index(condition.split("_")[1])
                xyzw = np.asarray(pose["sensor_quaternion"])[[1, 2, 3, 0]]
                rpy = Rotation.from_quat(xyzw).as_euler("xyz")
                rpy[axis] = previous_rpy[axis]
                pose["sensor_quaternion"] = Rotation.from_euler("xyz", rpy).as_quat()[[3, 0, 1, 2]].tolist()
            points, _, info, _, _ = lidar.scan(index, sensor["sim_time_s"], override_pose=pose)
            xyzw = np.asarray(pose["sensor_quaternion"])[[1, 2, 3, 0]]
            observation = PoseObservation(sensor["stamp_ns"], "world", "lidar",
                                          tuple(pose["sensor_position"]), tuple(xyzw))
            cloud = CloudFrame(sensor["stamp_ns"], "lidar", points.tolist())
            selected = background.select(cloud, observation, parameters)
            detections, components, kept = trace_candidates(selected.cloud, observation, terrain, parameters)
            row = {"scan_index": index, "condition": condition,
                   "sensor_position": pose["sensor_position"],
                   "sensor_rpy_degrees": Rotation.from_quat(xyzw).as_euler("xyz", degrees=True).tolist(),
                   "human_hits_scoring_only": info["human_hit_count_scoring_only"],
                   "foreground_points": len(selected.cloud.points), "height_kept": kept,
                   "detections": len(detections),
                   "components": [{key: value for key, value in part.items() if key != "points_world"}
                                  for part in components]}
            if condition == "recorded":
                saved = np.load(SOURCE / sensor["file"])["sensor_points"]
                row["saved_cloud_exact"] = bool(np.array_equal(saved, points))
                if not row["saved_cloud_exact"]:
                    raise AssertionError("Original sensor state no longer reproduces saved points")
            np.savez_compressed(out / f"{index}_{condition}.npz", sensor_points=points)
            rows.append(row)
    result = {"physics_steps": robot.steps, "conditions": rows,
              "claim": "Diagnostic ray pose controls only; body geometry, human, pattern and tracker gates fixed. Changed ray poses are not calibrated mounts or navigation evidence."}
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
