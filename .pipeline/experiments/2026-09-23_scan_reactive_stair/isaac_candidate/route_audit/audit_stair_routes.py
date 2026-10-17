"""Offline Building/PCT stair corridor audit; no Isaac, ROS, or actuation.

Every route height comes from a selected PCT ground cell (the sidecar's exact
selection). The pinned Building collision mesh independently checks support
and overhead. The transverse support width is a conservative grid test, not a
continuous collision proof; actual robot/person contact remains an Isaac gate.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
from pathlib import Path
import re
import sys

import numpy as np
from scipy.spatial import cKDTree


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[4]
P2B = PROJECT / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution"
PCT_CORE = P2B / "reactive_stair"
BUILDING = P2B / "inputs/building.usda"
BUILDING_SHA = "e55e4a9507441b8f1788503f909505a49b63d6eb36f6882ba782aee7c38a5d39"
PCT_SHA = "ab5499ff100fe233f6cfabb59ce7592290cddd042c92ead5e37e9e2b593d24da"
PLANNER_YAML = P2B / "baseline_config/planner.yaml"
PLANNER_YAML_SHA = "42a265a35cefb69eae43896acdd13780d1a7bd36a874b2f3aae967376b6e435e"
HUMAN_RADIUS_M = 0.30  # Pinned official-human envelope in run_isaac_v12_fallback.py:155.
HUMAN_HEIGHT_M = 1.7357525825500488  # Pinned official visible top, same source:152.
ROBOT_RADIUS_M = 0.25  # Frozen P2B planner.yaml grid_map.double_cylinder_radius.
ROBOT_CYLINDER_OFFSET_M = 0.18  # Frozen P2B planner.yaml, along route heading.
MARGIN_M = 0.05
PCT_SEARCH_M = 0.085
PCT_MESH_HEIGHT_TOL_M = 0.08

sys.path.insert(0, str(PCT_CORE))
from pct_sim_clock_core import load_pinned_map, selected_ground_points  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_building_mesh(path: Path) -> tuple[np.ndarray, np.ndarray]:
    if sha256(path) != BUILDING_SHA:
        raise ValueError("Building collision USDA SHA-256 mismatch")
    text = path.read_text()
    def array(kind):
        match = re.search(re.escape(kind) + r"\s*=\s*(\[.*?\])", text, re.S)
        if match is None:
            raise ValueError(f"Building mesh {kind} missing")
        return ast.literal_eval(match.group(1))
    vertices = np.asarray(array("point3f[] points"), dtype=np.float64)
    face_counts = np.asarray(array("int[] faceVertexCounts"), dtype=np.int32)
    indices = np.asarray(array("int[] faceVertexIndices"), dtype=np.int32)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or not np.isfinite(vertices).all():
        raise ValueError("Building mesh points invalid")
    if len(face_counts) != 16448 or not np.all(face_counts == 3) or len(indices) != 3 * len(face_counts):
        raise ValueError("Building mesh triangle topology changed")
    if np.min(indices) < 0 or np.max(indices) >= len(vertices):
        raise ValueError("Building mesh face index out of range")
    return vertices, indices.reshape(-1, 3)


class MeshHeights:
    def __init__(self, vertices: np.ndarray, faces: np.ndarray):
        tri = vertices[faces]
        self.tri = tri
        a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
        self.denom = ((b[:, 1] - c[:, 1]) * (a[:, 0] - c[:, 0])
                      + (c[:, 0] - b[:, 0]) * (a[:, 1] - c[:, 1]))
        self.normal = np.cross(b - a, c - a)
        self.xy_min = np.min(tri[:, :, :2], axis=1)
        self.xy_max = np.max(tri[:, :, :2], axis=1)
        self._cache = {}

    def hits(self, x: float, y: float) -> list[dict]:
        key = (round(x, 4), round(y, 4))
        if key in self._cache:
            return self._cache[key]
        candidate = (np.abs(self.denom) > 1e-9) & (self.xy_min[:, 0] - 1e-7 <= x) & \
                    (x <= self.xy_max[:, 0] + 1e-7) & (self.xy_min[:, 1] - 1e-7 <= y) & \
                    (y <= self.xy_max[:, 1] + 1e-7)
        ids = np.nonzero(candidate)[0]
        a, b, c = self.tri[ids, 0], self.tri[ids, 1], self.tri[ids, 2]
        d = self.denom[ids]
        wa = ((b[:, 1] - c[:, 1]) * (x - c[:, 0])
              + (c[:, 0] - b[:, 0]) * (y - c[:, 1])) / d
        wb = ((c[:, 1] - a[:, 1]) * (x - c[:, 0])
              + (a[:, 0] - c[:, 0]) * (y - c[:, 1])) / d
        wc = 1.0 - wa - wb
        keep = (wa >= -1e-6) & (wb >= -1e-6) & (wc >= -1e-6)
        z = wa * a[:, 2] + wb * b[:, 2] + wc * c[:, 2]
        result = sorted(({"triangle": int(idx), "z_m": float(height),
                          "normal_z": float(self.normal[idx, 2] /
                                            max(np.linalg.norm(self.normal[idx]), 1e-12))}
                         for idx, height in zip(ids[keep], z[keep])),
                        key=lambda row: row["z_m"])
        self._cache[key] = result
        return result


class SelectedGround:
    def __init__(self):
        source = load_pinned_map()
        points = selected_ground_points(source, "identity")
        self.points = points.copy()
        self.points[:, 2] -= np.float32(0.03)  # Published display offset, not ground.
        self.tree = cKDTree(self.points[:, :2])
        self.center = np.asarray(source["center"], dtype=np.float64)
        self.grid_offset = np.asarray([source["data"].shape[2] // 2,
                                       source["data"].shape[3] // 2], dtype=np.int32)
        self.resolution = float(source["resolution"])

    def nearest(self, x: float, y: float, expected_z: float,
                max_delta: float = 0.26) -> dict | None:
        ids = self.tree.query_ball_point([x, y], PCT_SEARCH_M)
        rows = []
        for idx in ids:
            px, py, pz, cost = [float(value) for value in self.points[idx]]
            if abs(pz - expected_z) > max_delta:
                continue
            rows.append((abs(pz - expected_z), math.hypot(px - x, py - y), idx,
                         px, py, pz, cost))
        if not rows:
            return None
        _, dist, _, px, py, pz, cost = min(rows)
        grid = [int(round((coordinate - self.center[i]) / self.resolution)) + int(self.grid_offset[i])
                for i, coordinate in enumerate((px, py))]
        return {"cell_xy": grid, "world_xyz_m": [px, py, pz], "cost": cost,
                "xy_query_distance_m": dist}


def support_and_overhead(ground: SelectedGround, mesh: MeshHeights,
                         x: float, y: float, expected_z: float) -> dict:
    selected = ground.nearest(x, y, expected_z)
    if selected is None:
        return {"supported": False, "reason": "no selected PCT ground cell"}
    pz = selected["world_xyz_m"][2]
    hits = mesh.hits(x, y)
    near = [hit for hit in hits if abs(hit["z_m"] - pz) <= PCT_MESH_HEIGHT_TOL_M
            and abs(hit["normal_z"]) >= 0.7]
    overhead = [hit for hit in hits if hit["z_m"] > pz + 0.15]
    closest = min(near, key=lambda row: abs(row["z_m"] - pz)) if near else None
    above = min(overhead, key=lambda row: row["z_m"]) if overhead else None
    return {"supported": bool(closest), "selected": selected,
            "mesh_ground": closest, "mesh_ground_error_m":
                None if closest is None else closest["z_m"] - pz,
            "overhead": above,
            "headroom_m": None if above is None else above["z_m"] - pz,
            "headroom_status": ("measured_mesh_intersection" if above else
                                "no_mesh_overhead_intersection_unknown_or_open"),
            "reason": None if closest else "PCT height has no matching Building support triangle"}


def lateral_clearance(ground: SelectedGround, mesh: MeshHeights,
                      x: float, y: float, z: float) -> dict:
    """Distance to first unsupported transverse sample on either side."""
    sides = {}
    for name, sign in (("left", -1), ("right", 1)):
        supported = 0.0
        failure = None
        for step in range(1, 17):  # 0.05 to 0.80 m.
            offset = round(step * 0.05, 3)
            check = support_and_overhead(ground, mesh, x + sign * offset, y, z)
            if not check["supported"]:
                failure = {"offset_m": offset, "reason": check["reason"]}
                break
            supported = offset
        sides[name] = {"supported_to_m": supported, "first_failure": failure}
    return sides


def audit_path(ground: SelectedGround, mesh: MeshHeights, x: float,
               ys: list[float], seed_z: float, radius_m: float,
               height_m: float, label: str) -> dict:
    rows = []
    expected = seed_z
    for y in ys:
        row = support_and_overhead(ground, mesh, x, y, expected)
        row.update({"x_m": x, "y_m": y})
        if row.get("selected"):
            expected = row["selected"]["world_xyz_m"][2]
            sides = lateral_clearance(ground, mesh, x, y, expected)
            row["lateral"] = sides
            row["envelope_fits_lateral"] = all(
                side["supported_to_m"] >= radius_m + MARGIN_M
                for side in sides.values())
            row["headroom_pass"] = (None if row["headroom_m"] is None else
                                    row["headroom_m"] >= height_m + MARGIN_M)
            if label.startswith("robot"):
                # SCAN checks two XY cylinders at center +/- 0.18 m heading.
                offsets = [(0.0, -ROBOT_CYLINDER_OFFSET_M),
                           (0.0, ROBOT_CYLINDER_OFFSET_M)]
            else:
                # Approximate two shoe positions and their lateral width;
                # animation-dependent foot contact still needs Isaac evidence.
                offsets = [(-0.10, -0.10), (-0.10, 0.10),
                           (0.10, -0.10), (0.10, 0.10)]
            placements = []
            for dx, dy in offsets:
                probe = support_and_overhead(ground, mesh, x + dx, y + dy, expected)
                probe.update({"offset_xy_m": [dx, dy]})
                placements.append(probe)
            row["placement_samples"] = placements
            row["placement_pass"] = all(probe["supported"] for probe in placements)
        else:
            row["lateral"] = None
            row["envelope_fits_lateral"] = False
            row["headroom_pass"] = None
            row["placement_samples"] = []
            row["placement_pass"] = False
        row["sample_pass"] = (row["supported"] and row["envelope_fits_lateral"]
                              and row["headroom_pass"] is True and row["placement_pass"])
        rows.append(row)
    return {"label": label, "x_m": x, "radius_m": radius_m,
            "height_m": height_m, "samples": rows,
            "all_samples_pass": all(row["sample_pass"] for row in rows),
            "supported_count": sum(row["supported"] for row in rows),
            "lateral_fit_count": sum(row["envelope_fits_lateral"] for row in rows),
            "headroom_pass_count": sum(row["headroom_pass"] is True for row in rows),
            "headroom_unknown_count": sum(row["headroom_pass"] is None for row in rows),
            "placement_pass_count": sum(row["placement_pass"] for row in rows)}


def transverse_screen(ground: SelectedGround, mesh: MeshHeights) -> list[dict]:
    """Look for a same-tread x crossing with both ends inside verified support."""
    elevations = [(5.5, 0.195), (4.0, 0.331), (3.5, 0.467),
                  (2.5, 0.604), (1.8, 0.740), (1.6, 0.740),
                  (1.4, 0.740), (0.5, 0.977), (-0.5, 1.145),
                  (-1.5, 1.285), (-2.5, 1.422), (-3.5, 1.559),
                  (-4.5, 1.570)]
    xs = [round(float(value), 2) for value in np.arange(-6.2, -4.0, 0.05)]
    result = []
    for y, seed in elevations:
        samples = [audit_path(ground, mesh, x, [y], seed,
                              HUMAN_RADIUS_M, HUMAN_HEIGHT_M,
                              "official_human_transverse_tread")["samples"][0]
                   for x in xs]
        good = [sample["x_m"] for sample in samples if sample["sample_pass"]]
        runs = []
        for x in good:
            if not runs or x - runs[-1][-1] > 0.051:
                runs.append([x])
            else:
                runs[-1].append(x)
        intervals = [[run[0], run[-1]] for run in runs]
        longest = max((hi - lo for lo, hi in intervals), default=0.0)
        result.append({"y_m": y, "seed_z_for_layer_selection_m": seed,
                       "valid_center_intervals_x_m": intervals,
                       "longest_valid_crossing_m": round(longest, 3),
                       "pass_minimum_0p4m_motion": longest >= 0.4,
                       "valid_center_count": len(good),
                       "unknown_headroom_count": sum(
                           sample["headroom_pass"] is None for sample in samples),
                       "samples": samples})
    return result


def main() -> int:
    if sha256(PLANNER_YAML) != PLANNER_YAML_SHA:
        raise ValueError("frozen SCAN planner.yaml SHA-256 mismatch")
    vertices, faces = parse_building_mesh(BUILDING)
    ground = SelectedGround()
    mesh = MeshHeights(vertices, faces)
    xs = [round(float(value), 2) for value in np.arange(-5.6, -4.99, 0.1)]
    # The longer 2.8 -> 0.9 m reference line had three front/rear support
    # mismatches at nosings. This bounded overlap segment is screened afresh.
    robot_ys = [round(float(value), 2) for value in np.arange(2.0, 1.29, -0.1)]
    # Keep the official person on one measured tread. The runtime's linear
    # waypoint interpolation cannot represent a physical step transition.
    human_ys = [round(float(value), 2) for value in np.arange(1.4, 1.91, 0.1)]
    candidates = []
    for x in xs:
        robot = audit_path(ground, mesh, x, robot_ys, 0.74,
                           ROBOT_RADIUS_M, 0.70, "robot_ascending_stair")
        human = audit_path(ground, mesh, x, human_ys, 0.88,
                           HUMAN_RADIUS_M, HUMAN_HEIGHT_M, "official_human_descending_stair")
        candidates.append({"x_m": x, "robot": robot, "human": human,
                           "joint_route_pass": robot["all_samples_pass"] and human["all_samples_pass"]})
    transverse = transverse_screen(ground, mesh)
    best = max(candidates, key=lambda row: (
        row["joint_route_pass"],
        row["robot"]["lateral_fit_count"] + row["human"]["lateral_fit_count"],
        row["robot"]["placement_pass_count"] + row["human"]["placement_pass_count"],
        row["robot"]["supported_count"] + row["human"]["supported_count"]))
    report = {"schema_version": 1, "building_sha256": BUILDING_SHA,
              "pct_map_sha256": PCT_SHA, "pct_selected_count": int(len(ground.points)),
              "mesh_vertex_count": int(len(vertices)), "mesh_triangle_count": int(len(faces)),
              "planner_yaml_sha256": PLANNER_YAML_SHA,
              "sample_xy_spacing_m": 0.1, "lateral_probe_spacing_m": 0.05,
              "pct_search_radius_m": PCT_SEARCH_M,
              "pct_mesh_height_tolerance_m": PCT_MESH_HEIGHT_TOL_M,
              "robot_radius_m": ROBOT_RADIUS_M, "human_radius_m": HUMAN_RADIUS_M,
              "robot_cylinder_offset_m": ROBOT_CYLINDER_OFFSET_M,
              "human_height_m": HUMAN_HEIGHT_M, "margin_m": MARGIN_M,
              "candidates": candidates, "best_x_m": best["x_m"],
              "transverse_same_tread_screen": transverse,
              "any_0p4m_transverse_crossing": any(
                  row["pass_minimum_0p4m_motion"] for row in transverse),
              "any_joint_route_pass": any(row["joint_route_pass"] for row in candidates),
              "normal_winding_note": ("Ground acceptance uses abs(normal_z)>=0.7 "
                                      "because triangle winding can invert; signed "
                                      "normal_z is recorded for every matched triangle."),
              "overhead_note": ("A missing overhead ray intersection is unknown or "
                                "open sky, not proof of an obstacle. It is not "
                                "accepted as measured clearance."),
              "claim": "offline selected-ground and collision-mesh screening only; no Isaac contact or route approval"}
    out = HERE / "route_audit.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    if best["joint_route_pass"]:
        initial_center_distance = math.hypot(best["robot"]["samples"][0]["x_m"] -
                                             best["human"]["samples"][0]["x_m"],
                                             robot_ys[0] - human_ys[0])
        # The robot's front SCAN cylinder is closer to the human start.
        initial_hull_gap = (initial_center_distance - ROBOT_CYLINDER_OFFSET_M -
                            ROBOT_RADIUS_M - HUMAN_RADIUS_M)
        def proposed_path(kind):
            rows = best[kind]["samples"]
            return {
                "waypoints_ground_xyz_m": [
                    [row["x_m"], row["y_m"], row["selected"]["world_xyz_m"][2]]
                    for row in rows],
                "source_pct_cells": [row["selected"]["cell_xy"] for row in rows],
                "pct_xy_residual_m": [row["selected"]["xy_query_distance_m"] for row in rows],
                "mesh_ground_triangle_ids": [row["mesh_ground"]["triangle"] for row in rows],
            }
        proposal = {
            "schema_version": 1,
            "status": "geometry_screen_only_not_approved_or_scheduled",
            "frame_id": "world", "units": "m", "geometry_reviewed": False,
            "building_usda_sha256": BUILDING_SHA, "pct_map_sha256": PCT_SHA,
            "planner_yaml_sha256": PLANNER_YAML_SHA,
            "audit_report_sha256": sha256(out),
            "robot": proposed_path("robot"),
            "official_human": proposed_path("human"),
            "shared_y_interval_m": [1.4, 1.9],
            "initial_center_distance_m": initial_center_distance,
            "initial_hull_gap_m": initial_hull_gap,
            "initial_hull_gap_with_margin_m": initial_hull_gap - MARGIN_M,
            "initial_placement_pass": initial_hull_gap >= MARGIN_M,
            "route_choice": ("both centerline envelopes and sampled foot placements passed "
                             "offline PCT/Building checks on this short stair overlap"),
            "limits": ("The proposed initial robot and human envelopes overlap; "
                       "separated staging and stopping distance need a new design. "
                       "The human route stays on one PCT-selected tread so "
                       "linear actor-height interpolation does not cross a riser. "
                       "No actor timing, measured robot pose, continuous "
                       "collision, contact, or Isaac/SCAN behavior proved"),
        }
        (HERE / "proposed_stair_encounter.json").write_text(
            json.dumps(proposal, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"any_joint_route_pass": report["any_joint_route_pass"],
                      "best_x_m": report["best_x_m"],
                      "summary": [{"x": row["x_m"],
                                   "robot_supported": row["robot"]["supported_count"],
                                   "robot_lateral": row["robot"]["lateral_fit_count"],
                                   "robot_placements": row["robot"]["placement_pass_count"],
                                   "human_supported": row["human"]["supported_count"],
                                   "human_lateral": row["human"]["lateral_fit_count"],
                                   "human_placements": row["human"]["placement_pass_count"],
                                   "human_headroom": row["human"]["headroom_pass_count"]}
                                  for row in candidates]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
