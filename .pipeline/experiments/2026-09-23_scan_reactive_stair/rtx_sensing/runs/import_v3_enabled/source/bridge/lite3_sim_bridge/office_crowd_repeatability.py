"""Repeatability comparison for same-input Office L0 crowd runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalized_identity(value: Any, run_id: str) -> Any:
    """Remove only run-directory identity while retaining runtime contracts."""
    if isinstance(value, dict):
        return {
            key: _normalized_identity(item, run_id)
            for key, item in value.items()
            if key not in {"config_sha256", "run_id"}
        }
    if isinstance(value, list):
        return [_normalized_identity(item, run_id) for item in value]
    if isinstance(value, str):
        return value.replace(run_id, "{RUN_ID}")
    return value


def _identity_contract_sha256(identity: Mapping[str, Any], run_id: str) -> str:
    normalized = _normalized_identity(identity, run_id)
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compare_office_crowd_runs(
    report_1: Mapping[str, Any],
    report_2: Mapping[str, Any],
    run_identity_1: Mapping[str, Any],
    run_identity_2: Mapping[str, Any],
    run_1_id: str,
    run_2_id: str,
    effective_input_sha256_1: str,
    effective_input_sha256_2: str,
    tolerances: Optional[Mapping[str, float]] = None,
) -> Dict[str, Any]:
    """Compare two same-input Office L0 crowd runs for repeatability."""
    tols = {
        "max_goal_xy_error_diff_m": 0.15,
    }
    if tolerances:
        tols.update(tolerances)

    sum_1 = report_1.get("summary", {})
    sum_2 = report_2.get("summary", {})

    status_1 = report_1.get("status")
    status_2 = report_2.get("status")
    both_passed = (status_1 == "PASS" and status_2 == "PASS")

    goal_err_1 = float(sum_1.get("goal_xy_error_m", math.inf))
    goal_err_2 = float(sum_2.get("goal_xy_error_m", math.inf))
    goal_err_diff = abs(goal_err_1 - goal_err_2)

    clearance_1 = float(sum_1.get("min_conservative_pedestrian_clearance_m", 0.0))
    clearance_2 = float(sum_2.get("min_conservative_pedestrian_clearance_m", 0.0))
    clearance_diff = abs(clearance_1 - clearance_2)

    root_z_min_1 = float(sum_1.get("min_root_z_m", 0.0))
    root_z_min_2 = float(sum_2.get("min_root_z_m", 0.0))
    root_z_diff = abs(root_z_min_1 - root_z_min_2)
    identity_hash_1 = _identity_contract_sha256(run_identity_1, run_1_id)
    identity_hash_2 = _identity_contract_sha256(run_identity_2, run_2_id)
    identity_contract_match = identity_hash_1 == identity_hash_2
    effective_input_match = (
        bool(effective_input_sha256_1)
        and effective_input_sha256_1 == effective_input_sha256_2
    )
    reactive_replan_both = (
        int(sum_1.get("reactive_replan_count", 0)) >= 1
        and int(sum_2.get("reactive_replan_count", 0)) >= 1
    )

    # Check key metrics consistency
    repeatability_passed = (
        both_passed
        and goal_err_diff <= tols["max_goal_xy_error_diff_m"]
        and clearance_1 >= 0.15
        and clearance_2 >= 0.15
        and int(sum_1.get("watchdog_events", 1)) == 0
        and int(sum_2.get("watchdog_events", 1)) == 0
        and float(sum_1.get("max_nonfoot_contact_n", 100.0)) <= 75.0
        and float(sum_2.get("max_nonfoot_contact_n", 100.0)) <= 75.0
        and int(sum_1.get("unique_trajectory_count", 0)) >= 2
        and int(sum_2.get("unique_trajectory_count", 0)) >= 2
        and reactive_replan_both
        and identity_contract_match
        and effective_input_match
    )

    comparison = {
        "schema_version": 1,
        "status": "PASS" if repeatability_passed else "FAIL",
        "run_1": {
            "run_id": run_1_id,
            "status": status_1,
            "goal_xy_error_m": goal_err_1,
            "max_nonfoot_contact_n": sum_1.get("max_nonfoot_contact_n"),
            "watchdog_events": sum_1.get("watchdog_events"),
            "min_root_z_m": root_z_min_1,
            "max_root_z_m": sum_1.get("max_root_z_m"),
            "min_conservative_pedestrian_clearance_m": clearance_1,
            "max_lidar_pedestrian_hits": sum_1.get("max_lidar_pedestrian_hits"),
            "max_depth_pedestrian_pixels": sum_1.get("max_depth_pedestrian_pixels"),
            "unique_trajectory_count": sum_1.get("unique_trajectory_count"),
            "reactive_replan_count": sum_1.get("reactive_replan_count"),
            "policy_rate_hz": sum_1.get("policy_rate_hz"),
            "sensor_rate_hz": sum_1.get("sensor_rate_hz"),
            "video_sha256": sum_1.get("video_sha256"),
            "video_duration_seconds": sum_1.get("video_duration_seconds"),
            "video_frame_count": sum_1.get("video_frame_count"),
            "overlay_sha256": sum_1.get("overlay_sha256"),
        },
        "run_2": {
            "run_id": run_2_id,
            "status": status_2,
            "goal_xy_error_m": goal_err_2,
            "max_nonfoot_contact_n": sum_2.get("max_nonfoot_contact_n"),
            "watchdog_events": sum_2.get("watchdog_events"),
            "min_root_z_m": root_z_min_2,
            "max_root_z_m": sum_2.get("max_root_z_m"),
            "min_conservative_pedestrian_clearance_m": clearance_2,
            "max_lidar_pedestrian_hits": sum_2.get("max_lidar_pedestrian_hits"),
            "max_depth_pedestrian_pixels": sum_2.get("max_depth_pedestrian_pixels"),
            "unique_trajectory_count": sum_2.get("unique_trajectory_count"),
            "reactive_replan_count": sum_2.get("reactive_replan_count"),
            "policy_rate_hz": sum_2.get("policy_rate_hz"),
            "sensor_rate_hz": sum_2.get("sensor_rate_hz"),
            "video_sha256": sum_2.get("video_sha256"),
            "video_duration_seconds": sum_2.get("video_duration_seconds"),
            "video_frame_count": sum_2.get("video_frame_count"),
            "overlay_sha256": sum_2.get("overlay_sha256"),
        },
        "differences": {
            "goal_xy_error_diff_m": goal_err_diff,
            "clearance_diff_m": clearance_diff,
            "min_root_z_diff_m": root_z_diff,
            "trajectory_count_diff": abs(int(sum_1.get("unique_trajectory_count", 0)) - int(sum_2.get("unique_trajectory_count", 0))),
        },
        "input_identity": {
            "effective_input_sha256_run_1": effective_input_sha256_1,
            "effective_input_sha256_run_2": effective_input_sha256_2,
            "effective_input_match": effective_input_match,
            "normalized_run_identity_sha256_run_1": identity_hash_1,
            "normalized_run_identity_sha256_run_2": identity_hash_2,
            "normalized_run_identity_match": identity_contract_match,
        },
        "repeatability_checks": {
            "both_runs_passed_acceptance": both_passed,
            "goal_error_repeatable": goal_err_diff <= tols["max_goal_xy_error_diff_m"],
            "zero_watchdog_both": int(sum_1.get("watchdog_events", 1)) == 0 and int(sum_2.get("watchdog_events", 1)) == 0,
            "safe_contacts_both": float(sum_1.get("max_nonfoot_contact_n", 100.0)) <= 75.0 and float(sum_2.get("max_nonfoot_contact_n", 100.0)) <= 75.0,
            "safe_clearance_both": clearance_1 >= 0.15 and clearance_2 >= 0.15,
            "multiple_trajectories_both": int(sum_1.get("unique_trajectory_count", 0)) >= 2 and int(sum_2.get("unique_trajectory_count", 0)) >= 2,
            "reactive_replan_both": reactive_replan_both,
            "same_effective_input": effective_input_match,
            "same_normalized_run_identity": identity_contract_match,
        },
        "claim_boundary": (
            "The project Foxy port of SCAN-Planner is integrated with the pinned Lite3 V12 policy "
            "in the declared Isaac Sim Office L0 crowd scenario, and two identical-input automated trials "
            "passed the frozen simulation gates. Final visual acceptance remains pending Dr Sun's review."
        ),
    }
    return comparison


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Compare two Office crowd runs for repeatability.")
    parser.add_argument("--report1", type=Path, required=True)
    parser.add_argument("--report2", type=Path, required=True)
    parser.add_argument("--run-identity1", type=Path, required=True)
    parser.add_argument("--run-identity2", type=Path, required=True)
    parser.add_argument("--run1-id", type=str, required=True)
    parser.add_argument("--run2-id", type=str, required=True)
    parser.add_argument("--effective-input1", type=Path, required=True)
    parser.add_argument("--effective-input2", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args(argv)
    report_1 = json.loads(args.report1.read_text(encoding="utf-8"))
    report_2 = json.loads(args.report2.read_text(encoding="utf-8"))
    identity_1 = json.loads(args.run_identity1.read_text(encoding="utf-8"))
    identity_2 = json.loads(args.run_identity2.read_text(encoding="utf-8"))

    comp = compare_office_crowd_runs(
        report_1=report_1,
        report_2=report_2,
        run_identity_1=identity_1,
        run_identity_2=identity_2,
        run_1_id=args.run1_id,
        run_2_id=args.run2_id,
        effective_input_sha256_1=_sha256(args.effective_input1),
        effective_input_sha256_2=_sha256(args.effective_input2),
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(comp, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": comp["status"], "output": str(args.output)}))
    return 0 if comp["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
