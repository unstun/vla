"""Freeze four actual v30_historical_full01 emergency-stop states for replay.

Adapted from audits/2026-09-28_v29_landing_stall/prepare_inputs.py. Only the
source run, the chosen stops and the automatic lookup of each stop's clock,
executing spline and last committed window differ.

Each state is frozen at the last recorded body pose at or before the stop's
sim time. The stop's sim time comes from timeline.json (container log wall
time mapped through the applied-command snapshots; residual <= 0.021 s).
"""
from pathlib import Path
import bisect, copy, hashlib, json, re, sys
import numpy as np
from rclpy.serialization import serialize_message
from rosidl_runtime_py.set_message import set_message_fields
from scan_planner_msgs.msg import P2BRoute, Bspline

# name: scan.log line of the stopping [SAFETY] transition (timeline.json "stops")
STOPS = {
    "stairs_replan": 467,          # stop 1, REPLAN_TRAJ, moving curve, route walk ends silently
    "stairs_hold": 523,            # stop 2, GEN_NEW_TRAJ on a hold, whole route reported blocked
    "corridor_entry_replan": 6460,  # stop 23, curve flagged by the first safety check after commit
    "upper_corridor_hold": 9452,    # stop 50, GEN_NEW_TRAJ on a hold in the final stationary period
}
base, audit = Path(sys.argv[1]), Path(sys.argv[2])
run = base / "runs/v30_historical_full01"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
timeline = json.loads((audit / "timeline.json").read_text())
stops = {s["line"]: s for s in timeline["stops"]}
obs = [json.loads(l) for l in (run / "artifacts/reactive_observations.jsonl").read_text().splitlines()]
route = next(x for x in obs if x["event"] == "pct_route")
bodies = sorted((x for x in obs if x["event"] == "body_pose_observer" and x["clock_ns"] is not None),
                key=lambda x: x["clock_ns"])
body_ns = [x["clock_ns"] for x in bodies]
navigation = base / "audits/2026-09-27_pct_precision/ground_precise.f32"
surface = base / "audits/2026-09-27_dense_static_sampling/raw_ground.f32"
assert f"payload_sha256={sha(navigation)}" in (run / "pct_support.log").read_text()
assert f"payload_sha256={sha(surface)}" in (run / "pct_surface_ground.log").read_text()
scan_log = (run / "scan.log").read_text(errors="replace").splitlines()
manifest = json.loads((run / "sensor_manifest.json").read_text())


def pose(path, p, q, v=(0, 0, 0), w=(0, 0, 0)):
    path.write_text(" ".join(format(float(x), ".17g") for x in [*p, q[1], q[2], q[3], q[0], *v, *w]) + "\n")


summary = {}
for state, line in STOPS.items():
    stop = stops[line]
    assert scan_log[line - 1].startswith("[SAFETY]: from") and scan_log[line - 1].endswith("to EMERGENCY_STOP")
    body = bodies[bisect.bisect_right(body_ns, round(stop["sim_s"] * 1e9)) - 1]
    now = body["clock_ns"]
    progress_line = max(i for i in range(line) if "reference_window_committed time=" in scan_log[i])
    progress = re.search(r"reference_window_committed time=([0-9.]+) ", scan_log[progress_line]).group(1)
    spline = next(x for x in reversed(obs) if x["event"] == "bspline" and x["clock_ns"] is not None and x["clock_ns"] <= now)
    assert spline["data"]["traj_id"] == stop["executing"]["trajectory"], (state, spline["data"]["traj_id"], stop["executing"])
    out = audit / state / "inputs"
    out.mkdir(parents=True, exist_ok=False)
    for name, record, cls in [("route", route, P2BRoute), ("spline", spline, Bspline)]:
        msg = cls()
        set_message_fields(msg, copy.deepcopy(record["data"]))
        (out / (name + ".cdr")).write_bytes(serialize_message(msg))
        (out / (name + ".json")).write_text(json.dumps(record, indent=2) + "\n")
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
    record = {"source_run": run.name, "state": state, "stop_line": line, "stop": stop, "now_ns": now,
              "clouds": len(clouds), "last_cloud_stamp_ns": clouds[-1]["stamp_ns"],
              "last_spline_traj_id": spline["data"]["traj_id"], "last_progress": progress,
              "last_progress_line": progress_line + 1, "final_body_xyz": [p[k] for k in "xyz"],
              "source_sha256": {str(x.relative_to(base)): sha(x) for x in [
                  run / "artifacts/reactive_observations.jsonl", run / "sensor_manifest.json",
                  run / "planner.yaml", run / "scan.log", navigation, surface]},
              "condition": "Original published scans up to the frozen clock, paired original sensor/body states, "
                           "the last recorded body pose at or before the stop, the executing spline and the last "
                           "committed window; no semantic data or altered timestamps.",
              "files": {x.name: sha(x) for x in sorted(out.iterdir()) if x.is_file()}}
    (out / "input_manifest.json").write_text(json.dumps(record, indent=2) + "\n")
    summary[state] = {k: record[k] for k in ("now_ns", "clouds", "last_cloud_stamp_ns", "last_spline_traj_id",
                                              "last_progress", "final_body_xyz")}
print(json.dumps(summary, indent=2))
