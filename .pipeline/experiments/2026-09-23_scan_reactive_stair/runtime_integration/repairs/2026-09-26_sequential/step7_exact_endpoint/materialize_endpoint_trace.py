"""Observe the first rejected seed edge before/after endpoint replacement."""
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
    base = P2B / "builds/scan_24"
    out = P2B / "builds/scan24_endpoint_trace"
    if out.exists():
        raise FileExistsError(out)
    expected = json.loads((base / "source_sha256.json").read_text())
    actual = {"src/" + p.relative_to(base / "src").as_posix(): sha(p)
              for p in (base / "src").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if actual != expected or not json.loads((base / "build_result.json").read_text())["passed"]:
        raise ValueError("scan_24 source/build identity gate failed")
    shutil.copytree(base / "src", out / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    manager = out / "src/plan_manage/src/planner_manager.cpp"
    once(manager, "    seed_path.front() = start_pt;", "    const auto original_seed_path = seed_path;\n    seed_path.front() = start_pt;")
    anchor = '        RCLCPP_WARN(node_->get_logger(), "reactive_stair_seed_edge_blocked edge=%zu sample=%d", i, blocked_sample);'
    once(manager, anchor, anchor + '''
        static bool endpoint_trace_emitted = false;
        if (!endpoint_trace_emitted) {
          endpoint_trace_emitted = true;
          const auto &old_from = original_seed_path[i - 1];
          const auto &old_to = original_seed_path[i];
          const auto &from = seed_path[i - 1];
          const auto &to = seed_path[i];
          const double old_yaw = grid_map_->collisionSegmentYaw(old_from, old_to);
          const double new_yaw = grid_map_->collisionSegmentYaw(from, to);
          int original_blocked_sample = -1;
          // Read-only comparison after failure; it never changes acceptance.
          const bool original_clear = grid_map_->collisionFreeSegment(old_from, old_to, &original_blocked_sample);
          RCLCPP_WARN(node_->get_logger(), "ENDPOINT_TRACE nodes=%zu edge=%zu sample=%d last_edge=%d original_clear=%d original_sample=%d old_yaw=%.12f new_yaw=%.12f",
                      seed_path.size(), i, blocked_sample, i + 1 == seed_path.size(), original_clear,
                      original_blocked_sample, old_yaw, new_yaw);
          RCLCPP_WARN(node_->get_logger(), "ENDPOINT_TRACE old_from=(%.12f,%.12f,%.12f) old_to=(%.12f,%.12f,%.12f) new_from=(%.12f,%.12f,%.12f) new_to=(%.12f,%.12f,%.12f)",
                      old_from.x(), old_from.y(), old_from.z(), old_to.x(), old_to.y(), old_to.z(),
                      from.x(), from.y(), from.z(), to.x(), to.y(), to.z());
          for (size_t j = original_seed_path.size() > 3 ? original_seed_path.size() - 3 : 0;
               j < original_seed_path.size(); ++j) {
            const auto &p = original_seed_path[j];
            RCLCPP_WARN(node_->get_logger(), "ENDPOINT_TRACE original_tail index=%zu p=(%.12f,%.12f,%.12f)", j, p.x(), p.y(), p.z());
          }
          if (blocked_sample >= 0) {
            // The existing predicate only reports a sample after finite/bound checks.
            const int intervals = std::max(1, static_cast<int>(std::ceil((to - from).norm() / (0.5 * grid_map_->getResolution()))));
            const auto failed_point = from + (to - from) * (static_cast<double>(blocked_sample) / intervals);
            grid_map_->logInitialSplineCollision(failed_point, new_yaw);
          }
        }''')
    (out / "endpoint_trace_manifest.json").write_text(json.dumps({
        "base": "scan_24", "base_source_manifest_sha256": sha(base / "source_sha256.json"),
        "changed_sha256": {str(manager.relative_to(out)): sha(manager)},
        "generator_sha256": sha(Path(__file__)),
        "claim": "Diagnostic-only first rejected edge geometry and read-only old-edge/failed-footprint requery after rejection; unchanged acceptance, thresholds and trajectory logic. Extra logging/query cost is not a timing control."}, indent=2) + "\n")
    print(out)


if __name__ == "__main__":
    main()
