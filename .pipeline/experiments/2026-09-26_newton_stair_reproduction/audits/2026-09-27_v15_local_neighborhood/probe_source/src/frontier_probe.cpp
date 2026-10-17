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
  const Eigen::Vector3d original_start=fsm.start_pt_;
  auto route=std::make_shared<scan_planner_msgs::msg::P2BRoute>(read_message<scan_planner_msgs::msg::P2BRoute>(root/"route.cdr"));
  fsm.p2bRouteCallback(route);
  if(!fsm.have_target_) throw std::runtime_error("Original route not accepted");
  fsm.have_new_target_=false;
  std::ifstream progress(root/"last_progress.txt");progress>>fsm.planner_manager_->global_data_.last_progress_time_;
  const bool target_ok=fsm.getLocalTarget();
  const auto target=fsm.local_target_pt_;
  const double frontier=fsm.reference_frontier_time_;
  const double target_distance=(target-original_start).norm();
  const double yaw=fsm.estimateYawFromSegment(fsm.odom_pos_,target);
  const int target_occupied=map->getInflateOccupancy(target,yaw);
  const double start_yaw=map->collisionSegmentYaw(original_start,target);
  const int start_occupied=map->getInflateOccupancy(original_start,start_yaw);
  const bool straight_segment_clear=map->collisionFreeSegment(original_start,target);
  std::cout<<"[FRONTIER-AUDIT] start_occupied="<<start_occupied<<" straight_segment_clear="<<straight_segment_clear<<" target_occupied="<<target_occupied<<std::endl;
  map->logInitialSplineCollision(original_start,start_yaw);
  const Eigen::Vector3d expected_velocity=fsm.start_vel_, expected_acceleration=fsm.start_acc_;
  const Eigen::Vector3d expected_target_velocity=fsm.local_target_vel_;
  const Eigen::Vector3d original_goal=fsm.end_pt_;
  const bool continued=fsm.planFromCurrentTraj();
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
  for(double t:{1.0,1.25,1.5,2.0,2.5,3.0}){
    const auto point=fsm.planner_manager_->global_data_.global_traj_.evaluate(t);
    const auto ahead=fsm.planner_manager_->global_data_.global_traj_.evaluate(t+.05);
    const double heading=fsm.estimateYawFromSegment(point,ahead);
    map->logInitialSplineCollision(point,heading);
    const Eigen::Vector3d direction(std::cos(heading),std::sin(heading),0.);
    detail(point+map->mp_.double_cylinder_offset_*direction,"t"+std::to_string(t)+"front");
    detail(point-map->mp_.double_cylinder_offset_*direction,"t"+std::to_string(t)+"rear");
  }
  detail(original_start+map->mp_.double_cylinder_offset_*Eigen::Vector3d(std::cos(start_yaw),std::sin(start_yaw),0.),"start_front");
  detail(original_start-map->mp_.double_cylinder_offset_*Eigen::Vector3d(std::cos(start_yaw),std::sin(start_yaw),0.),"start_rear");
  detail(target+map->mp_.double_cylinder_offset_*Eigen::Vector3d(std::cos(yaw),std::sin(yaw),0.),"rejected_target_front");
  std::ofstream alternatives(fs::path(output).parent_path()/"neighborhoods.json");
  alternatives<<std::setprecision(17)<<"[";
  bool comma=false;
  for(double proposal_t:{2.711835789595,1.880917894797,1.465458947399}) {
    const Eigen::Vector3d proposal=fsm.planner_manager_->global_data_.getPosition(proposal_t);
    const double tolerance=std::min(fsm.goal_neighbor_tolerance_,.5*(proposal-original_start).head<2>().norm());
    const auto path=fsm.planner_manager_->findGoalNeighborhoodPath(original_start,proposal,tolerance);
    bool planned=false,pva=false,clear=false,progress=false;
    Eigen::Vector3d selected=original_start;
    double projected=0.,best=std::numeric_limits<double>::infinity();
    if(path.size()>1) {
      selected=path.back();
      for(double t=0.;t<=proposal_t;t+=.01){
        const double distance=(fsm.planner_manager_->global_data_.getPosition(t)-selected).squaredNorm();
        if(distance<best){best=distance;projected=t;}
      }
      progress=fsm.planner_manager_->hasLocalTranslation(original_start,selected) &&
          (selected-original_start).head<2>().dot((proposal-original_start).head<2>())>0. &&
          projected>fsm.local_projection_time_;
      if(progress) planned=fsm.planner_manager_->reboundReplan(original_start,expected_velocity,expected_acceleration,
          selected,Eigen::Vector3d::Zero(),true,false);
      if(planned){
        const auto accepted=fsm.planner_manager_->local_data_.position_traj_;
        pva=reactive_stair::matchesBoundaryPva(accepted,original_start,selected,
            {expected_velocity,Eigen::Vector3d::Zero(),expected_acceleration,Eigen::Vector3d::Zero()});
        clear=reactive_stair::checkFullCubicTrajectory(accepted,0.,map->getResolution(),GridMap::collision_heading_lookahead_s,
          [&](const Eigen::Vector3d &q,const Eigen::Vector3d &ahead,const Eigen::Vector3d &v){return map->collisionTrajectoryYaw(q,ahead,v);},
          [&](const Eigen::Vector3d &q,double heading){return map->getInflateOccupancy(q,heading)!=0;}).clear();
      }
    }
    if(comma) alternatives<<",";comma=true;
    alternatives<<"{\"candidate_t\":"<<proposal_t<<",\"tolerance\":"<<tolerance<<",\"nodes\":"<<path.size()
      <<",\"selected\":["<<selected.x()<<","<<selected.y()<<","<<selected.z()<<"],\"projection_t\":"<<projected
      <<",\"progress\":"<<progress<<",\"planned\":"<<planned<<",\"pva\":"<<pva<<",\"clear\":"<<clear<<"}";
  }
  alternatives<<"]\n";alternatives.close();
  std::ofstream result(output);result<<std::setprecision(17);
  result<<"{\"now_s\":"<<node->now().seconds()<<",\"clouds\":"<<scans<<",\"start\":["<<original_start.x()<<","<<original_start.y()<<","<<original_start.z()<<"],\"target\":["<<target.x()<<","<<target.y()<<","<<target.z()<<"],\"frontier_time_s\":"<<frontier<<",\"target_distance_m\":"<<target_distance<<",\"start_occupied\":"<<start_occupied<<",\"target_occupied\":"<<target_occupied<<",\"straight_clear\":"<<(straight_segment_clear?"true":"false")<<",\"get_local_target\":"<<(target_ok?"true":"false")<<",\"continued\":"<<(continued?"true":"false")<<",\"has_translation\":"<<(fsm.planner_manager_->hasLocalTranslation(original_start,target)?"true":"false")<<",\"boundary_pass\":"<<(boundary_ok?"true":"false")<<",\"full_clear\":"<<(full_clear?"true":"false")<<"}\n";
  result.close();rclcpp::shutdown();
}
