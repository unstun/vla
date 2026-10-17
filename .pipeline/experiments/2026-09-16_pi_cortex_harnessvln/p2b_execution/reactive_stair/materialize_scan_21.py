"""Make A* and seed validation share the existing half-cell segment gate."""
import json
from pathlib import Path
import shutil

from materialize_scan_20 import once, sha

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "builds/scan_20"
OUT = HERE.parent / "builds/scan_21"


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    expected = json.loads((BASE / "source_sha256.json").read_text())
    actual = {"src/" + p.relative_to(BASE / "src").as_posix(): sha(p)
              for p in (BASE / "src").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if actual != expected or json.loads((BASE / "build_result.json").read_text()).get("passed") is not True:
        raise ValueError("scan_20 source/build identity gate failed")
    shutil.copytree(BASE / "src", OUT / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    helper = OUT / "src/plan_env/include/plan_env/collision_segment.h"
    header = OUT / "src/plan_env/include/plan_env/grid_map.h"
    methods = OUT / "src/plan_env/include/plan_env/scan_reactive_grid_methods.inc"
    astar = OUT / "src/path_searching/src/dyn_a_star.cpp"
    manager = OUT / "src/plan_manage/src/planner_manager.cpp"
    shutil.copy2(HERE / "collision_segment.h", helper)
    once(header, "#include <plan_env/reactive_collision.h>",
         "#include <plan_env/reactive_collision.h>\n#include <plan_env/collision_segment.h>")
    once(header, "  double collisionSegmentYaw(const Eigen::Vector3d &from, const Eigen::Vector3d &to) const;",
         "  double collisionSegmentYaw(const Eigen::Vector3d &from, const Eigen::Vector3d &to) const;\n"
         "  bool collisionFreeSegment(const Eigen::Vector3d &from, const Eigen::Vector3d &to,\n"
         "                            int *blocked_sample = nullptr);")
    once(methods, "double GridMap::collisionTrajectoryYaw", '''bool GridMap::collisionFreeSegment(const Eigen::Vector3d &from, const Eigen::Vector3d &to,
                                   int *blocked_sample) {
  return reactive_stair::collisionFreeSegment(from, to, getResolution(), collisionSegmentYaw(from, to),
      [this](const Eigen::Vector3d &point, double yaw) { return getInflateOccupancy(point, yaw); },
      blocked_sample);
}

double GridMap::collisionTrajectoryYaw''')
    once(astar, '''                const double neighbor_yaw = (dx == 0 && dy == 0)
                    ? std::atan2(end_pt.y() - start_pt.y(), end_pt.x() - start_pt.x())
                    : std::atan2(static_cast<double>(dy), static_cast<double>(dx));
                if (checkOccupancy(Index2Coord(neighborPtr->index), neighbor_yaw))''',
         '''                if (!grid_map_->collisionFreeSegment(Index2Coord(current->index),
                                                     Index2Coord(neighborPtr->index)))''')
    once(manager, '''      const auto delta = seed_path[i] - seed_path[i - 1];
      const int count = std::max(1, static_cast<int>(std::ceil(delta.norm() / (0.5 * grid_map_->getResolution()))));
      const double yaw = grid_map_->collisionSegmentYaw(seed_path[i - 1], seed_path[i]);
      for (int j = 0; j <= count; ++j) {
        const Eigen::Vector3d sample = seed_path[i - 1] + delta * (static_cast<double>(j) / count);
        if (grid_map_->getInflateOccupancy(sample, yaw)) {
          RCLCPP_WARN(node_->get_logger(), "reactive_stair_seed_edge_blocked edge=%zu sample=%d", i, j);
          continuous_failures_count_++;
          return false;
        }
      }''', '''      int blocked_sample = -1;
      if (!grid_map_->collisionFreeSegment(seed_path[i - 1], seed_path[i], &blocked_sample)) {
        RCLCPP_WARN(node_->get_logger(), "reactive_stair_seed_edge_blocked edge=%zu sample=%d", i, blocked_sample);
        continuous_failures_count_++;
        return false;
      }''')
    manifest = {"base": "scan_20", "base_manifest_sha256": sha(BASE / "source_sha256.json"),
                "changed_sha256": {str(p.relative_to(OUT)): sha(p) for p in (helper, header, methods, astar, manager)},
                "change": "Search evaluates exactly the shared seed segment predicate, including both endpoints and <=half-cell samples with collisionSegmentYaw",
                "preserved": "Occupancy/source/track/support thresholds, grid resolution, unknown/out-of-map blocking, heuristic, time cap, final spline and controller gates",
                "generator_sha256": sha(Path(__file__))}
    (OUT / "segment_gate_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(OUT)


if __name__ == "__main__":
    main()
