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

reactive_stair::TerrainSnapshot GridMap::decodeReactiveGround(sensor_msgs::msg::PointCloud2::ConstSharedPtr msg) const {
  reactive_stair::TerrainSnapshot terrain;
  terrain.frame = msg->header.frame_id;
  terrain.stamp_s = rclcpp::Time(msg->header.stamp).seconds();
  terrain.resolution_m = reactive_tomogram_resolution_m_;
  if (terrain.frame != mp_.frame_id_ || !std::isfinite(terrain.stamp_s) ||
      terrain.stamp_s <= 0.0 || !std::isfinite(terrain.resolution_m) ||
      terrain.resolution_m <= 0.0 || !std::isfinite(reactive_tomogram_z_offset_m_) ||
      !std::isfinite(reactive_cost_limit_) || reactive_cost_limit_ < 0.0 ||
      !std::isfinite(reactive_terrain_band_m_) || reactive_terrain_band_m_ < 0.0) {
    return {};
  }
  // Exact existing publisher layout; reject malformed metadata before PCL.
  if (msg->height != 1 || msg->width == 0 || msg->is_bigendian ||
      msg->point_step != 16 || msg->fields.size() != 4 ||
      uint64_t(msg->width) * 16 != msg->row_step ||
      uint64_t(msg->row_step) != msg->data.size()) return {};
  uint32_t expected_offset = 0;
  for (const char *field_name : {"x", "y", "z", "intensity"}) {
    bool found = false;
    for (const auto &field : msg->fields)
      if (field.name == field_name && field.datatype == sensor_msgs::msg::PointField::FLOAT32 &&
          field.count == 1 && field.offset == expected_offset) found = true;
    if (!found) {
      return {};
    }
    expected_offset += 4;
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
    return {};
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
  return terrain;
}

reactive_stair::TerrainSnapshot GridMap::supportGround(const reactive_stair::TerrainSnapshot &navigation) {
  // v34: PCT's navigation ground is inflated; the surface evidence is its
  // uninflated selection. Add the evidence floor that the navigation ground lacks,
  // except beside drops (audits/2026-09-29_corridor_entry, versions/v34/PLAN.md).
  reactive_stair::EvidenceFloorFill fill;
  auto ground = reactive_stair::addGuardedEvidenceFloor(navigation, &reactive_surface_ground_,
      reactive_parameters_.body_height_tolerance_m, reactive_stair::StepScoreParameters{}.critical_height_m,
      mp_.double_cylinder_radius_, &fill);
  size_t layers = 0;
  for (const auto &entry : navigation.cells) layers += entry.second.size();
  RCLCPP_INFO(node_->get_logger(),
      "evidence_floor_fill evidence_used=%d navigation_layers=%zu added=%zu drop_rejected=%zu",
      fill.evidence_used ? 1 : 0, layers, fill.added, fill.drop_rejected);
  return ground;
}

void GridMap::reactiveTomogramCallback(sensor_msgs::msg::PointCloud2::ConstSharedPtr msg) {
  invalidateRawContributorCache();
  reactive_ground_ = reactive_stair::TerrainSnapshot{};
  reactive_cloud_ready_ = false;
  reactive_pending_cloud_ = false;
  reactive_terrain_hits_.clear();
  auto terrain = decodeReactiveGround(msg);
  // v34: keep the navigation ground as decoded, and give SCAN's copy the guarded
  // evidence floor. An invalid ground passes unchanged.
  reactive_navigation_ground_ = terrain;
  terrain = supportGround(terrain);
  if (terrain.cells.empty()) {
    reactive_decision_.acceptTerrain(terrain);
    return;
  }
  // The surface evidence decides whether a neighbour without this level is a drop.
  reactive_stair::StepScoreResult scored =
      reactive_stair::precomputeEthStyleStepScores(terrain, {}, &reactive_surface_ground_);
  if (reactive_decision_.acceptTerrain(scored.support)) {
    reactive_ground_ = terrain; // Preserve source elevations independently of step scores.
    reactive_terrain_ = scored.support;
    reactive_step_result_ = std::move(scored);
  }
}

void GridMap::reactiveSurfaceGroundCallback(sensor_msgs::msg::PointCloud2::ConstSharedPtr msg) {
  invalidateRawContributorCache();
  reactive_surface_ground_ = decodeReactiveGround(msg);
  // A changed source must not retain positive labels from an older source.
  // Historical nonterrain evidence remains conservative and is not cleared.
  reactive_terrain_hits_.clear();
  reactive_cloud_ready_ = false;
  reactive_pending_cloud_ = false;
  // The step score consults this evidence, so rescore the accepted navigation
  // ground. Unusable evidence scores exactly as without evidence.
  // v34: re-augment the navigation ground as decoded with this evidence, so the
  // result does not depend on which message arrived first.
  if (!reactive_ground_.cells.empty()) reactive_ground_ = supportGround(reactive_navigation_ground_);
  if (!reactive_ground_.cells.empty()) {
    reactive_stair::StepScoreResult scored = reactive_stair::precomputeEthStyleStepScores(
        reactive_ground_, {}, &reactive_surface_ground_);
    if (reactive_decision_.acceptTerrain(scored.support)) {
      reactive_terrain_ = scored.support;
      reactive_step_result_ = std::move(scored);
    }
  }
}

bool GridMap::reactiveSurfaceGroundReady() const {
  if (reactive_surface_ground_topic_.empty()) return true;
  const double now = node_->now().seconds();
  const auto fresh = [&](const reactive_stair::TerrainSnapshot &surface) {
    return !surface.cells.empty() && surface.frame == mp_.frame_id_ &&
        std::isfinite(surface.stamp_s) && surface.stamp_s > 0.0 &&
        surface.stamp_s <= now && now - surface.stamp_s <= reactive_parameters_.terrain_max_age_s;
  };
  return fresh(reactive_ground_) && fresh(reactive_surface_ground_);
}

bool GridMap::reactiveTerrainReturn(const Eigen::Vector3d &point) const {
  if (!reactiveSurfaceGroundReady()) return false;
  // A configured source replaces the classification evidence, not navigation support.
  const auto &evidence = reactive_surface_ground_topic_.empty()
      ? reactive_ground_ : reactive_surface_ground_;
  return reactive_stair::selectedGroundReturn(evidence,
      point.x(), point.y(), point.z(), reactive_terrain_band_m_);
}

GridMap::TerrainCellLayers GridMap::terrainCellLayers(const reactive_stair::Cell2 &cell) {
  // Unsigned packing preserves every signed int32 XY pair, including negatives.
  const std::uint64_t key = (static_cast<std::uint64_t>(static_cast<std::uint32_t>(cell.x)) << 32) |
      static_cast<std::uint32_t>(cell.y);
  const bool cache = raw_contributor_cache_active_ && terrain_cell_cache_enabled_;
  if (cache) {
    const auto found = terrain_cell_cache_.find(key);
    if (found != terrain_cell_cache_.end()) {
      ++terrain_cell_cache_hits_;
      return found->second;
    }
  }
  TerrainCellLayers layers;
  const auto raw = reactive_ground_.cells.find(cell);
  const auto scored = reactive_terrain_.cells.find(cell);
  if (raw != reactive_ground_.cells.end()) layers.raw = &raw->second;
  if (scored != reactive_terrain_.cells.end()) layers.scored = &scored->second;
  if (cache) {
    ++terrain_cell_cache_evaluations_;
    if (terrain_cell_cache_.size() < terrain_cell_cache_capacity_)
      terrain_cell_cache_.emplace(key, layers);
  }
  return layers;
}

bool GridMap::reactiveFootprintSupportQuery(const Eigen::Vector3d &body_reference,
    const reactive_stair::NonTerrainVoxel &obstacle, reactive_stair::Query &query) {
  if (!body_reference.allFinite()) return false;
  const auto &raw = reactive_ground_;
  const auto &scored = reactive_terrain_;
  if (raw.source_id != scored.source_id || raw.frame != scored.frame ||
      raw.resolution_m != scored.resolution_m || raw.origin_x_m != scored.origin_x_m ||
      raw.origin_y_m != scored.origin_y_m) return false;
  auto body_query = query;
  body_query.x_m = body_reference.x();
  body_query.y_m = body_reference.y();
  body_query.z_m = body_reference.z();
  body_query.in_map = isInMap(body_reference);
  // This copy checks terrain support only. The original measured obstacle
  // still controls the final footprint verdict at the original physical XYZ.
  auto support_only = obstacle;
  support_only.occupancy = reactive_stair::Occupancy::Free;
  if (reactive_decision_.decide(body_query, support_only) != reactive_stair::Verdict::Free)
    return false;
  const auto associated_height = [&](double x, double y, double target, double limit, double &height) {
    const double ix = std::floor((x - raw.origin_x_m) / raw.resolution_m);
    const double iy = std::floor((y - raw.origin_y_m) / raw.resolution_m);
    if (!std::isfinite(ix) || !std::isfinite(iy) ||
        ix < std::numeric_limits<int>::min() || ix > std::numeric_limits<int>::max() ||
        iy < std::numeric_limits<int>::min() || iy > std::numeric_limits<int>::max()) return false;
    const reactive_stair::Cell2 cell{static_cast<int>(ix), static_cast<int>(iy)};
    const auto layers = terrainCellLayers(cell);
    if (!layers.raw || !layers.scored || layers.raw->size() != layers.scored->size()) return false;
    // Associate before considering scored status. Never skip an unknown or
    // unsupported nearest layer in favor of a farther supported floor.
    const int layer = reactive_stair::nearestSurface(*layers.raw, target, limit);
    if (layer < 0) return false;
    const auto &surface = (*layers.scored)[layer];
    if (surface.elevation_m != (*layers.raw)[layer].elevation_m ||
        !reactive_stair::selectedSurface(surface)) return false;
    height = surface.elevation_m;
    return true;
  };
  double body_ground, footprint_ground;
  const double step = reactive_stair::StepScoreParameters{}.critical_height_m;
  if (!associated_height(body_query.x_m, body_query.y_m,
          body_query.z_m - reactive_parameters_.body_clearance_m,
          reactive_parameters_.body_height_tolerance_m, body_ground) ||
      !associated_height(query.x_m, query.y_m, body_ground, step, footprint_ground) ||
      std::abs(footprint_ground - body_ground) >= step) return false;
  // Only the support-layer height changes; do not move the robot, spline,
  // obstacle query, map-boundary query or retained measured LiDAR evidence.
  query.z_m = footprint_ground + reactive_parameters_.body_clearance_m;
  return true;
}

reactive_stair::Occupancy GridMap::rawContributorOccupancy(const Eigen::Vector3i &id) {
  if (!isInMap(id)) return reactive_stair::Occupancy::Unknown;
  const int address = toAddress(id);
  if (raw_contributor_cache_active_) {
    const auto cached = raw_contributor_cache_.find(address);
    if (cached != raw_contributor_cache_.end()) {
      ++raw_contributor_cache_hits_;
      return cached->second;
    }
  }
      // Every raw occupied source contributing to SCAN's inflated hit must
      // have a retained, positively observed terrain classification. One unclassified
      // return, even at a supported XY, keeps the result occupied.
      bool contributor = false;
      bool unclassified = false;
      for (const auto &offset : md_.inflate_offsets_) {
        const Eigen::Vector3i source = id - offset;
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
      const auto result = !contributor ? reactive_stair::Occupancy::Unknown :
          (unclassified ? reactive_stair::Occupancy::Occupied : reactive_stair::Occupancy::Free);
  if (raw_contributor_cache_active_) {
    ++raw_contributor_cache_evaluations_;
    raw_contributor_cache_.emplace(address, result);
  }
  return result;
}

int GridMap::reactiveOccupancy(const Eigen::Vector3d &point, const Eigen::Vector3d *body_reference) {
  if (!reactiveSurfaceGroundReady()) return 1;
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
      obstacle.occupancy = rawContributorOccupancy(query_id);
    }
  }
  if (reactive_known_trunk_enabled_ && query.in_map && reactive_body_stamp_s_ > 0.0) {
    Eigen::Vector3i id;
    posToIndex(point, id);
    // Test the queried point, not its voxel centre, so the waiver does not
    // depend on how the grid aligns with the body height.
    const Eigen::Vector3d local = reactive_body_quaternion_.conjugate() *
                                 (point - md_.sliding_map_frame_pos_);
    const bool inside = reactive_stair::knownNavigationFootprintInterior(
        local.x(), local.y(), local.z(), query.stamp_s, reactive_body_stamp_s_,
        mp_.double_cylinder_radius_, mp_.double_cylinder_offset_);
    obstacle.occupancy = reactive_stair::measuredTrunkQuery(
        obstacle.occupancy, md_.occupancy_buffer_inflate_[toAddress(id)] != 0, inside);
  }
  if (body_reference && !reactiveFootprintSupportQuery(*body_reference, obstacle, query)) return 1;
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
        "reactive_collision_blocked verdict=%d voxel=%d q=(%.3f,%.3f,%.3f) support_z=%.3f now=%.3f cloud_stamp=%.3f cloud_ready=%d terrain_cells=%zu body_clearance=%.3f",
        static_cast<int>(verdict), static_cast<int>(obstacle.occupancy),
        point.x(), point.y(), point.z(), query.z_m, query.stamp_s, obstacle.stamp_s,
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
  reactiveOccupancy(pos + mp_.double_cylinder_offset_ * heading, &pos);
  reactiveOccupancy(pos - mp_.double_cylinder_offset_ * heading, &pos);
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
