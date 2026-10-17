// Included only by scan_06 grid_map.cpp after GridMap is defined.
// PCT selected ground cells are a static support map, not live obstacle truth.
// The LiDAR raycasting path remains unchanged; only the common collision query
// uses positively classified current LiDAR endpoints to waive terrain hits.
#include <cstdint>
#include <limits>
#include <pcl/point_types.h>
#include <plan_env/raw_return_classification.h>

void GridMap::reactiveTomogramCallback(sensor_msgs::msg::PointCloud2::ConstSharedPtr msg) {
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
  if (reactive_decision_.acceptTerrain(terrain)) reactive_terrain_ = std::move(terrain);
}

void GridMap::reactiveTracksCallback(
    scan_planner_msgs::msg::TrackedPersonSnapshot::ConstSharedPtr msg) {
  reactive_stair::TrackSnapshot snapshot;
  snapshot.frame = msg->header.frame_id;
  snapshot.stamp_s = rclcpp::Time(msg->header.stamp).seconds();
  snapshot.source_id = msg->source_id;
  snapshot.complete = msg->complete && snapshot.frame == mp_.frame_id_ && snapshot.stamp_s > 0.0;
  for (const auto &person : msg->tracks) {
    if (!std::isfinite(person.center.z)) snapshot.complete = false;
    snapshot.tracks.push_back({person.id, rclcpp::Time(person.observed_at).seconds(),
                               person.center.x, person.center.y, person.radius_m});
  }
  reactive_decision_.acceptTracks(snapshot);
}

bool GridMap::reactiveTerrainReturn(const Eigen::Vector3d &point) const {
  return reactive_stair::selectedGroundReturn(
      reactive_terrain_, point.x(), point.y(), point.z(), reactive_terrain_band_m_);
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
      // have a positively classified current terrain return. One unclassified
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
  return reactive_decision_.decide(query, obstacle) == reactive_stair::Verdict::Free ? 0 : 1;
}
