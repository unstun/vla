"""Seed the stair spline from a checked native 3D path at the actual start."""
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "builds/scan_18"
OUT = HERE.parent / "builds/scan_19"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace(path, old, new):
    source = path.read_bytes()
    if source.count(old) != 1:
        raise ValueError("anchor changed: " + repr(old[:70]))
    path.write_bytes(source.replace(old, new, 1))


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    expected = json.loads((BASE / "source_sha256.json").read_text())
    actual = {"src/" + p.relative_to(BASE / "src").as_posix(): sha(p)
              for p in (BASE / "src").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if expected != actual or json.loads((BASE / "build_result.json").read_text()).get("passed") is not True:
        raise ValueError("scan_18 source/build gate failed")
    shutil.copytree(BASE / "src", OUT / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    coords = OUT / "src/plan_env/include/plan_env/astar_grid_coordinates.h"
    astar_h = OUT / "src/path_searching/include/path_searching/dyn_a_star.h"
    astar_cpp = OUT / "src/path_searching/src/dyn_a_star.cpp"
    manager = OUT / "src/plan_manage/src/planner_manager.cpp"
    shutil.copy2(HERE / coords.name, coords)
    replace(astar_h, b'#include <plan_env/grid_map.h>',
            b'#include <plan_env/grid_map.h>\n#include <plan_env/astar_grid_coordinates.h>')
    replace(astar_h,
        b'\tidx = ((pt - center_) * inv_step_size_ + Eigen::Vector3d(0.5, 0.5, 0.5)).cast<int>() + CENTER_IDX_;',
        b'''    if (!pt.allFinite()) return false;
    for (int axis = 0; axis < 3; ++axis)
      idx(axis) = reactive_stair::nearestGridOffset((pt(axis) - center_(axis)) * inv_step_size_) + CENTER_IDX_(axis);''')
    replace(astar_cpp, b'    center_ = (start_pt + end_pt) / 2;',
        b'''    for (int axis = 0; axis < 3; ++axis)
      center_(axis) = reactive_stair::startAlignedSearchCenter(start_pt(axis), end_pt(axis), step_size_);''')
    seed = b'''    // A stair seed must come from the same current collision model as its
    // optimizer and final safety check. A single endpoint-height line is not
    // a supported stair profile. No fallback bypasses a failed graph search.
    auto seed_search = bspline_optimizer_rebound_->a_star_;
    const auto seed_status = seed_search->AstarSearch(grid_map_->getResolution(), start_pt, local_target_pt);
    if (seed_status != ASTAR_RET::SUCCESS) {
      RCLCPP_WARN(node_->get_logger(), "reactive_stair_seed_search_failed status=%d", static_cast<int>(seed_status));
      continuous_failures_count_++;
      return false;
    }
    std::vector<Eigen::Vector3d> seed_path = seed_search->getPath();
    if (seed_path.size() < 2 || (seed_path.front() - start_pt).norm() > 1e-6 ||
        (seed_path.back() - local_target_pt).norm() > grid_map_->getResolution()) {
      RCLCPP_WARN(node_->get_logger(), "reactive_stair_seed_endpoint_mismatch");
      continuous_failures_count_++;
      return false;
    }
    seed_path.front() = start_pt;
    seed_path.back() = local_target_pt;
    for (size_t i = 1; i < seed_path.size(); ++i) {
      const auto delta = seed_path[i] - seed_path[i - 1];
      const int count = std::max(1, static_cast<int>(std::ceil(delta.norm() / (0.5 * grid_map_->getResolution()))));
      const double yaw = grid_map_->collisionSegmentYaw(seed_path[i - 1], seed_path[i]);
      for (int j = 0; j <= count; ++j) {
        const Eigen::Vector3d sample = seed_path[i - 1] + delta * (static_cast<double>(j) / count);
        if (grid_map_->getInflateOccupancy(sample, yaw)) {
          RCLCPP_WARN(node_->get_logger(), "reactive_stair_seed_edge_blocked edge=%zu sample=%d", i, j);
          continuous_failures_count_++;
          return false;
        }
      }
    }
    PolynomialTraj seed_trajectory;
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
    point_set.back() = local_target_pt;
    start_end_derivatives = {start_vel, local_target_vel, start_acc, Eigen::Vector3d::Zero()};
    RCLCPP_INFO(node_->get_logger(), "reactive_stair_seed_checked nodes=%zu samples=%zu", seed_path.size(), point_set.size());'''
    replace(manager, b'    applyLinearZReference(point_set, start_pt(2), local_target_pt(2));', seed)
    source = manager.read_bytes()
    start = source.index(b'  namespace\r\n  {\r\n    void applyLinearZReference')
    end = source.index(b'  // SECTION interfaces', start)
    manager.write_bytes(source[:start] + source[end:])
    manifest = {"base": "scan_18", "base_manifest_sha256": sha(BASE / "source_sha256.json"),
                "changed_sha256": {str(p.relative_to(OUT)): sha(p) for p in (coords, astar_h, astar_cpp, manager)},
                "change": "Full native 3D path seed, half-cell edge validation, minimum-jerk arclength sampling, exact measured start lattice and correct signed rounding",
                "preserved": "original optimization.dist0=0.2 and cost weights, same hard collision rules, current tracks only, controller, native feasibility and final collision gates",
                "failure_policy": "No graph path, shifted endpoint or blocked seed edge returns failure; no straight-line or oracle fallback"}
    (OUT / "checked_path_seed_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()
