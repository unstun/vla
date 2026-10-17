"""Write the run's own later inputs for the four frozen v30 stop states as "pending" inputs.

The frozen states come from audits/2026-09-28_v30_stop_classes/<state>/inputs
(prepare_inputs.py there): original scans up to the frozen clock, paired poses,
the executing spline and route. This script adds what v30_historical_full01
itself published after that clock:

- scans_0p30: every scan whose stamp is after the last frozen scan and that was
  published (0.020 s after its stamp) by frozen clock + 0.30 s, with its paired
  sensor pose; plus the body poses the observer recorded in that interval.
- bodies_0p15: only the body poses recorded by frozen clock + 0.15 s.

The probe publishes these without spinning, as SCAN's subscriptions receive
them while a long callback runs. No stamp or payload is altered.

Usage: python3 prepare_pending.py <experiment root> <stop-class audit dir> <output dir>
"""
from pathlib import Path
import hashlib, json, sys
import numpy as np

base, audit, out_root = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
run = base / "runs/v30_historical_full01"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = json.loads((run / "sensor_manifest.json").read_text())
bodies = []
with (run / "artifacts/reactive_observations.jsonl").open() as f:
    for line in f:
        record = json.loads(line)
        if record["event"] == "body_pose_observer" and record["clock_ns"] is not None:
            bodies.append(record)
bodies.sort(key=lambda x: x["clock_ns"])


def pose(path, p, q, v=(0, 0, 0), w=(0, 0, 0)):
    # Same text layout as the frozen inputs: xyz, quaternion xyzw, linear, angular.
    path.write_text(" ".join(format(float(x), ".17g") for x in [*p, q[1], q[2], q[3], q[0], *v, *w]) + "\n")


summary = {}
for state in ["stairs_replan", "stairs_hold", "corridor_entry_replan", "upper_corridor_hold"]:
    frozen = json.loads((audit / state / "inputs/input_manifest.json").read_text())
    now, last_cloud = frozen["now_ns"], frozen["last_cloud_stamp_ns"]
    summary[state] = {"frozen_ns": now, "last_frozen_cloud_stamp_ns": last_cloud}
    for name, delta_ns, with_scans in [("scans_0p30", 300_000_000, True), ("bodies_0p15", 150_000_000, False)]:
        check = now + delta_ns
        out = out_root / state / name
        out.mkdir(parents=True, exist_ok=False)
        scan_lines, body_lines = [], []
        if with_scans:
            for i, r in enumerate(x for x in manifest if x["stamp_ns"] > last_cloud and
                                  round(x["published_at_physics_s"] * 1e9) <= check):
                p = run / r["file"]
                assert sha(p) == r["sha256"]
                with np.load(p) as d:
                    np.asarray(d["sensor_points"], dtype="<f4").tofile(out / f"cloud_{i:02d}.f32")
                b = r["body_sensor"]
                pose(out / f"sensor_{i:02d}.txt", b["sensor_position"], b["sensor_quaternion"])
                scan_lines.append(f"{r['stamp_ns']} cloud_{i:02d}.f32 sensor_{i:02d}.txt")
        for i, record in enumerate(x for x in bodies if now < x["clock_ns"] <= check):
            d = record["data"]
            p, q, t = d["pose"]["pose"]["position"], d["pose"]["pose"]["orientation"], d["twist"]["twist"]
            pose(out / f"body_{i:03d}.txt", [p[k] for k in "xyz"], [q[k] for k in "wxyz"],
                 [t["linear"][k] for k in "xyz"], [t["angular"][k] for k in "xyz"])
            body_lines.append(f"{record['clock_ns']} body_{i:03d}.txt")
        (out / "scans.txt").write_text("".join(line + "\n" for line in scan_lines))
        (out / "bodies.txt").write_text("".join(line + "\n" for line in body_lines))
        summary[state][name] = {"check_ns": check, "scans": len(scan_lines), "bodies": len(body_lines),
                                "scan_stamps_ns": [int(x.split()[0]) for x in scan_lines],
                                "last_body_ns": int(body_lines[-1].split()[0]) if body_lines else None,
                                "files": {x.name: sha(x) for x in sorted(out.iterdir())}}
(out_root / "pending_manifest.json").write_text(json.dumps({
    "source_run": run.name,
    "source_sha256": {str(x.relative_to(base)): sha(x) for x in [run / "sensor_manifest.json",
                                                                 run / "artifacts/reactive_observations.jsonl"]},
    "states": summary}, indent=2) + "\n")
print(json.dumps({s: {k: {kk: vv for kk, vv in v.items() if kk != "files"} if isinstance(v, dict) else v
                      for k, v in d.items()} for s, d in summary.items()}, indent=1))
