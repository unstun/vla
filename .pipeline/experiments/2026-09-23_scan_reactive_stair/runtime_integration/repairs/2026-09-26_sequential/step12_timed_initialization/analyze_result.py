"""Verify the received moving spline's numerical boundary and record native gates."""
import hashlib
import argparse
import json
import math
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument("--run-dir", type=Path, default=HERE / "scan28_height030_v1")
args = parser.parse_args()
run = args.run_dir
log = (run / "replay_result/scan.log").read_text()
review = json.loads((run / "review.json").read_text())
record = json.loads((run / "replay_result/result.json").read_text())
splines = [item["data"] for item in record["received"] if item["kind"] == "bspline"]
assert review["moving_spline_count"] == 1 and review["successful_plan_count"] == 1 and len(splines) == 1
spline = splines[0]
controls = [[p[k] for k in ("x", "y", "z")] for p in spline["pos_pts"]]
knots = spline["knots"]
assert spline["order"] == 3 and len(knots) == len(controls) + 4
h = knots[4] - knots[3]
assert all(abs((b-a)-h) < 1e-12 for a,b in zip(knots,knots[1:]))
norm = lambda p: math.sqrt(sum(x*x for x in p))
error = lambda a,b: norm([x-y for x,y in zip(a,b)])
def pva(q):
    return [[(q[0][k]+4*q[1][k]+q[2][k])/6 for k in range(3)],
            [(q[2][k]-q[0][k])/(2*h) for k in range(3)],
            [(q[0][k]-2*q[1][k]+q[2][k])/(h*h) for k in range(3)]]
start = pva(controls[:3]); end = pva(controls[-3:])
provenance = json.loads((HERE / "native_scan_28_foxy_v1/package/provenance.json").read_text())
body = provenance["body_event"]["data"]
seed = json.loads((HERE.parent / "step8_spline_seed/GEOMETRY_TRACE.json").read_text())["points"]["seed"]
expected_start = [body["position"], body["linear"], [0,0,0]]
expected_end = [seed[-1], [0,0,0], [0,0,0]]
world_velocity_error = error(start[1], body["linear"])
correct_frame = record.get("body_twist_contract_version") == 1
if not correct_frame:
    # Historical transport mislabeled world twist as body. Reconstruct exactly
    # what the native FSM actually consumed, while retaining the measured-world error.
    w,x,y,z = body["quaternion"]
    matrix = [[1-2*(y*y+z*z),2*(x*y-w*z),2*(x*z+w*y)],
              [2*(x*y+w*z),1-2*(x*x+z*z),2*(y*z-w*x)],
              [2*(x*z-w*y),2*(y*z+w*x),1-2*(x*x+y*y)]]
    expected_start[1] = [sum(a*b for a,b in zip(row,body["linear"])) for row in matrix]
errors = {"start":[error(a,b) for a,b in zip(start,expected_start)],
          "end":[error(a,b) for a,b in zip(end,expected_end)]}
assert max(errors["start"]+errors["end"]) < 1e-6
velocities = [[(b[k]-a[k])/h for k in range(3)] for a,b in zip(controls,controls[1:])]
accelerations = [[(b[k]-a[k])/h for k in range(3)] for a,b in zip(velocities,velocities[1:])]
gate = re.search(r"full_spline_sampled_clear duration=([\d.]+) samples=(\d+) wall_ms=([\d.]+)",log)
assert gate and "first_optimize_step_success=1" in log
assert "final_spline_boundary_pva_rejected" not in log and "timed_cubic_initialization_failed" not in log
result = {
    **review, "install_identity_sha256":"6e78dfea88efe9c2d4abb5c6713ea7721629f42f47b625b240b9f656afb96caf",
    "received_spline_sha256":hashlib.sha256(json.dumps(spline,sort_keys=True).encode()).hexdigest(),
    "control_count":len(controls), "interval_s":h, "duration_s":knots[len(controls)]-knots[3],
    "body_twist_frame_corrected":correct_frame, "start_velocity_error_vs_recorded_world":world_velocity_error,
    "boundary_errors_position_velocity_acceleration":errors,
    "velocity_control_component_bound":max(abs(x) for p in velocities for x in p),
    "velocity_control_norm_bound":max(map(norm,velocities)),
    "acceleration_control_component_bound":max(abs(x) for p in accelerations for x in p),
    "acceleration_control_norm_bound":max(map(norm,accelerations)),
    "full_sampled_collision_count":int(gate[2]), "full_sampled_collision_wall_ms":float(gate[3]),
    "original_optimizer_returned_success":True, "later_refinement_requested":"Need to reallocate time." in log,
    "claim":"One moving spline was accepted and received after original optimization, PVA, dynamics and complete sampled collision gates. Endpoint arithmetic verifies the boundary supplied to the planner. The body_twist_frame_corrected field distinguishes original measured-world velocity from the historical mis-rotated velocity. Zero start acceleration is an initialization request, not measured acceleration. No simulator motion, future-map or route-completion claim."
}
suffix = "" if correct_frame else "_legacy_twist"
(HERE / ("RUNTIME_RESULT"+suffix+".json")).write_text(json.dumps(result,indent=2)+"\n")
(HERE / ("accepted_spline"+suffix+".json")).write_text(json.dumps(spline,indent=2)+"\n")
print(json.dumps(result,indent=2))
