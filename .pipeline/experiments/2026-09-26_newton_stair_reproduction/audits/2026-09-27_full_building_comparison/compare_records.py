"""Read original evidence; write only this diagnostic directory."""
from pathlib import Path
import collections
import difflib
import hashlib
import importlib.util
import json
import re
import xml.etree.ElementTree as ET

import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = HERE.parents[4]
NAV = ROOT.parent / "machine-dog-nav"
OLD = NAV / ".pipeline/experiments/2026-09-11_pct_scan_upstream_baseline"
OLD_RUN = OLD / "full02_evidence/runs/native_full02"
RUN = BASE / "runs/v7_building_route01"
OLD_WS = NAV / "integration/pct_scan_upstream_ws"
NEW_WS = BASE / "runtime/scan46_cruise_v7"


def read(path):
    return json.loads(path.read_text())


def rows(path):
    return [json.loads(line) for line in path.open()]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def flat_parameters(path):
    source = yaml.safe_load(path.read_text())
    params = next(iter(source.values()))["ros__parameters"]
    result = {}
    def visit(prefix, value):
        if isinstance(value, dict):
            for key, item in value.items():
                visit(f"{prefix}.{key}" if prefix else key, item)
        else:
            result[prefix] = value
    visit("", params)
    return result


def main():
    manifest = read(OLD_WS / "UPSTREAM_MANIFEST.json")
    old_bad = [f["local_path"] for f in manifest["files"]
               if sha(NAV / f["local_path"]) != f["local_sha256"]]
    executed = read(OLD_RUN / "executed_source_manifest.json")["files"]
    old_executed = [f for f in executed if f["path"].startswith("foxy_ws/src/")
                    and (OLD_WS / f["path"].removeprefix("foxy_ws/")).is_file()]
    old_executed_bad = [f["path"] for f in old_executed
                        if sha(OLD_WS / f["path"].removeprefix("foxy_ws/")) != f["sha256"]]
    frozen = read(BASE / "versions/v7/manifest.json")
    current_bad = [path for path, digest in frozen["source_files"].items()
                   if sha(ROOT / path) != digest]
    snapshot_bad = [path for path, digest in frozen["source_files"].items()
                    if sha(BASE / "versions/v7/source" / path) != digest]
    assert not (old_bad or old_executed_bad or current_bad or snapshot_bad)
    source_diff = {}
    old_files = {str(p.relative_to(OLD_WS / "src")): p for p in (OLD_WS / "src").rglob("*") if p.is_file()}
    new_files = {str(p.relative_to(NEW_WS / "src")): p for p in (NEW_WS / "src").rglob("*") if p.is_file()}
    for name in sorted(old_files.keys() & new_files.keys()):
        if sha(old_files[name]) == sha(new_files[name]):
            continue
        old, new = old_files[name].read_text().splitlines(), new_files[name].read_text().splitlines()
        delta = collections.Counter(line[0] for line in difflib.ndiff(old, new))
        source_diff[name] = {"old_lines": len(old), "new_lines": len(new),
                             "added": delta["+"], "removed": delta["-"]}
    source_check = {"historical_manifest_files": len(manifest["files"]),
                    "historical_executed_source_matches": len(old_executed),
                    "current_frozen_source_matches": len(frozen["source_files"]),
                    "current_snapshot_matches": len(frozen["source_files"]),
                    "changed_shared_files": source_diff,
                    "current_only_files": sorted(new_files.keys() - old_files.keys()),
                    "all_selected_identity_checks_pass": True}

    old_params = flat_parameters(OLD_RUN / "planner_parameters.yaml")
    current_params = flat_parameters(RUN / "planner.yaml")
    params = {k: {"old": old_params.get(k), "current": current_params.get(k)}
              for k in sorted(old_params.keys() | current_params.keys())
              if old_params.get(k) != current_params.get(k)}
    old_ctrl = flat_parameters(OLD / "config/controller.yaml")
    new_ctrl = flat_parameters(BASE / "config_archived/controller.yaml")
    controller = {k: {"old": old_ctrl.get(k), "current": new_ctrl.get(k)}
                  for k in sorted(old_ctrl.keys() | new_ctrl.keys())
                  if old_ctrl.get(k) != new_ctrl.get(k)}
    old_scope = read(OLD_RUN / "executed_scope.json")
    assert sha(OLD / "config/controller.yaml") == old_scope["config_sha256"]["controller.yaml"]
    metric = rows(OLD_RUN / "metrics.jsonl")
    current_metric = rows(RUN / "telemetry.jsonl")
    old_xy = np.asarray([r["base_xyz"][:2] for r in metric])
    new_xy = np.asarray([r["body_sensor"]["position"][:2] for r in current_metric])
    spec = importlib.util.spec_from_file_location("versioned_review", BASE / "versions/v7/review_speed_runs.py")
    reviewer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reviewer)
    old_curves = []
    for record in rows(OLD_RUN / "scan_trace.jsonl"):
        if record["kind"] != "bspline":
            continue
        message = dict(record, pos_pts=[dict(zip("xyz", point)) for point in record["control_points_xyz"]])
        curve = reviewer.curve_review(message)
        if curve:
            old_curves.append(curve)
    # Applying the current floor measurement to old curves is descriptive only;
    # it was not an old acceptance criterion.
    observations = rows(RUN / "artifacts/reactive_observations.jsonl")
    new_curves = [c for r in observations if r["event"] == "bspline"
                  and (c := reviewer.curve_review(r["data"])) is not None]
    last_moving = max(r["clock_ns"] for r in observations if r["event"] == "bspline" and r["data"]["traj_id"] == 4)
    admissions = [{"sim_s": r["clock_ns"] / 1e9, **r["data"]} for r in observations if r["event"] == "scan_admission"]
    stop_admissions = [r for r in admissions if r["status"] in ("rejected", "stopped")]
    log = (RUN / "scan.log").read_text()
    verdicts = collections.Counter(re.findall(r"reactive_collision_blocked verdict=(\d+)", log))
    speed_rejects = [line for line in log.splitlines() if "minimum_cruise_check" in line and "passed=0" in line]
    backend = read(RUN / "result.json")["last_backend"]

    robot = {}
    for label, path in {"old": NAV / old_scope["frozen_assets"]["original_urdf"]["path"],
                        "current": BASE / "inputs/sensor_rig/lite3_pro_sensor_rig_real_with_interface.urdf"}.items():
        xml = ET.parse(path).getroot()
        masses = {e.get("name"): float(e.find("inertial/mass").get("value")) for e in xml.findall("link")
                  if e.find("inertial/mass") is not None}
        robot[label] = {"path": str(path), "sha256": sha(path), "link_count": len(xml.findall("link")),
                        "urdf_mass_sum_kg": sum(masses.values()), "link_masses": masses}
    old_sensor = json.loads(next((OLD_RUN / "sensor_metrics.jsonl").open()))
    new_sensor = json.loads(next((RUN / "sensor.jsonl").open()))
    evidence = {"source_identity": source_check, "planner_parameter_differences": params,
                "controller_parameter_differences": controller, "robot": robot,
                "measured_motion": {"historical_xy_travel_m": float(np.linalg.norm(np.diff(old_xy, axis=0), axis=1).sum()),
                    "historical_final_sim_s": metric[-1]["sim_time_s"],
                    "historical_goal_error_m": metric[-1]["goal_error_xy_m"],
                    "current_xy_travel_m": float(np.linalg.norm(np.diff(new_xy, axis=0), axis=1).sum()),
                    "current_net_xy_m": float(np.linalg.norm(new_xy[-1] - new_xy[0])),
                    "current_final_sim_s": current_metric[-1]["physics_time_s"]},
                "curves": {"historical_moving_count": len(old_curves), "historical_first": old_curves[0],
                           "current": new_curves, "old_curve_speed_scoring_is_retrospective": True},
                "sensor": {"old_first_ray_count": old_sensor["ray_count"], "old_first_return_count": old_sensor["planner_point_count"],
                           "current_first_ray_count": new_sensor["sensor"]["scan_window"]["point_count"],
                           "current_first_return_count": new_sensor["sensor"]["point_count"],
                           "not_a_same_pose_sensor_ablation": True},
                "failure_chain": {"replan_exhaustion_marker_count": log.count("Replan failed 1000 times"),
                    "logged_throttled_blocking_verdict_counts": dict(verdicts),
                    "minimum_cruise_rejection_count": len(speed_rejects),
                    "last_moving_curve_publication_s": last_moving / 1e9,
                    "admissions": admissions,
                    "first_stop_or_rejection_admission_s": min(r["sim_s"] for r in stop_admissions),
                    "last_backend_gate": backend["gate"]["closed_reason"],
                    "last_backend_owner": backend["gate"]["owner"],
                    "last_backend_terminal_results": backend["terminal_results"]},
                "native_replay01": read(HERE / "replay01.json"), "native_replay02": read(HERE / "replay02.json")}
    assert evidence["native_replay01"] == evidence["native_replay02"]
    assert (HERE / "replay01_queries.csv").read_bytes() == (HERE / "replay02_queries.csv").read_bytes()
    evidence["native_repeat_exact_result_and_query_parity"] = True
    paths = [OLD_RUN / name for name in ("metrics.jsonl", "scan_trace.jsonl", "executed_source_manifest.json", "planner_parameters.yaml", "executed_scope.json")]
    paths += [RUN / name for name in ("telemetry.jsonl", "scan.log", "planner.yaml", "result.json", "artifacts/reactive_observations.jsonl", "sensor_manifest.json", "pct_support.log")]
    paths += [BASE / "versions/v7/manifest.json", OLD_WS / "UPSTREAM_MANIFEST.json"]
    evidence["primary_evidence_sha256"] = {str(p): sha(p) for p in paths}
    (HERE / "comparison.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps({"identity": source_check["all_selected_identity_checks_pass"],
                      "historical_source_matches": len(old_executed), "current_source_matches": len(frozen["source_files"]),
                      "motion": evidence["measured_motion"], "curves": evidence["curves"],
                      "controller_parameter_differences": controller,
                      "native_repeat_parity": True}, indent=2))


if __name__ == "__main__":
    main()
