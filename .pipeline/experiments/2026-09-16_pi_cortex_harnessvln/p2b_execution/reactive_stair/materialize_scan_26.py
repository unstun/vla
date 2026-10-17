"""Preserve validated seed corners while resampling for spline initialization."""
import json
from pathlib import Path
import shutil

from materialize_scan_20 import once, sha

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "builds/scan_25"
OUT = HERE.parent / "builds/scan_26"


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    expected = json.loads((BASE / "source_sha256.json").read_text())
    actual = {"src/" + p.relative_to(BASE / "src").as_posix(): sha(p)
              for p in (BASE / "src").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if actual != expected or not json.loads((BASE / "build_result.json").read_text())["passed"]:
        raise ValueError("scan_25 source/build identity gate failed")
    shutil.copytree(BASE / "src", OUT / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    helper = OUT / "src/plan_manage/include/plan_manage/seed_polyline_sampling.h"
    shutil.copy2(HERE / helper.name, helper)
    manager = OUT / "src/plan_manage/src/planner_manager.cpp"
    manager.write_bytes(b'#include <plan_manage/seed_polyline_sampling.h>\n' + manager.read_bytes())
    once(manager, '''    PolynomialTraj seed_trajectory;
    std::string seed_error;
    if (!makePiecewiseLinearTrajectory(seed_path, pp_.max_vel_, seed_trajectory, &seed_error)) {
      RCLCPP_WARN(node_->get_logger(), "reactive_stair_seed_invalid: %s", seed_error.c_str());
      continuous_failures_count_++;
      return false;
    }
    const size_t sample_count = std::max<size_t>(7, point_set.size());
    point_set.clear();
    for (size_t i = 0; i < sample_count; ++i) {
      const double u = static_cast<double>(i) / (sample_count - 1);
      const double progress = u * u * u * (10.0 - 15.0 * u + 6.0 * u * u);
      point_set.push_back(seed_trajectory.evaluate(progress * seed_trajectory.getTimeSum()));
    }
    point_set.front() = start_pt;
    point_set.back() = local_target_pt;''', '''    const double seed_duration = ts * (std::max<size_t>(7, point_set.size()) - 1);
    auto sampled_seed = reactive_stair::sampleSeedPolyline(seed_path, 0.5 * grid_map_->getResolution(), seed_duration, 512);
    if (!sampled_seed.ready()) {
      RCLCPP_WARN(node_->get_logger(), "reactive_stair_resample_invalid status=%d", static_cast<int>(sampled_seed.status));
      continuous_failures_count_++;
      return false;
    }
    size_t heading_fallback_edges = 0;
    for (size_t i = 1; i < sampled_seed.points.size(); ++i) {
      const auto& from = sampled_seed.points[i - 1];
      const auto& to = sampled_seed.points[i];
      if ((to - from).head<2>().squaredNorm() < 1e-4) ++heading_fallback_edges;
      int blocked_sample = -1;
      if (!grid_map_->collisionFreeSegment(from, to, &blocked_sample)) {
        RCLCPP_WARN(node_->get_logger(), "reactive_stair_resample_edge_blocked edge=%zu parent=%zu sample=%d yaw=%.12f from=(%.12f,%.12f,%.12f) to=(%.12f,%.12f,%.12f)",
                    i, sampled_seed.parent_edges[i - 1], blocked_sample, grid_map_->collisionSegmentYaw(from, to),
                    from.x(), from.y(), from.z(), to.x(), to.y(), to.z());
        continuous_failures_count_++;
        return false;
      }
    }
    ts = sampled_seed.interval_s;
    point_set = std::move(sampled_seed.points);
    RCLCPP_INFO(node_->get_logger(), "reactive_stair_resample_checked samples=%zu duration=%.12f interval=%.12f timing_capped=%d max_vertex_time_error=%.12f fallback_edges=%zu",
                point_set.size(), seed_duration, ts, sampled_seed.temporal_budget_capped,
                sampled_seed.max_vertex_time_error_s, heading_fallback_edges);''')
    (OUT / "seed_sampling_manifest.json").write_text(json.dumps({
        "base": "scan_25", "base_manifest_sha256": sha(BASE / "source_sha256.json"),
        "changed_sha256": {str(p.relative_to(OUT)): sha(p) for p in (helper, manager)},
        "generator_sha256": sha(Path(__file__)), "helper_sha256": sha(HERE / helper.name),
        "change": "Preserve every nonzero seed edge/vertex, bound point spacing by half voxel, recheck all generated edges under actual unchanged yaw/collision rules; retain total initialization duration with bounded lower-quota quintic vertex-time approximation.",
        "budget": "At most512 output points. Insufficient geometric budget fails closed; only temporal fidelity may be capped, with measured vertex-time error. Exact duplicates may collapse, nonzero short edges may not.",
        "preserved": "Original soft fitted PVA terms, optimizer objectives and dynamics, search, height/terrain/person/Unknown rules and full final spline gate. Smaller interval/more controls changes the discrete optimization problem; runtime cost and feasibility remain to be measured."}, indent=2) + "\n")
    print(OUT)


if __name__ == "__main__":
    main()
