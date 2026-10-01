"""Exercise the actual replay appearance seam against original CAD meshes."""

import json
import os
from pathlib import Path
import shutil
import unittest
import xml.etree.ElementTree as ET

import numpy as np
import trimesh
import newton

from render_episode import BASE, prepare_robot_appearance
from flat_scene import FlatSceneRobot


class RobotRenderingTests(unittest.TestCase):
    def test_signed_scale_preserves_outer_shell_and_physics_geometry(self):
        robot = FlatSceneRobot(None, obstacle_kind="box", startup_mode="pd_stand")
        before = list(robot.model.shape_source)
        flags = robot.model.shape_flags.numpy().copy()
        scale_before = robot.model.shape_scale.numpy().copy()
        source = BASE / "inputs/sensor_rig"
        urdf = ET.parse(source / "lite3_pro_sensor_rig_real_with_interface.urdf").getroot()
        report = prepare_robot_appearance(robot)
        changed = []
        mirrored = []
        for item in report["base_visuals"]:
            i = item["shape"]
            name = item["link"]
            mesh_element = urdf.find(f"link[@name='{name}']/visual/geometry/mesh")
            scale = np.array([float(x) for x in mesh_element.get("scale", "1 1 1").split()])
            actual = robot.model.shape_source[i]
            if np.array_equal(scale, np.ones(3)):
                self.assertIs(actual, before[i])
                continue
            changed.append(i)
            reference = trimesh.load(source / mesh_element.get("filename"), force="mesh")
            original_normals = reference.vertex_normals.copy()
            transform = np.diag(np.r_[scale, 1.])
            reference.apply_transform(transform)
            np.testing.assert_array_equal(actual.vertices, before[i].vertices)
            np.testing.assert_array_equal(np.sort(actual.indices.reshape(-1, 3), axis=1),
                                          np.sort(before[i].indices.reshape(-1, 3), axis=1))
            np.testing.assert_allclose(actual.normals, original_normals * scale, atol=1e-6)
            np.testing.assert_array_equal(actual.indices, reference.faces.astype(np.int32).reshape(-1))
            if np.prod(scale) < 0:
                mirrored.append(name)
                rendered = trimesh.Trimesh(actual.vertices, actual.indices.reshape(-1, 3), process=False)
                self.assertGreater(rendered.volume, 0, name)
            self.assertEqual(int(flags[i]) & int(newton.ShapeFlags.COLLIDE_SHAPES), 0,
                             "display adapter must not touch collision shapes")
        self.assertEqual(len(changed), 5)
        self.assertEqual(set(mirrored), {"FR_HIP", "HL_HIP", "FR_THIGH", "HR_THIGH"})
        for i, previous in enumerate(before):
            if i not in changed:
                self.assertIs(robot.model.shape_source[i], previous)
        np.testing.assert_array_equal(robot.model.shape_flags.numpy(), flags)
        np.testing.assert_array_equal(robot.model.shape_scale.numpy(), scale_before)
        self.assertEqual(robot.steps, 0)
        self.assertEqual(robot.physics_time(), 0.)


if __name__ == "__main__":
    for path in (Path(__file__), Path(__file__).with_name("render_episode.py")):
        shutil.copyfile(path, Path(os.environ["NEWTON_RUN_DIR"]) / ("executed_" + path.name))
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(RobotRenderingTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    (Path(os.environ["NEWTON_RUN_DIR"]) / "result.json").write_text(json.dumps({
        "tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
        "passed": result.wasSuccessful()}, indent=2) + "\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)
