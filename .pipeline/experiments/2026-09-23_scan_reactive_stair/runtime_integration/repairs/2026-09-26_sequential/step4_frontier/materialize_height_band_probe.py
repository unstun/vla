"""CPU-only measured-map query: is there an edge between coarse Z levels?"""
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
    base, out = P2B / "builds/scan_23", P2B / "builds/scan23_height_band_probe"
    inputs = HERE / "height_band_inputs"
    if out.exists() or inputs.exists():
        raise FileExistsError("height probe already exists")
    expected = json.loads((base / "source_sha256.json").read_text())
    actual = {"src/" + p.relative_to(base / "src").as_posix(): sha(p)
              for p in (base / "src").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if actual != expected:
        raise ValueError("base source identity mismatch")
    shutil.copytree(base / "src", out / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    manager = out / "src/plan_manage/src/planner_manager.cpp"
    once(manager, "    node_ = node;", '''    node_ = node;
    if (!node->has_parameter("manager.height_band_probe"))
      node->declare_parameter<bool>("manager.height_band_probe", false);''')
    once(manager, "    static int count = 0;", '''    if (node_->get_parameter("manager.height_band_probe").as_bool()) {
      static bool probed = false;
      if (!probed) {
        probed = true;
        // First-search graph and short-seed replay independently accepted this
        // prefix endpoint. Probe the next 5 cm edge under the unchanged map.
        const Eigen::Vector3d from = start_pt + Eigen::Vector3d(0.0, -0.15, 0.05);
        for (int millimeters = 0; millimeters <= 120; ++millimeters) {
          const Eigen::Vector3d to = start_pt + Eigen::Vector3d(0.0, -0.20, .001 * millimeters);
          int blocked_sample = -1;
          const bool clear = grid_map_->collisionFreeSegment(from, to, &blocked_sample);
          RCLCPP_WARN(node_->get_logger(), "HEIGHT_BAND_PROBE dz_mm=%d clear=%d blocked_sample=%d from=(%.9f,%.9f,%.9f) to=(%.9f,%.9f,%.9f)",
                      millimeters, clear, blocked_sample, from.x(), from.y(), from.z(), to.x(), to.y(), to.z());
        }
      }
      return false;  // This observer must never publish a moving trajectory.
    }
    static int count = 0;''')
    parent_inputs = HERE.parents[2] / "diagnostics/2026-09-26_root_cause/search_inputs"
    shutil.copytree(parent_inputs, inputs)
    config = inputs / "planner.yaml"
    once(config, "    manager.planning_horizon: 3.5", "    manager.planning_horizon: 3.5\n    manager.height_band_probe: true")
    p = inputs / "input_manifest.json"
    manifest = json.loads(p.read_text())
    manifest["parent_input_manifest_sha256"] = sha(parent_inputs / "input_manifest.json")
    manifest["files"]["planner.yaml"] = sha(config)
    manifest["probe"] = "Only first measured-start map queries. Probe existing shared edge predicate at 1 mm endpoint height intervals over 0..120 mm; every planning call returns false. No state, threshold, occupancy or sensor modification; no trajectory/physics outcome."
    p.write_text(json.dumps(manifest, indent=2) + "\n")
    (out / "height_probe_manifest.json").write_text(json.dumps({
        "base": "scan_23", "base_source_manifest_sha256": sha(base / "source_sha256.json"),
        "changed_sha256": {str(manager.relative_to(out)): sha(manager)},
        "generator_sha256": sha(Path(__file__)), "input_manifest_sha256": sha(p), "claim": manifest["probe"]}, indent=2) + "\n")
    print(out)


if __name__ == "__main__":
    main()
