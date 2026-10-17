"""Extract the bounded native position/heading/time comparison, without inference of motion."""
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
run = HERE / "scan27_curve_pose_time_v1"
path = run / "replay_result/scan.log"
log = path.read_text()
curves = {}
for line in log.splitlines():
    if "CURVE_PROBE curve=" in line or "CURVE_PROBE dynamics=" in line or "CURVE_PROBE paired=" in line:
        data = dict(re.findall(r"(\w+)=([^ ]+)", line.split("CURVE_PROBE ", 1)[1]))
        kind = next(key for key in ("curve", "dynamics", "paired") if key in data)
        label = data.pop(kind)
        curves.setdefault(label, {})[kind] = data
footprints = re.findall(r"initial_spline_collision pos=(\([^\n]+?) body_stamp=([\d.]+) now=([\d.]+)",
                        log.split("CURVE_PROBE curve=initial ", 1)[1].split("final_plan_success", 1)[0])
assert len(footprints) == 4 and len({(body_stamp, now) for _, body_stamp, now in footprints}) == 1
for name in ("initial", "optimized"):
    pair = curves[name]["paired"]
    assert pair["same_position_parent_occupied"] == "0"
    assert pair["projected_curve_occupied"] == "1" and pair["projected_parent_occupied"] == "0"
    assert curves[name]["curve"]["status"] == "1"
scaled = curves["initial_time_scaled"]
assert scaled["curve"]["status"] == "0" and scaled["dynamics"]["feasible"] == "1"
result = {
    "build": "scan27_curve_pose_time_probe", "log_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    "input_manifest_sha256": json.loads((run / "candidate_request.json").read_text())["input_manifest_sha256"],
    "install_identity_sha256": "df216017c3e1295ecc07335f86a2cc924131ecbc9558951a7bc8bc24fbe3e827",
    "curves": curves, "paired_body_stamp": footprints[0][1], "paired_clock": footprints[0][2],
    "time_scale": float(re.search(r"CURVE_PROBE time_scale=([\d.]+)", log)[1]),
    "conclusion": "At the same first rejected position and frozen inputs, replacing only preview heading by nearest seed-edge heading changes occupied to clear. Projection alone does not. All-knot native-bound time scaling makes the unchanged centerline pass complete sampled collision and native component derivative bounds.",
    "boundary": "Diagnostic only after original optimizer failure. Time scaling changes boundary velocity/acceleration and fixed-.8s preview yaw. Native feasible is a component control-point bound, not the manager norm check; native_ratio is meaningless when feasible=true. No moving spline, actuation, tracking, future-map or 93-second execution evidence."
}
(HERE / "RESULT.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
