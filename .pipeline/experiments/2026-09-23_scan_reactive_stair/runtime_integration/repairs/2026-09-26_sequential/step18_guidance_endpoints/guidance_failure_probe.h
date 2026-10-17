#pragma once
#include <path_searching/dyn_a_star.h>
#include <bspline_opt/full_trajectory_collision.h>
#include <memory>

// Diagnostic build only. Capture failed guidance inputs without extra queries;
// all additional searches run after the original optimizer has returned false.
namespace guidance_failure_probe {
struct Failure {
  bool first_init;
  int begin_index, end_index;
  ASTAR_RET result;
  Eigen::Vector3d begin, end;
  Eigen::MatrixXd controls;
};
inline std::vector<Failure> failures;
inline bool emitted = false;
inline void beginAttempt() { if (!emitted) failures.clear(); }

inline void capture(bool first_init, int begin_index, int end_index,
                    const Eigen::Vector3d& begin, const Eigen::Vector3d& end,
                    ASTAR_RET result, const Eigen::MatrixXd& controls) {
  if (emitted) return;
  for (const auto& f : failures) if (f.first_init == first_init) return;
  failures.push_back({first_init, begin_index, end_index, result, begin, end, controls});
}

inline void observe(const GridMap::Ptr& map, const Eigen::MatrixXd& final_controls, double interval) {
  if (emitted || failures.empty()) return;
  emitted = true;
  scan_planner::UniformBspline curve(final_controls, 3, interval);
  const auto check = reactive_stair::checkFullCubicTrajectory(curve, 0.0, map->getResolution(),
      GridMap::collision_heading_lookahead_s,
      [&](const Eigen::Vector3d& p, const Eigen::Vector3d& ahead, const Eigen::Vector3d& v) {
        return map->collisionTrajectoryYaw(p, ahead, v);
      }, [&](const Eigen::Vector3d& p, double yaw) { return map->getInflateOccupancy(p, yaw) != 0; });
  RCLCPP_WARN(rclcpp::get_logger("guidance_probe"),
      "GUIDANCE_PROBE original_optimizer=false status=%d first_t=%.12f interval=%.12f controls=%ld failures=%zu",
      static_cast<int>(check.status), check.first_time_s, interval, final_controls.cols(), failures.size());
  // This is an independent diagnostic pool, never the optimizer's AStar state.
  auto search = std::make_unique<AStar>();
  search->initGridMap(map, Eigen::Vector3i(100, 100, 100));
  // Prefer the post-full-check retry, then report initial proxy failure.
  for (auto it = failures.rbegin(); it != failures.rend(); ++it) {
    const auto& f = *it;
    const double yaw = map->collisionSegmentYaw(f.begin, f.end);
    int blocked_sample = -1;
    const bool direct_clear = map->collisionFreeSegment(f.begin, f.end, &blocked_sample);
    const double delta = f.controls.rows() == final_controls.rows() && f.controls.cols() == final_controls.cols()
        ? (f.controls - final_controls).cwiseAbs().maxCoeff() : -1.0;
    RCLCPP_WARN(rclcpp::get_logger("guidance_probe"),
        "GUIDANCE_PROBE input first_init=%d indexes=%d,%d old_status=%d begin=(%.12f,%.12f,%.12f) end=(%.12f,%.12f,%.12f) yaw=%.12f direct_clear=%d blocked_sample=%d control_delta=%.17g",
        f.first_init, f.begin_index, f.end_index, static_cast<int>(f.result),
        f.begin.x(), f.begin.y(), f.begin.z(), f.end.x(), f.end.y(), f.end.z(),
        yaw, direct_clear, blocked_sample, delta);
    map->logInitialSplineCollision(f.begin, yaw);
    map->logInitialSplineCollision(f.end, yaw);
    const auto status = search->AstarSearch(map->getResolution(), f.begin, f.end, true);
    const auto path = search->getPath();
    bool all_edges_clear = status == SUCCESS && !path.empty();
    for (size_t i = 1; i < path.size(); ++i)
      if (!map->collisionFreeSegment(path[i - 1], path[i])) all_edges_clear = false;
    const double start_error = path.empty() ? -1.0 : (path.front() - f.begin).norm();
    const double end_error = path.empty() ? -1.0 : (path.back() - f.end).norm();
    RCLCPP_WARN(rclcpp::get_logger("guidance_probe"),
        "GUIDANCE_PROBE strict first_init=%d status=%d nodes=%zu all_edges_clear=%d start_error=%.12f end_error=%.12f original_result_unchanged=1",
        f.first_init, static_cast<int>(status), path.size(), all_edges_clear, start_error, end_error);
    for (size_t i = 0; i < path.size(); ++i)
      RCLCPP_WARN(rclcpp::get_logger("guidance_probe"), "GUIDANCE_PATH,%d,%zu,%.17g,%.17g,%.17g",
          f.first_init, i, path[i].x(), path[i].y(), path[i].z());
  }
}
}  // namespace guidance_failure_probe
