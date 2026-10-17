"""One-call, CPU-replay-only short-seed feasibility experiment; never deploy."""
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[6]
P2B = ROOT / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution"
sys.path.insert(0, str(P2B / "reactive_stair"))
from materialize_scan_20 import once, sha


def main():
    base, out = P2B / "builds/scan_23", P2B / "builds/scan23_short_prefix_probe"
    inputs = HERE / "short_prefix_inputs"
    if out.exists() or inputs.exists():
        raise FileExistsError("probe already materialized")
    expected = json.loads((base / "source_sha256.json").read_text())
    actual = {"src/" + p.relative_to(base / "src").as_posix(): sha(p)
              for p in (base / "src").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if expected != actual or not json.loads((base / "build_result.json").read_text())["passed"]:
        raise ValueError("base source/build identity failed")
    shutil.copytree(base / "src", out / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    manager = out / "src/plan_manage/src/planner_manager.cpp"
    once(manager, "    node_ = node;", '''    node_ = node;
    if (!node->has_parameter("manager.short_prefix_probe"))
      node->declare_parameter<bool>("manager.short_prefix_probe", false);''')
    once(manager, "    static int count = 0;", '''    const bool short_prefix_probe = node_->get_parameter("manager.short_prefix_probe").as_bool();
    if (short_prefix_probe) {
      // TEST ONLY: one initial-odom attempt. Never continue from a predicted
      // prefix endpoint or publish a chain that pretends the robot has moved.
      static bool probe_attempted = false;
      if (probe_attempted) return false;
      probe_attempted = true;
      local_target_pt = start_pt + Eigen::Vector3d(0.0, -0.15, 0.05);
      local_target_vel.setZero();
      RCLCPP_WARN(node_->get_logger(), "TEST_ONLY_SHORT_PREFIX first measured start, delta=(0,-0.15,0.05), zero terminal velocity; original collision and dynamics gates retained");
    }
    static int count = 0;''')
    once(manager, "    if ((start_pt - local_target_pt).norm() < 0.2)",
         "    if (!short_prefix_probe && (start_pt - local_target_pt).norm() < 0.2)")
    source_inputs = HERE.parents[2] / "diagnostics/2026-09-26_root_cause/search_inputs"
    shutil.copytree(source_inputs, inputs)
    config = inputs / "planner.yaml"
    once(config, "    manager.planning_horizon: 3.5", "    manager.planning_horizon: 3.5\n    manager.short_prefix_probe: true")
    manifest_path = inputs / "input_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["parent_input_manifest_sha256"] = sha(source_inputs / "input_manifest.json")
    manifest["files"]["planner.yaml"] = sha(config)
    manifest["probe"] = "Single initial-odom short-prefix trajectory feasibility. Target override is (0,-.15,+.05) relative to first actual start, terminal velocity zero. Original route/clock/cloud/odom/track records unchanged. No simulator/controller, no live candidate, no global-progress claim."
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    (out / "short_prefix_probe_manifest.json").write_text(json.dumps({
        "base": "scan_23", "base_source_manifest_sha256": sha(base / "source_sha256.json"),
        "changed_sha256": {str(manager.relative_to(out)): sha(manager)},
        "generator_sha256": sha(Path(__file__)), "input_manifest_sha256": sha(manifest_path),
        "claim": manifest["probe"],
        "constraints": "Only opt-in single-call short-distance heuristic bypass; preserve start state, graph edge predicate, all collision/heading/dynamic checks and no unknown clearing. Requires separate design before any live use."}, indent=2) + "\n")
    print(out)


if __name__ == "__main__":
    main()
