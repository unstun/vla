#!/usr/bin/env python3
"""Prepare a separated stair encounter from pinned PCT and Building geometry."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "isaac_candidate/route_audit"))
import audit_stair_routes as audit


def save(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def prepare(output, spawn_x=-5.3, spawn_y=6.0):
    if output.exists():
        raise FileExistsError(output)
    vertices, faces = audit.parse_building_mesh(audit.BUILDING)
    mesh, ground = audit.MeshHeights(vertices, faces), audit.SelectedGround()
    start = audit.audit_path(ground, mesh, spawn_x, [spawn_y], 0.058, audit.ROBOT_RADIUS_M, 0.70, "robot_spawn")
    goal = audit.audit_path(ground, mesh, -5.3, [1.0], 0.876, audit.ROBOT_RADIUS_M, 0.70, "robot_goal")
    human = audit.audit_path(ground, mesh, -5.3, [1.4, 1.5, 1.6, 1.7, 1.8, 1.9],
                            0.740, audit.HUMAN_RADIUS_M, audit.HUMAN_HEIGHT_M, "official_human_tread")
    if not all(row["all_samples_pass"] for row in (start, goal, human)):
        raise ValueError("spawn, goal, or human tread failed the unchanged geometry screen")
    def xyz(row):
        return [row["x_m"], row["y_m"], row["selected"]["world_xyz_m"][2]]
    spawn = xyz(start["samples"][0])
    target = xyz(goal["samples"][0])
    actor_points = [xyz(row) for row in human["samples"]]
    separation = math.dist(spawn[:2], actor_points[0][:2])
    if separation <= 0.83:
        raise ValueError("initial envelopes overlap")
    output.mkdir(parents=True)
    geometry = {"schema_version": 1, "building_usda_sha256": audit.BUILDING_SHA,
                "pct_map_sha256": audit.PCT_SHA, "planner_yaml_sha256": audit.PLANNER_YAML_SHA,
                "robot_start": start, "robot_goal": goal, "human": human,
                "initial_center_distance_m": separation,
                "claim": "Endpoint and actor-tread geometry screen; native PCT route and dynamic contacts require runtime evidence"}
    save(output / "geometry.json", geometry)
    route = {"schema_version": 1, "frame_id": "world", "geometry_reviewed": True,
             "geometry_reviewed_by": "Codex offline pinned PCT/Building screen; no human review claimed",
             "building_usda_sha256": audit.BUILDING_SHA,
             "geometry_evidence_sha256": hashlib.sha256((output / "geometry.json").read_bytes()).hexdigest(),
             "waypoints_ground_xyz_m": actor_points, "speed_mps": 0.3, "start_delay_s": 10.0,
             "claim": "Official actor remains on one measured tread; actor truth is scoring-only"}
    save(output / "actor_route.json", route)
    scenario = {"schema_version": 1, "frame_id": "world", "units": "m",
                "spawn_ground_xyz_m": spawn, "spawn_yaw_rad": -math.pi / 2,
                "goal_ground_xyz_m": target, "nominal_body_height_m": 0.35,
                "actor_route_sha256": hashlib.sha256((output / "actor_route.json").read_bytes()).hexdigest(),
                "initial_center_distance_m": separation, "initial_placement_pass": True,
                "max_sim_seconds": 35.0, "max_wall_seconds": 900.0,
                "outcome": "Report native route completion or measured reactive stop/yield with contact, fall and timing evidence",
                "navigation_input": "native PCT map, actual RTX/Livox geometric sweeps, sensor-derived current tracks",
                "human_truth": "excluded from planner/tracker input",
                "camera": {"trail_m": 1.4, "lateral_m": 0.0, "height_m": 1.3,
                           "look_ahead_m": 1.5, "look_down_m": -0.4, "heading_mode": "initial"}}
    save(output / "scenario.json", scenario)
    return scenario


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--spawn-x", type=float, default=-5.3)
    parser.add_argument("--spawn-y", type=float, default=6.0)
    args = parser.parse_args()
    print(json.dumps(prepare(args.output, args.spawn_x, args.spawn_y), indent=2))
