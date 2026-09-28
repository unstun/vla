// Actual native subscriptions, ray updates, footprint queries and AStar.
// Input files contain sensor measurements and ground support, not object labels.
#include <path_searching/dyn_a_star.h>
#include <plan_env/raw_return_classification.h>
#include <cstring>
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
  for(int kind=0;kind<5;++kind){
    auto broken=surface;
    if(kind==0) broken.fields[2].offset=0;
    if(kind==1) broken.data.pop_back();
    if(kind==2) broken.is_bigendian=true;
    if(kind==3) broken.row_step-=4;
    if(kind==4) broken.point_step=12;
    surface_pub->publish(broken);spin(50);
    if(map->reactiveSurfaceGroundReady()) throw std::runtime_error("Malformed surface layout accepted");
  }
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
  auto future_nav=ground;future_nav.header.stamp=rclcpp::Time(now+1000000000);
  ground_pub->publish(future_nav);spin(60);
  if(map->reactiveSurfaceGroundReady()) throw std::runtime_error("Future selected map accepted");
  ground_pub->publish(ground);spin(60);
  const double saved_age=map->reactive_parameters_.terrain_max_age_s;
  map->reactive_parameters_.terrain_max_age_s=.05;
  clock(now+100000000);
  auto fresh_surface=surface;fresh_surface.header.stamp=rclcpp::Time(now+100000000);
  surface_pub->publish(fresh_surface);spin(60);
  if(map->reactiveSurfaceGroundReady()) throw std::runtime_error("Expired selected map accepted");
  map->reactive_parameters_.terrain_max_age_s=saved_age;
  clock(now);surface_pub->publish(surface);ground_pub->publish(ground);spin(80);
  if(!map->reactiveSurfaceGroundReady()) throw std::runtime_error("Contract setup did not restore valid maps");
  std::cout<<"[SURFACE-GATE] missing/wrong-frame/future/order/navigation-support checks passed"<<std::endl;
  std::ifstream listing(root / "clouds.txt");
  std::string file;
  size_t scans = 0;
  while (listing >> file) {
    now += 100000000;
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
    break; // One actual measured scan is sufficient for evidence-revocation testing.
  }
  if (!scans) throw std::runtime_error("No measured scans");
  std::cout<<"[CONTRACT-STATE] now="<<node->now().seconds()<<" ready="<<map->reactiveSurfaceGroundReady()<<" ground_stamp="<<map->reactive_ground_.stamp_s<<" surface_stamp="<<map->reactive_surface_ground_.stamp_s<<" max_age="<<map->reactive_parameters_.terrain_max_age_s<<" ray_pose="<<map->md_.has_ray_pose_<<" cloud="<<map->md_.has_cloud_<<" projected="<<map->md_.proj_points_cnt<<" terrain="<<map->reactive_terrain_hits_.size()<<" history="<<map->reactive_nonterrain_history_.size()<<std::endl;
  if(map->reactive_terrain_hits_.empty()) throw std::runtime_error("Measured scan did not grant terrain evidence");
  const auto granted=map->reactive_terrain_hits_;
  const auto obstacle_history=map->reactive_nonterrain_history_;
  auto withdrawn=surface;
  for(size_t offset=8;offset<withdrawn.data.size();offset+=16){
    float z;std::memcpy(&z,withdrawn.data.data()+offset,4);z+=1.f;std::memcpy(withdrawn.data.data()+offset,&z,4);
  }
  surface_pub->publish(withdrawn);spin(80);
  if(!map->reactiveSurfaceGroundReady() || !map->reactive_terrain_hits_.empty() ||
     map->reactive_nonterrain_history_!=obstacle_history)
    throw std::runtime_error("Changed surface retained positive evidence or cleared obstacles");
  // A fresh scan which does not revisit every old endpoint must not renew the
  // old grants. Use one original measured endpoint, with its original pose.
  auto sparse=read_cloud(root/file,false);sparse.width=1;sparse.row_step=12;sparse.data.resize(12);
  now+=100000000;clock(now);body.header.stamp=sensor.header.stamp=rclcpp::Time(now);
  body_pub->publish(body);pose_pub->publish(sensor);spin(40);sparse.header.stamp=rclcpp::Time(now);
  cloud_pub->publish(sparse);spin(80);
  size_t retained=0;for(const auto &key:granted) retained+=map->reactive_terrain_hits_.count(key);
  if(granted.size()<2 || retained>1) throw std::runtime_error("Unobserved old grants survived source change");
  std::ofstream result(output);
  result<<"{\"malformed_layouts_rejected\":5,\"missing_and_wrong_frame_rejected\":true,\"both_input_times_checked\":true,\"original_granted_voxels\":"<<granted.size()<<",\"old_grants_after_one_point\":"<<retained<<",\"obstacle_history_preserved_on_source_update\":true}\n";
  rclcpp::shutdown();
}
