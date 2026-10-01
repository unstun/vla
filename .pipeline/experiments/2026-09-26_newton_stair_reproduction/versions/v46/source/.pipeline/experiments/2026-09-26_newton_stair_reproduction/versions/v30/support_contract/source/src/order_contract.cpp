// v30 support contract, node part (versions/v30/PLAN.md step 2).
// Real GridMap subscriptions receive the pinned navigation ground and surface
// evidence in both orders, then malformed evidence, then valid evidence again.
// At each checkpoint the node's scored labels, and the collision decision's
// copy of them, are compared with the tree's own header applied to the node's
// decoded inputs: with the currently usable evidence, and without evidence.
#include <plan_manage/scan_replan_fsm.h>
#include <plan_env/grid_map.h>
#include <rosgraph_msgs/msg/clock.hpp>

#include <chrono>
#include <cmath>
#include <cstring>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <thread>
#include <utility>

namespace fs = std::filesystem;
using namespace reactive_stair;

template <class T>
auto scoreWith(const T &input, const T *evidence, int)
    -> decltype(precomputeEthStyleStepScores(input, StepScoreParameters{}, evidence)) {
  return precomputeEthStyleStepScores(input, StepScoreParameters{}, evidence);
}
template <class T>
StepScoreResult scoreWith(const T &input, const T *, long) { return precomputeEthStyleStepScores(input); }

sensor_msgs::msg::PointCloud2 read_ground(const fs::path &path) {
  std::ifstream stream(path, std::ios::binary);
  sensor_msgs::msg::PointCloud2 cloud;
  cloud.data = std::vector<uint8_t>(std::istreambuf_iterator<char>(stream), {});
  cloud.point_step = 16;
  if (cloud.data.empty() || cloud.data.size() % 16) throw std::runtime_error("bad ground " + path.string());
  cloud.width = cloud.data.size() / 16;
  cloud.height = 1;
  cloud.row_step = cloud.width * 16;
  cloud.is_dense = true;
  cloud.header.frame_id = "world";
  for (size_t i = 0; i < 4; ++i) {
    sensor_msgs::msg::PointField field;
    field.name = std::vector<std::string>{"x", "y", "z", "intensity"}[i];
    field.offset = i * 4;
    field.datatype = sensor_msgs::msg::PointField::FLOAT32;
    field.count = 1;
    cloud.fields.push_back(field);
  }
  return cloud;
}

struct Comparison { size_t layers = 0, differ = 0; };
Comparison compare(const TerrainSnapshot &a, const TerrainSnapshot &b) {
  Comparison c;
  if (a.cells.size() != b.cells.size()) c.differ += 1000000;
  for (const auto &entry : a.cells) {
    const auto found = b.cells.find(entry.first);
    for (size_t i = 0; i < entry.second.size(); ++i) {
      ++c.layers;
      if (found == b.cells.end() || found->second.size() != entry.second.size() ||
          found->second[i].support != entry.second[i].support ||
          found->second[i].elevation_m != entry.second[i].elevation_m) ++c.differ;
    }
  }
  return c;
}

uint64_t digest(const TerrainSnapshot &terrain) {
  uint64_t value = UINT64_C(14695981039346656037);
  const auto mix = [&](const std::string &text) { for (unsigned char ch : text) { value ^= ch; value *= UINT64_C(1099511628211); } };
  for (const auto &entry : terrain.cells)
    for (size_t i = 0; i < entry.second.size(); ++i)
      mix(std::to_string(entry.first.x) + "," + std::to_string(entry.first.y) + "," + std::to_string(i) + "," +
          std::to_string(static_cast<int>(entry.second[i].support)) + ";");
  return value;
}

int main(int argc, char **argv) {
  const char *order = std::getenv("VLA_ORDER");
  const char *nav_path = std::getenv("VLA_NAVIGATION_GROUND");
  const char *evidence_path = std::getenv("VLA_SURFACE_EVIDENCE");
  const char *output = std::getenv("VLA_CONTRACT_OUTPUT");
  if (!order || !nav_path || !evidence_path || !output) throw std::runtime_error("explicit order, inputs and output required");
  rclcpp::init(argc, argv);
  auto node = std::make_shared<rclcpp::Node>("scan_planner_node");
  scan_planner::SCANReplanFSM fsm;
  fsm.init(node.get());
  fsm.exec_timer_->cancel();
  fsm.safety_timer_->cancel();
  auto map = fsm.planner_manager_->grid_map_;
  auto clock_pub = node->create_publisher<rosgraph_msgs::msg::Clock>("/clock", 10);
  auto nav_pub = node->create_publisher<sensor_msgs::msg::PointCloud2>("/pct_tomogram", rclcpp::QoS(1).reliable().transient_local());
  auto surface_pub = node->create_publisher<sensor_msgs::msg::PointCloud2>("/pct_ground_surface", rclcpp::QoS(1).reliable().transient_local());
  const auto spin = [&](int ms) {
    const auto end = std::chrono::steady_clock::now() + std::chrono::milliseconds(ms);
    do { rclcpp::spin_some(node); std::this_thread::sleep_for(std::chrono::milliseconds(2)); }
    while (std::chrono::steady_clock::now() < end);
  };
  spin(400);
  rosgraph_msgs::msg::Clock tick;
  tick.clock = rclcpp::Time(1000000000);
  clock_pub->publish(tick);
  spin(100);
  auto nav = read_ground(nav_path);
  auto surface = read_ground(evidence_path);
  nav.header.stamp = surface.header.stamp = rclcpp::Time(1000000000);
  auto malformed = surface;
  malformed.header.frame_id = "invalid_frame";
  // Integration-level real drop: remove the evidence walkway surface in the cell
  // column beside the landing ring (x -4.84532, y -3.29..-2.59). The ring beside
  // it must then score as a possible drop again.
  auto dropped = surface;
  dropped.data.clear();
  size_t removed = 0;
  for (size_t offset = 0; offset + 16 <= surface.data.size(); offset += 16) {
    float point[4];
    std::memcpy(point, surface.data.data() + offset, sizeof(point));
    const bool drop = std::abs(point[0] + 4.84532f) < 0.02f && point[1] > -3.30f && point[1] < -2.57f &&
                      point[2] - 0.03f > 1.35f && point[2] - 0.03f < 1.65f;
    if (drop) { ++removed; continue; }
    dropped.data.insert(dropped.data.end(), surface.data.begin() + offset, surface.data.begin() + offset + 16);
  }
  dropped.width = dropped.data.size() / 16;
  dropped.row_step = dropped.width * 16;
  const auto nav_decoded = map->decodeReactiveGround(std::make_shared<sensor_msgs::msg::PointCloud2>(nav));
  const auto surface_decoded = map->decodeReactiveGround(std::make_shared<sensor_msgs::msg::PointCloud2>(surface));
  const TerrainSnapshot without = precomputeEthStyleStepScores(nav_decoded).support;
  const TerrainSnapshot with = scoreWith(nav_decoded, &surface_decoded, 0).support;
  const auto dropped_decoded = map->decodeReactiveGround(std::make_shared<sensor_msgs::msg::PointCloud2>(dropped));
  const TerrainSnapshot with_dropped = scoreWith(nav_decoded, &dropped_decoded, 0).support;
  // Unknown walkway layers (1.35-1.65 m) in the landing box x[-5.3,-3.5] y[-4.5,-2.3].
  const auto box_unknown = [&](const TerrainSnapshot &labels) {
    size_t count = 0;
    for (const auto &entry : labels.cells) {
      const double x0 = nav_decoded.origin_x_m + entry.first.x * nav_decoded.resolution_m;
      const double y0 = nav_decoded.origin_y_m + entry.first.y * nav_decoded.resolution_m;
      if (x0 < -5.3 || x0 > -3.5 || y0 < -4.5 || y0 > -2.3) continue;
      for (const auto &surface : entry.second)
        if (surface.elevation_m >= 1.35 && surface.elevation_m <= 1.65 && surface.support == Support::Unknown) ++count;
    }
    return count;
  };

  std::ostringstream json;
  json << std::setprecision(17) << "{\"order\":\"" << order << "\",\"with_differs_from_without\":" << compare(with, without).differ
       << ",\"removed_evidence_points\":" << removed << ",\"with_dropped_differs_from_with\":" << compare(with_dropped, with).differ
       << ",\"expected_box_unknown\":{\"without\":" << box_unknown(without) << ",\"with\":" << box_unknown(with)
       << ",\"with_dropped\":" << box_unknown(with_dropped) << "},\"checkpoints\":{";
  bool first = true;
  const auto checkpoint = [&](const std::string &name) {
    const auto &node_labels = map->reactive_terrain_;
    const auto a = compare(node_labels, with), b = compare(node_labels, without);
    const auto d = compare(map->reactive_decision_.terrain_, node_labels);
    json << (first ? "" : ",") << "\"" << name << "\":{\"node_cells\":" << node_labels.cells.size()
         << ",\"node_layers\":" << a.layers << ",\"differ_with_evidence\":" << a.differ
         << ",\"differ_without_evidence\":" << b.differ << ",\"differ_with_dropped_evidence\":" << compare(node_labels, with_dropped).differ
         << ",\"box_unknown_walkway_layers\":" << box_unknown(node_labels) << ",\"decision_differs_from_node\":" << d.differ
         << ",\"decision_ready\":" << map->reactive_decision_.terrain_ready_
         << ",\"surface_cells\":" << map->reactive_surface_ground_.cells.size()
         << ",\"digest\":\"" << digest(node_labels) << "\"}";
    first = false;
  };
  if (std::string(order) == "nav_first") {
    nav_pub->publish(nav); spin(1500); checkpoint("navigation_only");
    surface_pub->publish(surface); spin(1500); checkpoint("navigation_then_evidence");
    surface_pub->publish(malformed); spin(1500); checkpoint("malformed_evidence");
    surface_pub->publish(surface); spin(1500); checkpoint("evidence_restored");
    nav_pub->publish(nav); spin(1500); checkpoint("navigation_again");
    surface_pub->publish(dropped); spin(1500); checkpoint("real_drop_evidence");
    surface_pub->publish(surface); spin(1500); checkpoint("evidence_restored_after_drop");
  } else if (std::string(order) == "evidence_first") {
    surface_pub->publish(surface); spin(1500); checkpoint("evidence_only");
    nav_pub->publish(nav); spin(1500); checkpoint("evidence_then_navigation");
  } else {
    throw std::runtime_error("unknown order");
  }
  json << "}}\n";
  std::ofstream(output) << json.str();
  std::cout << "[ORDER-CONTRACT] " << json.str();
  rclcpp::shutdown();
  return 0;
}
