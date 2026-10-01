#include <plan_env/local_hotspot_profile.h>
// Actual native subscriptions, ray updates, footprint queries and AStar.
// Input files contain sensor measurements and ground support, not object labels.
#include <path_searching/dyn_a_star.h>
#include <plan_manage/scan_replan_fsm.h>
#include <rclcpp/serialization.hpp>
#include <cstring>
#include <limits>
#include <bspline_opt/full_trajectory_collision.h>
#include <bspline_opt/bspline_optimizer.h>
#include <bspline_opt/timed_cubic_initialization.h>
#include <plan_env/grid_map.h>
#include <plan_env/known_lite3_trunk.h>
#include <plan_env/raw_return_classification.h>
#include <plan_env/eth_step_score_adaptation.h>
#include <cmath>
#include <sstream>
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
  auto &v = pose.twist.twist.linear; auto &w = pose.twist.twist.angular;
  stream >> p.x >> p.y >> p.z >> q.x >> q.y >> q.z >> q.w >> v.x >> v.y >> v.z >> w.x >> w.y >> w.z;
  if (!stream) throw std::runtime_error("Invalid measured pose");
  pose.header.frame_id = "world";
  return pose;
}

template<class Message> Message read_message(const fs::path &path) {
  std::ifstream stream(path, std::ios::binary);
  std::vector<char> bytes{std::istreambuf_iterator<char>(stream), {}};
  if (bytes.empty()) throw std::runtime_error("Empty original ROS message");
  rclcpp::SerializedMessage serial(bytes.size());
  auto &buffer = serial.get_rcl_serialized_message();
  std::memcpy(buffer.buffer, bytes.data(), bytes.size());
  buffer.buffer_length = bytes.size();
  Message message; rclcpp::Serialization<Message> serializer;
  serializer.deserialize_message(&serial, &message);
  return message;
}

int main(int argc, char **argv) {
  const char* input = std::getenv("VLA_GEOMETRY_INPUT");
  const char* output = std::getenv("VLA_GEOMETRY_OUTPUT");
  if (!input || !output) throw std::runtime_error("Explicit input/output required");
  const fs::path root(input);
  rclcpp::init(argc, argv);
  auto node = std::make_shared<rclcpp::Node>("scan_planner_node");
  scan_planner::SCANReplanFSM fsm;
  fsm.init(node.get());
  fsm.exec_timer_->cancel(); fsm.safety_timer_->cancel();
  auto map = fsm.planner_manager_->grid_map_;
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
  auto ground = read_cloud(std::getenv("VLA_NAV_GROUND") ? fs::path(std::getenv("VLA_NAV_GROUND")) : root / "ground.f32", true);
  ground.header.stamp = rclcpp::Time(now);
  ground_pub->publish(ground);
  spin(100);
  auto surface_pub=node->create_publisher<sensor_msgs::msg::PointCloud2>(
      "/pct_ground_surface",rclcpp::QoS(1).reliable().transient_local());
  if(map->reactiveSurfaceGroundReady()) throw std::runtime_error("Missing required surface input accepted");
  const auto support_id=map->reactive_terrain_.source_id;
  auto surface=read_cloud(std::getenv("VLA_RAW_GROUND")?fs::path(std::getenv("VLA_RAW_GROUND")):root/"ground.f32",true);
  surface.header.stamp=rclcpp::Time(now);
  auto malformed=surface;malformed.header.frame_id="invalid_frame";
  surface_pub->publish(malformed);spin(80);
  if(map->reactiveSurfaceGroundReady()) throw std::runtime_error("Wrong-frame surface accepted");
  auto future=surface;future.header.stamp=rclcpp::Time(now+1000000000);
  surface_pub->publish(future);spin(80);
  if(map->reactiveSurfaceGroundReady()) throw std::runtime_error("Future surface accepted");
  surface_pub->publish(surface);spin(80);
  if(!map->reactiveSurfaceGroundReady()||map->reactive_terrain_.source_id!=support_id)
    throw std::runtime_error("Required evidence not ready or navigation support changed");
  // Check the opposite delivery order using real subscriptions before any scan.
  auto invalid_nav=ground;invalid_nav.header.frame_id="invalid_frame";
  ground_pub->publish(invalid_nav);spin(80);
  if(map->reactiveSurfaceGroundReady()) throw std::runtime_error("Surface without selected map accepted");
  ground_pub->publish(ground);spin(80);
  if(!map->reactiveSurfaceGroundReady()||map->reactive_terrain_.source_id!=support_id)
    throw std::runtime_error("Selected map did not restore readiness");
  std::cout<<"[SURFACE-GATE] missing/wrong-frame/future/order/navigation-support checks passed"<<std::endl;
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
  std::ifstream final_clock(root / "final_clock.txt");
  final_clock >> now;
  clock(now);
  body = read_pose(root / "final_body.txt");
  body.child_frame_id = "base";
  body.header.stamp = rclcpp::Time(now);
  body_pub->publish(body);
  spin(50);
  const auto message=read_message<scan_planner_msgs::msg::Bspline>(root/"spline.cdr");
  Eigen::MatrixXd points(3,message.pos_pts.size());
  for(size_t i=0;i<message.pos_pts.size();++i) points.col(i)<<message.pos_pts[i].x,message.pos_pts[i].y,message.pos_pts[i].z;
  Eigen::VectorXd knots(message.knots.size());
  for(size_t i=0;i<message.knots.size();++i) knots[i]=message.knots[i];
  scan_planner::UniformBspline captured(points,message.order,message.knots[4]-message.knots[3]);
  captured.setKnot(knots);
  auto &local=fsm.planner_manager_->local_data_;
  local.position_traj_=captured;local.velocity_traj_=captured.getDerivative();local.acceleration_traj_=local.velocity_traj_.getDerivative();
  local.traj_id_=message.traj_id;local.duration_=captured.getTimeSum();local.start_time_=rclcpp::Time(message.start_time,RCL_ROS_TIME);
  const double current=std::min(std::max((node->now()-local.start_time_).seconds(),0.),local.duration_);
  fsm.start_pt_=captured.evaluateDeBoorT(current);fsm.start_vel_=local.velocity_traj_.evaluateDeBoorT(current);fsm.start_acc_=local.acceleration_traj_.evaluateDeBoorT(current);
  auto route=std::make_shared<scan_planner_msgs::msg::P2BRoute>(read_message<scan_planner_msgs::msg::P2BRoute>(root/"route.cdr"));
  fsm.p2bRouteCallback(route);
  if(!fsm.have_target_) throw std::runtime_error("Original route not accepted");
  fsm.have_new_target_=false;
  std::ifstream progress(root/"last_progress.txt");progress>>fsm.planner_manager_->global_data_.last_progress_time_;
  // ===== corridor-entry analysis (read-only; replaces gen_probe's frontier audit) =====
  std::cout << std::setprecision(12);
  auto executing = fsm.planner_manager_->local_data_;  // mutable copy: getControlPoint() is non-const
  struct Circle {
    std::string stage = "free"; int in_map = 0; double log_odds = NAN; int inflate = -1;
    int contributors = 0, terrain_contributors = 0, unclassified = 0;
    int raw_class = -1, trunk_inside = -1, final_class = -1, body_verdict = -1, verdict = -1, result = 1;
    int native = -1, support_native = -1;
    double body_ground = NAN, footprint_ground = NAN, support_z = NAN;
    Eigen::Vector3d center = Eigen::Vector3d::Constant(NAN);
    std::vector<Eigen::Vector3d> unclassified_xyz;
  };
  // v30 stop audit (make_probe.py), unchanged: replica of reactiveFootprintSupportQuery with stage codes.
  const auto support_replica = [&](const Eigen::Vector3d &body_reference, const reactive_stair::NonTerrainVoxel &obstacle,
                                   reactive_stair::Query &query, Circle &b) {
    if (!body_reference.allFinite()) { b.stage = "support_body_nonfinite"; return false; }
    const auto &raw = map->reactive_ground_;
    const auto &scored = map->reactive_terrain_;
    if (raw.source_id != scored.source_id || raw.frame != scored.frame || raw.resolution_m != scored.resolution_m ||
        raw.origin_x_m != scored.origin_x_m || raw.origin_y_m != scored.origin_y_m) { b.stage = "support_source_mismatch"; return false; }
    auto body_query = query;
    body_query.x_m = body_reference.x(); body_query.y_m = body_reference.y(); body_query.z_m = body_reference.z();
    body_query.in_map = map->isInMap(body_reference);
    auto support_only = obstacle;
    support_only.occupancy = reactive_stair::Occupancy::Free;
    const auto body_verdict = map->reactive_decision_.decide(body_query, support_only);
    b.body_verdict = static_cast<int>(body_verdict);
    if (body_verdict != reactive_stair::Verdict::Free) { b.stage = "support_body_verdict_" + std::to_string(b.body_verdict); return false; }
    // Codes: 1 invalid index, 2 missing cell, 3 layer count mismatch, 4 no unique
    // layer within the limit, 5 elevation mismatch, 6 nearest layer not selected.
    const auto associated_height = [&](double x, double y, double target, double limit, double &height) {
      const double ix = std::floor((x - raw.origin_x_m) / raw.resolution_m);
      const double iy = std::floor((y - raw.origin_y_m) / raw.resolution_m);
      if (!std::isfinite(ix) || !std::isfinite(iy) ||
          ix < std::numeric_limits<int>::min() || ix > std::numeric_limits<int>::max() ||
          iy < std::numeric_limits<int>::min() || iy > std::numeric_limits<int>::max()) return 1;
      const reactive_stair::Cell2 cell{static_cast<int>(ix), static_cast<int>(iy)};
      const auto original = raw.cells.find(cell), classified = scored.cells.find(cell);
      if (original == raw.cells.end() || classified == scored.cells.end()) return 2;
      if (original->second.size() != classified->second.size()) return 3;
      const int layer = reactive_stair::nearestSurface(original->second, target, limit);
      if (layer < 0) return 4;
      const auto &surface = classified->second[layer];
      if (surface.elevation_m != original->second[layer].elevation_m) return 5;
      if (!reactive_stair::selectedSurface(surface)) return 6;
      height = surface.elevation_m;
      return 0;
    };
    const double step = reactive_stair::StepScoreParameters{}.critical_height_m;
    int code = associated_height(body_query.x_m, body_query.y_m, body_query.z_m - map->reactive_parameters_.body_clearance_m,
                                 map->reactive_parameters_.body_height_tolerance_m, b.body_ground);
    if (code) { b.stage = "support_body_layer_" + std::to_string(code); return false; }
    code = associated_height(query.x_m, query.y_m, b.body_ground, step, b.footprint_ground);
    if (code) { b.stage = "support_footprint_layer_" + std::to_string(code); return false; }
    if (std::abs(b.footprint_ground - b.body_ground) >= step) { b.stage = "support_step"; return false; }
    query.z_m = b.footprint_ground + map->reactive_parameters_.body_clearance_m;
    b.support_z = query.z_m;
    return true;
  };
  // v30 stop audit (make_probe.py), unchanged: one footprint circle, step by step, against the native result.
  const auto circle_breakdown = [&](const Eigen::Vector3d &point, const Eigen::Vector3d &body) {
    Circle b;
    b.center = point;
    const double now_s = node->now().seconds();
    if (!map->reactiveSurfaceGroundReady()) { b.stage = "surface_not_ready"; return b; }
    if (!point.allFinite()) { b.stage = "nonfinite"; return b; }
    const double radius = map->mp_.double_cylinder_radius_;
    if (!std::isfinite(radius) || radius < 0.0 ||
        point.x() - radius < map->mp_.map_min_boundary_.x() || point.x() + radius > map->mp_.map_max_boundary_.x() ||
        point.y() - radius < map->mp_.map_min_boundary_.y() || point.y() + radius > map->mp_.map_max_boundary_.y() ||
        point.z() - map->mp_.obstacles_inflation_z_down < map->mp_.map_min_boundary_.z() ||
        point.z() + map->mp_.obstacles_inflation_z_up > map->mp_.map_max_boundary_.z()) { b.stage = "map_boundary"; return b; }
    reactive_stair::Query query;
    query.frame = map->mp_.frame_id_; query.stamp_s = now_s;
    query.x_m = point.x(); query.y_m = point.y(); query.z_m = point.z();
    query.in_map = map->isInMap(point); b.in_map = query.in_map;
    reactive_stair::NonTerrainVoxel obstacle;
    obstacle.frame = map->mp_.frame_id_; obstacle.stamp_s = map->reactive_cloud_stamp_s_;
    if (map->reactive_cloud_ready_) obstacle.source_id = "scan_lidar_cloud";
    if (query.in_map) {
      Eigen::Vector3i qid; map->posToIndex(point, qid);
      const int address = map->toAddress(qid);
      b.log_odds = map->md_.occupancy_buffer_[address];
      b.inflate = map->md_.occupancy_buffer_inflate_[address];
      if (map->md_.occupancy_buffer_[address] < map->mp_.clamp_min_log_ - 1e-3) {
        obstacle.occupancy = reactive_stair::Occupancy::Unknown;
      } else if (map->md_.occupancy_buffer_inflate_[address] == 0) {
        obstacle.occupancy = reactive_stair::Occupancy::Free;
      } else {
        for (const auto &offset : map->md_.inflate_offsets_) {
          const Eigen::Vector3i source = qid - offset;
          if (!map->isInMap(source) || map->md_.occupancy_buffer_[map->toAddress(source)] <= map->mp_.min_occupancy_log_) continue;
          ++b.contributors;
          const auto key = std::make_tuple(source.x(), source.y(), source.z());
          const bool tr = map->reactive_terrain_hits_.count(key) != 0, nt = map->reactive_nonterrain_hits_.count(key) != 0,
                     hi = map->reactive_nonterrain_history_.count(key) != 0;
          if (reactive_stair::mayWaiveRawContributor(tr, nt, hi)) { ++b.terrain_contributors; continue; }
          Eigen::Vector3d center; map->indexToPos(source, center);
          b.unclassified_xyz.push_back(center);
          ++b.unclassified;
        }
        obstacle.occupancy = !b.contributors ? reactive_stair::Occupancy::Unknown :
            (b.unclassified ? reactive_stair::Occupancy::Occupied : reactive_stair::Occupancy::Free);
      }
    }
    b.raw_class = static_cast<int>(obstacle.occupancy);
    if (map->reactive_known_trunk_enabled_ && query.in_map && map->reactive_body_stamp_s_ > 0.0) {
      Eigen::Vector3i id; map->posToIndex(point, id);
      const Eigen::Vector3d local = map->reactive_body_quaternion_.conjugate() * (point - map->md_.sliding_map_frame_pos_);
      const bool inside = reactive_stair::knownNavigationFootprintInterior(local.x(), local.y(), local.z(), query.stamp_s,
          map->reactive_body_stamp_s_, map->mp_.double_cylinder_radius_, map->mp_.double_cylinder_offset_);
      b.trunk_inside = inside;
      obstacle.occupancy = reactive_stair::measuredTrunkQuery(obstacle.occupancy, map->md_.occupancy_buffer_inflate_[map->toAddress(id)] != 0, inside);
    }
    b.final_class = static_cast<int>(obstacle.occupancy);
    b.native = map->reactiveOccupancy(point, &body);
    {
      reactive_stair::Query q2 = query; q2.z_m = point.z();
      b.support_native = map->reactiveFootprintSupportQuery(body, obstacle, q2) ? 1 : 0;
    }
    if (!support_replica(body, obstacle, query, b)) return b;
    const auto verdict = map->reactive_decision_.decide(query, obstacle);
    b.verdict = static_cast<int>(verdict);
    b.result = verdict == reactive_stair::Verdict::Free ? 0 : 1;
    b.stage = b.result ? "verdict_" + std::to_string(b.verdict) : "free";
    return b;
  };
  const auto vec = [](const Eigen::Vector3d &v) {
    std::ostringstream s; s << std::setprecision(12) << "[" << v.x() << "," << v.y() << "," << v.z() << "]"; return s.str();
  };
  const auto circle_json = [&](const Circle &b) {
    std::ostringstream s; s << std::setprecision(12);
    s << "{\"center\":" << vec(b.center) << ",\"stage\":\"" << b.stage << "\",\"in_map\":" << b.in_map
      << ",\"log_odds\":" << (std::isfinite(b.log_odds) ? b.log_odds : -999.0) << ",\"inflate\":" << b.inflate
      << ",\"contributors\":" << b.contributors << ",\"terrain_contributors\":" << b.terrain_contributors
      << ",\"unclassified\":" << b.unclassified << ",\"raw_class\":" << b.raw_class << ",\"trunk_inside\":" << b.trunk_inside
      << ",\"final_class\":" << b.final_class << ",\"body_verdict\":" << b.body_verdict << ",\"verdict\":" << b.verdict
      << ",\"replicated\":" << b.result << ",\"native\":" << b.native << ",\"support_native\":" << b.support_native
      << ",\"body_ground\":" << (std::isfinite(b.body_ground) ? b.body_ground : -999.0)
      << ",\"footprint_ground\":" << (std::isfinite(b.footprint_ground) ? b.footprint_ground : -999.0)
      << ",\"unclassified_xyz\":[";
    for (size_t i = 0; i < b.unclassified_xyz.size(); ++i) s << (i ? "," : "") << vec(b.unclassified_xyz[i]);
    s << "]}";
    return s.str();
  };
  int circle_mismatches = 0, support_mismatches = 0, query_mismatches = 0;
  // One heading at one point: native getInflateOccupancy and both circles, cross-checked.
  const auto pose_query = [&](const Eigen::Vector3d &p, double yaw, bool full) {
    const int occ = map->getInflateOccupancy(p, yaw);
    const Eigen::Vector3d h(std::cos(yaw), std::sin(yaw), 0.0);
    std::ostringstream s; s << std::setprecision(12);
    int replicated = 0;
    s << "{\"yaw\":" << yaw << ",\"occ\":" << occ;
    for (int side = 0; side < 2; ++side) {
      const Eigen::Vector3d c = p + (side == 0 ? 1.0 : -1.0) * map->mp_.double_cylinder_offset_ * h;
      const Circle b = circle_breakdown(c, p);
      const bool support_replicated = b.stage.rfind("support_", 0) != 0 && b.stage != "map_boundary" &&
                                      b.stage != "surface_not_ready" && b.stage != "nonfinite";
      if (b.native != b.result) ++circle_mismatches;
      if (b.stage != "map_boundary" && b.stage != "surface_not_ready" && (b.support_native == 1) != support_replicated) ++support_mismatches;
      replicated |= b.result;
      if (full) s << ",\"" << (side == 0 ? "front" : "rear") << "\":" << circle_json(b);
      else s << ",\"" << (side == 0 ? "front" : "rear") << "\":\"" << b.stage << "\"";
    }
    if ((occ != 0) != (replicated != 0)) ++query_mismatches;
    s << "}";
    return s.str();
  };
  const auto sweep = [&](const Eigen::Vector3d &p) {
    std::ostringstream s; s << "[";
    for (int d = -180; d < 180; ++d) s << (d > -180 ? "," : "") << pose_query(p, d * M_PI / 180.0, false);
    s << "]";
    return s.str();
  };
  const auto heading_fn = [&](const Eigen::Vector3d &p, const Eigen::Vector3d &ahead, const Eigen::Vector3d &v) {
    return map->collisionTrajectoryYaw(p, ahead, v); };
  const auto occupied_fn = [&](const Eigen::Vector3d &p, double yaw) { return map->getInflateOccupancy(p, yaw) != 0; };
  const auto status_json = [&](const reactive_stair::TrajectoryCheck &c) {
    std::ostringstream s; s << std::setprecision(12) << "{\"status\":" << static_cast<int>(c.status) << ",\"first_time_s\":"
      << c.first_time_s << ",\"duration_s\":" << c.duration_s << ",\"samples\":" << c.samples << "}"; return s.str();
  };

  const double t_cur = std::min(std::max((node->now() - executing.start_time_).seconds(), 0.0), executing.duration_);
  const Eigen::Vector3d start = executing.position_traj_.evaluateDeBoorT(t_cur);
  const Eigen::Vector3d start_vel = executing.velocity_traj_.evaluateDeBoorT(t_cur);
  const Eigen::Vector3d start_acc = executing.acceleration_traj_.evaluateDeBoorT(t_cur);
  const Eigen::Vector3d body_pos = map->md_.sliding_map_frame_pos_;
  const Eigen::Vector3d body_x = map->reactive_body_quaternion_.toRotationMatrix().col(0);
  const double body_yaw = std::atan2(body_x.y(), body_x.x());
  const std::string sweep_start = sweep(start), sweep_body = sweep(body_pos);

  // The live REPLAN_TRAJ entry.
  fsm.planner_manager_->local_data_ = executing;
  std::cout << "[CE-LIVE-BEGIN]" << std::endl;
  local_profile::start();
  const auto budget_started = std::chrono::steady_clock::now();
  const bool live_ok = fsm.planFromCurrentTraj();
  const double budget_elapsed_s = std::chrono::duration<double>(std::chrono::steady_clock::now() - budget_started).count();
  local_profile::stop(); local_profile::report();
  std::cout << "V36_NATIVE_PLAN_BUDGET success=" << live_ok << " wall_s=" << std::setprecision(12) << budget_elapsed_s << " budget_s=" << (1.0/30.0) << " overrun=" << (budget_elapsed_s > 1.0/30.0) << std::endl;
  std::cout << "[CE-LIVE-END] ok=" << live_ok << std::endl;
  std::string live_committed = "null";
  if (live_ok) {
    auto accepted = fsm.planner_manager_->local_data_.position_traj_;
    const auto check = reactive_stair::checkFullCubicTrajectory(accepted, 0.0, map->getResolution(),
        GridMap::collision_heading_lookahead_s, heading_fn, occupied_fn);
    live_committed = "{\"check\":" + status_json(check) + ",\"end\":" + vec(accepted.evaluateDeBoorT(fsm.planner_manager_->local_data_.duration_)) +
        ",\"window\":" + std::to_string(fsm.planner_manager_->global_data_.last_progress_time_) + "}";
  }

  // The first attempt of the live entry, once more, broken down read-only.
  fsm.planner_manager_->local_data_ = executing;
  std::ifstream progress_again(root/"last_progress.txt"); progress_again >> fsm.planner_manager_->global_data_.last_progress_time_;
  fsm.start_pt_ = start; fsm.start_vel_ = start_vel; fsm.start_acc_ = start_acc;
  const bool target_ok = fsm.getLocalTarget();
  const Eigen::Vector3d target = fsm.local_target_pt_, target_vel = fsm.local_target_vel_;
  bool attempted = false;
  std::cout << "[CE-ATTEMPT-BEGIN]" << std::endl;
  const bool attempt_ok = target_ok && fsm.planner_manager_->reboundReplanAttempt(start, start_vel, start_acc, target, target_vel,
                                                                                   true, false, attempted);
  std::cout << "[CE-ATTEMPT-END] ok=" << attempt_ok << " attempted=" << attempted << std::endl;
  auto &opt = *fsm.planner_manager_->bspline_optimizer_rebound_;
  const Eigen::MatrixXd cps = opt.cps_.points;
  const int order = opt.order_, size = opt.cps_.size;
  const int end_idx = size - order, i_end = end_idx - (end_idx - order) / 3;
  std::ostringstream cp_rows; cp_rows << std::setprecision(12);
  std::vector<int> occ(size, -1);
  for (int j = 0; j < size; ++j) {
    const double yaw = opt.estimateControlPointYaw(cps, j);
    occ[j] = map->getInflateOccupancy(cps.col(j), yaw);
    cp_rows << (j ? "," : "") << "{\"index\":" << j << ",\"xyz\":" << vec(cps.col(j)) << ",\"query\":" << pose_query(cps.col(j), yaw, true)
           << ",\"constraints\":" << opt.cps_.direction[j].size() << "}";
  }
  // check_collision_and_rebound's scan, read-only: the first control point that is a new collision, and the
  // backward search from it.
  int first_new = -1, in_id = -2;
  for (int i = order - 1; i <= i_end && first_new < 0; ++i) {
    bool hit = occ[i] != 0;
    if (hit)
      for (size_t k = 0; k < opt.cps_.direction[i].size(); ++k)
        if ((cps.col(i) - opt.cps_.base_point[i][k]).dot(opt.cps_.direction[i][k]) < map->getResolution()) { hit = false; break; }
    if (!hit) continue;
    first_new = i;
    in_id = -1;
    for (int j = i - 1; j >= 0; --j) if (occ[j] == 0) { in_id = j; break; }
  }
  // rebound_optimize's trajectory check, read-only: closest 2/3 of the curve, heading along the curve.
  std::string traj_first = "null";
  {
    scan_planner::UniformBspline traj(cps, 3, opt.bspline_interval_);
    double tm, tmp; traj.getTimeSpan(tm, tmp);
    const double t_step = (tmp - tm) / ((traj.evaluateDeBoorT(tmp) - traj.evaluateDeBoorT(tm)).norm() / map->getResolution());
    for (double t = tm; std::isfinite(t_step) && t_step > 0 && t < tmp * 2 / 3; t += t_step) {
      const Eigen::Vector3d p = traj.evaluateDeBoorT(t), next = traj.evaluateDeBoorT(std::min(t + t_step, tmp));
      const double yaw = opt.estimateSegmentYaw(p, next);
      if (map->getInflateOccupancy(p, yaw)) {
        traj_first = "{\"t\":" + std::to_string(t) + ",\"interval\":" + std::to_string(opt.bspline_interval_) +
                     ",\"within_first_interval\":" + (t <= opt.bspline_interval_ ? "true" : "false") +
                     ",\"xyz\":" + vec(p) + ",\"query\":" + pose_query(p, yaw, true) + "}";
        break;
      }
    }
  }
  std::ofstream result(output); result << std::setprecision(12);
  result << "{\"now_s\":" << node->now().seconds() << ",\"clouds\":" << scans
         << ",\"nav_ground\":\"" << (std::getenv("VLA_NAV_GROUND") ? std::getenv("VLA_NAV_GROUND") : "state") << "\""
         << ",\"executing_traj_id\":" << executing.traj_id_ << ",\"executing_duration_s\":" << executing.duration_ << ",\"t_cur\":" << t_cur
         << ",\"start\":" << vec(start) << ",\"start_vel\":" << vec(start_vel) << ",\"start_acc\":" << vec(start_acc)
         << ",\"body\":" << vec(body_pos) << ",\"body_yaw\":" << body_yaw
         << ",\"body_stamp_s\":" << map->reactive_body_stamp_s_ << ",\"cloud_stamp_s\":" << map->reactive_cloud_stamp_s_
         << ",\"inflation\":{\"radius\":" << map->mp_.double_cylinder_radius_ << ",\"offset\":" << map->mp_.double_cylinder_offset_
         << ",\"z_up\":" << map->mp_.obstacles_inflation_z_up << ",\"z_down\":" << map->mp_.obstacles_inflation_z_down
         << ",\"body_clearance\":" << map->reactive_parameters_.body_clearance_m
         << ",\"body_height_tolerance\":" << map->reactive_parameters_.body_height_tolerance_m
         << ",\"step\":" << reactive_stair::StepScoreParameters{}.critical_height_m << "}"
         << ",\"sweep_start\":" << sweep_start << ",\"sweep_body\":" << sweep_body
         << ",\"live\":{\"ok\":" << (live_ok ? "true" : "false") << ",\"committed\":" << live_committed << "}"
         << ",\"attempt\":{\"target_ok\":" << (target_ok ? "true" : "false") << ",\"target\":" << vec(target) << ",\"target_vel\":" << vec(target_vel)
         << ",\"frontier_s\":" << fsm.reference_frontier_time_ << ",\"target_time_s\":" << fsm.local_target_time_
         << ",\"ok\":" << (attempt_ok ? "true" : "false") << ",\"optimization_attempted\":" << (attempted ? "true" : "false")
         << ",\"order\":" << order << ",\"size\":" << size << ",\"i_end\":" << i_end << ",\"interval\":" << opt.bspline_interval_
         << ",\"first_new_collision\":" << first_new << ",\"backward_free\":" << in_id
         << ",\"inside_replicated\":" << (first_new >= 0 && in_id == -1 ? "true" : "false")
         << ",\"trajectory_first_occupied\":" << traj_first << ",\"control_points\":[" << cp_rows.str() << "]}"
         << ",\"circle_mismatches\":" << circle_mismatches << ",\"support_mismatches\":" << support_mismatches
         << ",\"query_mismatches\":" << query_mismatches << "}\n";
  result.close();
  std::cout << "[CE-ANALYSIS] done circle_mismatches=" << circle_mismatches << " support_mismatches=" << support_mismatches
            << " query_mismatches=" << query_mismatches << std::endl;
  rclcpp::shutdown();
}
