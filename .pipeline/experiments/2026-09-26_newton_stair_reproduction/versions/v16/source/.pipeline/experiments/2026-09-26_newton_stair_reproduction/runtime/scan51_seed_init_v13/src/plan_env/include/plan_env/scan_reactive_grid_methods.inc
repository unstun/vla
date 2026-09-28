// Included only by scan_06 grid_map.cpp after GridMap is defined.
// PCT selected ground cells are a static support map, not live obstacle truth.
// The LiDAR raycasting path remains unchanged; only the common collision query
// uses positively classified measured LiDAR endpoints to waive terrain hits.
#include <cstdint>
#include <limits>
#include <pcl/point_types.h>
#include <plan_env/raw_return_classification.h>
#include <plan_env/known_lite3_trunk.h>
#include <plan_env/motion_heading.h>

void GridMap::reactiveTomogramCallback(sensor_msgs::msg::PointCloud2::ConstSharedPtr msg) {
  reactive_ground_ = reactive_stair::TerrainSnapshot{};
  reactive_cloud_ready_ = false;
  reactive_pending_cloud_ = false;
  reactive_terrain_hits_.clear();
  reactive_nonterrain_hits_.clear();
  reactive_stair::TerrainSnapshot terrain;
  terrain.frame = msg->header.frame_id;
  terrain.stamp_s = rclcpp::Time(msg->header.stamp).seconds();
  terrain.resolution_m = reactive_tomogram_resolution_m_;
  if (terrain.frame != mp_.frame_id_ || !std::isfinite(terrain.stamp_s) ||
      terrain.stamp_s <= 0.0 || !std::isfinite(terrain.resolution_m) ||
      terrain.resolution_m <= 0.0 || !std::isfinite(reactive_tomogram_z_offset_m_) ||
      !std::isfinite(reactive_cost_limit_) || reactive_cost_limit_ < 0.0 ||
      !std::isfinite(reactive_terrain_band_m_) || reactive_terrain_band_m_ < 0.0) {
    reactive_decision_.acceptTerrain(terrain);
    return;
  }
  for (const char *field_name : {"x", "y", "z", "intensity"}) {
    bool found = false;
    for (const auto &field : msg->fields)
      if (field.name == field_name && field.datatype == sensor_msgs::msg::PointField::FLOAT32 &&
          field.count == 1) found = true;
    if (!found) {
      reactive_decision_.acceptTerrain(terrain);
      return;
    }
  }
  pcl::PointCloud<pcl::PointXYZI> points;
  pcl::fromROSMsg(*msg, points);
  double min_x = std::numeric_limits<double>::infinity();
  double min_y = std::numeric_limits<double>::infinity();
  for (const auto &point : points.points) {
    if (!std::isfinite(point.x) || !std::isfinite(point.y) || !std::isfinite(point.z) ||
        !std::isfinite(point.intensity) || point.intensity > reactive_cost_limit_) continue;
    min_x = std::min(min_x, static_cast<double>(point.x));
    min_y = std::min(min_y, static_cast<double>(point.y));
  }
  if (!std::isfinite(min_x) || !std::isfinite(min_y)) {
    reactive_decision_.acceptTerrain(terrain);
    return;
  }
  terrain.origin_x_m = min_x - terrain.resolution_m / 2.0;
  terrain.origin_y_m = min_y - terrain.resolution_m / 2.0;
  // A lightweight content identity ties this static version to the exact
  // delivered bytes. It is not a cryptographic source-file provenance hash.
  uint64_t fingerprint = UINT64_C(14695981039346656037);
  for (uint8_t value : msg->data) {
    fingerprint ^= value;
    fingerprint *= UINT64_C(1099511628211);
  }
  terrain.source_id = "pct_tomogram/fnv64/" + std::to_string(fingerprint);
  for (const auto &point : points.points) {
    if (!std::isfinite(point.x) || !std::isfinite(point.y) || !std::isfinite(point.z) ||
        !std::isfinite(point.intensity) || point.intensity > reactive_cost_limit_) continue;
    const double ix = std::floor((point.x - terrain.origin_x_m) / terrain.resolution_m);
    const double iy = std::floor((point.y - terrain.origin_y_m) / terrain.resolution_m);
    if (ix < std::numeric_limits<int>::min() || ix > std::numeric_limits<int>::max() ||
        iy < std::numeric_limits<int>::min() || iy > std::numeric_limits<int>::max()) continue;
    // "Stair" here means a selected supported PCT cell; the topic carries no
    // flat-vs-stair semantic label. Multiple heights at one XY are retained.
    terrain.cells[{static_cast<int>(ix), static_cast<int>(iy)}].push_back(
        {reactive_stair::Support::Stair, point.z - reactive_tomogram_z_offset_m_});
  }
  reactive_stair::StepScoreResult scored =
      reactive_stair::precomputeEthStyleStepScores(terrain);
  if (reactive_decision_.acceptTerrain(scored.support)) {
    reactive_ground_ = terrain; // Preserve source elevations independently of step scores.
    reactive_terrain_ = scored.support;
    reactive_step_result_ = std::move(scored);
  }
}

bool GridMap::reactiveTerrainReturn(const Eigen::Vector3d &point) const {
  return reactive_stair::selectedGroundReturn(
      reactive_ground_, point.x(), point.y(), point.z(), reactive_terrain_band_m_);
}

int GridMap::reactiveOccupancy(const Eigen::Vector3d &point) {
  if (!point.allFinite()) return 1;
  const double radius = mp_.double_cylinder_radius_;
  if (!std::isfinite(radius) || radius < 0.0 ||
      point.x() - radius < mp_.map_min_boundary_.x() ||
      point.x() + radius > mp_.map_max_boundary_.x() ||
      point.y() - radius < mp_.map_min_boundary_.y() ||
      point.y() + radius > mp_.map_max_boundary_.y() ||
      point.z() - mp_.obstacles_inflation_z_down < mp_.map_min_boundary_.z() ||
      point.z() + mp_.obstacles_inflation_z_up > mp_.map_max_boundary_.z()) return 1;
  reactive_stair::Query query;
  query.frame = mp_.frame_id_;
  query.stamp_s = node_->now().seconds();
  query.x_m = point.x(); query.y_m = point.y(); query.z_m = point.z();
  query.in_map = isInMap(point);
  reactive_stair::NonTerrainVoxel obstacle;
  obstacle.frame = mp_.frame_id_;
  obstacle.stamp_s = reactive_cloud_stamp_s_;
  if (reactive_cloud_ready_) obstacle.source_id = "scan_lidar_cloud";
  if (query.in_map) {
    Eigen::Vector3i query_id;
    posToIndex(point, query_id);
    const int address = toAddress(query_id);
    if (md_.occupancy_buffer_[address] < mp_.clamp_min_log_ - 1e-3) {
      obstacle.occupancy = reactive_stair::Occupancy::Unknown;
    } else if (md_.occupancy_buffer_inflate_[address] == 0) {
      obstacle.occupancy = reactive_stair::Occupancy::Free;
    } else {
      // Every raw occupied source contributing to SCAN's inflated hit must
      // have a retained, positively observed terrain classification. One unclassified
      // return, even at a supported XY, keeps the result occupied.
      bool contributor = false;
      bool unclassified = false;
      for (const auto &offset : md_.inflate_offsets_) {
        const Eigen::Vector3i source = query_id - offset;
        if (!isInMap(source) || md_.occupancy_buffer_[toAddress(source)] <= mp_.min_occupancy_log_)
          continue;
        contributor = true;
        const auto key = std::make_tuple(source.x(), source.y(), source.z());
        if (!reactive_stair::mayWaiveRawContributor(
                reactive_terrain_hits_.count(key) != 0,
                reactive_nonterrain_hits_.count(key) != 0,
                reactive_nonterrain_history_.count(key) != 0)) {
          unclassified = true;
          break;
        }
      }
      obstacle.occupancy = !contributor ? reactive_stair::Occupancy::Unknown :
          (unclassified ? reactive_stair::Occupancy::Occupied : reactive_stair::Occupancy::Free);
    }
  }
  if (reactive_known_trunk_enabled_ && query.in_map && reactive_body_stamp_s_ > 0.0) {
    Eigen::Vector3i id;
    posToIndex(point, id);
    Eigen::Vector3d cell_center;
    indexToPos(id, cell_center);
    const Eigen::Vector3d local = reactive_body_quaternion_.conjugate() *
                                 (cell_center - md_.sliding_map_frame_pos_);
    const bool inside = reactive_stair::knownNavigationFootprintInterior(
        local.x(), local.y(), local.z(), query.stamp_s, reactive_body_stamp_s_,
        mp_.double_cylinder_radius_, mp_.double_cylinder_offset_);
    obstacle.occupancy = reactive_stair::measuredTrunkQuery(
        obstacle.occupancy, md_.occupancy_buffer_inflate_[toAddress(id)] != 0, inside);
  }
  const auto verdict = reactive_decision_.decide(query, obstacle);
  static std::set<std::tuple<int, int, int>> diagnosed;
  Eigen::Vector3i diagnostic_id;
  posToIndex(point, diagnostic_id);
  const auto diagnostic_key = std::make_tuple(diagnostic_id.x(), diagnostic_id.y(), diagnostic_id.z());
  if (query.in_map && (reactive_diagnostic_force_ || ((point - md_.ray_pos_).norm() < 0.8 &&
      diagnosed.size() < 120 && diagnosed.insert(diagnostic_key).second))) {
    const int diagnostic_address = toAddress(diagnostic_id);
    RCLCPP_WARN(node_->get_logger(),
        "near_sensor_verdict verdict=%d voxel=%d q=(%.5f,%.5f,%.5f) sensor=(%.5f,%.5f,%.5f) log_odds=%.5f inflation=%d stamp=%.3f",
        static_cast<int>(verdict), static_cast<int>(obstacle.occupancy),
        point.x(), point.y(), point.z(), md_.ray_pos_.x(), md_.ray_pos_.y(), md_.ray_pos_.z(),
        md_.occupancy_buffer_[diagnostic_address], static_cast<int>(md_.occupancy_buffer_inflate_[diagnostic_address]), query.stamp_s);
  }
  if (verdict != reactive_stair::Verdict::Free) {
    RCLCPP_WARN_THROTTLE(node_->get_logger(), *node_->get_clock(), 1000,
        "reactive_collision_blocked verdict=%d voxel=%d q=(%.3f,%.3f,%.3f) now=%.3f cloud_stamp=%.3f cloud_ready=%d terrain_cells=%zu body_clearance=%.3f",
        static_cast<int>(verdict), static_cast<int>(obstacle.occupancy),
        query.x_m, query.y_m, query.z_m, query.stamp_s, obstacle.stamp_s,
        reactive_cloud_ready_, reactive_terrain_.cells.size(), reactive_parameters_.body_clearance_m);
  }
  return verdict == reactive_stair::Verdict::Free ? 0 : 1;
}

void GridMap::logInitialSplineCollision(const Eigen::Vector3d &pos, double yaw) {
  RCLCPP_WARN(node_->get_logger(),
      "initial_spline_collision pos=(%.8f,%.8f,%.8f) yaw=%.8f body=(%.8f,%.8f,%.8f) body_q=(%.8f,%.8f,%.8f,%.8f) body_stamp=%.8f now=%.8f",
      pos.x(), pos.y(), pos.z(), yaw,
      md_.sliding_map_frame_pos_.x(), md_.sliding_map_frame_pos_.y(), md_.sliding_map_frame_pos_.z(),
      reactive_body_quaternion_.w(), reactive_body_quaternion_.x(), reactive_body_quaternion_.y(), reactive_body_quaternion_.z(),
      reactive_body_stamp_s_, node_->now().seconds());
  const Eigen::Vector3d heading(std::cos(yaw), std::sin(yaw), 0.0);
  reactive_diagnostic_force_ = true;
  reactiveOccupancy(pos + mp_.double_cylinder_offset_ * heading);
  reactiveOccupancy(pos - mp_.double_cylinder_offset_ * heading);
  reactive_diagnostic_force_ = false;
}

double GridMap::collisionSegmentYaw(const Eigen::Vector3d &from, const Eigen::Vector3d &to) const {
  const Eigen::Vector3d direction = reactive_body_quaternion_.toRotationMatrix().col(0);
  const double body_yaw = std::atan2(direction.y(), direction.x());
  return reactive_stair::motionHeading(to.x() - from.x(), to.y() - from.y(), body_yaw,
                                      node_->now().seconds(), reactive_body_stamp_s_);
}

bool GridMap::collisionFreeSegment(const Eigen::Vector3d &from, const Eigen::Vector3d &to,
                                   int *blocked_sample) {
  return reactive_stair::collisionFreeSegment(from, to, getResolution(), collisionSegmentYaw(from, to),
      [this](const Eigen::Vector3d &point, double yaw) { return getInflateOccupancy(point, yaw); },
      blocked_sample);
}

double GridMap::collisionTrajectoryYaw(const Eigen::Vector3d &from, const Eigen::Vector3d &ahead,
                                       const Eigen::Vector3d &velocity) const {
  if (!from.allFinite() || !ahead.allFinite() || !velocity.allFinite())
    return std::numeric_limits<double>::quiet_NaN();
  if ((ahead - from).head<2>().squaredNorm() < 1e-4)
    return collisionSegmentYaw(Eigen::Vector3d::Zero(), velocity);
  return collisionSegmentYaw(from, ahead);
}
