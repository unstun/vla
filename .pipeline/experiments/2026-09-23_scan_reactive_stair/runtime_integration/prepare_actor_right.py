"""Move the official actor right on the same tread using actual mesh evidence.

PCT's robot-traversability mask is not treated as the human's physical boundary.
The navigation map is not changed or supplemented by this placement audit.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from prepare_stair_scenario import audit

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clip_height(poly, height, above):
    clipped = []
    for index, b in enumerate(poly):
        a = poly[index - 1]
        inside_a = a[2] >= height if above else a[2] <= height
        inside_b = b[2] >= height if above else b[2] <= height
        if inside_a != inside_b:
            clipped.append(a + (b - a) * ((height - a[2]) / (b[2] - a[2])))
        if inside_b:
            clipped.append(b)
    return clipped


def projected_distance(poly, xy):
    points = np.asarray(poly)[:, :2]
    signs, distances = [], []
    area_twice = 0.0
    for index, b in enumerate(points):
        a = points[index - 1]
        delta = b - a
        length2 = float(delta @ delta)
        area_twice += a[0] * b[1] - b[0] * a[1]
        if length2 > 1e-16:
            nearest = a + np.clip((xy - a) @ delta / length2, 0.0, 1.0) * delta
            distances.append(float(np.linalg.norm(nearest - xy)))
            signs.append(delta[0] * (xy[1] - a[1]) - delta[1] * (xy[0] - a[0]))
    if abs(area_twice) > 1e-10 and signs and (min(signs) >= -1e-10 or max(signs) <= 1e-10):
        return 0.0
    return min(distances) if distances else float(np.linalg.norm(points[0] - xy))


def body_clearance(triangles, x, y, ground_z, radius):
    lower, upper = ground_z + 0.45, ground_z + audit.HUMAN_HEIGHT_M + 0.02
    candidates = ((triangles[:, :, 2].max(axis=1) >= lower) &
                  (triangles[:, :, 2].min(axis=1) <= upper) &
                  (triangles[:, :, 0].max(axis=1) >= x - radius) &
                  (triangles[:, :, 0].min(axis=1) <= x + radius) &
                  (triangles[:, :, 1].max(axis=1) >= y - radius) &
                  (triangles[:, :, 1].min(axis=1) <= y + radius))
    minimum = radius
    for tri in triangles[candidates]:
        poly = clip_height(list(tri), lower, True)
        poly = clip_height(poly, upper, False) if poly else []
        if poly:
            minimum = min(minimum, projected_distance(poly, np.array([x, y])))
    return minimum


def floor_at(mesh, x, y, expected):
    hits = [h for h in mesh.hits(x, y) if h["normal_z"] >= 0.7 and abs(h["z_m"] - expected) <= 0.20]
    if not hits:
        raise ValueError("No matching actual floor at %r" % ((x, y),))
    return min(hits, key=lambda h: abs(h["z_m"] - expected))


def prepare(reference, output, right_m):
    if output.exists() or not 0.0 < right_m <= 1.5:
        raise ValueError("fresh output and bounded right offset required")
    original = json.loads((reference / "inputs/actor_route.json").read_text())
    scenario = json.loads((reference / "inputs/stair_scenario.json").read_text())
    yaw = scenario["spawn_yaw_rad"]
    shift = np.array([math.sin(yaw), -math.cos(yaw), 0.0]) * right_m
    vertices, faces = audit.parse_building_mesh(audit.BUILDING)
    mesh = audit.MeshHeights(vertices, faces)
    triangles = vertices[faces]
    old_points = np.asarray(original["waypoints_ground_xyz_m"])
    points = old_points + shift
    if not np.allclose(points[:, 2], old_points[:, 2]) or np.ptp(points[:, 2]) > 1e-8:
        raise ValueError("This controlled shift requires the same level tread")
    checks = []
    spacings = []
    for start, end, old_start, old_end in zip(points[:-1], points[1:], old_points[:-1], old_points[1:]):
        count = max(1, math.ceil(np.linalg.norm(end - start) / 0.01))
        spacings.append(float(np.linalg.norm(end - start) / count))
        for fraction in np.linspace(0.0, 1.0, count + 1):
            new = start + fraction * (end - start)
            old = old_start + fraction * (old_end - old_start)
            floor_checks = []
            for dx, dy in [(0, 0), (-0.1, -0.1), (-0.1, 0.1), (0.1, -0.1), (0.1, 0.1)]:
                previous = floor_at(mesh, old[0] + dx, old[1] + dy, old[2])
                current = floor_at(mesh, new[0] + dx, new[1] + dy, new[2])
                if abs(current["z_m"] - previous["z_m"]) > 0.02:
                    raise ValueError("Lateral shift changes the sampled foot-support profile")
                floor_checks.append({"offset_xy_m": [dx, dy], "old": previous, "new": current})
            clearance = body_clearance(triangles, *new, radius=0.8)
            checks.append({"ground_xyz_m": new.tolist(), "body_side_clearance_m": clearance,
                           "foot_profile": floor_checks})
    lower_bound = min(c["body_side_clearance_m"] for c in checks) - max(spacings) / 2.0
    if lower_bound < audit.HUMAN_RADIUS_M + audit.MARGIN_M:
        raise ValueError("Shifted human body envelope intersects Building geometry")
    geometry = {"schema_version": 1, "building_usda_sha256": audit.BUILDING_SHA,
                "reference_run": reference.name, "reference_route_sha256": sha(reference / "inputs/actor_route.json"),
                "right_shift_m": right_m, "world_shift_m": shift.tolist(),
                "body_clearance_continuous_lower_bound_m": lower_bound,
                "body_radius_plus_margin_m": audit.HUMAN_RADIUS_M + audit.MARGIN_M,
                "body_vertical_band_above_ground_m": [0.45, audit.HUMAN_HEIGHT_M + 0.02],
                "checks": checks,
                "claim": "Actual static Building mesh checks actor placement only; PCT and planner inputs unchanged; no animated human contact proof"}
    output.mkdir(parents=True)
    def save(name, value):
        (output / name).write_text(json.dumps(value, indent=2) + "\n")
    save("geometry.json", geometry)
    route = copy.deepcopy(original)
    route.update(waypoints_ground_xyz_m=points.tolist(), geometry_evidence_sha256=sha(output / "geometry.json"),
                 geometry_reviewed=True, geometry_reviewed_by="Codex actual pinned Building mesh; original foot profile and swept body envelope",
                 claim="Same official actor, walk schedule and tread; user-requested lateral placement ablation; truth remains scoring-only")
    save("actor_route.json", route)
    scenario["actor_route_sha256"] = sha(output / "actor_route.json")
    scenario["initial_center_distance_m"] = math.dist(scenario["spawn_ground_xyz_m"][:2], points[0, :2])
    save("scenario.json", scenario)
    return {"output": str(output), "right_shift_m": right_m,
            "new_waypoint_start": points[0].tolist(), "continuous_body_clearance_lower_bound_m": lower_bound}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, default=HERE / "runs/walk_v4_ego")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--right-m", type=float, default=0.65)
    args = parser.parse_args()
    print(json.dumps(prepare(args.reference, args.output, args.right_m), indent=2))
