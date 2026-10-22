"""Read-only A02 mesh/mask evidence; writes only a new compact audit directory.

The original simulator triangles and mask are never altered. No simulator,
controller, planner, GPU operation, or input substitution is performed.
"""
import os
for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "1"
os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np
import shapely
from shapely.geometry import Point, Polygon, box, mapping
from shapely.ops import nearest_points, unary_union
from pxr import Usd, UsdGeom


EXPECTED = {
    "mesh": "e55e4a9507441b8f1788503f909505a49b63d6eb36f6882ba782aee7c38a5d39",
    "floor": "20acd5cf1ef156c5bd336b12651efe9a18e9959816905b05178ed44b1a181c96",
    "mask": "219d7982eca6c7af94545158ec97fb3b0186ff0f2166f8697d53c0b0726c56d8",
    "pcd": "8721efeb74415336d47c97d861d6e30ad213669b120d5b37c62461100c1f2eae",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clip_z(vertices, level, above):
    output = []
    for a, b in zip(vertices, vertices[1:] + vertices[:1]):
        ina = a[2] >= level if above else a[2] <= level
        inb = b[2] >= level if above else b[2] <= level
        if ina:
            output.append(a)
        if ina != inb:
            output.append(a + (b-a) * ((level-a[2])/(b[2]-a[2])))
    return output


def coverage_union(triangles, low, high):
    polygons = []
    for triangle in triangles:
        if triangle[:, 2].max() < low or triangle[:, 2].min() > high:
            continue
        clipped = clip_z(list(triangle), low, True)
        if clipped:
            clipped = clip_z(clipped, high, False)
        if len(clipped) >= 3:
            polygon = Polygon(np.asarray(clipped)[:, :2])
            if polygon.area > 1e-16:
                assert polygon.is_valid
                polygons.append(polygon)
    return unary_union(polygons), len(polygons)


def vertical_heights(triangles, xy):
    a = triangles[:, 0]
    u, v = triangles[:, 1]-a, triangles[:, 2]-a
    det = u[:, 0]*v[:, 1]-u[:, 1]*v[:, 0]
    keep = abs(det) >= 1e-10
    a, u, v, det = a[keep], u[keep], v[keep], det[keep]
    px, py = xy[0]-a[:, 0], xy[1]-a[:, 1]
    s, t = (px*v[:, 1]-py*v[:, 0])/det, (u[:, 0]*py-u[:, 1]*px)/det
    inside = (s >= -1e-9) & (t >= -1e-9) & (s+t <= 1+1e-9)
    return sorted(set(float(z) for z in (a[:, 2]+s*u[:, 2]+t*v[:, 2])[inside]))


def read_pcd(path):
    with path.open("rb") as stream:
        header = []
        while True:
            line = stream.readline().decode("ascii").strip()
            header.append(line)
            if line.startswith("DATA "):
                assert line == "DATA binary"
                break
        assert "FIELDS x y z normal_x normal_y normal_z" in header
        points = np.fromfile(stream, dtype="<f4").reshape(-1, 6)
    assert len(points) == 2_000_000
    return points, header


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-root", type=Path, required=True)
    parser.add_argument("--pose-input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    began = time.monotonic()
    args.output.mkdir(parents=True, exist_ok=False)
    base = args.task_root
    experiment = base/"repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction"
    paths = {
        "mesh": experiment/"inputs/building.usda",
        "floor": base/"fixed_curve_input/physical_floor.f32",
        "mask": base/"support_coverage_v134/partial.txt",
        "triangles": base/"support_coverage_v134/triangles.f64",
        "pcd": experiment/"inputs/static_background/building2_9.pcd",
    }
    provenance = {}
    for kind, path in paths.items():
        value = digest(path)
        if kind in EXPECTED:
            assert value == EXPECTED[kind], (kind, value)
        provenance[kind] = {"path": str(path), "sha256": value, "bytes": path.stat().st_size}
    triangles = np.fromfile(paths["triangles"], dtype="<f8").reshape(-1, 3, 3)
    stage = Usd.Stage.Open(str(paths["mesh"]))
    assert UsdGeom.GetStageMetersPerUnit(stage) == 1 and UsdGeom.GetStageUpAxis(stage) == "Z"
    meshes = [UsdGeom.Mesh(p) for p in stage.Traverse() if p.IsA(UsdGeom.Mesh)]
    assert len(meshes) == 1
    mesh = meshes[0]
    points = np.array(mesh.GetPointsAttr().Get(), dtype=np.float64)
    transform = np.array(UsdGeom.Xformable(mesh).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
    vertices = (np.c_[points, np.ones(len(points))] @ transform)[:, :3].astype(np.float32)
    assert np.all(np.array(mesh.GetFaceVertexCountsAttr().Get()) == 3)
    faces = np.array(mesh.GetFaceVertexIndicesAttr().Get(), dtype=np.int32).reshape(-1, 3)
    assert np.array_equal(vertices[faces].astype("<f8"), triangles)
    floors = np.fromfile(paths["floor"], dtype="<f4").reshape(-1, 4).astype(float)
    floors[:, 2] -= .03
    negative = np.loadtxt(paths["mask"])
    pcd, pcd_header = read_pcd(paths["pcd"])
    pose_data = json.loads(args.pose_input.read_text())
    radius, offset, clearance, bound = .35, .18, .30, .26
    samples, triggers, results = [], [], []
    for pose in pose_data["poses"]:
        xyz, yaw = np.array(pose["body_xyz"]), pose["yaw"]
        ground = xyz[2]-clearance
        support, polygon_count = coverage_union(triangles, ground-bound, ground+bound)
        assert support.is_valid
        scene_window = box(xyz[0]-1., xyz[1]-1., xyz[0]+1., xyz[1]+1.)
        side_results = []
        for side, sign in (("front", 1), ("rear", -1)):
            center = xyz[:2]+sign*offset*np.array([math.cos(yaw), math.sin(yaw)])
            ix, iy = np.floor(center/.1).astype(int)
            target_bounds = np.array([ix*.1, iy*.1, (ix+1)*.1, (iy+1)*.1])
            dx = np.maximum.reduce([negative[:, 0]-.05-target_bounds[2], target_bounds[0]-negative[:, 0]-.05, np.zeros(len(negative))])
            dy = np.maximum.reduce([negative[:, 1]-.05-target_bounds[3], target_bounds[1]-negative[:, 1]-.05, np.zeros(len(negative))])
            selected = np.where((dx*dx+dy*dy <= radius*radius+1e-12) & (abs(negative[:, 2]-ground) < bound))[0]
            center_point = Point(center)
            covered = support.covers(center_point)
            distance = float(center_point.distance(support.boundary)) if covered else 0.
            closest = nearest_points(center_point, support.boundary)[1]
            disc = center_point.buffer(radius, quad_segs=4096)
            uncovered = disc.difference(support)
            all_failed = []
            exact_intersecting_source_squares = 0
            for source_id in selected:
                source = negative[source_id]
                source_box = box(source[0]-.05, source[1]-.05, source[0]+.05, source[1]+.05)
                center_to_square = center_point.distance(source_box)
                exact_intersecting_source_squares += int(center_to_square <= radius)
                failed_distances = []
                for sx in range(4):
                    for sy in range(4):
                        xy = source[:2]-.05+(np.array([sx, sy])+.5)*.025
                        heights = vertical_heights(triangles, xy)
                        present = any(abs(h-source[2]) < bound for h in heights)
                        covered_union = support.covers(Point(xy))
                        actual_present = any(abs(h-ground) < bound for h in heights)
                        assert covered_union == actual_present, (xy, heights)
                        d = float(np.linalg.norm(xy-center))
                        row = {"pose": pose["label"], "side": side, "source_id": int(source_id), "sample_x": sx, "sample_y": sy,
                            "x": float(xy[0]), "y": float(xy[1]), "source_z": float(source[2]), "mesh_heights": heights,
                            "present_generator_level": present, "present_query_level": actual_present,
                            "distance_to_center_m": d, "inside_exact_disc": d <= radius}
                        samples.append(row)
                        if not present:
                            failed_distances.append(d)
                            all_failed.append(row)
                assert failed_distances, (pose["label"], side, source_id)
                triggers.append({"pose": pose["label"], "side": side, "source_id": int(source_id), "source_xyz": source.tolist(),
                    "target_cell": [int(ix), int(iy)], "square_to_square_distance_m": float(math.hypot(dx[source_id], dy[source_id])),
                    "exact_center_to_source_square_m": float(center_to_square), "failed_samples": len(failed_distances),
                    "closest_failed_sample_m": min(failed_distances), "failed_samples_inside_exact_disc": sum(d <= radius for d in failed_distances)})
            local_floor = floors[(np.linalg.norm(floors[:, :2]-center, axis=1) < .7) & (abs(floors[:, 2]-ground) < bound)]
            local_pcd = pcd[(np.linalg.norm(pcd[:, :2]-center, axis=1) <= radius) & (abs(pcd[:, 2]-ground) < bound)]
            pcd_floor = local_pcd[np.abs(local_pcd[:, 5]) > .9]
            side_results.append({"side": side, "center_xy": center.tolist(), "mask_target_cell": [int(ix), int(iy)],
                "mask_target_bounds": target_bounds.tolist(), "mask_trigger_sources": len(selected), "mask_blocks": bool(len(selected)),
                "source_squares_intersecting_exact_disc": exact_intersecting_source_squares,
                "failed_samples_inside_exact_disc": sum(s["inside_exact_disc"] for s in all_failed),
                "nearest_failed_generator_sample_m": min((s["distance_to_center_m"] for s in all_failed), default=None),
                "center_covered": covered, "distance_to_uncovered_domain_m": distance,
                "continuous_disc_covered": bool(covered and distance >= radius), "coverage_margin_m": distance-radius,
                "nearest_mesh_boundary_xy": list(closest.coords)[0], "disc_uncovered_area_m2": float(uncovered.area),
                "pcd_points_inside_disc_height_band": len(local_pcd), "pcd_horizontal_normal_points": len(pcd_floor),
                "pcd_horizontal_z_bounds": [float(pcd_floor[:, 2].min()), float(pcd_floor[:, 2].max())] if len(pcd_floor) else None,
                "physical_floor_records_within_70cm_height_band": len(local_floor),
                "physical_floor_z_bounds": [float(local_floor[:, 2].min()), float(local_floor[:, 2].max())] if len(local_floor) else None})
        results.append({"label": pose["label"], "body_xyz": xyz.tolist(), "yaw": yaw, "ground_hint": ground,
            "mesh_height_band": [ground-bound, ground+bound], "clipped_polygons": polygon_count, "sides": side_results})
        geo = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"kind": "mesh_support", "label": pose["label"]}, "geometry": mapping(support.intersection(scene_window))}]}
        for side in side_results:
            geo["features"].append({"type": "Feature", "properties": {"kind": "oriented_cylinder", "side": side["side"]}, "geometry": mapping(Point(side["center_xy"]).buffer(radius, quad_segs=256))})
        (args.output/(pose["label"]+"_geometry.geojson")).write_text(json.dumps(geo)+"\n")
    (args.output/"mask_source_samples.json").write_text(json.dumps(samples, indent=2)+"\n")
    (args.output/"mask_trigger_sources.json").write_text(json.dumps(triggers, indent=2)+"\n")
    report = {"scope": "CPU-only original geometric evidence; no physics, planning, mask modification or pose snapping",
        "script_sha256": digest(Path(__file__)), "pose_input_sha256": digest(args.pose_input), "cpu_affinity": sorted(os.sched_getaffinity(0)),
        "numpy": np.__version__, "shapely": shapely.__version__, "physics_steps": 0, "inputs": provenance,
        "triangle_count": len(triangles), "transformed_usd_exactly_equals_archived_triangles": True,
        "parameters": {"radius_m": radius, "offset_m": offset, "native_body_clearance_m": clearance, "height_bound_m": bound},
        "geometry_contract": "Z-clip original transformed triangles to query ground +/- .26, project XY, union; covered center's distance to union boundary is distance to uncovered domain. Circle coverage uses distance >= .35, not polygonal circle sampling.",
        "circle_uncovered_area_contract": "Area uses inscribed circle polygon with 4096 segments per quadrant; coverage verdict uses exact point-to-mesh-polygon-boundary distance.",
        "mask_samples": len(samples), "trigger_source_pairs": len(triggers), "poses": results,
        "elapsed_s": time.monotonic()-began, "pcd_header": pcd_header}
    (args.output/"geometry_report.json").write_text(json.dumps(report, indent=2)+"\n")
    outputs = {p.name: {"sha256": digest(p), "bytes": p.stat().st_size} for p in args.output.iterdir() if p.is_file()}
    (args.output/"output_inventory.json").write_text(json.dumps(outputs, indent=2)+"\n")
    print(json.dumps({"poses": report["poses"], "elapsed_s": report["elapsed_s"], "cpu_affinity": report["cpu_affinity"]}, indent=2))


if __name__ == "__main__":
    main()
