"""Pinned Livox windows raycast against Newton visuals and current skinned human."""
import time

import numpy as np
import newton
import warp as wp
from scipy.spatial.transform import Rotation

from scene_assets import BASE, load_mid360_pattern


@wp.kernel
def human_rays(mesh: wp.uint64, origins: wp.array[wp.vec3], directions: wp.array[wp.vec3],
               distance: wp.array[float]):
    i = wp.tid()
    query = wp.mesh_query_ray(mesh, origins[i], directions[i], 40.0)
    distance[i] = query.t if query.result else -1.0


class GeometricLidar:
    def __init__(self, robot, human):
        self.robot, self.human = robot, human
        self.pattern = load_mid360_pattern(BASE / "inputs/livox_mid360/mid360.csv")
        points, _ = human.vertices(0.0)
        self.human_points = wp.array(points, dtype=wp.vec3, device="cpu")
        self.human_mesh = wp.Mesh(points=self.human_points,
                                  indices=wp.array(human.faces.reshape(-1), dtype=wp.int32, device="cpu"))
        n = self.pattern.points_per_scan
        self.worlds = wp.zeros(n, dtype=wp.int32, device="cpu")
        self.origins = wp.zeros(n, dtype=wp.vec3, device="cpu")
        self.directions = wp.zeros(n, dtype=wp.vec3, device="cpu")
        self.base_dist = wp.zeros(n, dtype=wp.float32, device="cpu")
        self.shape_id = wp.zeros(n, dtype=wp.int32, device="cpu")
        self.actor_dist = wp.zeros(n, dtype=wp.float32, device="cpu")

    def scan(self, scan_index, elapsed, *, fixed_frame=None, fixed_root=None, override_pose=None):
        started = time.monotonic()
        vertices, actor_info = self.human.vertices(elapsed, fixed_frame=fixed_frame, fixed_root=fixed_root)
        self.human_points.assign(vertices)
        self.human_mesh.refit()
        pose = self.robot.body_and_sensor() if override_pose is None else override_pose
        origin = np.asarray(pose["sensor_position"], dtype=np.float32)
        quat = np.array(pose["sensor_quaternion"], dtype=np.float64)
        rotation = Rotation.from_quat(quat[[1, 2, 3, 0]]).as_matrix()
        local_directions, window = self.pattern.scan_window(scan_index)
        world_directions = (local_directions @ rotation.T).astype(np.float32)
        self.origins.assign(np.repeat(origin[None, :], len(world_directions), axis=0))
        self.directions.assign(world_directions)
        self.robot.model.bvh_refit_shapes(self.robot.state)
        newton.intersect_ray(self.robot.model, ray_origins=self.origins, ray_directions=self.directions,
                             ray_worlds=self.worlds, out_dist=self.base_dist, out_shape_id=self.shape_id,
                             fast_math=False)
        wp.launch(human_rays, dim=len(world_directions),
                  inputs=[self.human_mesh.id, self.origins, self.directions, self.actor_dist], device="cpu")
        base, actor = self.base_dist.numpy(), self.actor_dist.numpy()
        base_valid = np.where(base >= 0, base, np.inf)
        actor_valid = np.where(actor >= 0, actor, np.inf)
        actor_nearest = actor_valid < base_valid
        distance = np.minimum(base_valid, actor_valid)
        keep = np.isfinite(distance) & (distance >= .1) & (distance <= 40.)
        sensor_points = (local_directions[keep] * distance[keep, None]).astype(np.float32)
        world_points = (world_directions[keep] * distance[keep, None] + origin).astype(np.float32)
        shape = self.shape_id.numpy()
        info = {"backend": "Newton CPU BVH + refitted official-skinned-mesh geometric rays",
                "scan_window": window.as_dict(), "point_count": int(keep.sum()),
                "human_hit_count_scoring_only": int((actor_nearest & keep).sum()),
                "building_hit_count_scoring_only": int((~actor_nearest & keep & (shape == self.robot.building_shape)).sum()),
                "robot_hit_count_scoring_only": int((~actor_nearest & keep & (shape != self.robot.building_shape)).sum()),
                "self_return_filter": "none", "wall_s": time.monotonic() - started}
        # Provenance masks and actor_info are separate audit outputs, never tracker input.
        return sensor_points, world_points, info, actor_info, {
            "ranges": distance, "keep": keep, "actor_nearest": actor_nearest, "shape_id": shape,
            "sensor_position": origin, "sensor_quaternion": quat}
