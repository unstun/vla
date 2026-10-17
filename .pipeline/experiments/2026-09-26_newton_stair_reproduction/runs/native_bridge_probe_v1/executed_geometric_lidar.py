"""Pinned Livox windows raycast against Newton visuals and current skinned human."""
import time
import copy
import xml.etree.ElementTree as ET

import numpy as np
import newton
import warp as wp
from scipy.spatial.transform import Rotation

from scene_assets import BASE, load_mid360_pattern


EXCLUSION_SOURCE = {
    "repository": "https://github.com/RobotecAI/RGLGazeboPlugin",
    "commit": "d4bf3cf36fe4a363a56df1bec2ce3809720db563",
    "file": "RGLServerPlugin/src/Scene.cc",
    "symbol": "RegisterNewLidarCb / LoadEntityToRGLCb",
    "adaptation": "original URDF sensor-link visuals only; no merged-body exclusion",
}


def sensor_view(model, state, excluded_shapes):
    """Apply the upstream sensor-owner exclusion convention to a private BVH.

    Robotec excludes sensor-link geometry from its ray scene. Newton's public
    Model.bvh_build_shapes accepts shape flags. Keep physics/render data intact.
    """
    view = copy.copy(model)
    flags = model.shape_flags.numpy().copy()
    indices = np.asarray(excluded_shapes, dtype=np.int32)
    if len(set(indices.tolist())) != len(indices) or np.any(indices < 0) or np.any(indices >= model.shape_count):
        raise ValueError("Invalid emitter shape selection")
    flags[indices] &= ~int(newton.ShapeFlags.VISIBLE)
    view.shape_flags = wp.array(flags, dtype=wp.int32, device=model.device)
    view.bvh_build_shapes(state)
    return view


def original_emitter_shapes(model):
    """Resolve the original sensor link before Newton's fixed-joint collapse."""
    from newton._src.utils.mesh import load_meshes_from_file
    rig = BASE / "inputs/sensor_rig"
    root = ET.parse(rig / "lite3_pro_sensor_rig_real_with_interface.urdf").getroot()
    link = root.find("link[@name='mid360_body_link']")
    if link is None:
        raise ValueError("Original MID360 link missing")
    visuals = link.findall("visual")
    if len(visuals) != 2:
        raise ValueError("Original MID360 two-visual contract changed")
    selected = []
    for visual in visuals:
        mesh = visual.find("geometry/mesh")
        if mesh is None:
            raise ValueError("Original MID360 visual is not a mesh")
        scale = np.array([float(x) for x in mesh.get("scale").split()])
        reference = load_meshes_from_file(str(rig / mesh.get("filename")), scale=scale, maxhullvert=None)
        if len(reference) != 1:
            raise ValueError("Emitter component must contain exactly one mesh")
        candidates = [i for i, shape in enumerate(model.shape_source)
                      if isinstance(shape, newton.Mesh) and
                      np.array_equal(shape.vertices, reference[0].vertices) and
                      np.array_equal(shape.indices, reference[0].indices)]
        if len(candidates) != 1:
            raise ValueError(f"Exact original emitter mesh match failed: {candidates}")
        selected.append(candidates[0])
    return selected


@wp.kernel
def human_rays(mesh: wp.uint64, origins: wp.array[wp.vec3], directions: wp.array[wp.vec3],
               distance: wp.array[float]):
    i = wp.tid()
    query = wp.mesh_query_ray(mesh, origins[i], directions[i], 40.0)
    distance[i] = query.t if query.result else -1.0


class GeometricLidar:
    def __init__(self, robot, human, *, emitter_self_exclusion=False):
        self.robot, self.human = robot, human
        self.sensor_model = robot.model
        self.emitter_shapes = []
        if emitter_self_exclusion:
            self.emitter_shapes = original_emitter_shapes(robot.model)
            self.sensor_model = sensor_view(robot.model, robot.state, self.emitter_shapes)
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
                "self_return_filter": ("sensor-owner exclusion: original MID360 link visuals only; other robot geometry retained"
                                       if self.emitter_shapes else "none"),
                "self_return_filter_source": EXCLUSION_SOURCE if self.emitter_shapes else None,
                "emitter_self_exclusion_shapes": self.emitter_shapes,
                "emitter_self_exclusion_is_newton_approximation": bool(self.emitter_shapes),
                "wall_s": time.monotonic() - started}
        info.update(near_hit_shapes=near_shapes,
                    near_hit_count=int(near.sum()),
                    near_hit_backfaces=int((near & (np.sum(self.normals.numpy() * world_directions, axis=1) > 0)).sum()))
        # Provenance masks and actor_info are separate audit outputs, never tracker input.
        return sensor_points, world_points, info, actor_info, {
            "ranges": distance, "keep": keep, "actor_nearest": actor_nearest, "shape_id": shape,
            "sensor_position": origin, "sensor_quaternion": quat}
