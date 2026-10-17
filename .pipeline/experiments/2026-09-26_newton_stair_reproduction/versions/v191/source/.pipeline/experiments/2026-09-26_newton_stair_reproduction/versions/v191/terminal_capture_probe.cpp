#include <scan_nav2_controller/tracking_node.hpp>
#include <fstream>
#include <iostream>
#include <stdexcept>

namespace {
void require(bool condition, const char *message) {
  if (!condition) throw std::runtime_error(message);
}

void cornerLookaheadProbe() {
  const auto pose = [](double x, double y, double z=0.42, double yaw=0.0) {
    geometry_msgs::msg::PoseStamped out;
    out.header.frame_id="world";
    out.pose.position.x=x;out.pose.position.y=y;out.pose.position.z=z;
    out.pose.orientation.z=std::sin(yaw/2);out.pose.orientation.w=std::cos(yaw/2);
    return out;
  };
  auto route=std::make_shared<nav_msgs::msg::Path>();
  route->header.frame_id="world";
  route->poses={pose(-1,0),pose(0,0),pose(0,4)};
  const Eigen::Vector3d endpoint(0,0,0.42);
  const auto prepare = [&](scan_planner::TrackingNode &tracker) {
    Eigen::MatrixXd points(3,6);
    for (int i=0;i<6;++i) points.col(i)=Eigen::Vector3d(i<3?-0.05:0.0,0,0.42);
    scan_planner::UniformBspline stub(points,3,0.1);
    tracker.traj_={stub,stub.getDerivative()};tracker.traj_duration_=stub.getTimeSum();
    tracker.exec_time_=tracker.traj_duration_;tracker.receive_traj_=true;
    tracker.pathCallback(route);
    require((stub.evaluateDeBoorT(tracker.traj_duration_)-endpoint).norm()<1e-9,
            "Corner stub endpoint mismatch");
    require(tracker.traj_[1].evaluateDeBoorT(tracker.traj_duration_).head<2>().squaredNorm()<1e-4,
            "Corner stub must have zero terminal velocity");
  };
  auto disabled=std::make_shared<scan_planner::TrackingNode>();prepare(*disabled);
  require(!disabled->get_parameter("route_lookahead_heading_enabled").as_bool(),
          "Standalone tracker default must remain disabled");
  require(disabled->sample(pose(0,0))==geometry_msgs::msg::Twist(),
          "Disabled corner heading changed v82 behavior");
  disabled.reset();

  rclcpp::NodeOptions options;
  options.parameter_overrides({rclcpp::Parameter("route_lookahead_heading_enabled",true)});
  auto tracker=std::make_shared<scan_planner::TrackingNode>(options);prepare(*tracker);
  const double middle=(tracker->goal_yaw_tolerance_+tracker->heading_error_threshold_)/2;
  for (double error : {M_PI/2,middle,tracker->goal_yaw_tolerance_/2}) {
    const auto command=tracker->sample(pose(0,0,0.42,M_PI/2-error));
    require(command.linear.x==0 && command.linear.y==0 && command.linear.z==0,
            "Expired stub must hold translation while aligning");
    require(error>tracker->goal_yaw_tolerance_ ? command.angular.z>0 : command.angular.z==0,
            "Corner heading stopped outside tolerance or turned inside it");
    bool used=false;
    require(std::abs(tracker->estimateDesiredYaw(tracker->traj_duration_,endpoint,&used)-M_PI/2)<1e-9 && used,
            "Degenerate stub did not use global route heading");
  }
  tracker->reverse_motion_=true;
  require(tracker->sample(pose(0,0))==geometry_msgs::msg::Twist(),"Reverse stub must not use route heading");
  tracker->reverse_motion_=false;
  double yaw=0.0;
  tracker->goal_position_latched_=true;
  require(!tracker->estimateRouteLookaheadYaw(endpoint,yaw),"Goal latch must own heading");
  auto refreshed=std::make_shared<nav_msgs::msg::Path>(*route);
  refreshed->poses={pose(-1,0),pose(0,0),pose(0,-2),pose(0,4)};
  const Eigen::Vector3d goal=tracker->goal_pos_;const double goal_yaw=tracker->goal_yaw_;
  tracker->pathCallback(refreshed);
  require(tracker->reference_path_.poses.size()==4 && tracker->goal_position_latched_ &&
          (tracker->goal_pos_-goal).norm()==0 && tracker->goal_yaw_==goal_yaw,
          "Same-goal refresh lost route geometry or reset goal capture");
  tracker->goal_position_latched_=false;
  require(tracker->sample(pose(0,0)).angular.z<0,"Refreshed path did not change heading");
  tracker->odom_pos_=goal;
  require(!tracker->estimateRouteLookaheadYaw(endpoint,yaw),"Final capture zone must own heading before latch");
  tracker->odom_pos_=endpoint;

  // The nearest XY segment is on another floor; 3D projection must use the upper route.
  auto floors=std::make_shared<nav_msgs::msg::Path>(*route);
  floors->poses={pose(-1,0,0.42),pose(1,0,0.42),pose(1,0,3.42),pose(0,0,3.42),pose(0,3,3.42)};
  tracker->pathCallback(floors);tracker->odom_pos_=Eigen::Vector3d(0,0,3.42);
  require(tracker->estimateRouteLookaheadYaw(tracker->odom_pos_,yaw) && std::abs(yaw-M_PI/2)<1e-9,
          "Route projection jumped to another floor");
  auto repeated=std::make_shared<nav_msgs::msg::Path>(*route);
  repeated->poses={pose(-1,0),pose(0,0),pose(0,0),pose(0,0.3)};
  tracker->pathCallback(repeated);tracker->odom_pos_=endpoint;
  require(tracker->estimateRouteLookaheadYaw(endpoint,yaw) && std::abs(yaw-M_PI/2)<1e-9,
          "Duplicate segments or final-carrot clamping lost heading");
  auto single=std::make_shared<nav_msgs::msg::Path>(*route);
  single->poses={pose(0,0)};tracker->pathCallback(single);tracker->goal_pos_<<0,4,0.42;
  require(!tracker->estimateRouteLookaheadYaw(endpoint,yaw),"Zero route direction must decline fallback");
  tracker->odom_pos_.y()=-0.1;
  require(tracker->estimateRouteLookaheadYaw(endpoint,yaw) && std::abs(yaw-M_PI/2)<1e-9,
          "Single-vertex route did not use odometry fallback");
  auto invalid=std::make_shared<nav_msgs::msg::Path>(*route);
  invalid->poses.back().pose.position.z=std::numeric_limits<double>::quiet_NaN();
  tracker->pathCallback(invalid);require(!tracker->goal_pose_valid_,"Nonfinite goal position accepted");
  invalid=std::make_shared<nav_msgs::msg::Path>(*route);
  invalid->poses.back().pose.orientation.w=2.0;
  tracker->pathCallback(invalid);require(!tracker->goal_pose_valid_,"Unnormalized goal quaternion accepted");
  std::cout << "V191_CORNER_LOOKAHEAD_PASS disabled=1 heading_bands=2 aligned_zero=1 refresh=1 reverse=1 final_capture=1 projection_3d=1 degenerate_path=1 invalid_path=1\n";
}
}  // namespace

int main(int argc, char **argv) {
  rclcpp::init(argc, argv);
  if (argc < 2) return 2;
  std::ifstream input(argv[1]);
  int n = 0; input >> n;
  Eigen::MatrixXd points(3, n); Eigen::VectorXd knots(n + 4);
  for (int i = 0; i < n; ++i) input >> points(0,i) >> points(1,i) >> points(2,i);
  for (int i = 0; i < n+4; ++i) input >> knots[i];
  geometry_msgs::msg::PoseStamped pose;
  pose.header.frame_id = "world";
  auto &p = pose.pose.position; auto &q = pose.pose.orientation;
  input >> p.x >> p.y >> p.z >> q.w >> q.x >> q.y >> q.z;
  if (!input) throw std::runtime_error("Incomplete recorded terminal fixture");
  scan_planner::UniformBspline curve(points, 3, knots[4]-knots[3]); curve.setKnot(knots);
  auto tracker = std::make_shared<scan_planner::TrackingNode>();
  tracker->traj_ = {curve, curve.getDerivative()};
  tracker->traj_duration_ = curve.getTimeSum();
  tracker->exec_time_ = tracker->traj_duration_;
  tracker->receive_traj_ = true;
  const Eigen::Vector3d target = curve.evaluateDeBoorT(tracker->traj_duration_);
  const auto query = [&](double tolerance, const geometry_msgs::msg::PoseStamped &body) {
    tracker->finish_dist_ = tolerance; tracker->last_update_time_ = tracker->now();
    return tracker->sample(body);
  };
  const auto old = query(.15, pose), candidate = query(.02, pose);
  if (old != geometry_msgs::msg::Twist()) throw std::runtime_error("Old failure not reproduced");
  const double yaw = tf2::getYaw(pose.pose.orientation);
  const Eigen::Vector2d world(std::cos(yaw)*candidate.linear.x-std::sin(yaw)*candidate.linear.y,
                            std::sin(yaw)*candidate.linear.x+std::cos(yaw)*candidate.linear.y);
  const Eigen::Vector2d error(target.x()-p.x, target.y()-p.y);
  if (error.norm() < .02 || error.norm() > .15 || world.dot(error) <= 0 ||
      world.norm() > .1 || std::abs(candidate.angular.z) > 1e-9)
    throw std::runtime_error("Candidate does not correct the recorded terminal error");
  auto close = pose; close.pose.position.x = target.x()+.01;
  close.pose.position.y = target.y(); close.pose.position.z = target.z();
  if (query(.02, close) != geometry_msgs::msg::Twist())
    throw std::runtime_error("Candidate does not stop inside capture tolerance");
  std::cout << "V176_TERMINAL_CAPTURE_PASS error_m=" << error.norm()
            << " old_zero=1 candidate_vx=" << candidate.linear.x
            << " candidate_vy=" << candidate.linear.y << " close_zero=1\n";
  tracker.reset(); cornerLookaheadProbe(); rclcpp::shutdown(); return 0;
}
