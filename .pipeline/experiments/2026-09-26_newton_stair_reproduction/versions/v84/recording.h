#pragma once
#include <plan_env/grid_map.h>
#include <rcl/time.h>
#include <openssl/sha.h>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <deque>
#include <chrono>
#include <thread>
namespace fs = std::filesystem;
#include "../v81/recorded_readers.h"
#include "../v81/map_digest.h"

struct RecordedScan {
  int index;
  int64_t stamp;
  nav_msgs::msg::Odometry::SharedPtr body, sensor;
  sensor_msgs::msg::PointCloud2::SharedPtr cloud;
};

inline std::vector<RecordedScan> read_scans(const fs::path &input) {
  std::ifstream list(input / "scans.txt");
  if (!list) throw std::runtime_error("Missing scan listing");
  std::vector<RecordedScan> scans;
  int index; int64_t stamp; std::string body, sensor, cloud;
  while (list >> index >> stamp >> body >> sensor >> cloud) {
    if (stamp <= 0 || (!scans.empty() && (stamp <= scans.back().stamp || index != scans.back().index + 1)))
      throw std::runtime_error("Scan order or timestamp invalid");
    RecordedScan scan{index, stamp,
      std::make_shared<nav_msgs::msg::Odometry>(read_pose(input / body)),
      std::make_shared<nav_msgs::msg::Odometry>(read_pose(input / sensor)),
      std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input / cloud, false))};
    scan.body->header.stamp = scan.sensor->header.stamp = scan.cloud->header.stamp =
        rclcpp::Time(stamp, RCL_ROS_TIME);
    scans.push_back(std::move(scan));
  }
  if (!list.eof() || scans.size() != 188 || scans.front().index != 0 || scans.back().index != 187)
    throw std::runtime_error("Expected the exact 188-scan prefix");
  return scans;
}

inline void set_clock(rclcpp::Node &node, int64_t ns) {
  auto handle = node.get_clock()->get_clock_handle();
  if (rcl_enable_ros_time_override(handle) != RCL_RET_OK ||
      rcl_set_ros_time_override(handle, ns) != RCL_RET_OK)
    throw std::runtime_error("Clock override failed");
}

inline void initialize_map(GridMap &map, rclcpp::Node &node, const fs::path &input) {
  set_clock(node, 1000000000LL);
  map.initMap(&node);
  map.occ_timer_->cancel(); map.vis_timer_->cancel();
  if (map.async_mapping_) throw std::runtime_error("Replay requires explicit synchronous map configuration");
  auto nav = std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input / "navigation.f32", true));
  auto surface = std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input / "surface.f32", true));
  auto floor = std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input / "physical_floor.f32", true));
  nav->header.stamp = surface->header.stamp = floor->header.stamp = rclcpp::Time(1000000000LL, RCL_ROS_TIME);
  map.reactiveTomogramCallback(nav); map.reactiveSurfaceGroundCallback(surface); map.reactivePhysicalFloorCallback(floor);
  if (!map.reactiveSurfaceGroundReady()) throw std::runtime_error("Paired original support not ready");
}

inline double apply_scan(GridMap &map, rclcpp::Node &node, const RecordedScan &scan) {
  set_clock(node, scan.stamp);
  const auto begin = std::chrono::steady_clock::now();
  map.slidingMapFrameCallback(scan.body);
  map.sensorPoseCallback(scan.sensor);
  map.cloudCallback(scan.cloud);
  if (!map.mapState().reactive_cloud_ready_ ||
      std::abs(map.mapState().reactive_cloud_stamp_s_ - scan.stamp * 1e-9) > 1e-8)
    throw std::runtime_error("Native cloud application did not preserve stamp/readiness");
  return std::chrono::duration<double>(std::chrono::steady_clock::now() - begin).count();
}
