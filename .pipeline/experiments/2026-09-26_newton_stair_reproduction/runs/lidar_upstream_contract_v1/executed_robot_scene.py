"""Original sensor-rig robot and exact Building mesh in Newton contacts."""
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import numpy as np
import newton
import warp as wp
from scipy.spatial.transform import Rotation

from scene_assets import BASE, building_mesh

QUALIFIED = BASE.parent / "2026-09-26_newton_macos_policy"
sys.path.insert(0, str(QUALIFIED / "scripts"))
from lite3_newton import Lite3Newton


def fixed_frame_transform(urdf, frame):
    root = ET.parse(urdf).getroot()
    transforms = {"TORSO": np.eye(4)}
    remaining = list(root.findall("joint"))
    while frame not in transforms:
        changed = False
        for joint in remaining[:]:
            parent, child = joint.find("parent").get("link"), joint.find("child").get("link")
            if parent not in transforms or joint.get("type") != "fixed":
                continue
            origin = joint.find("origin")
            xyz = [float(v) for v in origin.get("xyz", "0 0 0").split()] if origin is not None else [0., 0., 0.]
            rpy = [float(v) for v in origin.get("rpy", "0 0 0").split()] if origin is not None else [0., 0., 0.]
            matrix = np.eye(4)
            matrix[:3, :3] = Rotation.from_euler("xyz", rpy).as_matrix()
            matrix[:3, 3] = xyz
            transforms[child] = transforms[parent] @ matrix
            remaining.remove(joint)
            changed = True
        if not changed:
            raise ValueError(f"No fixed TORSO-to-{frame} chain")
    return transforms[frame]


class StairRobot(Lite3Newton):
    def __init__(self):
        self.building_vertices, self.building_faces, self.scenario = building_mesh()
        source = BASE / "inputs/sensor_rig/lite3_pro_sensor_rig_real_with_interface.urdf"
        self.sensor_mount = fixed_frame_transform(source, "mid360_scan_frame")

        def add_scene(builder):
            mesh = newton.Mesh(self.building_vertices, self.building_faces.reshape(-1), compute_inertia=False)
            self.building_shape = builder.add_shape_mesh(-1, mesh=mesh,
                cfg=newton.ModelBuilder.ShapeConfig(mu=1.0), label="archived_building", color=(.58, .62, .67))

        spawn = np.array(self.scenario["spawn_ground_xyz_m"])
        spawn[2] += self.scenario["spawn_body_height_m"]
        super().__init__(robot_source=source, scene_builder=add_scene, spawn_xyz=spawn,
                         spawn_yaw=self.scenario["spawn_yaw_rad"], newton_contacts=True)

    def body_and_sensor(self):
        q, qd = self.native_array("qpos"), self.native_array("qvel")
        rotation = Rotation.from_quat(q[[4, 5, 6, 3]]).as_matrix()
        body_matrix = np.eye(4)
        body_matrix[:3, :3], body_matrix[:3, 3] = rotation, q[:3]
        sensor = body_matrix @ self.sensor_mount
        xyzw = Rotation.from_matrix(sensor[:3, :3]).as_quat()
        # Native FREE qvel is origin-linear/world and angular/body.
        return {"position": q[:3].tolist(), "quaternion": q[3:7].tolist(),
                "linear_body": (rotation.T @ qd[:3]).tolist(), "angular_body": qd[3:6].tolist(),
                "linear_world": qd[:3].tolist(), "angular_world": (rotation @ qd[3:6]).tolist(),
                "sensor_position": sensor[:3, 3].tolist(), "sensor_quaternion": xyzw[[3, 0, 1, 2]].tolist()}
