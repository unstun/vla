// Known-footprint waiver contract for v29 (versions/v29/PLAN.md, step 2).
// One source is compiled against a native tree. It replays a frozen saved state
// through the real subscriptions and compares GridMap::reactiveOccupancy at
// 27 points in every voxel near the body with two independent oracles:
//   v28: footprint and trunk band |z - 0.01| <= 0.06 tested at the voxel centre;
//   v29: footprint and -0.05 <= z <= 0.10854 tested at the queried point.
// The waiver changes only never-observed (Unknown) voxels. Other voxels, and
// Unknown points on which both specifications agree, are folded into digests
// that must match between trees; points where the specifications differ are
// written to <output>_discriminating.csv.
#include <plan_manage/scan_replan_fsm.h>
#include <plan_env/grid_map.h>
#include <rclcpp/serialization.hpp>
#include <rosgraph_msgs/msg/clock.hpp>
#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <thread>

namespace fs = std::filesystem;

sensor_msgs::msg::PointCloud2 read_cloud(const fs::path &path, bool ground) {
  std::ifstream stream(path, std::ios::binary);
  if (!stream) throw std::runtime_error("Missing measured cloud: " + path.string());
  sensor_msgs::msg::PointCloud2 cloud;
  cloud.data = std::vector<uint8_t>(std::istreambuf_iterator<char>(stream), {});
  cloud.point_step = ground ? 16 : 12;
  if (cloud.data.empty() || cloud.data.size() % cloud.point_step) throw std::runtime_error("Invalid cloud layout");
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

nav_msgs::msg::Odometry read_pose(const fs::path &path) {
  std::ifstream stream(path);
  nav_msgs::msg::Odometry pose;
  auto &p = pose.pose.pose.position;
  auto &q = pose.pose.pose.orientation;
  auto &v = pose.twist.twist.linear;
  auto &w = pose.twist.twist.angular;
  stream >> p.x >> p.y >> p.z >> q.x >> q.y >> q.z >> q.w >> v.x >> v.y >> v.z >> w.x >> w.y >> w.z;
  if (!stream) throw std::runtime_error("Invalid measured pose");
  pose.header.frame_id = "world";
  return pose;
}

bool inFootprintXY(double x, double y, double radius, double offset) {
  const double dx = std::min(std::abs(x - offset), std::abs(x + offset));
  return dx * dx + y * y <= radius * radius;
}

int main(int argc, char **argv) {
  const char *input = std::getenv("VLA_CONTRACT_INPUT");
  const char *output = std::getenv("VLA_CONTRACT_OUTPUT");
  const char *raw_ground = std::getenv("VLA_RAW_GROUND");
  if (!input || !output || !raw_ground) throw std::runtime_error("Explicit input, output and raw ground required");
  const fs::path root(input);
  rclcpp::init(argc, argv);
  auto node = std::make_shared<rclcpp::Node>("scan_planner_node");
  scan_planner::SCANReplanFSM fsm;
  fsm.init(node.get());
  fsm.exec_timer_->cancel();
  fsm.safety_timer_->cancel();
  auto map = fsm.planner_manager_->grid_map_;
  auto clock_pub = node->create_publisher<rosgraph_msgs::msg::Clock>("/clock", 10);
  auto body_pub = node->create_publisher<nav_msgs::msg::Odometry>("body_pose", rclcpp::SensorDataQoS());
  auto pose_pub = node->create_publisher<nav_msgs::msg::Odometry>("sensor_pose", rclcpp::SensorDataQoS());
  auto cloud_pub = node->create_publisher<sensor_msgs::msg::PointCloud2>("cloud", rclcpp::SensorDataQoS());
  auto ground_pub = node->create_publisher<sensor_msgs::msg::PointCloud2>(
      "/pct_tomogram", rclcpp::QoS(1).reliable().transient_local());
  auto surface_pub = node->create_publisher<sensor_msgs::msg::PointCloud2>(
      "/pct_ground_surface", rclcpp::QoS(1).reliable().transient_local());
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
  // Same replay order as the regression gen_probe: pose, navigation support,
  // surface evidence, then each recorded scan with its paired poses.
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
  auto surface = read_cloud(fs::path(raw_ground), true);
  surface.header.stamp = rclcpp::Time(now);
  surface_pub->publish(surface);
  spin(80);
  if (!map->reactiveSurfaceGroundReady()) throw std::runtime_error("Surface evidence not ready");
  std::ifstream listing(root / "clouds.txt");
  std::ifstream poses(root / "poses.txt");
  std::string file;
  size_t scans = 0;
  while (listing >> file) {
    std::string body_file, sensor_file;
    poses >> now >> body_file >> sensor_file;
    if (!poses) throw std::runtime_error("Incomplete recorded pose sequence");
    body = read_pose(root / body_file);
    sensor = read_pose(root / sensor_file);
    body.child_frame_id = "base";
    sensor.child_frame_id = "lidar";
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
  std::ifstream final_clock(root / "final_clock.txt");
  final_clock >> now;
  clock(now);
  body = read_pose(root / "final_body.txt");
  body.child_frame_id = "base";
  body.header.stamp = rclcpp::Time(now);
  body_pub->publish(body);
  spin(50);

  const double radius = map->mp_.double_cylinder_radius_, offset = map->mp_.double_cylinder_offset_;
  const double resolution = map->mp_.resolution_;
  const Eigen::Vector3d body_position = map->md_.sliding_map_frame_pos_;
  const Eigen::Quaterniond body_rotation = map->reactive_body_quaternion_;
  const auto local_of = [&](const Eigen::Vector3d &p) { return Eigen::Vector3d(body_rotation.conjugate() * (p - body_position)); };
  const auto boundary_ok = [&](const Eigen::Vector3d &p) {
    return p.allFinite() && std::isfinite(radius) && radius >= 0.0 &&
        p.x() - radius >= map->mp_.map_min_boundary_.x() && p.x() + radius <= map->mp_.map_max_boundary_.x() &&
        p.y() - radius >= map->mp_.map_min_boundary_.y() && p.y() + radius <= map->mp_.map_max_boundary_.y() &&
        p.z() - map->mp_.obstacles_inflation_z_down >= map->mp_.map_min_boundary_.z() &&
        p.z() + map->mp_.obstacles_inflation_z_up <= map->mp_.map_max_boundary_.z();
  };
  // Verdict the tree would return after waiving: the same query with a Free voxel.
  const auto free_verdict = [&](const Eigen::Vector3d &p) {
    reactive_stair::Query query;
    query.frame = map->mp_.frame_id_;
    query.stamp_s = node->now().seconds();
    query.x_m = p.x(); query.y_m = p.y(); query.z_m = p.z();
    query.in_map = map->isInMap(p);
    reactive_stair::NonTerrainVoxel voxel;
    voxel.frame = map->mp_.frame_id_;
    voxel.stamp_s = map->reactive_cloud_stamp_s_;
    if (map->reactive_cloud_ready_) voxel.source_id = "scan_lidar_cloud";
    voxel.occupancy = reactive_stair::Occupancy::Free;
    return map->reactive_decision_.decide(query, voxel);
  };

  struct Row { Eigen::Vector3i id; Eigen::Vector3d point; bool unknown, inflated, waived28, waived29; int observed; };
  std::vector<Row> rows;
  const fs::path out_json(output);
  std::ofstream csv(out_json.parent_path() / (out_json.stem().string() + "_discriminating.csv"));
  csv << std::setprecision(9) << "ix,iy,iz,fx,fy,fz,x,y,z,local_x,local_y,local_z,centre_local_x,centre_local_y,centre_local_z,inflated,free_verdict,waived_v28,waived_v29,observed\n";
  // FNV-1a over (voxel, sub-point, observed); matching digests show matching results.
  uint64_t digest_not_unknown = 1469598103934665603ULL, digest_agreeing = 1469598103934665603ULL;
  const auto fold = [](uint64_t &digest, const Eigen::Vector3i &id, int sub_point, int observed) {
    for (long value : {long(id.x()), long(id.y()), long(id.z()), long(sub_point), long(observed)})
      for (int byte = 0; byte < 8; ++byte) { digest ^= (uint64_t(value) >> (8 * byte)) & 0xff; digest *= 1099511628211ULL; }
  };
  std::map<std::string, std::map<std::string, long>> counts;
  long mismatches28 = 0, mismatches29 = 0, sub_voxel_errors = 0;
  std::vector<std::string> examples28, examples29;
  const double query_now = node->now().seconds();
  const bool pose_fresh = map->reactive_known_trunk_enabled_ && map->reactive_body_stamp_s_ > 0.0 &&
      reactive_stair::fresh(query_now, map->reactive_body_stamp_s_, 0.1);
  Eigen::Vector3i low, high;
  map->posToIndex(body_position - Eigen::Vector3d(0.8, 0.8, 0.25), low);
  map->posToIndex(body_position + Eigen::Vector3d(0.8, 0.8, 0.30), high);
  const double fractions[3] = {0.1, 0.5, 0.9};
  for (int ix = low.x(); ix <= high.x(); ++ix)
    for (int iy = low.y(); iy <= high.y(); ++iy)
      for (int iz = low.z(); iz <= high.z(); ++iz) {
        const Eigen::Vector3i id(ix, iy, iz);
        if (!map->isInMap(id)) continue;
        Eigen::Vector3d centre;
        map->indexToPos(id, centre);
        const Eigen::Vector3d centre_local = local_of(centre);
        if (std::abs(centre_local.x()) > 0.75 || std::abs(centre_local.y()) > 0.55 ||
            centre_local.z() < -0.20 || centre_local.z() > 0.25) continue;
        const int address = map->toAddress(id);
        const bool unknown = map->md_.occupancy_buffer_[address] < map->mp_.clamp_min_log_ - 1e-3;
        const bool inflated = map->md_.occupancy_buffer_inflate_[address] != 0;
        int sub_point = -1;
        for (double fx : fractions) for (double fy : fractions) for (double fz : fractions) {
          ++sub_point;
          const Eigen::Vector3d point = centre + resolution * Eigen::Vector3d(fx - 0.5, fy - 0.5, fz - 0.5);
          Eigen::Vector3i check;
          map->posToIndex(point, check);
          if (check != id) { ++sub_voxel_errors; continue; }
          const Eigen::Vector3d local = local_of(point);
          const bool bounded = boundary_ok(point) && map->isInMap(point);
          const auto verdict = free_verdict(point);
          const bool waiver_applies = unknown && !inflated && pose_fresh && bounded;
          const bool waived28 = waiver_applies && inFootprintXY(centre_local.x(), centre_local.y(), radius, offset) &&
              std::abs(centre_local.z() - 0.01) <= 0.06;
          const bool waived29 = waiver_applies && inFootprintXY(local.x(), local.y(), radius, offset) &&
              local.z() >= -0.05 && local.z() <= 0.10854;
          const int observed = map->reactiveOccupancy(point);
          rows.push_back({id, point, unknown, inflated, waived28, waived29, observed});
          if (!unknown) {
            ++counts["not_unknown"]["points"];
            counts["not_unknown"]["blocked"] += observed;
            fold(digest_not_unknown, id, sub_point, observed);
            continue;
          }
          if (waived28 == waived29) fold(digest_agreeing, id, sub_point, observed);
          else
            csv << ix << "," << iy << "," << iz << "," << fx << "," << fy << "," << fz << "," << point.x() << "," << point.y() << ","
                << point.z() << "," << local.x() << "," << local.y() << "," << local.z() << "," << centre_local.x() << ","
                << centre_local.y() << "," << centre_local.z() << "," << inflated << "," << static_cast<int>(verdict) << ","
                << waived28 << "," << waived29 << "," << observed << "\n";
          const bool informative = bounded && verdict == reactive_stair::Verdict::Free;
          const std::string category = waived28 ? (waived29 ? "both_waive" : "v28_only") : (waived29 ? "v29_only" : "neither");
          ++counts[category]["points"];
          if (informative) ++counts[category]["informative"];
          if (inflated) ++counts[category]["inflated"];
          const int expected28 = waived28 && informative ? 0 : 1;
          const int expected29 = waived29 && informative ? 0 : 1;
          std::ostringstream example;
          example << std::setprecision(6) << "id=" << ix << "," << iy << "," << iz << " local=" << local.transpose()
                  << " centre_local=" << centre_local.transpose() << " observed=" << observed;
          if (observed != expected28) { ++mismatches28; if (examples28.size() < 5) examples28.push_back(example.str()); }
          if (observed != expected29) { ++mismatches29; if (examples29.size() < 5) examples29.push_back(example.str()); }
        }
      }

  // Stale pose: 0.15 s later the pose is outside the waiver's 0.1 s freshness,
  // while the 0.25 s obstacle age still holds. No Unknown point may be free.
  clock(now + 150000000);
  spin(50);
  long stale_checked = 0, stale_free = 0;
  for (const auto &row : rows) {
    if (!row.unknown || !(row.waived28 || row.waived29)) continue;
    ++stale_checked;
    if (map->reactiveOccupancy(row.point) == 0) ++stale_free;
  }

  std::ofstream result(output);
  result << std::setprecision(17) << "{\"scans\":" << scans << ",\"query_now_s\":" << query_now
         << ",\"pose_stamp_s\":" << map->reactive_body_stamp_s_ << ",\"pose_fresh\":" << (pose_fresh ? "true" : "false")
         << ",\"waiver_enabled\":" << (map->reactive_known_trunk_enabled_ ? "true" : "false")
         << ",\"body\":[" << body_position.x() << "," << body_position.y() << "," << body_position.z() << "]"
         << ",\"radius_m\":" << radius << ",\"offset_m\":" << offset << ",\"resolution_m\":" << resolution
         << ",\"points\":" << rows.size() << ",\"sub_voxel_errors\":" << sub_voxel_errors << ",\"categories\":{";
  bool first_category = true;
  for (const auto &category : counts) {
    result << (first_category ? "" : ",") << "\"" << category.first << "\":{";
    bool first_field = true;
    for (const auto &field : category.second) {
      result << (first_field ? "" : ",") << "\"" << field.first << "\":" << field.second;
      first_field = false;
    }
    result << "}";
    first_category = false;
  }
  const auto list = [&](const std::vector<std::string> &values) {
    std::string text = "[";
    for (size_t i = 0; i < values.size(); ++i) text += (i ? ",\"" : "\"") + values[i] + "\"";
    return text + "]";
  };
  result << "},\"mismatches_vs_v28_spec\":" << mismatches28 << ",\"mismatches_vs_v29_spec\":" << mismatches29
         << ",\"examples_vs_v28_spec\":" << list(examples28) << ",\"examples_vs_v29_spec\":" << list(examples29)
         << ",\"stale_pose\":{\"checked\":" << stale_checked << ",\"free_while_stale\":" << stale_free << "}"
         << ",\"digest_not_unknown\":\"" << std::hex << digest_not_unknown << "\",\"digest_unknown_where_specs_agree\":\""
         << digest_agreeing << std::dec << "\"}\n";
  result.close();
  std::cout << "[WAIVER-CONTRACT] points=" << rows.size() << " mismatches_v28=" << mismatches28
            << " mismatches_v29=" << mismatches29 << " stale_free=" << stale_free << std::endl;
  rclcpp::shutdown();
}
