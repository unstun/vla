#include <scan_nav2_controller/tracking_node.hpp>
#include <fstream>
#include <iostream>
#include <stdexcept>

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
  tracker.reset(); rclcpp::shutdown(); return 0;
}
