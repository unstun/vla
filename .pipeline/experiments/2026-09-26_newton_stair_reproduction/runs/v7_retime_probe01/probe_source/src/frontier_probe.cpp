// Actual native subscriptions, ray updates, footprint queries and AStar.
// Input files contain sensor measurements and ground support, not object labels.
#include <path_searching/dyn_a_star.h>
#include <plan_manage/scan_replan_fsm.h>
#include <plan_manage/minimum_cruise.h>
#include <rclcpp/serialization.hpp>
#include <cstring>
#include <limits>
#include <bspline_opt/full_trajectory_collision.h>
#include <bspline_opt/bspline_optimizer.h>
#include <bspline_opt/timed_cubic_initialization.h>
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

  std::ifstream curves("/version/recorded_curves.txt");
  std::string name;
  bool found=false;
  while(curves>>name) {
    int count,knot_count;curves>>count>>knot_count;
    Eigen::MatrixXd controls(3,count);Eigen::VectorXd knots(knot_count);
    for(int i=0;i<count;++i) for(int axis=0;axis<3;++axis) curves>>controls(axis,i);
    for(int i=0;i<knot_count;++i) curves>>knots[i];
    if(!curves) throw std::runtime_error("Incomplete captured curve");
    if(name!="flat_3") continue;
    found=true;
    scan_planner::UniformBspline curve(controls,3,knots[4]-knots[3]);curve.setKnot(knots);
    auto velocity=curve.getDerivative(),acceleration=velocity.getDerivative();
    const double original_duration=curve.getTimeSum();
    const Eigen::Vector3d start=curve.evaluateDeBoorT(0.),end=curve.evaluateDeBoorT(original_duration);
    std::vector<Eigen::Vector3d> boundary{velocity.evaluateDeBoorT(0.),velocity.evaluateDeBoorT(original_duration),acceleration.evaluateDeBoorT(0.),acceleration.evaluateDeBoorT(original_duration)};
    const auto before=scan_planner::measureMinimumCruise(curve,.6,.5,4.);
    auto collision_check=[&](scan_planner::UniformBspline candidate){
      return reactive_stair::checkFullCubicTrajectory(candidate,0.,map->getResolution(),GridMap::collision_heading_lookahead_s,
        [&](const Eigen::Vector3d &p,const Eigen::Vector3d &ahead,const Eigen::Vector3d &v){return map->collisionTrajectoryYaw(p,ahead,v);},
        [&](const Eigen::Vector3d &p,double heading){return map->getInflateOccupancy(p,heading)!=0;}).clear();
    };
    const bool original_clear=collision_check(curve);
    double interval=knots[4]-knots[3];
    const bool accepted=fsm.planner_manager_->enforceMinimumCruise(curve,boundary,interval);
    const auto after=scan_planner::measureMinimumCruise(curve,.6,.5,4.);
    const bool pva=reactive_stair::matchesBoundaryPva(curve,start,end,boundary);
    curve.setPhysicalLimits(1.,.5,.5);double ratio=0.;
    const bool dynamics=curve.checkFeasibility(ratio,false)&&fsm.planner_manager_->checkDynamicFeasibility(curve);
    const bool final_clear=collision_check(curve);
    const bool passed=!before.passed&&accepted&&after.passed&&pva&&dynamics&&original_clear&&final_clear;
    std::ofstream result(output);result<<std::setprecision(17)
      <<"{\"passed\":"<<passed<<",\"original_clear\":"<<original_clear<<",\"before_min\":"<<before.minimum_speed
      <<",\"before_duration\":"<<original_duration<<",\"native_enforce_return\":"<<accepted<<",\"after_min\":"<<after.minimum_speed
      <<",\"after_duration\":"<<curve.getTimeSum()<<",\"boundary_pva\":"<<pva<<",\"dynamic_limits\":"<<dynamics<<",\"final_curve_clear\":"<<final_clear<<"}\n";
    result.close();
  }
  if(!found) throw std::runtime_error("Missing original flat_3 curve");
  rclcpp::shutdown();
}
