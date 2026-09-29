"""Frozen-state ray controls; no dynamics step or tracker-policy modification."""
import json
import os
from pathlib import Path

import numpy as np
from pxr import UsdGeom
from scipy.spatial.transform import Rotation
import warp as wp
wp.config.kernel_cache_dir = os.environ["WARP_CACHE_PATH"]
wp.init()
wp.set_device("cpu")
import newton

from diagnose_tracker_replay import BASE, SOURCE, inputs
from diagnose_tracker_gates import trace_candidates
from scan_reactive_tracker.core import CloudFrame, PoseObservation, TrackerParameters
from scan_reactive_tracker.static_background import load_building_background
from robot_scene import StairRobot
from scene_assets import OfficialHuman
from geometric_lidar import GeometricLidar


def main():
    out = Path(os.environ["NEWTON_RUN_DIR"])
    sensors, _, _, _, _, terrain = inputs()
    telemetry = {r["state_sequence"]: r for r in (json.loads(x) for x in (SOURCE / "telemetry.jsonl").open())}
    robot = StairRobot()
    human = OfficialHuman(out)
    lidar = GeometricLidar(robot, human, emitter_self_exclusion=True)
    original_human_mesh = lidar.human_mesh
    offset, visible = 0, []
    for path, _, points, faces in human.meshes:
        if UsdGeom.Imageable(human.stage.GetPrimAtPath(path)).ComputeVisibility() != "invisible":
            visible.append(faces + offset)
        offset += len(points)
    visible_mesh = wp.Mesh(points=lidar.human_points,
        indices=wp.array(np.concatenate(visible).reshape(-1), dtype=wp.int32, device="cpu"))
    background = load_building_background(BASE / "inputs/static_background/building2_9.pcd")
    parameters = TrackerParameters()
    report = []
    for index in (128, 129):
        sensor = sensors[index]
        for condition, pose_index, pattern_index in (("recorded", index, index),
                ("previous_pattern_only", index, 127), ("previous_robot_pose_only", 127, index),
                ("visible_human_only", index, index)):
            pose_sensor = sensors[pose_index]
            state = telemetry[(pose_index + 1) * 5]
            robot.state.joint_q.assign(np.asarray(state["joint_q"], dtype=np.float32))
            robot.state.joint_qd.assign(np.asarray(state["joint_qd"], dtype=np.float32))
            newton.eval_fk(robot.model, robot.state.joint_q, robot.state.joint_qd, robot.state)
            lidar.human_mesh = visible_mesh if condition == "visible_human_only" else original_human_mesh
            points, _, info, _, _ = lidar.scan(pattern_index, sensor["sim_time_s"], override_pose=pose_sensor["body_sensor"])
            np.savez_compressed(out / f"{index}_{condition}.npz", sensor_points=points)
            quaternion = pose_sensor["body_sensor"]["sensor_quaternion"]
            xyzw = [quaternion[k] for k in (1, 2, 3, 0)]
            pose = PoseObservation(sensor["stamp_ns"], "world", "lidar",
                tuple(pose_sensor["body_sensor"]["sensor_position"]), tuple(xyzw))
            cloud = CloudFrame(sensor["stamp_ns"], "lidar", points.tolist())
            selected = background.select(cloud, pose, parameters)
            detections, components, kept = trace_candidates(selected.cloud, pose, terrain, parameters)
            row = {"scan_index": index, "condition": condition, "points": len(points),
                "human_hits_scoring_only": info["human_hit_count_scoring_only"],
                "sensor_rpy_degrees": Rotation.from_quat(xyzw).as_euler("xyz", degrees=True).tolist(),
                "foreground_points": len(selected.cloud.points), "height_kept": kept,
                "detections": len(detections),
                "components": [{k:v for k,v in c.items() if k != "points_world"} for c in components]}
            if condition == "recorded":
                prior = np.load(SOURCE / sensor["file"])["sensor_points"]
                row["saved_cloud_same_shape"] = points.shape == prior.shape
                row["saved_cloud_max_abs_error_m"] = float(np.max(np.abs(points-prior))) if points.shape == prior.shape else None
                if not row["saved_cloud_same_shape"] or row["saved_cloud_max_abs_error_m"] > 1e-5:
                    raise AssertionError("Frozen-state rays do not reproduce the recorded cloud")
            report.append(row)
    result = {"physics_steps": robot.steps, "conditions": report,
        "claim": "Frozen-state geometric ray diagnostics. Counterfactual clouds are never substituted into the old run or used as accepted navigation evidence."}
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
