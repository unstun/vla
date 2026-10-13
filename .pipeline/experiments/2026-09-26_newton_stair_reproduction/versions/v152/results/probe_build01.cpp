#include <plan_manage/scan_replan_fsm.h>
#include <bspline_opt/full_trajectory_collision.h>
#include "v84/recording.h"
#include <array>
#include <plan_manage/reference_path_utils.h>
#include <bspline_opt/timed_cubic_initialization.h>

struct Query {
  std::string name;
  int64_t clock_ns, body_ns;
  std::string body_file;
};

int main(int argc, char **argv) {
  rclcpp::init(argc, argv);
  const char *location = std::getenv("REPLAY_INPUT");
  if (!location) throw std::runtime_error("Missing replay input");
  const fs::path input(location);
  auto node = std::make_shared<rclcpp::Node>("scan_planner_node");
  node->declare_parameter<bool>("grid_map.asynchronous_mapping", false);
  node->set_parameter(rclcpp::Parameter("grid_map.asynchronous_mapping", false));
  set_clock(*node, 1000000000LL);
  scan_planner::SCANReplanFSM fsm;
  fsm.init(node.get());
  fsm.exec_timer_->cancel();
  fsm.safety_timer_->cancel();
  auto map = fsm.planner_manager_->grid_map_;
  map->occ_timer_->cancel();
  map->vis_timer_->cancel();
  if (map->async_mapping_) throw std::runtime_error("Ordered replay required");
  auto nav = std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input / "navigation.f32", true));
  auto surface = std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input / "surface.f32", true));
  auto floor = std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input / "physical_floor.f32", true));
  nav->header.stamp = surface->header.stamp = floor->header.stamp = node->now();
  map->reactiveTomogramCallback(nav);
  map->reactiveSurfaceGroundCallback(surface);
  map->reactivePhysicalFloorCallback(floor);
  if (!map->reactiveSurfaceGroundReady()) throw std::runtime_error("Original support missing");
  std::ifstream scans(input / "scans.txt");
  int index; int64_t stamp; std::string body_file, sensor_file, cloud_file;
  size_t count = 0;
  while (scans >> index >> stamp >> body_file >> sensor_file >> cloud_file) {
    if (index != static_cast<int>(count)) throw std::runtime_error("Disordered scan index");
    RecordedScan scan{index, stamp,
      std::make_shared<nav_msgs::msg::Odometry>(read_pose(input / body_file)),
      std::make_shared<nav_msgs::msg::Odometry>(read_pose(input / sensor_file)),
      std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input / cloud_file, false))};
    scan.body->header.stamp = scan.sensor->header.stamp = scan.cloud->header.stamp = rclcpp::Time(stamp, RCL_ROS_TIME);
    apply_scan(*map, *node, scan);
    ++count;
  }
  if (!scans.eof() || count == 0) throw std::runtime_error("Incomplete scan replay");
  std::ifstream curve_input(input / "curve.txt");
  int64_t origin_ns; size_t points_count, knots_count;
  curve_input >> origin_ns >> points_count >> knots_count;
  if (points_count < 4 || points_count > 10000 || knots_count != points_count + 4)
    throw std::runtime_error("Invalid recorded curve dimensions");
  Eigen::MatrixXd points(3, points_count);
  Eigen::VectorXd knots(knots_count);
  for (size_t i = 0; i < points_count; ++i)
    curve_input >> points(0, i) >> points(1, i) >> points(2, i);
  for (size_t i = 0; i < knots_count; ++i) curve_input >> knots[i];
  if (!curve_input) throw std::runtime_error("Incomplete recorded curve");
  scan_planner::UniformBspline curve(points, 3, knots[4] - knots[3]);
  curve.setKnot(knots);
  std::array<Query, 2> queries;
  std::ifstream query_input(input / "queries.txt");
  for (auto &q : queries) query_input >> q.name >> q.clock_ns >> q.body_ns >> q.body_file;
  if (!query_input || queries[0].name != "clear" || queries[1].name != "blocked")
    throw std::runtime_error("Invalid recorded query pair");
  std::cout << "V150_MAP scans=" << count << " digest=" << map_digest(*map) << std::endl;
  const auto check = [&](const std::string &name, const Query &body_query,
                         int64_t clock_ns, double begin_s) {
    set_clock(*node, clock_ns);
    auto body = std::make_shared<nav_msgs::msg::Odometry>(read_pose(input / body_query.body_file));
    body->header.stamp = rclcpp::Time(body_query.body_ns, RCL_ROS_TIME);
    map->slidingMapFrameCallback(body);
    GridMap::RawContributorCacheScope cache(*map);
    Eigen::Vector3d rejected = Eigen::Vector3d::Zero();
    double rejected_yaw = 0;
    auto result = reactive_stair::checkFullCubicTrajectory(curve, begin_s,
      map->getResolution(), GridMap::collision_heading_lookahead_s,
      [&](const Eigen::Vector3d &p, const Eigen::Vector3d &a, const Eigen::Vector3d &v) {
        return map->collisionTrajectoryYaw(p, a, v);
      }, [&](const Eigen::Vector3d &p, double yaw) {
        const bool occupied = map->getInflateOccupancy(p, yaw) != 0;
        if (occupied) { rejected = p; rejected_yaw = yaw; }
        return occupied;
      });
    std::cout << std::setprecision(17) << "V150_QUERY name=" << name
      << " status=" << static_cast<int>(result.status) << " samples=" << result.samples
      << " first_t=" << result.first_time_s << " duration=" << result.duration_s
      << " begin=" << begin_s << " body=" << map->queryBodyPosition().transpose()
      << " rejected=" << rejected.transpose() << " yaw=" << rejected_yaw << std::endl;
    if (!result.clear()) map->logInitialSplineCollision(rejected, rejected_yaw);
  };
  const auto &query = queries[0];
  set_clock(*node, query.clock_ns);
  auto body = std::make_shared<nav_msgs::msg::Odometry>(read_pose(input / query.body_file));
  body->header.stamp = rclcpp::Time(query.body_ns, RCL_ROS_TIME);
  map->slidingMapFrameCallback(body); fsm.odometryCallback(body);
  auto manager = fsm.planner_manager_;
  const double phase = (query.clock_ns-origin_ns)*1e-9;
  auto velocity = curve.getDerivative(); auto acceleration = velocity.getDerivative();
  const Eigen::Vector3d start = curve.evaluateDeBoorT(phase);
  const Eigen::Vector3d start_v = velocity.evaluateDeBoorT(phase);
  const Eigen::Vector3d start_a = acceleration.evaluateDeBoorT(phase);
  const Eigen::Vector3d target = curve.evaluateDeBoorT(curve.getTimeSum());
  const Eigen::Vector3d target_v = velocity.evaluateDeBoorT(curve.getTimeSum());
  const rclcpp::Time origin(query.clock_ns,RCL_ROS_TIME);
  const std::string mode = std::getenv("REPLAN_MODE") ? std::getenv("REPLAN_MODE") : "direct";
  bool accepted = false;
  auto started=std::chrono::steady_clock::now();
  if (mode=="direct") {
    accepted=manager->reboundReplan(start,start_v,start_a,target,target_v,true,false,&origin);
  } else if(mode=="reference") {
    std::ifstream route(std::getenv("REPLAY_ROUTE")); size_t count; route>>count;
    nav_msgs::msg::Path path;
    for(size_t i=0;i<count;++i){ geometry_msgs::msg::PoseStamped pose;
      route>>pose.pose.position.x>>pose.pose.position.y>>pose.pose.position.z;path.poses.push_back(pose); }
    if(!route)throw std::runtime_error("Invalid reference input");
    std::vector<Eigen::Vector3d> waypoints; std::string error;
    if(!scan_planner::prepareReferenceWaypoints(path,fsm.body_height_,fsm.reference_path_min_distance_,waypoints,&error,fsm.reference_path_simplify_tolerance_))throw std::runtime_error(error);
    if(!fsm.planGlobalTrajByWaypoints(waypoints))throw std::runtime_error("Reference admission failed");
    manager->updateTrajInfo(curve,rclcpp::Time(origin_ns,RCL_ROS_TIME));
    fsm.have_new_target_=false;
    accepted=fsm.planFromCurrentTraj();
  } else throw std::runtime_error("Unknown mode");
  const double wall_ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-started).count();
  std::cout<<std::setprecision(17)<<"V152_REPLAN mode="<<mode<<" accepted="<<accepted<<" wall_ms="<<wall_ms<<" start="<<start.transpose()<<" original_target="<<target.transpose()<<std::endl;
  if(accepted){
    auto result=manager->local_data_.position_traj_;
    auto checked=reactive_stair::checkFullCubicTrajectory(result,0.0,map->getResolution(),GridMap::collision_heading_lookahead_s,
      [&](const Eigen::Vector3d&p,const Eigen::Vector3d&a,const Eigen::Vector3d&v){return map->collisionTrajectoryYaw(p,a,v);},
      [&](const Eigen::Vector3d&p,double yaw){return map->getInflateOccupancy(p,yaw)!=0;});
    const Eigen::Vector3d end = mode=="direct" ? target : fsm.local_target_pt_;
    const Eigen::Vector3d end_v = mode=="direct" ? target_v : fsm.local_target_vel_;
    std::vector<Eigen::Vector3d> derivatives{start_v,end_v,start_a,Eigen::Vector3d::Zero()};
    const bool pva=reactive_stair::matchesBoundaryPva(result,start,end,derivatives);
    const bool dynamics=manager->checkDynamicFeasibility(result);
    std::cout<<"V152_VALIDATION clear="<<checked.clear()<<" samples="<<checked.samples<<" pva="<<pva<<" dynamics="<<dynamics<<" duration="<<result.getTimeSum()<<std::endl;
    if(!checked.clear()||!pva||!dynamics)throw std::runtime_error("Accepted replacement violates original gates");
  }
  rclcpp::shutdown(); return 0;
}
