#!/usr/bin/env python3
"""Review full-rate robot records and current-track evidence for one scene."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import statistics


def read(path):
    return json.loads(path.read_text())


def rows(path):
    return [json.loads(s) for s in path.read_text().splitlines() if s.strip()]


def review(run):
    artifacts = run / "returned_artifacts"
    robot = artifacts / "runner_output"
    summary = read(robot / "summary.json")
    metrics = rows(robot / "metrics.jsonl")
    truth = rows(robot / "official_human_truth.jsonl")
    events = rows(artifacts / "reactive_observations.jsonl")
    sensors = rows(robot / "sensor_metrics.jsonl")
    scenario = read(run / "inputs/stair_scenario.json")
    origin = read(robot / "run_clock.json")["simulation_origin_s"]
    journal = read(artifacts / "stair_driver_result.json")["journal"]
    moving = [r for r in metrics if r["command_horizontal_norm_mps"] > 0.02]
    first_motion = moving[0]["sim_time_s"] if moving else None
    before = [r for r in metrics if first_motion is not None and first_motion - 1.0 <= r["sim_time_s"] < first_motion]
    baseline_z = statistics.median(r["base_xyz"][2] for r in before or metrics[:50])
    first_xyz = metrics[0]["base_xyz"]
    yaw = scenario["spawn_yaw_rad"]
    progress = max((r["base_xyz"][0] - first_xyz[0]) * math.cos(yaw)
                   + (r["base_xyz"][1] - first_xyz[1]) * math.sin(yaw) for r in metrics)
    tracks = [e for e in events if e["event"] == "tracks" and e["data"]["complete"] and e["data"]["tracks"]]
    first_track = ((tracks[0]["data"]["header"]["stamp"]["sec"]
                    + tracks[0]["data"]["header"]["stamp"]["nanosec"] * 1e-9 - origin) if tracks else None)
    actor_moving = [r for r in truth if r["actor_truth"]["distance_m"] > 1e-5]
    actor_start = actor_moving[0]["sim_time_s"] if actor_moving else None
    deadline_cancel = next((r["sim_time_s"] for r in journal if r.get("event") == "end_observation_cancel"), math.inf)
    stop_windows, current = [], []
    for r in metrics:
        eligible = (first_motion is not None and first_motion < r["sim_time_s"] < deadline_cancel
                    and r["command_horizontal_norm_mps"] <= 0.01 and abs(r["admitted_command"][2]) <= 0.01
                    and r["horizontal_speed_mps"] <= 0.1 and abs(r["yaw_rate_radps"]) <= 0.15)
        if eligible and (not current or r["sim_time_s"] - current[-1]["sim_time_s"] <= 0.031):
            current.append(r)
        else:
            if current and current[-1]["sim_time_s"] - current[0]["sim_time_s"] >= 1.0:
                stop_windows.append([current[0]["sim_time_s"], current[-1]["sim_time_s"]])
            current = [r] if eligible else []
    if current and current[-1]["sim_time_s"] - current[0]["sim_time_s"] >= 1.0:
        stop_windows.append([current[0]["sim_time_s"], current[-1]["sim_time_s"]])
    # Simulator truth is consumed only here, after the episode. The footprint
    # proxy is conservative for this diagnostic; it is not a human contact sensor.
    by_step = {r["step"]: r for r in truth}
    gaps = []
    for r in metrics:
        human = by_step[r["step"]]["actor_truth"]["ground_xyz_m"]
        yaw = r["base_rpy_rad"][2]
        for offset in (-0.18, 0.18):
            center = [r["base_xyz"][0] + offset * math.cos(yaw), r["base_xyz"][1] + offset * math.sin(yaw)]
            gaps.append(math.dist(center, human[:2]) - 0.25 - 0.60)
    planner_log = (artifacts / "logs/scan_planner_node.log").read_text(errors="replace")
    blocks = [{"verdict": int(m[0]), "sim_time_s": float(m[1]) - origin}
              for m in re.findall(r"reactive_collision_blocked verdict=(\d+).*?now=([0-9.]+)", planner_log)]
    after_track = [e for e in events if e["event"] == "bspline" and first_track is not None
                   and e["clock_ns"] * 1e-9 - origin >= first_track]
    unique_terminals = {}
    for row in journal:
        for value in row.get("terminal_results", []):
            unique_terminals[json.dumps(value, sort_keys=True)] = value
    report = {
        "execution_completed": read(artifacts / "result.json").get("passed"),
        "returned_hashes_match": read(run / "return_verdict.json").get("returned_hashes_match"),
        "mode": scenario["mode"], "sim_seconds": summary["sim_seconds"],
        "first_nonzero_admitted_command_s": first_motion, "forward_progress_m": progress,
        "max_body_rise_from_precommand_m": max(r["base_xyz"][2] for r in metrics) - baseline_z,
        "max_nonfoot_force_n": summary["max_nonfoot_force_n"],
        "native_case_failed": summary["case_failed"], "native_termination_code": summary["termination_code"],
        "autoresets": summary["autoresets"], "pose_injection_events": summary["pose_injection_events"],
        "actual_sweep_count": len(sensors), "ready_sweeps": sum(r["rtx_capture"]["ready"] for r in sensors),
        "max_ray_direction_error": max(r["rtx_capture"]["max_direction_vector_error"] or 0 for r in sensors),
        "max_sensor_capture_wall_s": max(r["rtx_capture"]["wall_seconds"] for r in sensors),
        "actor_first_measured_motion_s": actor_start, "first_nonempty_track_s": first_track,
        "actor_motion_to_first_track_s": None if first_track is None or actor_start is None else first_track - actor_start,
        "nonempty_track_snapshots": len(tracks),
        "track_ids": sorted({t["id"] for e in tracks for t in e["data"]["tracks"]}),
        "full_rate_stop_windows_before_deadline_cancel_s": stop_windows,
        "minimum_conservative_xy_proxy_gap_m": min(gaps),
        "proxy_contract": "robot two 0.25 m disks at +/-0.18 m heading; actor 0.60 m disk; no physical human collider/contact claim",
        "collision_verdict_samples": blocks,
        "first_trajectory_update_after_first_track_delay_s": None if not after_track else after_track[0]["clock_ns"] * 1e-9 - origin - first_track,
        "timing_boundary": "next trajectory message after detection is temporal association, not proof of causality",
        "terminal_results": list(unique_terminals.values()),
        "video": str(robot / "third_person_master.mp4"),
        "video_sha256": hashlib.sha256((robot / "third_person_master.mp4").read_bytes()).hexdigest(),
        "claim": "One bounded integration observation; deadline cancellation never counts as avoidance"}
    report["navigation_assessment"] = ("no_navigation_motion" if not moving else "motion_observed_requires_route_contact_and_visual_review")
    (run / "scene_review.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    print(json.dumps(review(args.run), indent=2))
