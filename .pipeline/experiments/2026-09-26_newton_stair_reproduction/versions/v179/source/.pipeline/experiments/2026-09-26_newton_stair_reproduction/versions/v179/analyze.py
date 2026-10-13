"""Describe measured stop drift; never infer a navigation or training pass."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from protocol import LATE_START_SECONDS, DRIFT_FLAG_METERS


def analyze(run):
    request = json.loads((run / "probe_request.json").read_text())
    result = json.loads((run / "result.json").read_text())
    rows = [json.loads(x) for x in (run / "telemetry.jsonl").read_text().splitlines()] if (run / "telemetry.jsonl").exists() else []
    summary = dict(run=run.name, terrain=request["terrain"], attempt=request["attempt"],
                   execution=result, stops=[], walks=[])
    for phase in ("walk1", "stop1", "walk2", "stop2"):
        chosen = [r for r in rows if r["phase"] == phase]
        if not chosen:
            continue
        times = np.array([r["physics_time_s"] for r in chosen])
        xyz = np.array([r["joint_q"][:3] for r in chosen])
        start = np.array(chosen[0]["command_start_base_xyz"])
        elapsed = times - chosen[0]["command_applied_start_s"]
        speed = np.linalg.norm(np.array([r["joint_qd"][:2] for r in chosen]), axis=1)
        displacement = np.linalg.norm(xyz[:, :2] - start[:2], axis=1)
        record = dict(phase=phase, samples=len(chosen), seconds=float(elapsed[-1]),
                      start_s=chosen[0]["command_applied_start_s"], start_xyz=start.tolist(),
                      end_xyz=xyz[-1].tolist(), net_xy_m=float(displacement[-1]),
                      max_xy_excursion_m=float(displacement.max()), max_speed_mps=float(speed.max()),
                      minimum_up_z=min(r["base_up_z"] for r in chosen))
        if phase.startswith("walk"):
            record["command_mps"] = chosen[0]["command"][0]
            summary["walks"].append(record)
            continue
        record["complete_10s_window"] = len(chosen) == 500
        record["pure_policy_zero_verified"] = all(r["effective_command"] == [0., 0., 0.]
            and r["stance_mode"] == "POLICY_ONLY" and r["policy_owns_joints"] for r in chosen)
        if not record["pure_policy_zero_verified"]:
            raise ValueError("Contaminated stop window: " + str(run))
        braking = np.flatnonzero(elapsed <= LATE_START_SECONDS)
        record["first_2s_max_excursion_m"] = float(displacement[braking].max()) if len(braking) else None
        late = np.flatnonzero(elapsed >= LATE_START_SECONDS)
        if len(late):
            points = xyz[late, :2]
            record.update(late_start_s=float(times[late[0]]),
                late_net_xy_m=float(np.linalg.norm(points[-1] - points[0])),
                late_max_excursion_m=float(np.linalg.norm(points - points[0], axis=1).max()),
                late_xy_path_m=float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum()),
                late_speed_median_mps=float(np.median(speed[late])),
                late_speed_p95_mps=float(np.quantile(speed[late], .95)))
            record["late_drift_over_5cm_flag"] = record["late_max_excursion_m"] > DRIFT_FLAG_METERS
            feet = np.array([r["foot_positions_world"] for r in chosen])[late]
            forces = np.array([r["foot_forces_n"] for r in chosen])[late]
            dt = np.diff(times[late])
            if len(dt):
                foot_speed = np.linalg.norm(np.diff(feet[:, :, :2], axis=0), axis=2) / dt[:, None]
                contact = (forces[:-1] > 5.) & (forces[1:] > 5.)
                values = foot_speed[contact]
                record.update(persistent_contact_foot_speed_median_mps=float(np.median(values)) if len(values) else None,
                    persistent_contact_foot_speed_p95_mps=float(np.quantile(values, .95)) if len(values) else None,
                    sampled_unloaded_foot_fraction=float(np.mean(forces <= 5.)),
                    contact_measurement_note="50Hz finite differences, both endpoints >5N; not continuous slip/contact classification")
        summary["stops"].append(record)
    summary["source_hashes"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (run / "probe_request.json", run / "result.json", run / "telemetry.jsonl", run / "recorded_frames.json") if p.exists()}
    return summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--runs", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    results = [analyze(run) for run in sorted(args.runs.iterdir()) if (run / "result.json").exists()]
    payload = dict(claim="Current policy in pinned Newton only; no original-training causal proof", runs=results)
    (args.output / "summary.json").write_text(json.dumps(payload, indent=2) + "\n")
    fields = ["run", "terrain", "attempt", "phase", "complete_10s_window", "net_xy_m", "first_2s_max_excursion_m",
              "late_net_xy_m", "late_max_excursion_m", "late_speed_median_mps", "late_speed_p95_mps", "late_drift_over_5cm_flag"]
    with (args.output / "stops.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fields, extrasaction="ignore")
        writer.writeheader()
        for run in results:
            for stop in run["stops"]:
                writer.writerow(dict(run=run["run"], terrain=run["terrain"], attempt=run["attempt"], **stop))
    print(json.dumps(dict(runs=len(results), stops=sum(len(r["stops"]) for r in results))))


if __name__ == "__main__":
    main()
