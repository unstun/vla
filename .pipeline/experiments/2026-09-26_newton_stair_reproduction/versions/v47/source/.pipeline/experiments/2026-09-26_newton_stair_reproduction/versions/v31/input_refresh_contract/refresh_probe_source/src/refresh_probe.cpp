#include <atomic>
#include <functional>
#include <set>
#include <type_traits>
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
  auto ground = read_cloud(root / "ground.f32", true);
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
  // ===== v31 input-refresh contract (one case per process) =====
  std::cout << std::setprecision(12);
  const int64_t frozen_ns = now;
  const std::string contract_case = std::getenv("VLA_REFRESH_CASE") ? std::getenv("VLA_REFRESH_CASE") : "";
  const std::string entry_name = std::getenv("VLA_ENTRY_STATE") ? std::getenv("VLA_ENTRY_STATE") : "";
  const std::set<std::string> known_cases{"C1", "C2", "C3", "C4", "C5spin", "C6", "C7spin", "C7refresh"};
  if (!known_cases.count(contract_case)) throw std::runtime_error("Unknown contract case");
  if (entry_name != "GEN_NEW_TRAJ" && entry_name != "REPLAN_TRAJ") throw std::runtime_error("Unknown entry state");
  const auto entry = entry_name == "GEN_NEW_TRAJ" ? scan_planner::SCANReplanFSM::GEN_NEW_TRAJ
                                                  : scan_planner::SCANReplanFSM::REPLAN_TRAJ;
  const bool batched = contract_case == "C7spin" || contract_case == "C7refresh";
  const auto executing = fsm.planner_manager_->local_data_;
  const double delta = contract_case == "C3" ? 0.15 : 0.30;
  const int64_t check_ns = frozen_ns + static_cast<int64_t>(std::llround(delta * 1e9));
  clock(check_ns);
  if (contract_case != "C3") {
    body.header.stamp = rclcpp::Time(check_ns);
    body_pub->publish(body);
    spin(50);
  }
  // The run's own pending inputs, in stamp order; a scan is its sensor pose and cloud.
  struct Pending { int64_t ns; int kind; nav_msgs::msg::Odometry pose; sensor_msgs::msg::PointCloud2 cloud; };
  std::vector<Pending> events;
  if (contract_case != "C1") {
    const char *pending_env = std::getenv("VLA_PENDING_INPUT");
    if (!pending_env) throw std::runtime_error("Missing pending input");
    const fs::path pending(pending_env);
    std::vector<std::tuple<int64_t, int, std::string, std::string>> listed;
    int64_t stamp = 0;
    std::string first, second;
    std::ifstream scans_list(pending / "scans.txt");
    while (scans_list >> stamp >> first >> second) listed.emplace_back(stamp, 0, first, second);
    std::ifstream bodies_list(pending / "bodies.txt");
    while (bodies_list >> stamp >> first) listed.emplace_back(stamp, 1, first, "");
    std::sort(listed.begin(), listed.end());
    if (listed.empty()) throw std::runtime_error("No pending input");
    for (const auto &[event_ns, kind, file, sensor_file] : listed) {
      if (event_ns <= frozen_ns || event_ns > check_ns) throw std::runtime_error("Pending input outside the interval");
      Pending event{event_ns, kind, {}, {}};
      if (kind == 0) {
        event.pose = read_pose(pending / sensor_file);
        event.pose.child_frame_id = "lidar";
        event.cloud = read_cloud(pending / file, false);
        event.cloud.header.stamp = rclcpp::Time(event_ns);
      } else {
        event.pose = read_pose(pending / file);
        event.pose.child_frame_id = "base";
      }
      event.pose.header.stamp = rclcpp::Time(event_ns);
      events.push_back(std::move(event));
    }
  }
  int published_scans = 0, published_bodies = 0;
  std::vector<double> newest_body_xyz;
  const auto publish_pose = [&](const Pending &event) { pose_pub->publish(event.pose); };
  const auto publish_cloud = [&](const Pending &event) { cloud_pub->publish(event.cloud); ++published_scans; };
  const auto publish_body = [&](const Pending &event) {
    body_pub->publish(event.pose);
    ++published_bodies;
    const auto &p = event.pose.pose.pose.position;
    newest_body_xyz = {p.x, p.y, p.z};
  };
  std::vector<int64_t> scan_ns;
  for (const auto &event : events) if (event.kind == 0) scan_ns.push_back(event.ns);
  // C6: everything up to the second scan is pending at the call; the rest is published during it.
  std::vector<std::vector<std::function<void()>>> call_batches;
  if (contract_case == "C6") {
    if (scan_ns.size() < 3) throw std::runtime_error("C6 needs three pending scans");
    std::vector<std::pair<bool, std::function<void()>>> during;  // (starts a batch, action)
    for (const auto &event : events) {
      if (event.ns <= scan_ns[1]) {
        if (event.kind == 0) { publish_pose(event); publish_cloud(event); } else publish_body(event);
      } else if (event.kind == 0) {
        during.emplace_back(false, [&, e = &event] { publish_pose(*e); });
        during.emplace_back(true, [&, e = &event] { publish_cloud(*e); });  // its cloud starts the next batch
      } else {
        during.emplace_back(false, [&, e = &event] { publish_body(*e); });
      }
    }
    for (const auto &[starts, action] : during) {
      if (call_batches.empty() || starts || call_batches.back().size() == 3) call_batches.emplace_back();
      call_batches.back().push_back(action);
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(300));
  } else if (contract_case != "C1" && !batched) {
    for (const auto &event : events) {
      if (event.kind == 0) { publish_pose(event); publish_cloud(event); } else publish_body(event);
    }
    // Delivery without spinning: the messages wait as during a long callback.
    std::this_thread::sleep_for(std::chrono::milliseconds(300));
  }
  if (contract_case == "C5spin") spin(500);
  const double now_before = node->now().seconds();
  const double cloud_stamp_before = map->reactive_cloud_stamp_s_;
  const double body_stamp_before = map->reactive_body_stamp_s_;
  double call_ms = 0.0;
  int batches_total = 0, batches_before_call_end = 0;
  std::ostringstream batch_record;
  if (batched) {
    // C7: the same five batches, then an executor spin or one direct refresh each.
    if (scan_ns.size() < 3) throw std::runtime_error("C7 needs three pending scans");
    const auto refresh = [](auto &grid) -> decltype(grid.refreshSensorInputs("probe"), void()) {
      grid.refreshSensorInputs("probe");
    };
    // Instantiated only for the build's GridMap, so the red build compiles without the method.
    const auto try_refresh = [&](auto &grid) {
      if constexpr (std::is_invocable_v<decltype(refresh), decltype(grid)>) { refresh(grid); return true; }
      else return false;
    };
    std::vector<std::vector<std::function<void()>>> batches(5);
    for (const auto &event : events) {
      const Pending *e = &event;
      if (event.kind == 0 && event.ns == scan_ns[0]) {
        batches[0].push_back([&, e] { publish_pose(*e); });
        batches[0].push_back([&, e] { publish_cloud(*e); });
      } else if (event.kind == 0 && event.ns == scan_ns[1]) {
        batches[1].push_back([&, e] { publish_pose(*e); });
        batches[2].push_back([&, e] { publish_cloud(*e); });
      } else if (event.kind == 0 && event.ns == scan_ns[2]) {
        batches[3].push_back([&, e] { publish_cloud(*e); });
        batches[4].push_back([&, e] { publish_pose(*e); });
      } else if (event.kind == 0) {
        throw std::runtime_error("C7 expects exactly three pending scans");
      } else {
        batches[event.ns <= scan_ns[0] ? 0 : event.ns <= scan_ns[1] ? 2 : 4].push_back([&, e] { publish_body(*e); });
      }
    }
    std::cout << "[CONTRACT-CALL-BEGIN] case=" << contract_case << " entry=" << entry_name << std::endl;
    batch_record << "[";
    for (size_t b = 0; b < batches.size(); ++b) {
      for (const auto &action : batches[b]) action();
      std::this_thread::sleep_for(std::chrono::milliseconds(100));
      if (contract_case == "C7spin") spin(100);
      else if (!try_refresh(*map)) throw std::runtime_error("This build has no GridMap::refreshSensorInputs");
      const auto &md = map->md_;
      batch_record << (b ? "," : "") << "{\"batch\":" << b + 1 << ",\"cloud_stamp_s\":" << map->reactive_cloud_stamp_s_
                   << ",\"ray_pos\":[" << md.ray_pos_.x() << "," << md.ray_pos_.y() << "," << md.ray_pos_.z()
                   << "],\"body_stamp_s\":" << map->reactive_body_stamp_s_ << "}";
    }
    batch_record << "]";
    std::cout << "[CONTRACT-CALL-END] exec_state=" << static_cast<int>(fsm.exec_state_) << std::endl;
  } else {
    fsm.planner_manager_->local_data_ = executing;
    fsm.changeFSMExecState(entry, "CONTRACT");
    std::atomic<int> batches_published{0};
    std::thread helper;
    batches_total = static_cast<int>(call_batches.size());
    std::cout << "[CONTRACT-CALL-BEGIN] case=" << contract_case << " entry=" << entry_name << std::endl;
    const auto wall_start = std::chrono::steady_clock::now();
    if (contract_case == "C6") {
      helper = std::thread([&] {
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
        for (const auto &batch : call_batches) {
          for (const auto &action : batch) action();
          ++batches_published;
          std::this_thread::sleep_for(std::chrono::milliseconds(25));
        }
      });
    }
    if (contract_case == "C4" || contract_case == "C6") fsm.execFSMCallback();
    else fsm.checkCollisionCallback();
    call_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - wall_start).count();
    batches_before_call_end = batches_published.load();
    std::cout << "[CONTRACT-CALL-END] exec_state=" << static_cast<int>(fsm.exec_state_) << std::endl;
    if (helper.joinable()) helper.join();
    // Whatever is still pending goes through the executor, so the final map holds every input.
    if (contract_case == "C6") spin(500);
  }
  const double now_after = node->now().seconds();
  auto traj = executing.position_traj_;
  const double raw_t = (node->now() - executing.start_time_).seconds();
  const auto safety = reactive_stair::checkFullCubicTrajectory(
      traj, raw_t, map->getResolution(), GridMap::collision_heading_lookahead_s,
      [&map](const Eigen::Vector3d &p, const Eigen::Vector3d &ahead, const Eigen::Vector3d &v) {
        return map->collisionTrajectoryYaw(p, ahead, v);
      },
      [&map](const Eigen::Vector3d &p, double yaw) { return map->getInflateOccupancy(p, yaw) != 0; });
  // FNV-1a over the state that pose and scan processing writes.
  uint64_t digest = 1469598103934665603ULL;
  const auto mix = [&digest](const void *data, size_t size) {
    const auto *bytes = static_cast<const unsigned char *>(data);
    for (size_t i = 0; i < size; ++i) { digest ^= bytes[i]; digest *= 1099511628211ULL; }
  };
  const auto &md = map->md_;
  const auto &mp = map->mp_;
  mix(md.occupancy_buffer_.data(), md.occupancy_buffer_.size() * sizeof(double));
  mix(md.occupancy_buffer_inflate_.data(), md.occupancy_buffer_inflate_.size());
  mix(md.occupancy_buffer_inflate_cnt_.data(), md.occupancy_buffer_inflate_cnt_.size() * sizeof(int));
  for (const auto *keys : {&map->reactive_terrain_hits_, &map->reactive_nonterrain_hits_,
                           &map->reactive_nonterrain_history_}) {
    const size_t count = keys->size();
    mix(&count, sizeof(count));
    for (const auto &key : *keys) {
      const int values[3] = {std::get<0>(key), std::get<1>(key), std::get<2>(key)};
      mix(values, sizeof(values));
    }
  }
  const double scalars[] = {map->reactive_cloud_stamp_s_, map->reactive_body_stamp_s_,
                            md.ray_pos_.x(), md.ray_pos_.y(), md.ray_pos_.z(),
                            md.ray_q_.w(), md.ray_q_.x(), md.ray_q_.y(), md.ray_q_.z(),
                            md.sliding_map_frame_pos_.x(), md.sliding_map_frame_pos_.y(), md.sliding_map_frame_pos_.z(),
                            map->reactive_body_quaternion_.w(), map->reactive_body_quaternion_.x(),
                            map->reactive_body_quaternion_.y(), map->reactive_body_quaternion_.z(),
                            mp.map_origin_.x(), mp.map_origin_.y(), mp.map_origin_.z()};
  mix(scalars, sizeof(scalars));
  const int indices[] = {mp.map_origin_idx_.x(), mp.map_origin_idx_.y(), mp.map_origin_idx_.z(),
                         md.local_bound_min_.x(), md.local_bound_min_.y(), md.local_bound_min_.z(),
                         md.local_bound_max_.x(), md.local_bound_max_.y(), md.local_bound_max_.z(),
                         static_cast<int>(map->reactive_cloud_ready_), static_cast<int>(md.has_cloud_),
                         static_cast<int>(md.has_ray_pose_)};
  mix(indices, sizeof(indices));
  std::ostringstream digest_hex;
  digest_hex << std::hex << std::setw(16) << std::setfill('0') << digest;
  const char *status_names[] = {"Clear", "Collision", "InvalidCurve"};
  const int status = static_cast<int>(safety.status);
  const auto xyz = [](const auto &v) {
    std::ostringstream s;
    s << std::setprecision(12) << "[" << v[0] << "," << v[1] << "," << v[2] << "]";
    return s.str();
  };
  std::ofstream result(output);
  result << std::setprecision(12);
  result << "{\"case\":\"" << contract_case << "\",\"entry\":\"" << entry_name << "\",\"frozen_ns\":" << frozen_ns
         << ",\"check_ns\":" << check_ns << ",\"published_scans\":" << published_scans
         << ",\"published_bodies\":" << published_bodies << ",\"now_before_s\":" << now_before
         << ",\"cloud_age_before_s\":" << now_before - cloud_stamp_before
         << ",\"body_age_before_s\":" << now_before - body_stamp_before << ",\"now_after_s\":" << now_after
         << ",\"cloud_stamp_after_s\":" << map->reactive_cloud_stamp_s_
         << ",\"cloud_age_after_s\":" << now_after - map->reactive_cloud_stamp_s_
         << ",\"body_age_after_s\":" << now_after - map->reactive_body_stamp_s_
         << ",\"exec_state_after\":" << static_cast<int>(fsm.exec_state_) << ",\"call_wall_ms\":" << call_ms
         << ",\"call_batches\":" << batches_total << ",\"call_batches_before_call_end\":" << batches_before_call_end
         << ",\"batches\":" << (batched ? batch_record.str() : std::string("null"))
         << ",\"fsm_odom_xyz\":" << xyz(fsm.odom_pos_) << ",\"map_body_xyz\":" << xyz(md.sliding_map_frame_pos_)
         << ",\"newest_pending_body_xyz\":" << (newest_body_xyz.empty() ? std::string("null") : xyz(newest_body_xyz))
         << ",\"recheck\":{\"status\":\"" << (status >= 0 && status < 3 ? status_names[status] : "Other")
         << "\",\"first_time_s\":" << safety.first_time_s << ",\"samples\":" << safety.samples
         << ",\"raw_t\":" << raw_t << "},\"map_digest\":\"" << digest_hex.str() << "\"}\n";
  result.close();
  std::cout << "[CONTRACT] done case=" << contract_case << " exec_state=" << static_cast<int>(fsm.exec_state_)
            << " recheck=" << status << " digest=" << digest_hex.str() << std::endl;
  rclcpp::shutdown();
}
