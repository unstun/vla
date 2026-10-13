#include <scan_nav2_controller/tracking_node.hpp>
#include <fstream>
#include <iostream>
#include <stdexcept>
static void require(bool x,const char *message){if(!x)throw std::runtime_error(message);}
static bool zero(const geometry_msgs::msg::Twist &x){return x==geometry_msgs::msg::Twist();}
int main(int argc,char **argv){
 rclcpp::init(argc,argv);if(argc<2)return 2;
 std::ifstream input(argv[1]);int n=0;input>>n;
 Eigen::MatrixXd points(3,n);Eigen::VectorXd knots(n+4);
 for(int i=0;i<n;++i)input>>points(0,i)>>points(1,i)>>points(2,i);
 for(int i=0;i<n+4;++i)input>>knots[i];
 geometry_msgs::msg::PoseStamped body;body.header.frame_id="world";
 auto &p=body.pose.position;auto &q=body.pose.orientation;
 input>>p.x>>p.y>>p.z>>q.w>>q.x>>q.y>>q.z;require(bool(input),"Incomplete recorded fixture");
 scan_planner::UniformBspline curve(points,3,knots[4]-knots[3]);curve.setKnot(knots);
 const auto end=curve.evaluateDeBoorT(curve.getTimeSum());
 auto tracker=std::make_shared<scan_planner::TrackingNode>();
 auto message=std::make_shared<scan_planner_msgs::msg::Bspline>();
 message->order=3;message->traj_id=1;message->run_id="run";message->epoch=1;
 message->request_id="request";message->goal_id="goal";message->route_id="route";
 message->command_id="command";message->generation=1;message->map_epoch="map";message->map_revision=1;
 message->start_time=tracker->now()-rclcpp::Duration::from_seconds(curve.getTimeSum()+1);
 for(int i=0;i<n;++i){geometry_msgs::msg::Point point;point.x=points(0,i);point.y=points(1,i);point.z=points(2,i);message->pos_pts.push_back(point);}
 for(int i=0;i<n+4;++i)message->knots.push_back(knots[i]);tracker->bsplineCallback(message);
 const auto pose=[&](double error){auto x=body;x.pose.position.x=end.x()+error;x.pose.position.y=end.y();x.pose.position.z=end.z();return x;};
 const auto query=[&](const geometry_msgs::msg::PoseStamped &x){tracker->last_update_time_=tracker->now();return tracker->sample(x);};
 tracker->finish_dist_=.15;require(zero(query(body)),"Old15cm failure not reproduced");
 tracker->finish_dist_=.02;auto v=query(body);
 const double yaw=tf2::getYaw(q);Eigen::Vector2d world(std::cos(yaw)*v.linear.x-std::sin(yaw)*v.linear.y,std::sin(yaw)*v.linear.x+std::cos(yaw)*v.linear.y);
 require(world.dot(Eigen::Vector2d(end.x()-p.x,end.y()-p.y))>0,"Recorded5cm recovery no longer moves inward");
 require(!zero(query(pose(.02187977))),"Legacy plateau must command correction");
 tracker->terminal_correction_since_=tracker->now()-rclcpp::Duration::from_seconds(10);
 require(!zero(query(pose(.02187977)))&&!tracker->terminal_correction_expired_,"Disabled feature changed legacy output");
 tracker->terminal_correction_enabled_=true;
 require(!zero(query(body)),"Enabled feature prevents initial recovery motion");
 tracker->terminal_correction_since_=tracker->now()-rclcpp::Duration::from_seconds(1.4);
 require(!zero(query(pose(.02187977)))&&!tracker->terminal_correction_expired_,"Correction ended before1.5s");
 tracker->terminal_correction_since_=tracker->now()-rclcpp::Duration::from_seconds(1.6);
 require(zero(query(pose(.02187977)))&&tracker->terminal_correction_expired_,"Expired correction did not request failure");
 ++message->traj_id;tracker->bsplineCallback(message);
 require(!tracker->terminal_correction_expired_&&!zero(query(body)),"New accepted curve did not reset failed tracker");
 require(zero(query(pose(.01))),"Ordinary2cm capture changed");
 require(!zero(query(pose(.04))),"Ordinary capture wrongly latches and suppresses later correction");
 query(pose(.06));tracker->terminal_correction_since_=tracker->now()-rclcpp::Duration::from_seconds(5);
 require(!zero(query(pose(.06)))&&!tracker->terminal_correction_expired_,"Timeout leaked outside final5cm");
 tracker->exec_time_=0.;require(!tracker->terminal_correction_expired_,"Unexpected failed state");query(pose(.02187977));
 require(!tracker->terminal_correction_watching_,"Unexpired curve entered terminal timeout");
 auto cancel=std::make_shared<scan_planner_msgs::msg::P2BCancel>();
 cancel->run_id=message->run_id;cancel->epoch=1;cancel->request_id=message->request_id;cancel->goal_id=message->goal_id;
 cancel->route_id=message->route_id;cancel->command_id=message->command_id;cancel->generation=1;
 tracker->p2bCancelCallback(cancel);tracker->bsplineCallback(message);
 require(!tracker->receive_traj_&&zero(query(body)),"Cancelled curve restarted");
 message->generation=2;message->emergency_stop=true;++message->traj_id;tracker->bsplineCallback(message);
 require(zero(query(body)),"Emergency stop lost priority");
 std::cout<<"V187_TERMINAL_CAPTURE_PASS legacy_preserved=1 ordinary_capture_not_latched=1 correction_budget_s=1.5 timeout_requests_failure=1\n";
 tracker.reset();rclcpp::shutdown();return 0;
}
