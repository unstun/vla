#!/usr/bin/env python3
"""Prepare a local, non-executable SCAN reactive stair integration overlay.

The old two-goal worker is deliberately not reused as an executor: its process
graph omits the terrain sidecar and current-track subscriber. This tool freezes
the exact local sources and runtime configuration needed for a reviewed worker.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EXP = ROOT / ".pipeline/experiments/2026-09-23_scan_reactive_stair"
P2B = ROOT / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution"
PILOT = ROOT / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/run_two_goal_pilot.py"
SCAN = P2B / "builds/scan_09"
REMOTE_SCAN = "/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/builds/scan_09"
OFFICIAL = EXP / "isaac_candidate/building_official_mesh_source"
FIRST_HIT = EXP / "isaac_candidate/first_hit_v2/result.json"
ROUTE = EXP / "isaac_candidate/route_audit/proposed_stair_encounter.json"
FOXY = "e4aa715467b93f20a9d9cdbb6a1dbd0d3c8c1e033e7792f2d889cba03db227d8"
HUMBLE = "40f0fa16091e2b6e24fd82058ceb01dbe76c001276234af0b9a44ac0e3787555"
SOURCE_FILES = {
    "runner/run_pct_scan_building.py": OFFICIAL / "run_pct_scan_building.py",
    "runner/official_building_human.py": OFFICIAL / "official_building_human.py",
    "sidecar/pct_sim_clock_core.py": P2B / "reactive_stair/pct_sim_clock_core.py",
    "sidecar/pct_sim_clock_publisher.py": P2B / "reactive_stair/pct_sim_clock_publisher.py",
    "driver/single_goal_driver.py": HERE / "single_goal_driver.py",
    "evidence/first_hit_result.json": FIRST_HIT,
    "evidence/scan_build_result.json": SCAN / "build_result.json",
    "evidence/scan_source_sha256.json": SCAN / "source_sha256.json",
    "evidence/scan_install_identity.json": SCAN / "install_identity.json",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_pilot():
    spec = importlib.util.spec_from_file_location("two_goal_pilot_reference", PILOT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def gate_report(route: Path = ROUTE, first_hit: Path = FIRST_HIT) -> dict:
    """Record observed gates; no caller-supplied hash can approve an actor route."""
    errors = []
    source = (OFFICIAL / "official_building_human.py").read_text(encoding="utf-8")
    match = re.search(r"^APPROVED_ROUTE_SHA256\s*=\s*(.+)$", source, re.MULTILINE)
    approval = None if match is None else match.group(1).strip()
    if approval in (None, "None"):
        errors.append("official actor route has no source-pinned APPROVED_ROUTE_SHA256")
    elif not re.fullmatch(r'["\'][0-9a-f]{64}["\']', approval):
        errors.append("official actor route approval has an invalid source literal")
    elif not route.is_file() or digest(route) != approval[1:-1]:
        errors.append("official actor route bytes differ from source-pinned approval")
    if route.is_file():
        route_data = read(route)
        if route_data.get("geometry_reviewed") is not True:
            errors.append("actor route has no reviewed geometry")
        robot = (route_data.get("robot") or {}).get("waypoints_ground_xyz_m") or []
        human = (route_data.get("official_human") or {}).get("waypoints_ground_xyz_m") or []
        if robot and human:
            distance = sum((float(robot[0][axis]) - float(human[0][axis])) ** 2
                           for axis in (0, 1)) ** 0.5
            if distance <= 0.83:
                errors.append("proposed robot/person start separation %.3f m <= 0.83 m minimum" % distance)
    if not first_hit.is_file() or read(first_hit).get("passed") is not True:
        errors.append("official mesh two-pose LiDAR first-hit has not passed")
    build = read(SCAN / "build_result.json")
    if build.get("passed") is not True or build.get("source_matches_before_after") is not True:
        errors.append("scan_09 Foxy build source identity failed")
    return {
        "passed": not errors,
        "errors": errors,
        "approved_route_source_literal": approval,
        "actor_route": str(route),
        "actor_route_sha256": digest(route) if route.is_file() else None,
        "first_hit": str(first_hit),
        "first_hit_sha256": digest(first_hit) if first_hit.is_file() else None,
        "scan_build_result_sha256": digest(SCAN / "build_result.json"),
    }


def prepare(output: Path, run_id: str, goal: list[float] | None = None) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_]{1,64}", run_id):
        raise ValueError("run_id must contain only ASCII letters, digits, or underscore")
    if output.exists():
        raise FileExistsError(output)
    pilot = load_pilot()
    scan_gate = pilot.build_scan_workspace_gate(SCAN, REMOTE_SCAN, False)
    if scan_gate["install_identity_present"] is not True:
        raise RuntimeError("scan_09 install identity is required")
    pilot.verify_input_manifest()
    pilot.verify_bridge_source()
    pilot.verify_pct_runtime_manifest()
    gate = gate_report()
    output.mkdir(parents=True)
    try:
        for relative, source in SOURCE_FILES.items():
            destination = output / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        for name in ("planner.yaml", "controller.yaml"):
            destination = output / "config" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(P2B / "baseline_config" / name, destination)
        pilot.make_scan_runtime_configs(output / "config")
        planner = (output / "config/planner.yaml").read_text(encoding="utf-8")
        if "use_sim_time: true" not in planner or "grid_map.cloud_is_world: false" not in planner:
            raise RuntimeError("SCAN planner clock or cloud frame contract changed")
        pilot.make_bridge_config(output / "config/foxy_bridge.yaml", 46240, 46241)
        baseline = read(P2B / "inputs/pilot.json")
        pilot.make_backend_config(output / "config/backend.json", baseline, run_id, 8765, 47631)
        backend = read(output / "config/backend.json")
        backend["map"]["epoch"] = "stair_reactive"
        write(output / "config/backend.json", backend)
        for relative, source in {
            "inputs/building.usda": P2B / "inputs/building.usda",
            "inputs/new_building.pickle": P2B / "inputs/new_building.pickle",
            "inputs/actor_route.proposed.json": ROUTE,
        }.items():
            destination = output / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        if goal is not None and (len(goal) != 3 or not all(-1e6 < value < 1e6 for value in goal)):
            raise ValueError("goal must be three finite world ground coordinates")
        write(output / "inputs/single_goal.json", {
            "schema_version": 1,
            "frame_id": "world",
            "map_epoch": "stair_reactive",
            "map_revision": 1,
            "goal_id": "stair-goal",
            "goal_ground_xyz_m": goal,
            "spawn_ground_xyz_m": None,
            "max_sim_seconds": 45.0,
            "max_wall_seconds": 1200.0,
            "stop_dwell_sim_seconds": 1.0,
            "stop_command_norm": baseline["stop_command_norm"],
            "stop_speed_mps": baseline["stop_speed_mps"],
            "stop_yaw_rate_radps": baseline["stop_yaw_rate_radps"],
            "status": "unapproved_goal_candidate" if goal else "pending_reviewed_stair_goal",
        })
        files = {
            path.relative_to(output).as_posix(): digest(path)
            for path in sorted(output.rglob("*")) if path.is_file()
        }
        write(output / "source_manifest.json", {
            "schema_version": 1,
            "candidate_status": "historical_scan_09_first_hit_v2_preparation_snapshot",
            "files": files,
            "source_paths": {key: str(value) for key, value in SOURCE_FILES.items()},
            "scan_remote_workspace": REMOTE_SCAN,
            "scan_source_manifest_sha256": digest(SCAN / "source_sha256.json"),
            "scan_install_identity_sha256": digest(SCAN / "install_identity.json"),
            "scan_source_file_count": len(scan_gate["expected_source_files"]),
            "scan_installed_file_count": scan_gate["installed_file_count"],
            "foxy_image_id": FOXY,
            "humble_image_id": HUMBLE,
            "planner_baseline_sha256": digest(P2B / "baseline_config/planner.yaml"),
            "cloud_input": "raw paired LiDAR and lidar_pose; no simulator actor truth",
            "person_input": "scan_reactive_tracker/moving_cluster_tracker from current LiDAR only",
            "tomogram_publishers": ["pct_sim_clock_ground_publisher"],
            "pct_socket_worker": "backend_adapter.pct_worker; does not publish /pct_tomogram",
            "ros_domain_id": 192,
        })
        write(output / "execution_gate.json", gate)
        write(output / "package_status.json", {
            "schema_version": 1,
            "run_id": run_id,
            "status": "prepared_overlay_execution_blocked",
            "candidate_status": "historical_scan_09_first_hit_v2_preparation_snapshot",
            "execution_allowed": False,
            "gate_errors": gate["errors"] + [
                "scan_09 and first_hit_v2 are historical preparation identities, not latest candidate selection",
                "single-goal worker has not replaced pilot two-goal worker",
                "remote source/install before-after and artifact return checks are not wired",
                "stair goal and robot spawn require route review",
            ],
            "claim": "Local source/configuration preparation only; no ROS, Isaac, contact, or robot motion evidence",
        })
    except BaseException:
        shutil.rmtree(output)
        raise
    return read(output / "package_status.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--goal-ground-xyz", type=float, nargs=3)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if args.execute:
        gate = gate_report()
        raise RuntimeError("execution refused: " + "; ".join(gate["errors"] + [
            "single-goal remote worker and sync-back gate are not implemented"
        ]))
    status = prepare(args.output, args.run_id, args.goal_ground_xyz)
    print(json.dumps(status, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
