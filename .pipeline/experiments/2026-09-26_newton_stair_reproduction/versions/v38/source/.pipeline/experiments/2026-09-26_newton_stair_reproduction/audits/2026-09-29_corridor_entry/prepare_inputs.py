"""Freeze the corridor-entry stand of v32's and v33's trials for replay.

Adapted from audits/2026-09-28_v30_stop_classes/prepare_inputs.py. What differs: the source runs, and each state is
chosen by the executing curve and a sim time instead of a stop line.

Each state is frozen at the recorded body pose at which the live REPLAN_TRAJ call of the first stand cycle began.
The FSM leaves EXEC_TRAJ once t_cur > duration - 0.01 on its 10 ms timer, so that moment can fall on either side of the
executing curve's end; it is identified from logged values:
- v33: traj 12 ran 30.885-33.151 s. The cycle's first line printing the sim time shows now=33.153 (scan.log line 1084)
  and the printed start velocity is 0 (clamped), so the moment is the first pose at or after the curve's end
  (33.1534 s). The chosen pose must round to 33.153.
- v32: traj 12 ran 38.091-39.920 s. The printed start velocity (scan.log line 2128: 1.3e-08 -8.88e-08 9.47e-09) is
  the curve's velocity 0.27 ms before its end, and the cycle's cloud_age (0.1099 s) gives now = 39.9197 s. So the
  moment is the last pose at or before the curve's end (39.919689 s). The curve's velocity there, printed as SCAN
  prints it, must equal the logged start velocity. (Independent review round 1, B2: the first version froze v32 at
  the first pose after the end, 5 ms late; that state is kept in attempt03_v32_freeze_late/.)
The replan start that SCAN used is the executing curve at that moment (planFromCurrentTraj clamps t_cur to the
duration).

Frozen: the original published scans up to the clock with their paired sensor and body states, the last body pose, the
executing spline (its traj_id checked), the original route and the last committed window from scan.log.
Usage: python3 prepare_inputs.py <experiment root> <audit dir> [state ...]   (inside the pinned image: needs rclpy
and msgs; without state names it prepares every state)
"""
from pathlib import Path
import bisect, copy, hashlib, json, re, sys
import numpy as np
from rclpy.serialization import serialize_message
from rosidl_runtime_py.set_message import set_message_fields
from scan_planner_msgs.msg import P2BRoute, Bspline

STATES = {
    "v33_stand": {"run": "v33_historical_full01", "traj_id": 12, "moment": "first_pose_at_or_after_end",
                  "live_now_s": 33.153},
    "v32_stand": {"run": "v32_historical_full01", "traj_id": 12, "moment": "last_pose_at_or_before_end",
                  "live_start_velocity": "1.3e-08 -8.88e-08 9.47e-09"},
}
base, audit = Path(sys.argv[1]), Path(sys.argv[2])
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
navigation = base / "audits/2026-09-27_pct_precision/ground_precise.f32"
surface = base / "audits/2026-09-27_dense_static_sampling/raw_ground.f32"


def pose(path, p, q, v=(0, 0, 0), w=(0, 0, 0)):
    path.write_text(" ".join(format(float(x), ".17g") for x in [*p, q[1], q[2], q[3], q[0], *v, *w]) + "\n")


summary = {}
selected = sys.argv[3:] or list(STATES)
for state, spec in STATES.items():
    if state not in selected:
        continue
    run = base / "runs" / spec["run"]
    assert f"payload_sha256={sha(navigation)}" in (run / "pct_support.log").read_text()
    assert f"payload_sha256={sha(surface)}" in (run / "pct_surface_ground.log").read_text()
    obs = [json.loads(l) for l in (run / "artifacts/reactive_observations.jsonl").read_text().splitlines()]
    route = next(x for x in obs if x["event"] == "pct_route")
    bodies = sorted((x for x in obs if x["event"] == "body_pose_observer" and x["clock_ns"] is not None),
                    key=lambda x: x["clock_ns"])
    body_ns = [x["clock_ns"] for x in bodies]
    spline = next(x for x in obs if x["event"] == "bspline" and x["data"]["traj_id"] == spec["traj_id"])
    start_s = spline["data"]["start_time"]["sec"] + spline["data"]["start_time"]["nanosec"] * 1e-9
    k = spline["data"]["knots"]
    end_s = start_s + (len(spline["data"]["pos_pts"]) - 3) * (k[4] - k[3])
    if spec["moment"] == "first_pose_at_or_after_end":
        body = bodies[bisect.bisect_left(body_ns, round(end_s * 1e9))]
        assert end_s <= body["clock_ns"] * 1e-9 < end_s + 0.01, (state, end_s, body["clock_ns"])
        assert round(body["clock_ns"] * 1e-9, 3) == spec["live_now_s"], (state, body["clock_ns"])
    else:
        body = bodies[bisect.bisect_right(body_ns, round(end_s * 1e9)) - 1]
        assert end_s - 0.01 < body["clock_ns"] * 1e-9 <= end_s, (state, end_s, body["clock_ns"])
        controls = np.array([[p["x"], p["y"], p["z"]] for p in spline["data"]["pos_pts"]])
        interval = k[4] - k[3]
        u_all = (body["clock_ns"] * 1e-9 - start_s) / interval
        span = min(int(np.floor(u_all)), len(controls) - 4)
        u = u_all - span
        velocity = np.array([-(1 - u) ** 2, 3 * u ** 2 - 4 * u, -3 * u ** 2 + 2 * u + 1, u ** 2]) / 2 / interval @ controls[span:span + 4]
        assert " ".join(format(v, ".3g") for v in velocity) == spec["live_start_velocity"], (state, velocity)
    now = body["clock_ns"]
    # No other curve was committed between the executing curve and the frozen clock.
    later = [x for x in obs if x["event"] == "bspline" and x["clock_ns"] is not None and spline["clock_ns"] < x["clock_ns"] <= now]
    assert not later, (state, [x["data"]["traj_id"] for x in later])
    scan_log = (run / "scan.log").read_text(errors="replace").splitlines()
    # The stand begins at the first "Local reference window complete" after the last committed window of the run.
    committed = [i for i, l in enumerate(scan_log) if "reference_window_committed time=" in l]
    stand_line = next(i for i, l in enumerate(scan_log) if "Local reference window complete" in l and i > committed[-1])
    progress_line = max(i for i in committed if i < stand_line)
    progress = re.search(r"reference_window_committed time=([0-9.]+) ", scan_log[progress_line]).group(1)
    out = audit / state / "inputs"
    out.mkdir(parents=True, exist_ok=False)
    for name, record, cls in [("route", route, P2BRoute), ("spline", spline, Bspline)]:
        msg = cls()
        set_message_fields(msg, copy.deepcopy(record["data"]))
        (out / (name + ".cdr")).write_bytes(serialize_message(msg))
        (out / (name + ".json")).write_text(json.dumps(record, indent=2) + "\n")
    manifest = json.loads((run / "sensor_manifest.json").read_text())
    clouds = [r for r in manifest if round(r["published_at_physics_s"] * 1e9) <= now]
    lines, files = [], []
    for i, r in enumerate(clouds):
        p = run / r["file"]
        assert sha(p) == r["sha256"]
        with np.load(p) as d:
            points = np.asarray(d["sensor_points"], dtype="<f4")
        filename = f"cloud_{i:03d}.f32"
        points.tofile(out / filename)
        files.append(filename)
        b = r["body_sensor"]
        pose(out / f"body_{i:03d}.txt", b["position"], b["quaternion"], b["linear_body"], b["angular_body"])
        pose(out / f"sensor_{i:03d}.txt", b["sensor_position"], b["sensor_quaternion"])
        lines.append(f"{r['stamp_ns']} body_{i:03d}.txt sensor_{i:03d}.txt")
    (out / "clouds.txt").write_text("\n".join(files) + "\n")
    (out / "poses.txt").write_text("\n".join(lines) + "\n")
    (out / "body_pose.txt").write_bytes((out / "body_000.txt").read_bytes())
    (out / "sensor_pose.txt").write_bytes((out / "sensor_000.txt").read_bytes())
    b = body["data"]
    p, q, t = b["pose"]["pose"]["position"], b["pose"]["pose"]["orientation"], b["twist"]["twist"]
    pose(out / "final_body.txt", [p[k] for k in "xyz"], [q[k] for k in "wxyz"],
         [t["linear"][k] for k in "xyz"], [t["angular"][k] for k in "xyz"])
    (out / "final_clock.txt").write_text(str(now) + "\n")
    (out / "ground.f32").write_bytes(navigation.read_bytes())
    (out / "last_progress.txt").write_text(progress + "\n")
    (out / "planner.yaml").write_bytes((run / "planner.yaml").read_bytes())
    last = spline["data"]["pos_pts"][-1]
    record = {"source_run": run.name, "state": state, "spec": spec, "now_ns": now,
              "executing_traj_id": spline["data"]["traj_id"], "executing_start_s": start_s, "executing_end_s": end_s,
              "executing_end_xyz": [last["x"], last["y"], last["z"]],
              "clouds": len(clouds), "last_cloud_stamp_ns": clouds[-1]["stamp_ns"],
              "last_progress": progress, "last_progress_line": progress_line + 1, "stand_line": stand_line + 1,
              "final_body_xyz": [p[k] for k in "xyz"], "final_body_wxyz": [q[k] for k in "wxyz"],
              "source_sha256": {str(x.relative_to(base)): sha(x) for x in [
                  run / "artifacts/reactive_observations.jsonl", run / "sensor_manifest.json",
                  run / "planner.yaml", run / "scan.log", navigation, surface]},
              "condition": "Original published scans up to the frozen clock, paired original sensor/body states, "
                           "the last recorded body pose at or before the clock, the executing (completed) spline and "
                           "the last committed window; no semantic data or altered timestamps.",
              "files": {x.name: sha(x) for x in sorted(out.iterdir()) if x.is_file()}}
    (out / "input_manifest.json").write_text(json.dumps(record, indent=2) + "\n")
    summary[state] = {k: record[k] for k in ("now_ns", "clouds", "last_cloud_stamp_ns", "executing_traj_id",
                                              "executing_end_xyz", "last_progress", "final_body_xyz")}
print(json.dumps(summary, indent=2))
