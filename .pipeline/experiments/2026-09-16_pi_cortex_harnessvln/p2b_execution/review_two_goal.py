#!/usr/bin/env python3
"""Independently review returned two-goal artifacts against frozen criteria.

The HTTP terminal ledger is an input to correlate with raw physics records,
never sufficient proof by itself. This script does not drive any simulator.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path


def load(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def instant_still(row, pilot):
    command = row["admitted_command"]
    return (
        not row["command_stale"]
        and row["command_reason"] in {"active", "held", "stopped", "zero_hold", "cancelled"}
        and math.hypot(command[0], command[1]) <= pilot["stop_command_norm"]
        and abs(command[2]) <= pilot["stop_command_norm"]
        and row["horizontal_speed_mps"] <= pilot["stop_speed_mps"]
        and abs(row["yaw_rate_radps"]) <= pilot["stop_yaw_rate_radps"]
    )


def review(run):
    artifacts = run / "returned_artifacts"
    summary = load(artifacts / "runner_output/summary.json")
    pilot = load(run / "inputs/pilot.json")
    journal = load(artifacts / "pilot_journal.json")
    rows = [json.loads(line) for line in (artifacts / "runner_output/metrics.jsonl").read_text().splitlines() if line]
    hash_manifest = artifacts / "artifact_hashes.json"
    expected = load(hash_manifest) if hash_manifest.exists() else {}
    returned = {
        str(p.relative_to(artifacts)): digest(p)
        for p in artifacts.rglob("*") if p.is_file() and p.name != "artifact_hashes.json"
    }
    expected.pop("artifact_hashes.json", None)
    source = load(run / "source_env_hashes.json")
    checks = {
        "artifact_hash_manifest_present": hash_manifest.exists(),
        "returned_hashes_match": bool(expected) and returned == expected,
        "executed_runner_matches_package": digest(artifacts / "runner_output/executed_run_pct_scan_building.py") == source["patched_runner_sha256"],
        "external_finished": summary.get("status") == "EXTERNAL_EPISODE_FINISHED",
        "driver_finished": journal.get("passed") is True,
        "within_sim_ceiling": summary["sim_seconds"] <= pilot["max_sim_seconds"] + 0.03,
        "within_wall_ceiling": summary["wall_seconds"] <= pilot["max_wall_seconds"],
        "no_reset_or_pose_injection": all(summary.get(k) == 0 for k in ("autoresets", "reset_attempts", "pose_write_attempts", "pose_injection_events")),
        "no_contact_guard_failure": not summary["contact_guard"]["failed"] and not summary["contact_guard"]["contact_detected"],
        "metrics_count_matches_summary": bool(rows) and len(rows) == summary["record_count"],
        "continuous_control_steps": bool(rows) and all(b["step"] == a["step"] + 1 for a, b in zip(rows, rows[1:])),
        "continuous_sim_clock": bool(rows) and all(0 < b["sim_time_s"] - a["sim_time_s"] <= 0.020001 for a, b in zip(rows, rows[1:])),
        "continuous_state_sequence": bool(rows) and all(b["state_sequence"] == a["state_sequence"] + 1 for a, b in zip(rows, rows[1:])),
        "command_observation_parity": bool(rows) and max(r["command_obs_error"] for r in rows) <= 1e-7,
        "actual_nonzero_motion": bool(rows) and max(r["command_horizontal_norm_mps"] for r in rows) > 0.01,
    }
    terminals = {}
    plans = {}
    cancel_event = None
    initial_snapshot = None
    for event in journal["events"]:
        state = event.get("state", {})
        for record in state.get("terminal_results", []):
            terminals[(record["request_id"], record["status"])] = record
        for record in state.get("pct", {}).get("plan_history", []):
            plans[record.get("request_id", str(len(plans)))] = record
        if event.get("event") == "post_cancel":
            cancel_event = event
        if event.get("event") in {"initial_snapshot", "initial_cancel_reference_snapshot"}:
            initial_snapshot = event["snapshot"]
    run_id = load(run / "run_request.json")["run_id"]
    wanted = [
        (run_id + "-goal-a-attempt-1", "cancelled", pilot["goals"][0]),
        (run_id + "-goal-a-attempt-2", "arrived", pilot["goals"][0]),
        (run_id + "-goal-b", "arrived", pilot["goals"][1]),
    ]
    records = []
    for request_id, status, goal in wanted:
        terminal = terminals.get((request_id, status))
        item = {"request_id": request_id, "status": status, "present": terminal is not None}
        checks[request_id + ":terminal_present"] = terminal is not None
        if terminal is None:
            records.append(item)
            continue
        before = [r for r in rows if r["state_sample_monotonic_ns"] <= terminal["monotonic_s"] * 1e9]
        window = []
        for row in reversed(before):
            if not instant_still(row, pilot):
                break
            window.append(row)
            if window[0]["sim_time_s"] - window[-1]["sim_time_s"] >= pilot["stop_dwell_sim_seconds"]:
                break
        span = window[0]["sim_time_s"] - window[-1]["sim_time_s"] if window else 0.0
        valid_dwell = span >= pilot["stop_dwell_sim_seconds"]
        item.update({"terminal": terminal, "raw_stop_span_sim_s": span, "raw_stop_samples": len(window)})
        checks[request_id + ":raw_physics_stop_dwell"] = valid_dwell
        if before:
            row = before[-1]
            xy_error = math.dist(row["base_xyz"][:2], goal["ground_xyz_m"][:2])
            z_error = abs(row["base_xyz"][2] - goal["ground_xyz_m"][2] - pilot["nominal_body_height_m"])
            lag = terminal["monotonic_s"] - row["state_sample_monotonic_ns"] / 1e9
            item.update({"base_xyz": row["base_xyz"], "sim_time_s": row["sim_time_s"], "target_xy_error_m": xy_error, "target_body_z_error_m": z_error, "raw_state_age_s": lag})
            checks[request_id + ":raw_state_fresh"] = 0 <= lag <= 0.25
            if status == "arrived":
                checks[request_id + ":requested_target_geometry"] = xy_error <= pilot["goal_xy_tolerance_m"] and z_error <= pilot["goal_z_tolerance_m"]
        else:
            checks[request_id + ":raw_state_fresh"] = False
        records.append(item)
    terminal_times = [r["terminal"]["monotonic_s"] for r in records if r["present"]]
    checks["cancel_then_two_arrivals_in_order"] = len(terminal_times) == 3 and all(a < b for a, b in zip(terminal_times, terminal_times[1:]))
    plan_reviews = []
    for request_id, _, goal in wanted:
        plan = plans.get(request_id)
        checks[request_id + ":native_plan_recorded"] = bool(plan and plan.get("ok") and plan.get("waypoints_m"))
        if not plan or not plan.get("ok"):
            continue
        request = plan["request"]
        before = [r for r in rows if r["state_sample_monotonic_ns"] <= plan["started_monotonic_s"] * 1e9]
        checks[request_id + ":requested_pct_target"] = request["target_xyz_m"] == goal["ground_xyz_m"]
        checks[request_id + ":frozen_pct_layer"] = request["start_layer"] == pilot["pct_layer"] == request["target_layer"]
        if before:
            measured = before[-1]["base_xyz"]
            start_error = math.dist(request["start_xyz_m"], [measured[0], measured[1], measured[2] - pilot["nominal_body_height_m"]])
            age = plan["started_monotonic_s"] - before[-1]["state_sample_monotonic_ns"] / 1e9
            # The ROS observation can precede this last physics record slightly.
            # A 5 cm envelope accommodates that transport delay at native speed.
            checks[request_id + ":plan_starts_at_measured_pose"] = start_error <= 0.05 and 0 <= age <= 0.25
            plan_reviews.append({"request_id": request_id, "start_error_m": start_error, "raw_pose_age_s": age})
        else:
            checks[request_id + ":plan_starts_at_measured_pose"] = False
    if cancel_event is None:
        checks["cancel_after_0p4m_measured_displacement"] = False
    else:
        cancel_position = cancel_event["trigger_snapshot"]["measured"]["base_xyz"]
        # Use the driver's declared cancellation reference, not startup balance
        # drift before a goal was even issued. The PCT request provides an
        # independent measured reference if an older journal lacks this event.
        if initial_snapshot is not None:
            start_xy = initial_snapshot["measured"]["base_xyz"][:2]
        else:
            first_plan = plans.get(wanted[0][0])
            start_xy = first_plan["request"]["start_xyz_m"][:2] if first_plan else rows[0]["base_xyz"][:2]
        displacement = math.dist(cancel_position[:2], start_xy)
        checks["cancel_after_0p4m_measured_displacement"] = displacement >= 0.4
        records[0]["cancel_displacement_m"] = displacement
        if records[0].get("raw_stop_samples", 0):
            checks["cancel_stop_precedes_resubmission"] = terminal_times[0] < terminal_times[1] if len(terminal_times) == 3 else False
    return {
        "passed": all(checks.values()),
        "claim": "Known-map, simulator-truth continuous PCT/SCAN/V12 two-goal pilot only; not language/vision/SLAM or physical deployment validation.",
        "checks": checks,
        "terminals": records,
        "plan_history": list(plans.values()),
        "plan_pose_reviews": plan_reviews,
        "rows": len(rows),
        "sim_seconds": summary["sim_seconds"],
        "wall_seconds": summary["wall_seconds"],
        "travel_xy_m": summary["travel_xy_m"],
        "max_nonfoot_force_n": summary["max_nonfoot_force_n"],
        "max_roll_deg": summary["max_abs_roll_deg"],
        "max_pitch_deg": summary["max_abs_pitch_deg"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = review(args.run)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": result["passed"], "checks": result["checks"]}, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
