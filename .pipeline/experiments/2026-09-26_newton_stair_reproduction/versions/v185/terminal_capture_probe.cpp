#include <scan_nav2_controller/tracking_node.hpp>
#include <fstream>
#include <iostream>
#include <stdexcept>

static void require(bool value, const char *message) {
  if (!value) throw std::runtime_error(message);
}
static bool zero(const geometry_msgs::msg::Twist &v) {
  return v == geometry_msgs::msg::Twist();
}
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
  require(bool(input), "Incomplete recorded terminal fixture");
  scan_planner::UniformBspline curve(points, 3, knots[4]-knots[3]); curve.setKnot(knots);
  const auto target = curve.evaluateDeBoorT(curve.getTimeSum());
  auto tracker = std::make_shared<scan_planner::TrackingNode>();
  auto message = std::make_shared<scan_planner_msgs::msg::Bspline>();
  message->order = 3; message->traj_id = 1;
  message->run_id="run";message->epoch=1;message->request_id="request";
  message->goal_id="goal";message->route_id="route";message->command_id="command";
  message->generation=1;message->map_epoch="map";message->map_revision=1;
  message->start_time = (tracker->now()-rclcpp::Duration::from_seconds(curve.getTimeSum()+1));
  for(int i=0;i<n;++i) { geometry_msgs::msg::Point point;point.x=points(0,i);point.y=points(1,i);point.z=points(2,i);message->pos_pts.push_back(point); }
  for(int i=0;i<n+4;++i) message->knots.push_back(knots[i]);
  tracker->bsplineCallback(message);
  const auto query = [&](const geometry_msgs::msg::PoseStamped &body) {
    tracker->last_update_time_ = tracker->now(); return tracker->sample(body);
  };
  const auto offset = [&](double error) {
    auto body=pose;body.pose.position.x=target.x()+error;
    body.pose.position.y=target.y();body.pose.position.z=target.z();return body;
  };
  tracker->finish_dist_=.15;
  require(zero(query(pose)), "Old five-cm recovery failure not reproduced");
  tracker->finish_dist_=.02;
  require(!zero(query(offset(.02187977))), "Old two-cm plateau should command correction");
  require(zero(query(offset(.01))), "Old inside capture stop missing");
  require(!zero(query(offset(.04))), "Default-off legacy behavior unexpectedly latched");
  tracker->stateful_local_capture_=true;tracker->finish_dist_=.03;
  const auto candidate=query(pose);
  const double yaw=tf2::getYaw(q);
  const Eigen::Vector2d world(std::cos(yaw)*candidate.linear.x-std::sin(yaw)*candidate.linear.y,
                            std::sin(yaw)*candidate.linear.x+std::cos(yaw)*candidate.linear.y);
  const Eigen::Vector2d error(target.x()-p.x,target.y()-p.y);
  require(error.norm()>.03 && world.dot(error)>0 && world.norm()<.1,
          "Short recovery no longer commands inward movement at recorded 4.9246 cm");
  require(zero(query(offset(.02187977))) && tracker->local_capture_reached_,
          "Recorded plateau magnitude did not enter completion");
  require(zero(query(offset(.04))), "Same curve restarted after capture drift");
  tracker->bsplineCallback(message);
  require(zero(query(offset(.04))), "Identical retransmission reset completion");
  ++message->traj_id;tracker->bsplineCallback(message);
  require(!tracker->local_capture_reached_ && !zero(query(pose)),
          "New curve to same endpoint cannot resume recovery");
  require(zero(query(offset(.01))), "New curve inside capture did not stop");
  // The full mission yaw contract retains precedence over local completion.
  auto goal=std::make_shared<scan_planner_msgs::msg::P2BRoute>();
  goal->run_id=message->run_id;goal->epoch=1;goal->request_id=message->request_id;
  goal->goal_id=message->goal_id;goal->route_id=message->route_id;
  goal->command_id=message->command_id;goal->generation=1;
  goal->map_epoch=message->map_epoch;goal->map_revision=1;goal->has_goal_pose=true;
  goal->path.poses.push_back(pose);goal->goal_pose=offset(.01).pose;
  tf2::Quaternion goal_q;goal_q.setRPY(0,0,yaw+.6);goal->goal_pose.orientation=tf2::toMsg(goal_q);
  tracker->goalCallback(goal);require(!tracker->local_capture_reached_, "New goal did not reset latch");
  tracker->local_capture_reached_=true;
  const auto align=query(offset(.01));
  require(align.linear.x==0 && align.linear.y==0 && std::abs(align.angular.z)>.1,
          "Local completion suppressed mission yaw alignment");
  tracker->goal_route_.reset();tracker->goal_xy_reached_=false;
  // Full owner identity changes reset even with an unchanged endpoint and curve ID.
  ++message->map_revision;tracker->bsplineCallback(message);
  require(!tracker->local_capture_reached_ && !zero(query(pose)), "Map identity did not reset completion");
  require(zero(query(offset(.01))), "Recapture failed");
  auto cancel=std::make_shared<scan_planner_msgs::msg::P2BCancel>();
  cancel->run_id=message->run_id;cancel->epoch=1;cancel->request_id=message->request_id;
  cancel->goal_id=message->goal_id;cancel->route_id=message->route_id;
  cancel->command_id=message->command_id;cancel->generation=1;
  cancel->map_epoch=message->map_epoch;cancel->map_revision=message->map_revision;
  tracker->p2bCancelCallback(cancel);
  require(!tracker->local_capture_reached_ && zero(query(pose)), "Cancel did not revoke local capture");
  tracker->bsplineCallback(message);require(!tracker->receive_traj_ && zero(query(pose)), "Cancelled curve restarted");
  message->generation=2;tracker->bsplineCallback(message);
  require(!zero(query(pose)), "New generation cannot resume");
  message->emergency_stop=true;++message->traj_id;tracker->bsplineCallback(message);
  require(!tracker->local_capture_reached_ && zero(query(pose)), "Emergency stop did not take precedence");
  message->emergency_stop=false;--message->traj_id;tracker->bsplineCallback(message);
  require(zero(query(pose)), "Pre-emergency curve escaped safety stop");
  std::cout << "V184_TERMINAL_CAPTURE_PASS error_m=" << error.norm()
            << " old_plateau_nonzero=1 captured_zero=1 drift_restart=0 new_curve_resume=1"
            << " mission_yaw_preserved=1 cancelled_rejected=1 emergency_preserved=1\n";
  tracker.reset();rclcpp::shutdown();return 0;
}
