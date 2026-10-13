"""Record observed old-curve expiry around the largest completed cold rounds.

This is observer evidence, not reconstruction of the controller's frozen clock.
Run on gpu5070ti, where the original observation archives remain.
"""
from pathlib import Path
import hashlib
import json
import re
import sys

import numpy as np
from scipy.interpolate import BSpline

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[2]
sys.path.insert(0, str(BASE / "versions/v51"))
import artifacts


def process(run_name):
    run = BASE / "runs" / run_name
    tail_path = HERE / (run_name + "_tail_evidence.json")
    evidence = json.loads(tail_path.read_text())
    with artifacts.open_text(run, "artifacts/reactive_observations.jsonl") as stream:
        raw = stream.read()
    events = [json.loads(line) for line in raw.splitlines()
              if '"event": "bspline"' in line]
    events = [event for event in events if not event["data"].get("emergency_stop")]
    records = []
    for tail in evidence["tails"]:
        round_ = tail["round"]
        previous = [event for event in events
                    if event["wall_monotonic_ns"] * 1e-9 < round_["start_wall_s"]]
        if not previous:
            continue
        event = max(previous, key=lambda item: item["wall_monotonic_ns"])
        message = event["data"]
        knots, degree = message["knots"], message["order"]
        origin = message["start_time"]["sec"] + message["start_time"]["nanosec"] * 1e-9
        duration = knots[-degree - 1] - knots[degree]
        points = np.array([[point[axis] for axis in ("x", "y", "z")]
                           for point in message["pos_pts"]])
        endpoint = BSpline(knots, points, degree)(knots[-degree - 1]).tolist()
        epochs = []
        for line in tail["evidence"]:
            match = re.search(r"V59_TRAJECTORY_EPOCH sampled=(\d+) origin_s=([\d.]+) publication_s=([\d.]+)", line["text"])
            if match:
                epochs.append(dict(sampled=bool(int(match[1])), origin_s=float(match[2]),
                                   publication_s=float(match[3]), source_line=line["line"]))
        records.append(dict(round_sim_s=round_["ros_s"], solve_ms=round_["wall_s"] * 1000,
                            prior_observed_curve=dict(traj_id=message["traj_id"], origin_s=origin,
                                duration_s=duration, nominal_expiry_s=origin + duration,
                                endpoint_xyz=endpoint, receipt_wall_ns=event["wall_monotonic_ns"]),
                            recovery_epochs=epochs))
    result = dict(run=run_name, tails=records, source_sha256={
        "reactive_observations.jsonl": hashlib.sha256(raw.encode()).hexdigest(),
        "tail_evidence": artifacts.digest(tail_path),
        "script": artifacts.digest(Path(__file__))},
        scope="Last non-emergency curve observed before round start. Nominal expiry is origin plus duration; internal controller pauses are not reconstructed.")
    output = HERE / (run_name + "_curve_reserve.json")
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    for name in ("v58_realtime_trial02", "v59_realtime_trial01"):
        process(name)
