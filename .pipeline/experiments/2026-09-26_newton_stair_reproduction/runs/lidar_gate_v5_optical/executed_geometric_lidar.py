"""Pinned Livox windows raycast against Newton visuals and current skinned human."""
import time
import copy

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
    def __init__(self, robot, human, *, optical_transmission=True):
        self.robot, self.human = robot, human
        self.sensor_model = robot.model
        self.optical_shape = None
        if optical_transmission:
            # Geometric approximation of the emitter's transmissive optical cover.
            # Match exact source mesh bytes/geometry; never exclude a whole body,
            # unknown cell or range band. Physics and rendering remain unchanged.
            from newton._src.utils.mesh import load_meshes_from_file
            path = BASE / "inputs/sensor_rig/meshes/mid360-optical-runtime.stl"
            reference = load_meshes_from_file(str(path), scale=np.array([.001, .001, .001]), maxhullvert=None)
            if len(reference) != 1:
                raise ValueError("Optical source must contain exactly one mesh")
            candidates = [i for i, mesh in enumerate(robot.model.shape_source)
                          if isinstance(mesh, newton.Mesh) and
                          np.array_equal(mesh.vertices, reference[0].vertices) and
                          np.array_equal(mesh.indices, reference[0].indices)]
            if len(candidates) != 1:
                raise ValueError(f"Exact optical-window mesh match failed: {candidates}")
            self.optical_shape = candidates[0]
            self.sensor_model = copy.copy(robot.model)
            flags = robot.model.shape_flags.numpy().copy()
            flags[self.optical_shape] &= ~int(newton.ShapeFlags.VISIBLE)
            self.sensor_model.shape_flags = wp.array(flags, dtype=wp.int32, device="cpu")
            self.sensor_model.bvh_build_shapes(robot.state)
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
        self.normals = wp.zeros(n, dtype=wp.vec3, device="cpu")
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
        self.sensor_model.bvh_refit_shapes(self.robot.state)
        newton.intersect_ray(self.sensor_model, ray_origins=self.origins, ray_directions=self.directions,
                             ray_worlds=self.worlds, out_dist=self.base_dist, out_shape_id=self.shape_id,
                             out_normal=self.normals,
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
        near = (base >= 0) & (base < .1)
        near_ids, near_counts = np.unique(shape[near], return_counts=True)
        near_shapes = [{"id": int(i), "label": self.robot.model.shape_label[i], "count": int(c)}
                       for i, c in zip(near_ids, near_counts, strict=True)]
        info = {"backend": "Newton CPU BVH + refitted official-skinned-mesh geometric rays",
                "scan_window": window.as_dict(), "point_count": int(keep.sum()),
                "human_hit_count_scoring_only": int((actor_nearest & keep).sum()),
                "building_hit_count_scoring_only": int((~actor_nearest & keep & (shape == self.robot.building_shape)).sum()),
                "robot_hit_count_scoring_only": int((~actor_nearest & keep & (shape != self.robot.building_shape)).sum()),
                "self_return_filter": "no post-hit filter; optical cover transmission explicitly modeled",
                "optical_window_transmission_shape": self.optical_shape,
                "optical_transmission_is_newton_approximation": True,
                "wall_s": time.monotonic() - started}
        info.update(near_hit_shapes=near_shapes,
                    near_hit_count=int(near.sum()),
                    near_hit_backfaces=int((near & (np.sum(self.normals.numpy() * world_directions, axis=1) > 0)).sum()))
        # Provenance masks and actor_info are separate audit outputs, never tracker input.
        return sensor_points, world_points, info, actor_info, {
            "ranges": distance, "keep": keep, "actor_nearest": actor_nearest, "shape_id": shape,
            "sensor_position": origin, "sensor_quaternion": quat}
