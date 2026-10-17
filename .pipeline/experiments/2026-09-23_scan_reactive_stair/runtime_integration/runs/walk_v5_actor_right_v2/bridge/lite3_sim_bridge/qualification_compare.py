"""Compare the legacy and sensor-rig V12 qualification runs without attribution."""

import argparse
import hashlib
import json
import math
from pathlib import Path


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _roll_pitch(quaternion_wxyz):
    w, x, y, z = quaternion_wxyz
    roll = math.atan2(2.0 * (w * x + y * z), 1.0 - 2.0 * (x * x + y * y))
    pitch_term = max(-1.0, min(1.0, 2.0 * (w * y - z * x)))
    return math.atan2(math.sin(roll), math.cos(roll)), math.asin(pitch_term)


def summarize_metrics(records):
    if not records:
        raise ValueError("qualification metrics are empty")
    segment_order = []
    segment_commands = {}
    for row in records:
        segment = row["schedule_segment"]
        if not segment_order or segment_order[-1] != segment:
            segment_order.append(segment)
        segment_commands.setdefault(segment, set()).add(tuple(row["applied_command"]))
    responses = {}
    for name, field, index in (
        ("forward", "root_lin_vel_b", 0),
        ("lateral", "root_lin_vel_b", 1),
        ("yaw", "root_ang_vel_b", 2),
    ):
        values = [
            row[field][index]
            for row in records
            if row["schedule_segment"] == name
            and row["schedule_segment_elapsed_seconds"] >= 0.75
        ]
        responses[name] = sum(values) / len(values) if values else None
    roll_pitch = [_roll_pitch(row["root_quat_wxyz"]) for row in records]
    actions = [value for row in records for value in row["actions"]]
    joints = [value for row in records for value in row["joint_position"]]
    return {
        "record_count": len(records),
        "sim_duration_seconds": records[-1]["sim_time_seconds"]
        - records[0]["sim_time_seconds"],
        "segment_order": segment_order,
        "segment_commands": {
            name: [list(command) for command in sorted(commands)]
            for name, commands in segment_commands.items()
        },
        "response_means": responses,
        "supported_contact_fraction": sum(
            row["contact_count"] >= 2 for row in records
        )
        / len(records),
        "minimum_root_height_m": min(row["root_pos_w"][2] for row in records),
        "maximum_abs_roll_rad": max(abs(value[0]) for value in roll_pitch),
        "maximum_abs_pitch_rad": max(abs(value[1]) for value in roll_pitch),
        "maximum_nonfoot_contact_n": max(
            row["nonfoot_contact_max_n"] for row in records
        ),
        "maximum_command_observation_error": max(
            row["command_observation_max_error"] for row in records
        ),
        "action_rms": math.sqrt(sum(value * value for value in actions) / len(actions)),
        "maximum_abs_action": max(abs(value) for value in actions),
        "minimum_joint_position_rad": min(joints),
        "maximum_joint_position_rad": max(joints),
        "finite": all(row["finite"] for row in records),
        "terminated": any(row["done"] for row in records),
        "watchdog_zero_observed": any(
            row["command_reason"] in ("disconnected", "watchdog_timeout")
            and row["applied_command"] == [0.0, 0.0, 0.0]
            for row in records
        ),
    }


def compare_asset_qualifications(
    legacy_dir: Path,
    sensor_rig_dir: Path,
    legacy_asset: Path,
):
    legacy_identity = _read_json(legacy_dir / "run_identity.json")
    sensor_rig_identity = _read_json(sensor_rig_dir / "run_identity.json")
    legacy_report = _read_json(legacy_dir / "qualification_report.json")
    sensor_rig_report = _read_json(sensor_rig_dir / "qualification_report.json")
    runtime_composition = _read_json(sensor_rig_dir / "runtime_composition.json")
    legacy_summary = summarize_metrics(_read_jsonl(legacy_dir / "metrics.jsonl"))
    sensor_rig_summary = summarize_metrics(
        _read_jsonl(sensor_rig_dir / "metrics.jsonl")
    )
    invariant_fields = (
        "source_commit",
        "checkpoint_sha256",
        "task",
        "seed",
        "command_limits",
        "watchdog_seconds",
        "policy_observation_contract",
        "inference_policy",
    )
    invariant_checks = {
        field: legacy_identity.get(field) == sensor_rig_identity.get(field)
        for field in invariant_fields
    }
    legacy_asset_sha256 = _sha256(legacy_asset)
    checks = {
        "legacy_qualification_passed": legacy_report.get("status") == "PASS",
        "sensor_rig_qualification_passed": sensor_rig_report.get("status")
        == "PASS",
        "identity_invariants_match": all(invariant_checks.values()),
        "schedule_order_matches": legacy_summary["segment_order"]
        == sensor_rig_summary["segment_order"],
        "schedule_commands_match": legacy_summary["segment_commands"]
        == sensor_rig_summary["segment_commands"],
        "legacy_asset_matches_v12_registry": legacy_asset_sha256
        == runtime_composition["v12_task_contract"]["original_robot_asset_sha256"],
        "sensor_rig_runtime_has_no_missing_links": not runtime_composition[
            "missing_required_sensor_rig_links"
        ],
        "sensor_rig_runtime_mass_check_passed": runtime_composition[
            "silent_default_mass_check"
        ]["status"]
        == "pass",
    }
    deltas = {}
    for key in (
        "supported_contact_fraction",
        "minimum_root_height_m",
        "maximum_abs_roll_rad",
        "maximum_abs_pitch_rad",
        "maximum_nonfoot_contact_n",
        "action_rms",
        "maximum_abs_action",
    ):
        deltas[key] = sensor_rig_summary[key] - legacy_summary[key]
    deltas["response_means"] = {
        name: sensor_rig_summary["response_means"][name]
        - legacy_summary["response_means"][name]
        for name in ("forward", "lateral", "yaw")
    }
    return {
        "schema_version": 1,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "claim": "same-input V12 legacy-asset versus sensor-rig qualification",
        "checks": checks,
        "identity_invariant_checks": invariant_checks,
        "asset_identity": {
            "legacy_asset_path": str(legacy_asset.resolve()),
            "legacy_asset_sha256": legacy_asset_sha256,
            "canonical_sensor_rig_sha256": sensor_rig_identity["robot_asset"][
                "canonical_asset_sha256"
            ],
            "isaac_sensor_rig_sha256": sensor_rig_identity["robot_asset"][
                "asset_sha256"
            ],
        },
        "legacy_summary": legacy_summary,
        "sensor_rig_summary": sensor_rig_summary,
        "sensor_rig_minus_legacy": deltas,
        "attribution_boundary": (
            "The report records one fixed-seed composition comparison. It does "
            "not attribute a numerical delta to any individual payload mass, "
            "collision primitive, sensor housing, contact event, or policy mode."
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-dir", type=Path, required=True)
    parser.add_argument("--sensor-rig-dir", type=Path, required=True)
    parser.add_argument("--legacy-asset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    report = compare_asset_qualifications(
        args.legacy_dir.resolve(),
        args.sensor_rig_dir.resolve(),
        args.legacy_asset.resolve(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": report["status"], "output": str(args.output)}))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
