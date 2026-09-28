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
  // ---- Diagnostic support oracle (counterfactual only) ----
  {
    auto &terrain = map->reactive_terrain_;
    size_t relabelled = 0, walkway = 0;
    for (auto &entry : terrain.cells) {
      const double x0 = terrain.origin_x_m + entry.first.x * terrain.resolution_m;
      const double y0 = terrain.origin_y_m + entry.first.y * terrain.resolution_m;
      if (x0 < -5.3 || x0 > -3.5 || y0 < -4.5 || y0 > -2.3) continue;
      for (auto &surface : entry.second) {
        if (surface.elevation_m < 1.35 || surface.elevation_m > 1.65) continue;
        ++walkway;
        if (surface.support == reactive_stair::Support::Unknown) {
          surface.support = reactive_stair::Support::Flat;
          ++relabelled;
        }
      }
    }
    const bool accepted = map->reactive_decision_.acceptTerrain(terrain);
    std::cout << "[SUPPORT-ORACLE] box=[-5.3,-3.5]x[-4.5,-2.3] walkway_layers=" << walkway
              << " relabelled_unknown_to_flat=" << relabelled << " decision_snapshot_accepted=" << accepted << std::endl;
    if (!accepted) throw std::runtime_error("Oracle terrain rejected");
  }
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
  // ---- Landing-stall breakdown (read-only, before the stale-clock negative) ----
  {
    struct Breakdown {
      std::string stage = "free"; int in_map = 0; double log_odds = NAN; int inflate = -1;
      int contributors = 0, unclassified = 0; Eigen::Vector3d first_unclassified = Eigen::Vector3d::Constant(NAN);
      std::string first_flags = "-"; int raw_class = -1, trunk_inside = -1, final_class = -1, body_verdict = -1;
      double body_ground = NAN, footprint_ground = NAN, support_z = NAN; int verdict = -1, result = 1;
    };
    const double now_s = node->now().seconds();
    const auto support_replica = [&](const Eigen::Vector3d &body_reference, const reactive_stair::NonTerrainVoxel &obstacle,
                                     reactive_stair::Query &query, Breakdown &b) {
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
      if (body_verdict != reactive_stair::Verdict::Free) { b.stage = "support_body_verdict"; return false; }
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
    const auto breakdown = [&](const Eigen::Vector3d &point, const Eigen::Vector3d &body) {
      Breakdown b;
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
            if (!reactive_stair::mayWaiveRawContributor(tr, nt, hi)) {
              if (!b.unclassified) { map->indexToPos(source, b.first_unclassified); b.first_flags = std::to_string(tr) + std::to_string(nt) + std::to_string(hi); }
              ++b.unclassified;
            }
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
      if (!support_replica(body, obstacle, query, b)) return b;
      const auto verdict = map->reactive_decision_.decide(query, obstacle);
      b.verdict = static_cast<int>(verdict);
      b.result = verdict == reactive_stair::Verdict::Free ? 0 : 1;
      b.stage = b.result ? "verdict_" + std::to_string(b.verdict) : "free";
      return b;
    };
    auto &gd = fsm.planner_manager_->global_data_;
    const double duration = gd.global_duration_;
    const int sample_num = std::max(1, static_cast<int>(std::ceil(duration / 0.05)));
    std::ofstream diag(fs::path(output).parent_path() / (fs::path(output).stem().string() + "_breakdown.csv"));
    diag << std::setprecision(12)
         << "i,t,x,y,z,yaw,native,circle,cx,cy,cz,local_x,local_y,local_z,sensor_range,sensor_elev_deg,stage,in_map,log_odds,inflate,contributors,unclassified,first_unclassified_x,first_unclassified_y,first_unclassified_z,first_flags,first_on_ground,raw_class,trunk_inside,final_class,body_verdict,body_ground,footprint_ground,support_z,verdict,replicated,native_circle,support_native\n";
    std::ofstream walk(fs::path(output).parent_path() / (fs::path(output).stem().string() + "_walk.csv"));
    walk << std::setprecision(12) << "i,t,x,y,z,yaw,native\n";
    int circle_mismatches = 0, sample_mismatches = 0, support_mismatches = 0, rows = 0, first_free = -1;
    for (int i = sample_num; i >= 0; --i) {
      const double t = duration * i / sample_num;
      const double prev_t = duration * std::max(0, i - 1) / sample_num;
      const Eigen::Vector3d pt = gd.global_traj_.evaluate(t), prev = gd.global_traj_.evaluate(prev_t);
      const double yaw = fsm.estimateYawFromSegment(prev, pt);
      const int native = map->getInflateOccupancy(pt, yaw);
      walk << i << "," << t << "," << pt.x() << "," << pt.y() << "," << pt.z() << "," << yaw << "," << native << "\n";
      if (native == 0 && first_free < 0) first_free = i;
      if (t < frontier - 0.35 || t > frontier + 4.5) continue;
      const Eigen::Vector3d heading(std::cos(yaw), std::sin(yaw), 0.0);
      int circle_native[2];
      for (int side = 0; side < 2; ++side) {
        const Eigen::Vector3d c = pt + (side == 0 ? 1.0 : -1.0) * map->mp_.double_cylinder_offset_ * heading;
        const Breakdown b = breakdown(c, pt);
        circle_native[side] = map->reactiveOccupancy(c, &pt);
        reactive_stair::Query probe_query;
        probe_query.frame = map->mp_.frame_id_; probe_query.stamp_s = now_s;
        probe_query.x_m = c.x(); probe_query.y_m = c.y(); probe_query.z_m = c.z(); probe_query.in_map = map->isInMap(c);
        reactive_stair::NonTerrainVoxel probe_obstacle; probe_obstacle.frame = map->mp_.frame_id_;
        probe_obstacle.stamp_s = map->reactive_cloud_stamp_s_;
        if (map->reactive_cloud_ready_) probe_obstacle.source_id = "scan_lidar_cloud";
        const bool support_native = map->reactiveFootprintSupportQuery(pt, probe_obstacle, probe_query);
        const bool support_replicated = b.stage.rfind("support_", 0) != 0 && b.stage != "map_boundary" &&
                                        b.stage != "surface_not_ready" && b.stage != "nonfinite";
        if (b.stage != "map_boundary" && support_native != support_replicated) ++support_mismatches;
        if (circle_native[side] != b.result) ++circle_mismatches;
        const Eigen::Vector3d local = map->reactive_body_quaternion_.conjugate() * (c - map->md_.sliding_map_frame_pos_);
        const Eigen::Vector3d ray = c - map->md_.ray_pos_;
        const double elevation = std::atan2(ray.z(), ray.head<2>().norm()) * 180.0 / 3.14159265358979323846;
        const bool on_ground = b.first_unclassified.allFinite() && map->reactiveTerrainReturn(b.first_unclassified);
        diag << i << "," << t << "," << pt.x() << "," << pt.y() << "," << pt.z() << "," << yaw << "," << native << ","
             << (side == 0 ? "front" : "rear") << "," << c.x() << "," << c.y() << "," << c.z() << ","
             << local.x() << "," << local.y() << "," << local.z() << "," << ray.norm() << "," << elevation << ","
             << b.stage << "," << b.in_map << "," << b.log_odds << "," << b.inflate << "," << b.contributors << "," << b.unclassified << ","
             << b.first_unclassified.x() << "," << b.first_unclassified.y() << "," << b.first_unclassified.z() << "," << b.first_flags << ","
             << on_ground << "," << b.raw_class << "," << b.trunk_inside << "," << b.final_class << "," << b.body_verdict << ","
             << b.body_ground << "," << b.footprint_ground << "," << b.support_z << "," << b.verdict << "," << b.result << ","
             << circle_native[side] << "," << support_native << "\n";
        ++rows;
      }
      if (native != (circle_native[0] ? 1 : circle_native[1])) ++sample_mismatches;
    }
    walk.close();
    diag.close();
    std::cout << "[LANDING-BREAKDOWN] frontier=" << frontier << " duration=" << duration << " sample_num=" << sample_num
              << " first_free_from_end_i=" << first_free << " t=" << duration * first_free / sample_num << " rows=" << rows
              << " circle_mismatches=" << circle_mismatches << " sample_mismatches=" << sample_mismatches
              << " support_mismatches=" << support_mismatches << " body=" << map->md_.sliding_map_frame_pos_.transpose()
              << " sensor=" << map->md_.ray_pos_.transpose() << " map_min=" << map->mp_.map_min_boundary_.transpose()
              << " map_max=" << map->mp_.map_max_boundary_.transpose() << " now=" << now_s
              << " cloud_stamp=" << map->reactive_cloud_stamp_s_ << " body_stamp=" << map->reactive_body_stamp_s_ << std::endl;
  }
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
