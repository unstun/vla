"""Read-only evidence review; no fabricated terminal results or robot steps."""
from pathlib import Path
import hashlib
import json
import math

import numpy as np
from scipy.interpolate import BSpline

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]


def read(path):
    return json.loads(path.read_text())


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def curve_review(message):
    controls = np.asarray([[p[k] for k in ("x", "y", "z")] for p in message["pos_pts"]])
    if np.max(np.linalg.norm(controls - controls[0], axis=1)) < 1e-6:
        return None
    knots, degree = np.asarray(message["knots"]), message["order"]
    curve = BSpline(knots, controls, degree)
    duration = knots[len(controls)] - knots[degree]
    count = max(1, math.ceil(duration / .01))
    times = knots[degree] + np.linspace(0., duration, count + 1)
    positions, velocities = curve(times), curve.derivative()(times)
    speed = np.linalg.norm(velocities[:, :2], axis=1)
    arc = np.r_[0., np.cumsum(np.linalg.norm(np.diff(positions[:, :2], axis=0), axis=1))]
    # Independent SciPy derivative/arc calculation of the documented boundary envelope.
    def envelope(boundary_speed):
        difference = max(0., .6 - boundary_speed)
        ramp_time = difference / .5 + .5 / 4. if difference >= .5**2 / 4. else 2. * math.sqrt(difference / 4.)
        return .5 * (boundary_speed + .6) * ramp_time
    entry, exit_ = envelope(speed[0]), envelope(speed[-1])
    cruise = (arc >= entry) & (arc[-1] - arc >= exit_)
    minimum = float(np.min(speed[cruise])) if np.any(cruise) else None
    return {"trajectory_id": message["traj_id"], "duration_s": float(duration),
            "horizontal_length_m": float(arc[-1]), "maximum_speed_mps": float(max(speed)),
            "cruise_samples": int(sum(cruise)), "minimum_cruise_mps": minimum,
            "cruise_requirement_met": minimum is not None and minimum + 1e-9 >= .6,
            "classification": "cruise" if minimum is not None else "boundary_only_no_cruise"}


def main():
    run = BASE / "runs/v7_building_route01"
    telemetry = rows(run / "telemetry.jsonl")
    applied = rows(run / "applied_sent.jsonl")
    by_sequence = {r["state_sequence"]: r for r in telemetry}
    ack_errors = []
    for item in applied:
        state, ack = item["snapshot"], item["ack"]
        sequence = state["state_epoch"]["state_sequence"]
        digest = hashlib.sha256(json.dumps(state, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        actual = [state["applied_command"][k] for k in ("vx", "vy", "wz")]
        if (digest != ack["sha256"] or sequence != ack["sequence"] or
                sequence != ack["original_reader_sequence"] or actual != by_sequence[sequence]["command"]):
            ack_errors.append(sequence)
    sensors = read(run / "sensor_manifest.json")
    sensor_checks = all(sha(run / r["file"]) == r["sha256"] for r in sensors)
    startup_steps = len(np.load(run / "factory_full_rate.npz")["records"])
    expected_time = np.float32(0.)
    time_by_steps = {}
    for step in range(1, telemetry[-1]["physics_steps"] + 1):
        expected_time = np.float32(expected_time + np.float32(.001))
        if step > startup_steps and (step - startup_steps) % 20 == 0:
            time_by_steps[step] = float(expected_time)
    continuous = all(r["physics_steps"] == startup_steps + 20 * (i + 1) and
                     r["physics_time_s"] == time_by_steps[r["physics_steps"]]
                     for i, r in enumerate(telemetry))
    native_curves = []
    for observation in rows(run / "artifacts/reactive_observations.jsonl"):
        if observation["event"] != "bspline":
            continue
        review = curve_review(observation["data"])
        if review:
            review["observed_sim_s"] = observation["clock_ns"] / 1e9
            native_curves.append(review)
    points = [r["body_sensor"]["position"] for r in telemetry]
    moving = [r for r in telemetry if math.hypot(*r["command"][:2]) > .01]
    goal = read(run / "inputs/stair_scenario.json")["goal_ground_xyz_m"][:2]
    tail_hold = []
    for row in reversed(telemetry):
        if row["stance_mode"] != "FIXED_STAND":
            break
        tail_hold.append(row)
    result = read(run / "result.json")
    summary = {
        "integration_version": "v7", "run_id": run.name,
        "physics_duration_s": telemetry[-1]["physics_time_s"],
        "physics_steps": telemetry[-1]["physics_steps"], "telemetry_rows": len(telemetry),
        "continuous_clock_and_steps": continuous,
        "positive_acks": len(applied), "ack_errors": ack_errors,
        "sensor_files_intact": sensor_checks, "copyback_verified": read(run / "state_copyback.json")["verified"],
        "net_xy_m": math.dist(points[0][:2], points[-1][:2]),
        "accumulated_xyz_m": sum(math.dist(a, b) for a, b in zip(points, points[1:])),
        "remaining_goal_xy_m": math.dist(points[-1][:2], goal),
        "command_peak_xy_mps": max(math.hypot(*r["command"][:2]) for r in telemetry),
        "moving_command_mean_xy_mps": sum(math.hypot(*r["command"][:2]) for r in moving) / len(moving),
        "body_peak_xy_mps": max(math.hypot(*r["body_sensor"]["linear_world"][:2]) for r in telemetry),
        "minimum_base_up_z": min(r["base_up_z"] for r in telemetry),
        "final_stance_mode": telemetry[-1]["stance_mode"],
        "final_pd_dwell_s": tail_hold[0]["physics_time_s"] - tail_hold[-1]["physics_time_s"] if tail_hold else 0.,
        "backend_terminal_results": result["last_backend"]["terminal_results"],
        "driver_terminal_file_present": (run / "artifacts/stair_driver_result.json").exists(),
        "published_moving_curves": native_curves,
        "cruise_observed": any(r["cruise_samples"] > 0 for r in native_curves),
        "full_navigation_passed": False,
        "claim": "Bounded physical observation only: no arrival, no final PD hold, no sustained cruise. Short-curve exceptions are not a 0.6 m/s pass.",
        "source_sha256": {name: sha(run / name) for name in (
            "telemetry.jsonl", "result.json", "process.json", "planner.yaml", "video_states.json",
            "applied_sent.jsonl", "artifacts/reactive_observations.jsonl")},
    }
    (run / "bounded_speed_review.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
