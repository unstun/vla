"""Read-only audit of pinned locomotion height versus spawn/route offsets."""
import ast
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[6]
RI = HERE.parents[2]
LOCAL = ROOT.parent / "machine-dog-nav/references/locomotion/2026-08-13_v12_model149999/source/v12_runtime_20260718_recovered"
REMOTE = "/home/sun/machine-dog-nav-runs/2026-09-08_new_building_lite3_dynamics/source/v12"
FILES = ("source/robot_lab/robot_lab/tasks/lite3/env_cfg.py", "source/robot_lab/robot_lab/tasks/lite3/__init__.py",
         "source/robot_lab/robot_lab/assets/deeprobotics.py")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output = HERE / "height_contract_evidence.json"
    if output.exists():
        raise FileExistsError(output)
    expected = {name: sha(LOCAL / name) for name in FILES}
    script = "import pathlib,hashlib,json\nr=pathlib.Path(%r)\nfiles=%r\n" % (REMOTE, FILES)
    script += "print(json.dumps({name:hashlib.sha256((r/name).read_bytes()).hexdigest() for name in files},sort_keys=True))\n"
    result = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "gpu5070ti", "python3 -"],
                            input=script, capture_output=True, text=True, timeout=45)
    (HERE / "remote_source_verification.log").write_text(result.stdout + result.stderr)
    result.check_returncode()
    actual = json.loads(result.stdout)
    assert actual == expected
    module = ast.parse((LOCAL / FILES[0]).read_text())
    target = next(ast.literal_eval(n.value) for n in module.body if isinstance(n, ast.Assign) and
                  any(isinstance(t, ast.Name) and t.id == "BASE_HEIGHT_TARGET" for t in n.targets))
    assert target == .30
    evidence_lines = {}
    for name in FILES:
        evidence_lines[name] = [{"line": i, "text": line} for i, line in enumerate((LOCAL / name).read_text().splitlines(), 1)
                                if any(k in line for k in ("BASE_HEIGHT_TARGET", '"target_height"', "pos=(0.0, 0.0, 0.35)", "env_cfg_entry_point", 'id="Wave-C-Stairs-V12'))]
    sys.path.insert(0, str(ROOT / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution/reactive_stair"))
    from pct_sim_clock_core import load_pinned_map, selected_ground_points
    from moving_cluster_io import terrain_from_pct_records
    ground = selected_ground_points(load_pinned_map(), cost_limit=None)
    terrain = terrain_from_pct_records(ground.tolist(), ground.tobytes(), "world", 1, cost_limit=None)
    run = RI / "runs/stand_scan23_tracker_right_v1"
    metrics = run / "returned_artifacts/runner_output/metrics.jsonl"
    heights = []
    for line in metrics.open():
        row = json.loads(line)
        if 5. <= row["sim_time_s"] <= 9.:
            x, y, z = row["base_xyz"]
            floor = terrain.ground_below(x, y, z)
            if floor is None:
                raise ValueError("missing ground for standing-height audit")
            heights.append(z - floor)
    assert heights
    identity = json.loads((run / "returned_artifacts/runner_output/runtime_identity.json").read_text())
    value = {"local_immutable_reference": str(LOCAL), "remote_execution_copy": REMOTE,
             "source_hashes_match": actual == expected, "source_sha256": expected, "source_lines": evidence_lines,
             "v12_source_commit_reported_by_runtime": identity["source_commit"],
             "registry": identity["v12_contract"]["registry_task"],
             "checkpoint_sha256": identity["checkpoint_sha256"],
             "configured_locomotion_height_target_m": target,
             "declared_spawn_height_m": identity["v12_contract"]["default_base_position_m"][2],
             "current_pilot_nominal_height_m": identity["nominal_body_height_m"],
             "actual_stable_standing_height_above_pinned_ground_m": {
                 "samples": len(heights), "mean": statistics.mean(heights), "median": statistics.median(heights),
                 "min": min(heights), "max": max(heights), "interval_s": [5., 9.]},
             "metrics_sha256": sha(metrics), "runtime_identity_sha256": sha(run / "returned_artifacts/runner_output/runtime_identity.json"),
             "script_sha256": sha(Path(__file__)),
             "claim": "Height semantics audit only. The fixed reward target is .30 m; the .35 m init height is a spawn setting. This does not by itself authorize a collision-free trajectory or prove behavior at all terrain heights."}
    output.write_text(json.dumps(value, indent=2) + "\n")
    print(json.dumps({k:v for k,v in value.items() if k not in ('source_lines','source_sha256')}, indent=2))


if __name__ == "__main__":
    main()
