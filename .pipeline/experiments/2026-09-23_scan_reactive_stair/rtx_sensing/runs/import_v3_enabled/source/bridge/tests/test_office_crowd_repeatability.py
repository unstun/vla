"""Unit tests for Office L0 crowd repeatability evaluator."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from lite3_sim_bridge.office_crowd_repeatability import compare_office_crowd_runs, main


@pytest.fixture
def sample_reports() -> tuple[dict, dict]:
    r1 = {
        "status": "PASS",
        "summary": {
            "goal_xy_error_m": 0.125,
            "max_nonfoot_contact_n": 0.0,
            "watchdog_events": 0,
            "min_root_z_m": 0.286,
            "max_root_z_m": 0.350,
            "min_conservative_pedestrian_clearance_m": 0.205,
            "max_lidar_pedestrian_hits": 385,
            "max_depth_pedestrian_pixels": 844,
            "unique_trajectory_count": 6,
            "reactive_replan_count": 2,
            "policy_rate_hz": 50.0,
            "sensor_rate_hz": 10.0,
            "video_sha256": "abc1",
            "overlay_sha256": "def1",
        },
    }
    r2 = {
        "status": "PASS",
        "summary": {
            "goal_xy_error_m": 0.128,
            "max_nonfoot_contact_n": 0.0,
            "watchdog_events": 0,
            "min_root_z_m": 0.285,
            "max_root_z_m": 0.351,
            "min_conservative_pedestrian_clearance_m": 0.201,
            "max_lidar_pedestrian_hits": 380,
            "max_depth_pedestrian_pixels": 840,
            "unique_trajectory_count": 6,
            "reactive_replan_count": 1,
            "policy_rate_hz": 50.0,
            "sensor_rate_hz": 10.0,
            "video_sha256": "abc2",
            "overlay_sha256": "def2",
        },
    }
    return r1, r2


def test_compare_office_crowd_runs_pass(sample_reports: tuple[dict, dict]) -> None:
    r1, r2 = sample_reports
    res = compare_office_crowd_runs(
        report_1=r1,
        report_2=r2,
        run_identity_1={"run_id": "dryrun11"},
        run_identity_2={"run_id": "dryrun12"},
        run_1_id="office_crowd_dryrun11",
        run_2_id="office_crowd_dryrun12",
        effective_input_sha256_1="same",
        effective_input_sha256_2="same",
    )
    assert res["status"] == "PASS"
    assert res["repeatability_checks"]["both_runs_passed_acceptance"] is True
    assert res["repeatability_checks"]["goal_error_repeatable"] is True
    assert res["repeatability_checks"]["same_effective_input"] is True
    assert res["repeatability_checks"]["same_normalized_run_identity"] is True
