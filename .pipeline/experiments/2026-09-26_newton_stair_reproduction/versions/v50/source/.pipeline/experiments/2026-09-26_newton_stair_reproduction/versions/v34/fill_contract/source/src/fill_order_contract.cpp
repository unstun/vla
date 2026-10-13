// v34 fill contract, node part (versions/v34/PLAN.md, K2). Adapted from
// versions/v30/support_contract/source/src/order_contract.cpp.
// Real GridMap subscriptions receive the pinned navigation ground and surface
// evidence in both orders, then malformed evidence, valid evidence again, the
// navigation ground again, evidence with a hole beside the corridor entry, and
// valid evidence once more. At each checkpoint the node's raw ground, its scored
// terrain and the collision decision's copy are compared with the tree's own
// headers applied to the node's decoded inputs and the evidence currently usable:
// green (scan65) must hold the navigation ground plus the guarded evidence floor,
// red (scan64) the navigation ground alone.
#include <plan_manage/scan_replan_fsm.h>
#include <plan_env/grid_map.h>
#include <rosgraph_msgs/msg/clock.hpp>
#if __has_include(<plan_env/evidence_floor_fill.h>)
#define VLA_HAS_FILL 1
#else
#define VLA_HAS_FILL 0
#endif

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

namespace fs = std::filesystem;
using namespace reactive_stair;

TerrainSnapshot expectedRaw(const TerrainSnapshot &navigation, const TerrainSnapshot *evidence, size_t &added) {
#if VLA_HAS_FILL
  EvidenceFloorFill fill;
  auto out = addGuardedEvidenceFloor(navigation, evidence, 0.12, 0.26, 0.35, &fill);
  added = fill.added;
  return out;
#else
  (void)evidence;
  added = 0;
  return navigation;
#endif
}

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
Comparison compare(const TerrainSnapshot &a, const TerrainSnapshot &b, bool with_support) {
  Comparison c;
  if (a.cells.size() != b.cells.size()) c.differ += 1000000;
  for (const auto &entry : a.cells) {
    const auto found = b.cells.find(entry.first);
    for (size_t i = 0; i < entry.second.size(); ++i) {
      ++c.layers;
      if (found == b.cells.end() || found->second.size() != entry.second.size() ||
          (with_support && found->second[i].support != entry.second[i].support) ||
          found->second[i].elevation_m != entry.second[i].elevation_m) ++c.differ;
    }
  }
  return c;
}

size_t layerCount(const TerrainSnapshot &terrain) {
  size_t n = 0;
  for (const auto &entry : terrain.cells) n += entry.second.size();
  return n;
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
  // Integration-level drop: remove the evidence floor (1.50-1.62 m) in the cell column east of the corridor-entry
  // band (x -4.4953...-4.3953, y -3.55...-3.15). Those cells keep only the ground floor below and the upper floors,
  // so the added floor within 0.35 m of them must go.
  auto holed = surface;
  holed.data.clear();
  size_t removed = 0;
  for (size_t offset = 0; offset + 16 <= surface.data.size(); offset += 16) {
    float point[4];
    std::memcpy(point, surface.data.data() + offset, sizeof(point));
    const bool hole = point[0] >= -4.4953f && point[0] < -4.3953f && point[1] > -3.55f && point[1] < -3.15f &&
                      point[2] - 0.03f > 1.50f && point[2] - 0.03f < 1.62f;
    if (hole) { ++removed; continue; }
    holed.data.insert(holed.data.end(), surface.data.begin() + offset, surface.data.begin() + offset + 16);
  }
  holed.width = holed.data.size() / 16;
  holed.row_step = holed.width * 16;
  const auto nav_decoded = map->decodeReactiveGround(std::make_shared<sensor_msgs::msg::PointCloud2>(nav));
  const auto surface_decoded = map->decodeReactiveGround(std::make_shared<sensor_msgs::msg::PointCloud2>(surface));
  const auto holed_decoded = map->decodeReactiveGround(std::make_shared<sensor_msgs::msg::PointCloud2>(holed));
  const TerrainSnapshot none;  // no usable evidence
  size_t added_none = 0, added_surface = 0, added_holed = 0;
  const TerrainSnapshot raw_none = expectedRaw(nav_decoded, nullptr, added_none);
  const TerrainSnapshot raw_surface = expectedRaw(nav_decoded, &surface_decoded, added_surface);
  const TerrainSnapshot raw_holed = expectedRaw(nav_decoded, &holed_decoded, added_holed);
  const TerrainSnapshot scored_none = precomputeEthStyleStepScores(raw_none, StepScoreParameters{}, &none).support;
  const TerrainSnapshot scored_surface = precomputeEthStyleStepScores(raw_surface, StepScoreParameters{}, &surface_decoded).support;
  const TerrainSnapshot scored_holed = precomputeEthStyleStepScores(raw_holed, StepScoreParameters{}, &holed_decoded).support;

  std::ostringstream json;
  json << std::setprecision(17) << "{\"order\":\"" << order << "\",\"fill_available\":" << (VLA_HAS_FILL ? "true" : "false")
       << ",\"navigation_layers\":" << layerCount(nav_decoded) << ",\"removed_evidence_points\":" << removed
       << ",\"expected_added\":{\"none\":" << added_none << ",\"surface\":" << added_surface << ",\"holed\":" << added_holed
       << "},\"checkpoints\":{";
  bool first = true;
  const auto checkpoint = [&](const std::string &name, const TerrainSnapshot &raw, const TerrainSnapshot &scored) {
    const auto r = compare(map->reactive_ground_, raw, false);
    const auto t = compare(map->reactive_terrain_, scored, true);
    const auto d = compare(map->reactive_decision_.terrain_, map->reactive_terrain_, true);
    json << (first ? "" : ",") << "\"" << name << "\":{\"node_raw_layers\":" << layerCount(map->reactive_ground_)
         << ",\"raw_differs\":" << r.differ << ",\"terrain_differs\":" << t.differ
         << ",\"decision_differs_from_node\":" << d.differ << ",\"decision_ready\":" << map->reactive_decision_.terrain_ready_
         << ",\"surface_cells\":" << map->reactive_surface_ground_.cells.size();
#if VLA_HAS_FILL
    json << ",\"kept_navigation_differs\":" << compare(map->reactive_navigation_ground_, nav_decoded, false).differ;
#endif
    json << "}";
    first = false;
  };
  const auto empty_checkpoint = [&](const std::string &name) {
    json << (first ? "" : ",") << "\"" << name << "\":{\"node_raw_layers\":" << layerCount(map->reactive_ground_)
         << ",\"node_terrain_layers\":" << layerCount(map->reactive_terrain_)
         << ",\"decision_ready\":" << map->reactive_decision_.terrain_ready_
         << ",\"surface_cells\":" << map->reactive_surface_ground_.cells.size() << "}";
    first = false;
  };
  if (std::string(order) == "nav_first") {
    nav_pub->publish(nav); spin(3000); checkpoint("navigation_only", raw_none, scored_none);
    surface_pub->publish(surface); spin(3000); checkpoint("navigation_then_evidence", raw_surface, scored_surface);
    surface_pub->publish(malformed); spin(3000); checkpoint("malformed_evidence", raw_none, scored_none);
    surface_pub->publish(surface); spin(3000); checkpoint("evidence_restored", raw_surface, scored_surface);
    nav_pub->publish(nav); spin(3000); checkpoint("navigation_again", raw_surface, scored_surface);
    surface_pub->publish(holed); spin(3000); checkpoint("entry_hole_evidence", raw_holed, scored_holed);
    surface_pub->publish(surface); spin(3000); checkpoint("evidence_restored_after_hole", raw_surface, scored_surface);
  } else if (std::string(order) == "evidence_first") {
    surface_pub->publish(surface); spin(3000); empty_checkpoint("evidence_only");
    nav_pub->publish(nav); spin(3000); checkpoint("evidence_then_navigation", raw_surface, scored_surface);
  } else {
    throw std::runtime_error("unknown order");
  }
  json << "}}\n";
  std::ofstream(output) << json.str();
  std::cout << "[FILL-ORDER-CONTRACT] " << json.str();
  rclcpp::shutdown();
  return 0;
}
