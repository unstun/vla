// Actual native subscriptions, ray updates, footprint queries and AStar.
// Input files contain sensor measurements and ground support, not object labels.
#include <path_searching/dyn_a_star.h>
#include <plan_env/grid_map.h>
#include <rosgraph_msgs/msg/clock.hpp>
#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <stdexcept>
#include <thread>

namespace fs = std::filesystem;

sensor_msgs::msg::PointCloud2 read_cloud(const fs::path& path, bool ground) {
  std::ifstream stream(path, std::ios::binary);
  if (!stream) throw std::runtime_error("Missing measured cloud: " + path.string());
  sensor_msgs::msg::PointCloud2 cloud;
  cloud.data = std::vector<uint8_t>(std::istreambuf_iterator<char>(stream), {});
  cloud.point_step = ground ? 16 : 12;
  if (cloud.data.empty() || cloud.data.size() % cloud.point_step)
    throw std::runtime_error("Invalid cloud layout");
  cloud.width = cloud.data.size() / cloud.point_step;
  cloud.height = 1;
  cloud.row_step = cloud.width * cloud.point_step;
  cloud.is_dense = true;
  cloud.header.frame_id = ground ? "world" : "lidar";
  for (size_t i = 0; i < (ground ? 4u : 3u); ++i) {
    sensor_msgs::msg::PointField field;
    field.name = std::vector<std::string>{"x", "y", "z", "intensity"}[i];
    field.offset = i * 4;
    field.datatype = sensor_msgs::msg::PointField::FLOAT32;
    field.count = 1;
    cloud.fields.push_back(field);
  }
  return cloud;
}

nav_msgs::msg::Odometry read_pose(const fs::path& path) {
  std::ifstream stream(path);
  nav_msgs::msg::Odometry pose;
  auto &p = pose.pose.pose.position;
  auto &q = pose.pose.pose.orientation;
  stream >> p.x >> p.y >> p.z >> q.x >> q.y >> q.z >> q.w;
  if (!stream) throw std::runtime_error("Invalid measured pose");
  pose.header.frame_id = "world";
  return pose;
}

int main(int argc, char **argv) {
  const char* input = std::getenv("VLA_GEOMETRY_INPUT");
  const char* output = std::getenv("VLA_GEOMETRY_OUTPUT");
  if (!input || !output) throw std::runtime_error("Explicit input/output required");
  const fs::path root(input);
  rclcpp::init(argc, argv);
  auto node = std::make_shared<rclcpp::Node>("scan_planner_node");
  auto map = std::make_shared<GridMap>();
  map->initMap(node.get());
  auto clock_pub = node->create_publisher<rosgraph_msgs::msg::Clock>("/clock", 10);
  auto body_pub = node->create_publisher<nav_msgs::msg::Odometry>("body_pose", rclcpp::SensorDataQoS());
  auto pose_pub = node->create_publisher<nav_msgs::msg::Odometry>("sensor_pose", rclcpp::SensorDataQoS());
  auto cloud_pub = node->create_publisher<sensor_msgs::msg::PointCloud2>("cloud", rclcpp::SensorDataQoS());
  auto ground_pub = node->create_publisher<sensor_msgs::msg::PointCloud2>(
      "/pct_tomogram", rclcpp::QoS(1).reliable().transient_local());
  auto spin = [&](int ms) {
    const auto end = std::chrono::steady_clock::now() + std::chrono::milliseconds(ms);
    do { rclcpp::spin_some(node); std::this_thread::sleep_for(std::chrono::milliseconds(2)); }
    while (std::chrono::steady_clock::now() < end);
  };
  auto clock = [&](int64_t ns) {
    rosgraph_msgs::msg::Clock message;
    message.clock = rclcpp::Time(ns);
    clock_pub->publish(message);
    spin(30);
  };
  spin(400);
  int64_t now = 1000000000;
  clock(now);
  auto body = read_pose(root / "body_pose.txt");
  auto sensor = read_pose(root / "sensor_pose.txt");
  body.child_frame_id = "base";
  sensor.child_frame_id = "lidar";
  body.header.stamp = sensor.header.stamp = rclcpp::Time(now);
  body_pub->publish(body);
  pose_pub->publish(sensor);
  spin(50);
  auto ground = read_cloud(root / "ground.f32", true);
  ground.header.stamp = rclcpp::Time(now);
  ground_pub->publish(ground);
  spin(100);
  std::ifstream listing(root / "clouds.txt");
  // Optional recorded poses retain the original sensor/body pairing while
  // replaying continuous measurements through the existing native map.
  std::ifstream poses(root / "poses.txt");
  std::string file;
  size_t scans = 0;
  while (listing >> file) {
    if (poses.is_open()) {
      std::string body_file, sensor_file;
      poses >> now >> body_file >> sensor_file;
      if (!poses) throw std::runtime_error("Incomplete recorded pose sequence");
      body = read_pose(root / body_file);
      sensor = read_pose(root / sensor_file);
      body.child_frame_id = "base";
      sensor.child_frame_id = "lidar";
    } else {
      now += 100000000;
    }
    clock(now);
    body.header.stamp = sensor.header.stamp = rclcpp::Time(now);
    body_pub->publish(body);
    pose_pub->publish(sensor);
    spin(30);
    auto cloud = read_cloud(root / file, false);
    cloud.header.stamp = rclcpp::Time(now);
    cloud_pub->publish(cloud);
    spin(80);
    ++scans;
  }
  if (!scans) throw std::runtime_error("No measured scans");
  std::ofstream result(output);
  result << std::setprecision(17) << "{\"clouds\":" << scans << ",\"semantic_messages\":0,\"queries\":[";
  // These locations only score the map after all sensor inputs have been used.
  std::ifstream queries(root / "queries.txt");
  Eigen::Vector3d point;
  double yaw;
  std::string label;
  size_t count = 0;
  while (queries >> point.x() >> point.y() >> point.z() >> yaw >> label) {
    if (count++) result << ",";
    result << "{\"label\":" << std::quoted(label) << ",\"occupied\":"
           << map->getInflateOccupancy(point, yaw) << "}";
    if (std::getenv("VLA_QUERY_DIAGNOSTICS")) map->logInitialSplineCollision(point, yaw);
  }
  std::ifstream endpoints(root / "start_goal.txt");
  Eigen::Vector3d start, goal;
  endpoints >> start.x() >> start.y() >> start.z() >> goal.x() >> goal.y() >> goal.z();
  if (!endpoints) throw std::runtime_error("Invalid requested endpoints");
  AStar search;
  search.initGridMap(map, Eigen::Vector3i(100, 100, 100));
  search.use_upstream_search_plane = node->declare_parameter<bool>("manager.use_upstream_search_plane", false);
  search.goal_approach_max_iterations = node->declare_parameter<int>("manager.goal_approach_max_iterations", 1000);
  const auto prior = search.AstarSearch(map->getResolution(), start, Eigen::Vector3d(1.924999999639,0.,0.299999669849), true);
  const auto status = search.AstarSearch(map->getResolution(), start, goal, true);
  const auto path = search.getPath();
  result << "],\"prior_status\":" << static_cast<int>(prior) << ",\"search_status\":" << static_cast<int>(status) << ",\"path\":[";
  bool checked = status == ASTAR_RET::SUCCESS;
  for (size_t i = 0; i < path.size(); ++i) {
    if (i) { result << ","; checked = checked && map->collisionFreeSegment(path[i-1], path[i]); }
    result << "[" << path[i].x() << "," << path[i].y() << "," << path[i].z() << "]";
  }
  clock(now + 300000000);
  result << "],\"all_path_edges_checked\":" << (checked ? "true" : "false")
         << ",\"stale_sensor_blocks_start\":" << (map->getInflateOccupancy(start, 0.) != 0 ? "true" : "false") << "}\n";
  result.close();
  rclcpp::shutdown();
}
