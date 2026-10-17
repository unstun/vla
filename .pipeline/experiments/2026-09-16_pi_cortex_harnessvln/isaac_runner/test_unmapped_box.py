import math
import unittest

import unmapped_box as box


class UnmappedBoxGeometryTests(unittest.TestCase):
    def test_d3_pose_and_padded_aabb(self):
        start = (0.0, 0.0, 1.0)
        yaw = 0.0
        pose = box.box_pose_from_stand(start, yaw)
        self.assertEqual(pose["prim"], "/World/unmapped_box")
        self.assertEqual(pose["size_xyz_m"], (0.4, 0.4, 0.8))
        self.assertEqual(pose["center_xyz_m"], (2.5, 0.0, 1.4))
        aabb = box.expanded_aabb(pose["center_xyz_m"], pose["size_xyz_m"])
        for got, expected in (
            (aabb["min_xyz_m"], (2.29, -0.21, 0.99)),
            (aabb["max_xyz_m"], (2.71, 0.21, 1.81)),
        ):
            for value, want in zip(got, expected):
                self.assertAlmostEqual(value, want, places=12)

        yaw = math.pi / 2.0
        pose = box.box_pose_from_stand(start, yaw)
        self.assertAlmostEqual(pose["center_xyz_m"][0], 0.0)
        self.assertAlmostEqual(pose["center_xyz_m"][1], 2.5)
        self.assertAlmostEqual(pose["center_xyz_m"][2], 1.4)

        start = (-1.6088105720747303, -4.542777504301488, 1.5608844757080078)
        yaw = 0.057418473165896385
        pose = box.box_pose_from_stand(start, yaw)
        self.assertAlmostEqual(
            pose["center_xyz_m"][0], start[0] + 2.5 * math.cos(yaw), places=12)
        self.assertAlmostEqual(
            pose["center_xyz_m"][1], start[1] + 2.5 * math.sin(yaw), places=12)
        self.assertAlmostEqual(pose["center_xyz_m"][2], start[2] + 0.4, places=12)

    def test_overlap_fail_closed_versus_torso_plus_0p25(self):
        start = (0.0, 0.0, 1.0)
        yaw = 0.0
        body_height = 0.35
        pose = box.box_pose_from_stand(start, yaw)
        box_aabb = box.expanded_aabb(pose["center_xyz_m"], pose["size_xyz_m"])
        robot_aabb = box.robot_aabb_world(start, yaw, body_height)
        box.require_no_robot_overlap(box_aabb, robot_aabb)

        colliding = box.box_pose_from_stand(start, yaw, offset_m=0.0)
        colliding_aabb = box.expanded_aabb(colliding["center_xyz_m"], colliding["size_xyz_m"])
        with self.assertRaisesRegex(box.UnmappedBoxError, "intersects the robot AABB"):
            box.require_no_robot_overlap(colliding_aabb, robot_aabb)

        identity = box.unmapped_box_identity("lidar", start, yaw, body_height)
        self.assertFalse(identity["robot_overlap"]["intersects"])
        zero = box.unmapped_box_identity("spawn", start, yaw, body_height, offset_m=0.0)
        self.assertTrue(zero["robot_overlap"]["intersects"])

        frozen_start = (-1.6088105720747303, -4.542777504301488, 1.5608844757080078)
        frozen_yaw = 0.057418473165896385
        frozen = box.unmapped_box_identity("lidar", frozen_start, frozen_yaw, 0.35)
        self.assertFalse(frozen["robot_overlap"]["intersects"])
        pose = box.box_pose_from_stand(frozen_start, frozen_yaw)
        box.require_no_robot_overlap(
            box.expanded_aabb(pose["center_xyz_m"], pose["size_xyz_m"]),
            box.robot_aabb_world(frozen_start, frozen_yaw, 0.35),
        )

    def test_sensor_frame_to_world_inside_and_outside(self):
        pose = box.box_pose_from_stand((0.0, 0.0, 1.0), 0.0)
        aabb = box.expanded_aabb(pose["center_xyz_m"], pose["size_xyz_m"])
        sensor_position = (0.0, 0.0, 1.4)
        identity = (1.0, 0.0, 0.0, 0.0)
        inside = box.sensor_points_to_world([(2.5, 0.0, 0.0)], sensor_position, identity)[0]
        outside = box.sensor_points_to_world([(4.0, 0.0, 0.0)], sensor_position, identity)[0]
        self.assertEqual(inside, (2.5, 0.0, 1.4))
        self.assertTrue(box.point_in_aabb(inside, aabb["min_xyz_m"], aabb["max_xyz_m"]))
        self.assertFalse(box.point_in_aabb(outside, aabb["min_xyz_m"], aabb["max_xyz_m"]))

        yaw = math.pi / 2.0
        quat = (math.cos(yaw / 2.0), 0.0, 0.0, math.sin(yaw / 2.0))
        rotated = box.sensor_points_to_world([(1.0, 0.0, 0.0)], (0.0, 0.0, 0.0), quat)[0]
        self.assertAlmostEqual(rotated[0], 0.0, places=12)
        self.assertAlmostEqual(rotated[1], 1.0, places=12)
        self.assertAlmostEqual(rotated[2], 0.0, places=12)

        counts = box.aabb_hit_count([inside, outside, (2.5, 0.0, 1.4)], aabb)
        self.assertEqual(counts, 2)

    def test_target_list_membership(self):
        base = ["/World/ground", "/World/ground/terrain"]
        self.assertEqual(box.lidar_mesh_prim_paths(base, "off"), list(base))
        self.assertEqual(box.lidar_mesh_prim_paths(base, "spawn"), list(base))
        self.assertEqual(
            box.lidar_mesh_prim_paths(base, "lidar"),
            ["/World/ground", "/World/ground/terrain", "/World/unmapped_box"],
        )
        with self.assertRaises(box.UnmappedBoxError):
            box.lidar_mesh_prim_paths(base, "scan")

        identity = box.unmapped_box_identity("off", (0.0, 0.0, 0.0), 0.0, 0.35)
        self.assertEqual(
            (identity["spawn"], identity["lidar_target"], identity["mode"], identity["prim"]),
            (False, False, "off", "/World/unmapped_box"),
        )
        self.assertTrue(box.unmapped_box_identity("spawn", (0.0, 0.0, 0.0), 0.0, 0.35)["spawn"])
        self.assertFalse(box.unmapped_box_identity("spawn", (0.0, 0.0, 0.0), 0.0, 0.35)["lidar_target"])
        self.assertTrue(box.unmapped_box_identity("lidar", (0.0, 0.0, 0.0), 0.0, 0.35)["lidar_target"])


if __name__ == "__main__":
    unittest.main()
