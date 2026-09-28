"""Freeze two actual v29 landing-stall states for native frontier diagnosis.

Adapted from audits/2026-09-28_v28_start_thrash/prepare_inputs.py; only the
source run, the frozen clocks, the expected spline and the recorded window end
differ.
- onset: 47.360599518 s, the last body pose before the REPLAN at 47.361 s whose
  frontier first became t = 8.6446 s (scan.log line 10025). traj 47 executing;
  last committed window 6.810039928888 s (scan.log line 10013).
- landing: 80.977127075 s, the last body pose before the REPLAN at 80.982 s
  after "Local reference window complete (8.64/73.60s)" (scan.log line 77915).
  traj 63 executing; last committed window 8.644578442007 s (line 77910).
"""
from pathlib import Path
import copy, hashlib, json, sys
import numpy as np
from rclpy.serialization import serialize_message
from rosidl_runtime_py.set_message import set_message_fields
from scan_planner_msgs.msg import P2BRoute, Bspline

STATES = {
    "onset": (47360599518, 47, "6.810039928888", 10013),
    "landing": (80977127075, 63, "8.644578442007", 77910),
}
base, audit = Path(sys.argv[1]), Path(sys.argv[2])
run = base / "runs/v29_historical_full01"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
obs = [json.loads(l) for l in (run / "artifacts/reactive_observations.jsonl").read_text().splitlines()]
route = next(x for x in obs if x["event"] == "pct_route")
parent = base / "audits/2026-09-27_pct_precision"
assert sha(parent / "ground_precise.f32") in (run / "pct_support.log").read_text()
scan_log = (run / "scan.log").read_text(errors="replace").splitlines()


def pose(path, p, q, v=(0, 0, 0), w=(0, 0, 0)):
    path.write_text(" ".join(format(float(x), ".17g") for x in [*p, q[1], q[2], q[3], q[0], *v, *w]) + "\n")


summary = {}
for state, (now, traj_id, progress, progress_line) in STATES.items():
    assert f"reference_window_committed time={progress} " in scan_log[progress_line - 1]
    out = audit / state / "inputs"
    out.mkdir(parents=True, exist_ok=False)
    spline = next(x for x in reversed(obs) if x["event"] == "bspline" and x["clock_ns"] is not None and x["clock_ns"] <= now)
    body = next(x for x in obs if x["event"] == "body_pose_observer" and x["clock_ns"] is not None and x["clock_ns"] >= now)
    assert body["clock_ns"] == now and spline["data"]["traj_id"] == traj_id
    for name, record, cls in [("route", route, P2BRoute), ("spline", spline, Bspline)]:
        msg = cls()
        set_message_fields(msg, copy.deepcopy(record["data"]))
        (out / (name + ".cdr")).write_bytes(serialize_message(msg))
        (out / (name + ".json")).write_text(json.dumps(record, indent=2) + "\n")
    clouds = [r for r in json.loads((run / "sensor_manifest.json").read_text()) if round(r["published_at_physics_s"] * 1e9) <= now]
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
    pose(out / "final_body.txt", [p[k] for k in "xyz"], [q[k] for k in "wxyz"], [t["linear"][k] for k in "xyz"], [t["angular"][k] for k in "xyz"])
    (out / "final_clock.txt").write_text(str(now) + "\n")
    (out / "ground.f32").write_bytes((parent / "ground_precise.f32").read_bytes())
    (out / "last_progress.txt").write_text(progress + "\n")
    (out / "planner.yaml").write_bytes((run / "planner.yaml").read_bytes())
    record = {"source_run": run.name, "state": state, "now_ns": now, "clouds": len(clouds),
              "last_cloud_stamp_ns": clouds[-1]["stamp_ns"], "last_spline_traj_id": spline["data"]["traj_id"],
              "last_progress": progress, "final_body_xyz": [p[k] for k in "xyz"],
              "source_sha256": {str(x.relative_to(base)): sha(x) for x in [run / "artifacts/reactive_observations.jsonl",
                                run / "sensor_manifest.json", run / "planner.yaml", run / "scan.log", parent / "ground_precise.f32"]},
              "condition": "Original published scans up to the frozen clock, paired original sensor/body states, original latest body message and executing spline, original route and recorded committed window; no semantic data or altered timestamps.",
              "files": {x.name: sha(x) for x in out.iterdir() if x.is_file()}}
    (out / "input_manifest.json").write_text(json.dumps(record, indent=2) + "\n")
    summary[state] = {k: record[k] for k in ("now_ns", "clouds", "last_cloud_stamp_ns", "last_spline_traj_id", "final_body_xyz")}
print(json.dumps(summary, indent=2))
