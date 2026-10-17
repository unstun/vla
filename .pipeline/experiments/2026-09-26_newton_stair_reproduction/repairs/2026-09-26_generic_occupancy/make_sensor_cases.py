"""Actual first-hit rays for stationary, unlabelled obstacle planning cases."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

from materialize import BASE
sys.path.insert(0, str(BASE / "scripts"))
import numpy as np
import warp as wp
wp.config.kernel_cache_dir = os.environ["WARP_CACHE_PATH"]
wp.init()
wp.set_device("cpu")
import newton
from pxr import UsdGeom
from scipy.spatial.transform import Rotation
from scene_assets import OfficialHuman, load_mid360_pattern
from robot_scene import fixed_frame_transform


def main():
    out = Path(os.environ["NEWTON_RUN_DIR"])
    shutil.copyfile(__file__, out / "executed_make_sensor_cases.py")
    human = OfficialHuman(out)
    vertices, _ = human.vertices(0., fixed_frame=0, fixed_root=(0., 0., 0.))
    faces, offset = [], 0
    for path, _, points, part in human.meshes:
        if UsdGeom.Imageable(human.stage.GetPrimAtPath(path)).ComputeVisibility() != "invisible":
            faces.append(part + offset)
        offset += len(points)
    faces = np.concatenate(faces).reshape(-1)
    visible = vertices[np.unique(faces)]
    vertices[:, :2] += np.array([1.6, 0.]) - (visible[:, :2].min(axis=0) + visible[:, :2].max(axis=0)) / 2
    vertices[:, 2] -= visible[:, 2].min()
    human_mesh = newton.Mesh(vertices, faces, compute_inertia=False)
    mount = fixed_frame_transform(BASE / "inputs/sensor_rig/lite3_pro_sensor_rig_real_with_interface.urdf", "mid360_scan_frame")
    origin = mount[:3, 3] + [0., 0., .3]
    rotation = mount[:3, :3]
    quaternion = Rotation.from_matrix(rotation).as_quat()
    pattern = load_mid360_pattern(BASE / "inputs/livox_mid360/mid360.csv")
    cells = np.arange(-4.95, 5.001, .1)
    xx, yy = np.meshgrid(cells, cells, indexing="ij")
    # Prior support is a flat ground map only; it has no obstacle geometry.
    ground = np.c_[xx.reshape(-1), yy.reshape(-1), np.full(xx.size, .03), np.zeros(xx.size)].astype("<f4")
    results = []
    cases = ("empty", "static_human", "box", "thin_wall", "post", "low_box", "occluded_human", "blocked_corridor")
    for case in cases:
        target = out / case
        target.mkdir()
        builder = newton.ModelBuilder()
        def box(x, y, z, hx, hy, hz, label):
            return builder.add_shape_box(-1, xform=wp.transform(wp.vec3(x, y, z)),
                                         hx=hx, hy=hy, hz=hz, label=label)
        box(0., 0., -.1, 5.5, 5.5, .1, "floor")
        # Physical distant room surfaces provide finite returns, not a free map.
        box(4.5, 0., 1.5, .1, 5., 1.5, "far_wall")
        box(-4.5, 0., 1.5, .1, 5., 1.5, "rear_wall")
        box(0., 4.5, 1.5, 4.5, .1, 1.5, "side_wall_a")
        box(0., -4.5, 1.5, 4.5, .1, 1.5, "side_wall_b")
        obstacle_ids = []
        if case in ("static_human", "occluded_human"):
            obstacle_ids.append(builder.add_shape_mesh(-1, mesh=human_mesh, label="official_visible_static_human"))
        if case == "box":
            obstacle_ids.append(box(1.6, 0., .45, .3, .35, .45, "box"))
        if case == "thin_wall":
            obstacle_ids.append(box(1.6, 0., .7, .025, .55, .7, "thin_wall"))
        if case == "post":
            obstacle_ids.append(box(1.6, 0., .6, .045, .045, .6, "post"))
        if case == "low_box":
            obstacle_ids.append(box(1.6, 0., .065, .3, .35, .065, "low_box"))
        if case == "occluded_human":
            obstacle_ids.append(box(1.1, -.23, .55, .035, .22, .55, "partial_occluder"))
        if case == "blocked_corridor":
            obstacle_ids.append(box(1.6, 0., 1., .05, 4.5, 1., "blocked_corridor"))
        model = builder.finalize(device="cpu")
        model.bvh_build_shapes(model.state())
        files, metrics = [], []
        for index in range(20):
            directions, window = pattern.scan_window(index)
            world_directions = (directions @ rotation.T).astype(np.float32)
            n = len(directions)
            distances = wp.zeros(n, dtype=wp.float32, device="cpu")
            hits = wp.zeros(n, dtype=wp.int32, device="cpu")
            newton.intersect_ray(model,
                ray_origins=wp.array(np.repeat(origin[None, :], n, axis=0), dtype=wp.vec3, device="cpu"),
                ray_directions=wp.array(world_directions, dtype=wp.vec3, device="cpu"),
                ray_worlds=wp.zeros(n, dtype=wp.int32, device="cpu"),
                out_dist=distances, out_shape_id=hits, fast_math=False)
            ranges = distances.numpy()
            keep = np.isfinite(ranges) & (ranges >= .1) & (ranges <= 40.)
            measured = (directions[keep] * ranges[keep, None]).astype("<f4")
            name = f"cloud_{index:03d}.f32"
            measured.tofile(target / name)
            files.append(name)
            metrics.append({"window": window.as_dict(), "points": int(keep.sum()),
                            "obstacle_hits_scoring_only": int((np.isin(hits.numpy(), obstacle_ids) & keep).sum())})
        ground.tofile(target / "ground.f32")
        (target / "clouds.txt").write_text("\n".join(files) + "\n")
        (target / "body_pose.txt").write_text("0 0 0.3 0 0 0 1\n")
        (target / "sensor_pose.txt").write_text(" ".join(format(float(x), ".17g") for x in np.r_[origin, quaternion]) + "\n")
        (target / "start_goal.txt").write_text("0 0 0.3 3.0 1.0 0.3\n")
        (target / "queries.txt").write_text("0 0 0.3 0 start\n1.6 0 0.3 0 obstacle_center\n1.3 0 0.3 0 obstacle_front\n1.6 1.2 0.3 0 detour\n3.0 1.0 0.3 0 goal\n4.8 4.8 0.3 0 unknown_corner\n")
        # Scoring geometry is separate and is never read by the native probe.
        results.append({"case": case, "sensor_only_input": str(target), "scans": metrics,
                        "shape_count_scoring_only": model.shape_count,
                        "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(target.iterdir())}})
    (out / "result.json").write_text(json.dumps({"cases": results,
        "claim": "Frozen stationary scene first-hit measurements from one original-mounted Livox sensor view. No robot dynamics or navigation success claim. Native input has no actor/object metadata or semantic tracks."}, indent=2) + "\n")
    print(json.dumps({"cases": len(results), "scans_per_case": 20, "sensor_position": origin.tolist(),
                      "sensor_euler_xyz": Rotation.from_matrix(rotation).as_euler("xyz", degrees=True).tolist()}))


if __name__ == "__main__":
    main()
