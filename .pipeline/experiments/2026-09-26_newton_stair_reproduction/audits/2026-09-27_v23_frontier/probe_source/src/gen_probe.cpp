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
  if(std::getenv("VLA_FULL_RAW_RISER")) {
    const auto support_id=map->reactive_terrain_.source_id;
    map->reactive_ground_=map->reactive_surface_ground_;
    if(map->reactive_terrain_.source_id!=support_id) throw std::runtime_error("Scored support changed");
    std::cout<<"[RAW-RISER-DIAGNOSTIC] existing riser rule uses uninflated-cost source; scored support unchanged"<<std::endl;
  }
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
  fsm.setStartStateFromOdomOrCurrentTraj();
  const Eigen::Vector3d original_start=fsm.start_pt_;
  const bool target_ok=fsm.getLocalTarget();
  const auto target=fsm.local_target_pt_;
  const double frontier=fsm.reference_frontier_time_;
  const double target_distance=(target-original_start).norm();
  const double yaw=fsm.estimateYawFromSegment(original_start,target);
  const int target_occupied=map->getInflateOccupancy(target,yaw);
  const double start_yaw=map->collisionSegmentYaw(original_start,target);
  const int start_occupied=map->getInflateOccupancy(original_start,start_yaw);
  const bool straight_segment_clear=map->collisionFreeSegment(original_start,target);
  std::cout<<"[FRONTIER-AUDIT] start_occupied="<<start_occupied<<" straight_segment_clear="<<straight_segment_clear<<" target_occupied="<<target_occupied<<std::endl;
  map->logInitialSplineCollision(original_start,start_yaw);
  const Eigen::Vector3d expected_velocity=fsm.start_vel_, expected_acceleration=fsm.start_acc_;
  const Eigen::Vector3d expected_target_velocity=fsm.local_target_vel_;
  const Eigen::Vector3d original_goal=fsm.end_pt_;
  const auto saved_local=fsm.planner_manager_->local_data_;
  const bool continued=fsm.callReboundReplan(true,false);
  bool boundary_ok=false, full_clear=false;
  double accepted_displacement=0.;
  if(continued) {
    auto accepted=fsm.planner_manager_->local_data_.position_traj_;
    const auto accepted_target=fsm.local_target_pt_;
    boundary_ok=reactive_stair::matchesBoundaryPva(accepted,original_start,accepted_target,
      {expected_velocity,fsm.local_target_vel_,expected_acceleration,Eigen::Vector3d::Zero()});
    const auto collision=reactive_stair::checkFullCubicTrajectory(accepted,0.,map->getResolution(),GridMap::collision_heading_lookahead_s,
      [&](const Eigen::Vector3d &p,const Eigen::Vector3d &ahead,const Eigen::Vector3d &velocity){return map->collisionTrajectoryYaw(p,ahead,velocity);},
      [&](const Eigen::Vector3d &p,double heading){return map->getInflateOccupancy(p,heading)!=0;});
    full_clear=collision.clear();accepted_displacement=(accepted_target-original_start).head<2>().norm();
  }

  std::ofstream queries(fs::path(output).parent_path() / (fs::path(output).stem().string()+"_queries.csv"));
  queries<<std::setprecision(17)<<"kind,t,x,y,z,yaw,active_occupied,raw_front_inflate,raw_rear_inflate,front_unknown,rear_unknown,front_support_count,rear_support_count,translation_ok\n";
  auto inspect=[&](const std::string &kind,double t,const Eigen::Vector3d &p,double heading){
    const Eigen::Vector3d direction(std::cos(heading),std::sin(heading),0.);
    const Eigen::Vector3d front=p+map->mp_.double_cylinder_offset_*direction;
    const Eigen::Vector3d rear=p-map->mp_.double_cylinder_offset_*direction;
    auto supports=[&](const Eigen::Vector3d &q){
      const auto &terrain=map->reactive_terrain_;
      const reactive_stair::Cell2 cell{static_cast<int>(std::floor((q.x()-terrain.origin_x_m)/terrain.resolution_m)),static_cast<int>(std::floor((q.y()-terrain.origin_y_m)/terrain.resolution_m))};
      const auto found=terrain.cells.find(cell);
      return found==terrain.cells.end()?size_t(0):found->second.size();
    };
    queries<<kind<<","<<t<<","<<p.x()<<","<<p.y()<<","<<p.z()<<","<<heading<<","<<map->getInflateOccupancy(p,heading)<<","<<map->getInflateOccupancyFromBuffer(front,map->md_.occupancy_buffer_inflate_)<<","<<map->getInflateOccupancyFromBuffer(rear,map->md_.occupancy_buffer_inflate_)<<","<<map->isUnknown(front)<<","<<map->isUnknown(rear)<<","<<supports(front)<<","<<supports(rear)<<","<<fsm.planner_manager_->hasLocalTranslation(original_start,p)<<"\n";
  };
  inspect("rejected_target",fsm.local_target_time_,target,yaw);
  map->logInitialSplineCollision(target,yaw);
  for(double t=0.;t<=fsm.planner_manager_->global_data_.global_duration_;t+=.05){
    const auto p=fsm.planner_manager_->global_data_.global_traj_.evaluate(t);
    const auto ahead=fsm.planner_manager_->global_data_.global_traj_.evaluate(std::min(t+.05,fsm.planner_manager_->global_data_.global_duration_));
    inspect("reference_tangent",t,p,fsm.estimateYawFromSegment(p,ahead));
  }
  // Read-only diagnosis of the first blocked stair query and native support scores.
  std::cout<<std::setprecision(17);
  const auto detail=[&](const Eigen::Vector3d &q,const std::string &label){
    Eigen::Vector3i id;map->posToIndex(q,id);
    const auto &terrain=map->reactive_terrain_;
    const reactive_stair::Cell2 cell{static_cast<int>(std::floor((q.x()-terrain.origin_x_m)/terrain.resolution_m)),static_cast<int>(std::floor((q.y()-terrain.origin_y_m)/terrain.resolution_m))};
    std::cout<<"[DETAIL] "<<label<<" xyz="<<q.transpose()<<" cell="<<cell.x<<","<<cell.y<<" raw_unknown="<<map->isUnknown(q)<<" inflation="<<map->getInflateOccupancyFromBuffer(q,map->md_.occupancy_buffer_inflate_)<<std::endl;
    const auto entry=terrain.cells.find(cell);
    if(entry!=terrain.cells.end()) for(size_t i=0;i<entry->second.size();++i){
      const auto &surface=entry->second[i];const auto &score=map->reactive_step_result_.scores.at(cell)[i];
      std::cout<<"[SUPPORT] "<<label<<" z="<<surface.elevation_m<<" status="<<static_cast<int>(surface.support)<<" known="<<score.known<<" first_height="<<score.first_pass_height_m<<" score="<<score.score<<std::endl;
    }
    std::map<std::string,int> contributor_types;int printed=0;
    for(const auto &offset:map->md_.inflate_offsets_){
      Eigen::Vector3i source=id-offset;
      if(!map->isInMap(source)||map->md_.occupancy_buffer_[map->toAddress(source)]<=map->mp_.min_occupancy_log_)continue;
      const auto key=std::make_tuple(source.x(),source.y(),source.z());
      bool tr=map->reactive_terrain_hits_.count(key), nt=map->reactive_nonterrain_hits_.count(key), history=map->reactive_nonterrain_history_.count(key);
      contributor_types[std::to_string(tr)+std::to_string(nt)+std::to_string(history)]++;
      if((!tr||nt||history)&&printed++<12){Eigen::Vector3d center;map->indexToPos(source,center);std::cout<<"[BLOCKING_CONTRIBUTOR] "<<label<<" xyz="<<center.transpose()<<" flags="<<tr<<nt<<history<<" ground_return_at_voxel_center="<<map->reactiveTerrainReturn(center)<<std::endl;}
    }
    for(const auto &entry:contributor_types)std::cout<<"[CONTRIBUTORS] "<<label<<" terrain_nonterrain_history="<<entry.first<<" count="<<entry.second<<std::endl;
  };
  for(const auto &item:std::vector<std::pair<std::string,Eigen::Vector3d>>{{"actual_start",original_start},{"target",target}}){
    const Eigen::Vector3d direction(std::cos(yaw),std::sin(yaw),0.);
    detail(item.second+map->mp_.double_cylinder_offset_*direction,item.first+"_front");
    detail(item.second-map->mp_.double_cylinder_offset_*direction,item.first+"_rear");
  }
  for(double t:{2.2,2.3,2.471185370848,2.842370741697,3.584741483394}){
    const auto point=fsm.planner_manager_->global_data_.global_traj_.evaluate(t);
    const double heading=fsm.estimateYawFromSegment(original_start,point);
    const Eigen::Vector3d dir(std::cos(heading),std::sin(heading),0.);
    const auto label="prefix_"+std::to_string(t);
    std::cout<<"[PREFIX_QUERY] t="<<t<<" yaw="<<heading<<" occupancy="<<map->getInflateOccupancy(point,heading)<<std::endl;
    detail(point+map->mp_.double_cylinder_offset_*dir,label+"_front");
    detail(point-map->mp_.double_cylinder_offset_*dir,label+"_rear");
  }
  for(double heading:{-1.994691,-1.5707963267948966,2.54264767,-1.57547993}){
    std::cout<<"[FIXED_START_YAW] yaw="<<heading<<" occupancy="<<map->getInflateOccupancy(original_start,heading)<<std::endl;
  }
  std::ofstream result(output);result<<std::setprecision(17);
  result<<"{\"now_s\":"<<node->now().seconds()<<",\"clouds\":"<<scans<<",\"start\":["<<original_start.x()<<","<<original_start.y()<<","<<original_start.z()<<"],\"target\":["<<target.x()<<","<<target.y()<<","<<target.z()<<"],\"frontier_time_s\":"<<frontier<<",\"target_distance_m\":"<<target_distance<<",\"accepted_xy_displacement_m\":"<<accepted_displacement<<",\"start_occupied\":"<<start_occupied<<",\"target_occupied\":"<<target_occupied<<",\"straight_clear\":"<<(straight_segment_clear?"true":"false")<<",\"get_local_target\":"<<(target_ok?"true":"false")<<",\"continued\":"<<(continued?"true":"false")<<",\"has_translation\":"<<(fsm.planner_manager_->hasLocalTranslation(original_start,target)?"true":"false")<<",\"boundary_pass\":"<<(boundary_ok?"true":"false")<<",\"full_clear\":"<<(full_clear?"true":"false")<<"}\n";
  result.close();
  std::ofstream negatives(fs::path(output).parent_path()/(fs::path(output).stem().string()+"_negatives.json"));
  const bool no_progress=!fsm.planner_manager_->hasLocalTranslation(original_start,original_start);
  const bool unknown_blocked=map->getInflateOccupancy(Eigen::Vector3d(1e6,1e6,1e6),0.)!=0;
  clock(now+500000000);
  fsm.setStartStateFromOdomOrCurrentTraj();
  const bool stale_rejected=!fsm.callReboundReplan(true,false);
  negatives<<"{\"no_progress_rejected\":"<<no_progress<<",\"out_of_map_blocked\":"<<unknown_blocked<<",\"stale_rejected\":"<<stale_rejected<<"}\n";
  negatives.close();
  if(!fsm.planner_manager_->bspline_optimizer_rebound_->optimizesHeight())
    throw std::runtime_error("Configured height mode leaked after complete planner calls");
  std::cout << "[RECOVERY-STATE] configured_height_mode_restored=1" << std::endl;
  rclcpp::shutdown();
}
