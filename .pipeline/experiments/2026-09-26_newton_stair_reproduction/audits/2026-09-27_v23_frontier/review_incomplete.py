"""Review recorded cross-layer evidence without running or changing the robot."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    run = BASE / "runs" / args.run_id
    if run.parent != BASE / "runs":
        raise ValueError("Expected an experiment run ID")
    result, process = read(run / "result.json"), read(run / "process.json")
    request = read(run / "episode_request.json")
    telemetry = rows(run / "telemetry.jsonl")
    applied = rows(run / "applied_sent.jsonl")
    observations = rows(run / "artifacts/reactive_observations.jsonl")
    errors = rows(run / "applied_read_errors.jsonl")
    clock = rows(run / "clock_samples.jsonl")
    source_checks = {}
    for manifest, key in (("source_identity.json", "inputs"), ("runtime_sources.json", "records")):
        records = read(BASE / "setup" / manifest)[key]
        source_checks[manifest] = {"files": len(records), "mismatches": [r["path"] for r in records
            if sha(BASE / r["path"]) != r["sha256"]]}
    build = Path(request.get("native_build", str(BASE / "builds/scan33_humble_amd64_v1")))
    for manifest in ("source_sha256.json", "install_sha256.json"):
        records = read(build / manifest)
        source_checks[manifest] = {"files": len(records), "mismatches": [p for p, digest in records.items()
            if sha(build / p) != digest]}
    native_audit = rows(run / "bridge_scan_audit.jsonl")
    sensor_manifest = read(run / "sensor_manifest.json")
    moving_curves = []
    for row in observations:
        if row["event"] != "bspline":
            continue
        curve = row["data"]
        points = [[p[k] for k in ("x", "y", "z")] for p in curve["pos_pts"]]
        if max(math.dist(points[0], p) for p in points) > 1e-6:
            moving_curves.append({"received_sim_s": row["clock_ns"] / 1e9,
                "received_linux_s": row["wall_monotonic_ns"] / 1e9,
                "control_points": len(points), "duration_sim_s": curve["knots"][-curve["order"]-1] - curve["knots"][curve["order"]],
                "first_control_xyz": points[0], "last_control_xyz": points[-1]})
    first_ack_ns = applied[0]["ack"]["linux_receive_ns"]
    after_ready_errors = [r for r in errors if r["monotonic_ns"] >= first_ack_ns]
    failures = [r for r in telemetry if r["command_reason"] in ("disconnected", "clock_unsynchronized")]
    by_sequence = {r["state_sequence"]: r for r in telemetry}
    ack_errors = []
    for row in applied:
        snapshot, ack = row["snapshot"], row["ack"]
        seq = snapshot["state_epoch"]["state_sequence"]
        digest = hashlib.sha256(json.dumps(snapshot, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        actual = [snapshot["applied_command"][k] for k in ("vx", "vy", "wz")]
        if (digest != ack["sha256"] or seq != ack["sequence"] or seq != ack["original_reader_sequence"]
                or actual != by_sequence[seq]["command"] or not 0 <= ack["receive_age_s"] <= 2.):
            ack_errors.append(seq)
    last = telemetry[-1]
    stop_window = [r for r in telemetry if r["physics_time_s"] >= last["physics_time_s"] - 1.]
    config = read(run / "backend_config.json")["applied_evidence"]
    stop_verified = all(math.dist(r["command"], [0, 0, 0]) <= config["stop_command_norm"]
        and math.hypot(*r["body_sensor"]["linear_world"][:2]) <= config["stop_speed_mps"]
        and abs(r["body_sensor"]["angular_body"][2]) <= config["stop_yaw_rate_radps"] for r in stop_window)
    terminal = result["last_backend"]["terminal_results"]
    copyback = read(run / "state_copyback.json")
    startup_steps = 0
    if request.get("startup_mode") == "factory_pd":
        import numpy as np
        startup_steps = len(np.load(run / "factory_full_rate.npz")["records"])
    checks = {
        "process_completed": process["exit_code"] == 0 and not process["timed_out"],
        "source_identity": all(not x["mismatches"] for x in source_checks.values()),
        "continuous_physics_steps": all(r["physics_steps"] == startup_steps + 20 * (i + 1) for i, r in enumerate(telemetry)),
        "positive_ack_and_applied_trace": bool(applied) and not ack_errors,
        "source_timestamp_not_restamped": all(r["snapshot"]["wall_monotonic_ns"] ==
            r["snapshot"]["host_step_started_monotonic_ns"] - r["snapshot"]["clock_mapping"]["local_minus_remote_ns"]
            - r["snapshot"]["clock_mapping"]["uncertainty_ns"] for r in applied),
        "actual_command_enters_policy": max(r["snapshot"]["measured"]["command_obs_error"] for r in applied) == 0,
        "clock_and_disconnect_fail_closed": all(r["command"] == [0., 0., 0.] for r in failures),
        "no_applied_read_errors_after_first_ack": not after_ready_errors,
        "linux_bytes_returned": copyback.get("verified", False) and
            sha(run / "returned_external_episode/current_command.json") == applied[-1]["ack"]["sha256"],
        "paired_unfiltered_sensor": len(native_audit) == len(sensor_manifest) and all(
            r["raw_point_count"] == r["planning_point_count"] > 0 and r["filtered_ground_point_count"] == 0
            and r["telemetry_overwrite_count"] == 0 for r in native_audit),
        "sensor_files_intact": all(sha(run / r["file"]) == r["sha256"] for r in sensor_manifest),
        "native_moving_curves_observed": bool(moving_curves),
        "actual_nonzero_commands_observed": result["nonzero_command_steps"] > 0,
        "bounded_driver_completed": (run / "artifacts/stair_driver_result.json").exists() and read(run / "artifacts/stair_driver_result.json")["execution_completed"],
        "measured_stop_verified": stop_verified,
    }
    goal = read(run / "inputs/stair_scenario.json")["goal_ground_xyz_m"][:2]
    contact_rows = [r.get("obstacle_contact_scoring_only") for r in telemetry]
    contact_complete = all(isinstance(c, dict) and c["physics_substeps_checked"] == row["physics_steps"]
                           for row, c in zip(telemetry, contact_rows))
    navigation_rows = telemetry
    if request.get("startup_mode", "policy") == "pd_stand":
        navigation_rows = [r for r in telemetry if r.get("navigation_ready") is True]
        checks["startup_completed_before_navigation"] = bool(navigation_rows) and all(
            r["command"] == [0., 0., 0.] for r in telemetry if not r.get("navigation_ready", False))
        checks["no_fabricated_pd_policy_evidence"] = all(
            r["snapshot"].get("control", {}).get("policy_observation_valid") is True
            and by_sequence[r["snapshot"]["state_epoch"]["state_sequence"]]["policy_calls"] > 0 for r in applied)
    flat_checks = {
        "actual_goal_arrival": any(t["status"] == "arrived" for t in terminal),
        "every_physics_substep_scored": contact_complete,
        "no_obstacle_surface_contact": contact_complete and contact_rows[-1]["touching_substeps"] == 0,
        "upright_above_09": min(r["base_up_z"] for r in telemetry) > .9,
        "body_above_025m": bool(navigation_rows) and min(r["body_sensor"]["position"][2] for r in navigation_rows) > .25,
        "goal_distance_below_025m": math.dist(last["body_sensor"]["position"][:2], goal) < .25,
    }
    flat_validated = (request.get("scene") in ("flat_static", "flat_box") and
                      all(checks.values()) and all(flat_checks.values()))
    output = {"run_id": args.run_id, "stage": "experiment + analysis", "source_checks": source_checks,
        "checks": checks, "interface_checks_passed": all(checks.values()),
        "navigation_validated": flat_validated, "flat_navigation_checks": flat_checks,
        "height_assessment_window": "navigation_ready" if request.get("startup_mode") == "pd_stand" else "all_physics",
        "full_rate_obstacle_contact_scoring": contact_rows[-1] if contact_complete else None,
        "navigation_terminal_results": terminal,
        "moving_curves": moving_curves, "event_counts": dict(Counter(r["event"] for r in observations)),
        "physics_duration_s": result["physics_duration_s"],
        "policy_steps": result.get("policy_steps", len(telemetry)), "control_steps": len(telemetry),
        "nonzero_command_steps": result["nonzero_command_steps"], "displacement_xyz_m": result["displacement_xyz_m"],
        "final_goal_xy_distance_m": math.dist(last["body_sensor"]["position"][:2], goal),
        "minimum_base_up_z": min(r["base_up_z"] for r in telemetry),
        "positive_applied_acknowledgments": len(applied), "ack_errors": ack_errors,
        "receive_age_range_s": [min(r["ack"]["receive_age_s"] for r in applied), max(r["ack"]["receive_age_s"] for r in applied)],
        "applied_reader_errors_before_first_ack": dict(Counter(r["error"] for r in errors if r["monotonic_ns"] < first_ack_ns)),
        "applied_reader_errors_after_first_ack": after_ready_errors,
        "command_reasons": dict(Counter(r["command_reason"] for r in telemetry)),
        "rejected_clock_samples": sum(r.get("accepted") is False for r in clock),
        "command_transport": result["command_transport"],
        "nonempty_current_track_messages": sum(r["event"] == "tracks" and bool(r["data"].get("tracks")) for r in observations),
        "claim": ("The declared flat control-scene arrival, full-rate contact, posture and stop checks passed; not arbitrary-world, stair or hardware validation"
                  if flat_validated else "Recorded native/Newton episode; full flat-navigation acceptance not established by this review"),
        "video_states_sha256": sha(run / "video_states.json"),
        "review_script_sha256": sha(Path(__file__))}
    target = BASE / "validation" / (args.run_id + "_review.json")
    if target.exists():
        raise FileExistsError(target)
    target.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))
    if not all(checks.values()):
        raise AssertionError("One or more interface checks failed")


if __name__ == "__main__":
    main()
