#include <plan_env/grid_map.h>
#include <rcl/time.h>
#include <openssl/sha.h>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include "map_meter.h"
namespace fs = std::filesystem;
#include "recorded_readers.h"

std::string map_digest(const GridMap &map) {
  SHA256_CTX context;
  SHA256_Init(&context);
  const auto vector_bytes = [&](const auto &v) {
    if (!v.empty()) SHA256_Update(&context, v.data(), v.size() * sizeof(v[0]));
  };
  vector_bytes(map.md_.occupancy_buffer_);
  vector_bytes(map.md_.occupancy_buffer_inflate_);
  vector_bytes(map.md_.occupancy_buffer_inflate_cnt_);
  vector_bytes(map.md_.count_hit_);
  vector_bytes(map.md_.count_hit_and_miss_);
  vector_bytes(map.md_.flag_rayend_);
  vector_bytes(map.md_.flag_traverse_);
  SHA256_Update(&context, map.mp_.map_origin_idx_.data(), 3 * sizeof(int));
  SHA256_Update(&context, &map.md_.raycast_num_, sizeof(map.md_.raycast_num_));
  for (const auto *set : {&map.reactive_terrain_hits_, &map.reactive_nonterrain_hits_, &map.reactive_nonterrain_history_}) {
    std::vector<std::tuple<int,int,int>> keys(set->begin(), set->end());
    std::sort(keys.begin(), keys.end());
    for (const auto &key : keys) {
      const int values[] = {std::get<0>(key), std::get<1>(key), std::get<2>(key)};
      SHA256_Update(&context, values, sizeof(values));
    }
    const auto size = set->size();
    SHA256_Update(&context, &size, sizeof(size));
  }
  unsigned char hash[SHA256_DIGEST_LENGTH];
  SHA256_Final(hash, &context);
  std::ostringstream text;
  for (auto c : hash) text << std::hex << std::setw(2) << std::setfill('0') << unsigned(c);
  return text.str();
}

int main(int argc, char **argv) {
  const fs::path input(std::getenv("V80_INPUT"));
  const fs::path output(std::getenv("V80_OUTPUT"));
  rclcpp::init(argc, argv);
  auto node = std::make_shared<rclcpp::Node>("scan_planner_node");
  GridMap map;
  map.initMap(node.get());
  map.occ_timer_->cancel();
  map.vis_timer_->cancel();
  const auto clock = [&](int64_t ns) {
    auto handle = node->get_clock()->get_clock_handle();
    if (rcl_enable_ros_time_override(handle) != RCL_RET_OK ||
        rcl_set_ros_time_override(handle, ns) != RCL_RET_OK) throw std::runtime_error("Clock override failed");
  };
  clock(1000000000);
  auto nav = std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input / "navigation.f32", true));
  auto surface = std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input / "surface.f32", true));
  auto physical = std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input / "physical_floor.f32", true));
  nav->header.stamp = surface->header.stamp = physical->header.stamp = rclcpp::Time(1000000000LL, RCL_ROS_TIME);
  map.reactiveTomogramCallback(nav);
  map.reactiveSurfaceGroundCallback(surface);
  map.reactivePhysicalFloorCallback(physical);
  if (!map.reactiveSurfaceGroundReady()) throw std::runtime_error("Original paired support inputs are not ready");
  std::ifstream list(input / "scans.txt");
  std::ofstream rows(output);
  rows << std::setprecision(15);
  int index, scans = 0;
  int64_t ns;
  std::string body_name, sensor_name, cloud_name;
  if (std::getenv("V80_SYNTHETIC")) {
    // Exercise occupied/free transitions, inflation overlap, ignored outgoing
    // cells, ring wrapping, multiaxis and full-grid displacement.
    for (int phase = 0; phase < 14; ++phase) {
      for (int k = 0; k < 200; ++k) {
        Eigen::Vector3i id = map.mp_.map_bound_min_idx_ + Eigen::Vector3i(
            (k * 37 + phase) % map.mp_.map_voxel_num_.x(),
            (k * 17 + phase * 3) % map.mp_.map_voxel_num_.y(),
            (k * 11 + phase * 7) % map.mp_.map_voxel_num_.z());
        map.applyOccupancyUpdate(id, map.mp_.clamp_max_log_);
        const auto key = std::make_tuple(id.x(),id.y(),id.z());
        map.reactive_terrain_hits_.insert(key);
        map.reactive_nonterrain_history_.insert(key);
        if (k % 3 == 0) map.applyOccupancyUpdate(id, map.mp_.clamp_min_log_);
      }
      const Eigen::Vector3d shift = phase == 12 ? Eigen::Vector3d(11,-11,6) :
          Eigen::Vector3d(phase % 2 ? -.31 : .29, phase % 3 ? .27 : -.26, phase % 4 ? 0 : .23);
      Eigen::Vector3d center;
      map.indexToPos(map.mp_.map_origin_idx_,center);
      map.updateSlidingMap(center + shift);
      rows << "{\"phase\":" << phase << ",\"state_sha256\":\"" << map_digest(map) << "\"}\n";
    }
    std::cout << "V80_SYNTHETIC_PASS" << std::endl;
    rclcpp::shutdown();
    return 0;
  }
  while (list >> index >> ns >> body_name >> sensor_name >> cloud_name) {
    clock(ns);
    auto body = std::make_shared<nav_msgs::msg::Odometry>(read_pose(input / body_name));
    auto sensor = std::make_shared<nav_msgs::msg::Odometry>(read_pose(input / sensor_name));
    body->header.stamp = sensor->header.stamp = rclcpp::Time(ns, RCL_ROS_TIME);
    auto cloud = std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input / cloud_name, false));
    cloud->header.stamp = rclcpp::Time(ns, RCL_ROS_TIME);
    const auto before = map_meter::meter;
    const auto native_before = map.planning_profile_.values;
    const auto origin_before = map.mp_.map_origin_idx_;
    auto started = std::chrono::steady_clock::now();
    auto cpu = map_meter::cpu_ms();
    map.slidingMapFrameCallback(body);
    map.sensorPoseCallback(sensor);
    const auto pose_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - started).count();
    const auto pose_cpu = map_meter::cpu_ms() - cpu;
    started = std::chrono::steady_clock::now();
    cpu = map_meter::cpu_ms();
    map.cloudCallback(cloud);
    const auto cloud_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - started).count();
    const auto cloud_cpu = map_meter::cpu_ms() - cpu;
    if (!map.reactive_cloud_ready_) throw std::runtime_error("Recorded cloud was not applied");
    rows << "{\"scan\":" << index << ",\"stamp_ns\":" << ns << ",\"points\":" << cloud->width
         << ",\"pose_ms\":" << pose_ms << ",\"pose_cpu_ms\":" << pose_cpu
         << ",\"cloud_ms\":" << cloud_ms << ",\"cloud_cpu_ms\":" << cloud_cpu
         << ",\"origin_before\":[" << origin_before.x() << ',' << origin_before.y() << ',' << origin_before.z()
         << "],\"origin_after\":[" << map.mp_.map_origin_idx_.x() << ',' << map.mp_.map_origin_idx_.y() << ',' << map.mp_.map_origin_idx_.z()
         << "],\"state_sha256\":\"" << map_digest(map) << "\""
         << ",\"native_profile\":" << map.planning_profile_.since(native_before)
         << ",\"instrumentation\":" << map_meter::difference(before) << "}\n";
    ++scans;
  }
  if (!list.eof() || scans == 0) throw std::runtime_error("Incomplete recorded scan listing");
  std::cout << "V80_MAP_REPLAY_COMPLETE scans=" << scans << " state_sha256=" << map_digest(map)
            << " voxels=" << map.mp_.map_voxel_num_.transpose()
            << " inflation_offsets=" << map.md_.inflate_offsets_.size()
            << " terrain_cells=" << map.reactive_terrain_.cells.size() << std::endl;
  rclcpp::shutdown();
}
