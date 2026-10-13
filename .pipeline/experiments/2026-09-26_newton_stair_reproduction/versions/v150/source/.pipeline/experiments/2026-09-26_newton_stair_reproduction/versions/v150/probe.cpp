#include <plan_manage/scan_replan_fsm.h>
#include <bspline_opt/full_trajectory_collision.h>
#include "v84/recording.h"
#include <array>

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
  const double first = (queries[0].clock_ns - origin_ns) * 1e-9;
  const double second = (queries[1].clock_ns - origin_ns) * 1e-9;
  check("recorded_clear", queries[0], queries[0].clock_ns, first);
  check("recorded_blocked", queries[1], queries[1].clock_ns, second);
  check("counterfactual_earlier_body", queries[0], queries[1].clock_ns, second);
  check("counterfactual_full_curve", queries[1], queries[1].clock_ns, first);
  rclcpp::shutdown();
  return 0;
}
