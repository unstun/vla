"""Reuse the captured CPU replay transport for one immutable repair candidate."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil

HERE = Path(__file__).resolve().parent
RI = HERE.parents[1]
ROOT = RI.parents[3]
P2B = ROOT / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution"
AUDIT = RI / "diagnostics/2026-09-26_root_cause"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--step", default="step1_astar")
    parser.add_argument("--inputs", type=Path, default=AUDIT / "search_inputs")
    args = parser.parse_args()
    for value in (args.build, args.run_id, args.step):
        if not value.replace("_", "").isalnum():
            raise ValueError("invalid run/build/step identity")
    out = HERE / args.step / args.run_id
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True)
    shutil.copytree(args.inputs, out / "search_inputs")
    driver = AUDIT / "run_search_trace.py"
    request = {"build": args.build, "input_directory": str(args.inputs),
               "input_manifest_sha256": sha(args.inputs / "input_manifest.json"),
               "transport_source_sha256": sha(driver), "wrapper_sha256": sha(Path(__file__)),
               "claim": "Repair candidate replay of recorded input. No simulator, controller or physics; graph/seed/spline outcomes remain separate."}
    (out / "candidate_request.json").write_text(json.dumps(request, indent=2) + "\n")
    spec = importlib.util.spec_from_file_location("captured_search_transport", driver)
    transport = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(transport)
    transport.HERE = out
    transport.BUILD = P2B / "builds" / args.build
    transport.REMOTE = "/home/sun/vla_exec/2026-09-26_stair_repairs/" + args.run_id
    transport.REMOTE_BUILD = "/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/builds/" + args.build
    transport.NAME = "vla-stair-repair-" + args.run_id
    transport.main()
    log = (out / "replay_result/scan.log").read_text()
    native = json.loads((out / "replay_result/result.json").read_text())
    splines = [v["data"] for v in native["received"] if v["kind"] == "bspline"]
    moving = []
    for spline in splines:
        pts = spline["pos_pts"]
        if pts and any(sum((p[k] - pts[0][k]) ** 2 for k in ("x", "y", "z")) > 0.0004 for p in pts):
            moving.append(spline)
    review = {"build": args.build, "input_manifest_sha256": request["input_manifest_sha256"],
              "native_completed": native["completed"],
              "seed_search_failures": log.count("reactive_stair_seed_search_failed"),
              "seed_endpoint_mismatch": log.count("reactive_stair_seed_endpoint_mismatch"),
              "seed_edge_blocked": log.count("reactive_stair_seed_edge_blocked"),
              "checked_seed_count": log.count("reactive_stair_seed_checked"),
              "successful_plan_count": len(re.findall(r"final_plan_success=1", log)),
              "moving_spline_count": len(moving),
              "search_time_cap_hit": "0.2 second time limit exceeded" in log,
              "log_sha256": sha(out / "replay_result/scan.log"),
              "claim": "Native CPU recorded-input result only; does not establish live timing, locomotion or avoidance."}
    (out / "review.json").write_text(json.dumps(review, indent=2) + "\n")
    print(json.dumps(review, indent=2))


if __name__ == "__main__":
    main()
