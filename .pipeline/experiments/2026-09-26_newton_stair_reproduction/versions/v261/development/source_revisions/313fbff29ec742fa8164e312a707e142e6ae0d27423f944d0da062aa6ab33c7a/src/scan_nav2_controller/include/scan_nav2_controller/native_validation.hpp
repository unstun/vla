#pragma once
#include <plan_env/grid_map.h>
#include <bspline_opt/full_trajectory_collision.h>
#include <string>
#include <cstdint>

namespace scan_nav2_controller {
struct NativeCurveValidation {
  bool clear{false};
  std::string status;
  int64_t traj_id{0};
  double observation_stamp_s{0.0};
  int64_t local_map_revision{0};
};
// Call under the controller owner lock. Geometry and timestamps are checked
// against an immutable revision, with caches private to this control tick.
inline NativeCurveValidation validateNativeCurve(
    const GridMap &map,const rclcpp::Clock::SharedPtr &clock,
    const geometry_msgs::msg::PoseStamped &body,scan_planner::UniformBspline curve,double phase) {
    NativeCurveValidation proof;
    auto lease=map.snapshotQuery(clock,body);
    if(!lease){proof.status="snapshot_unavailable";return proof;}
    auto &view=*lease->view;
    GridMap::RawContributorCacheScope cache(view);
    proof.observation_stamp_s=view.observationStamp();
    proof.local_map_revision=static_cast<int64_t>(view.mapRevision());
    const auto checked=reactive_stair::checkFullCubicTrajectory(
      curve,phase,view.getResolution(),GridMap::collision_heading_lookahead_s,
      [&view](const Eigen::Vector3d &p,const Eigen::Vector3d &ahead,const Eigen::Vector3d &velocity) {
        return view.collisionTrajectoryYaw(p,ahead,velocity);
      },[&view](const Eigen::Vector3d &p,double yaw){return view.getInflateOccupancy(p,yaw)!=0;});
    proof.clear=checked.clear() && view.mapperHealthy();
    if(!proof.clear)proof.status="native_curve status="+std::to_string(int(checked.status))+
      " phase="+std::to_string(phase)+" first="+std::to_string(checked.first_time_s)+" samples="+std::to_string(checked.samples);
    return proof;
}
} // namespace scan_nav2_controller
