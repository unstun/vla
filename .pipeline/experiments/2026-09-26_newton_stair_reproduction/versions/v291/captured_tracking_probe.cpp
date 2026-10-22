// Native controller over recorded poses/splines. No counterfactual physics.
#include <scan_nav2_controller/controller.hpp>
#include <scan_nav2_controller/tracking_node.hpp>
#include <rcl/time.h>
#include <fstream>
#include <iomanip>

int main(int argc,char **argv) {
  rclcpp::init(argc,argv);rclcpp::NodeOptions options;
  options.parameter_overrides({rclcpp::Parameter("use_sim_time",true),
    rclcpp::Parameter("SCAN.native_worker_enabled",false)});
  auto node=std::make_shared<rclcpp_lifecycle::LifecycleNode>("controller_server",options);
  scan_nav2_controller::Controller controller;controller.configure(node,"SCAN",nullptr,nullptr);controller.activate();
  const auto set_clock=[&](int64_t stamp) {
    for(const auto &clock:{node->get_clock(),controller.bridge_->get_clock(),controller.motion_->tracker_->get_clock()}) {
      if(rcl_enable_ros_time_override(clock->get_clock_handle())!=RCL_RET_OK ||
          rcl_set_ros_time_override(clock->get_clock_handle(),stamp)!=RCL_RET_OK)
        throw std::runtime_error("Native replay clock override failed");
    }
  };
  const auto read_pose=[](std::istream &in,geometry_msgs::msg::Pose &p) {
    in>>p.position.x>>p.position.y>>p.position.z>>p.orientation.x>>p.orientation.y>>p.orientation.z>>p.orientation.w;
  };
  std::ifstream input(std::getenv("TRACKING_INPUT"));std::ofstream out(std::getenv("TRACKING_OUTPUT"));
  out<<"stamp_ns,distance_m,speed_m_s,vx,vy,wz,phase_s,braking,error\n"<<std::setprecision(17);
  char type;int64_t stamp;
  while(input>>type>>stamp) {
    set_clock(stamp);
    if(type=='G') {
      nav_msgs::msg::Path path;path.header.frame_id="world";path.header.stamp=node->now();
      size_t size;input>>size;
      for(size_t i=0;i<size;++i) {geometry_msgs::msg::PoseStamped p;p.header=path.header;read_pose(input,p.pose);path.poses.push_back(p);}
      controller.setPlan(path);
    } else if(type=='B') {
      scan_planner_msgs::msg::Bspline spline;int64_t origin;size_t points,knots;
      input>>spline.traj_id>>origin>>spline.emergency_stop>>spline.reverse_motion>>spline.order>>points>>knots;
      spline.start_time=rclcpp::Time(origin,RCL_ROS_TIME);
      for(size_t i=0;i<points;++i) {geometry_msgs::msg::Point p;input>>p.x>>p.y>>p.z;spline.pos_pts.push_back(p);}
      for(size_t i=0;i<knots;++i) {double k;input>>k;spline.knots.push_back(k);}
      if(controller.motion_->hasRoute())controller.motion_->exchange_->publish(controller.motion_->generation_,spline);
    } else if(type=='C') {
      geometry_msgs::msg::PoseStamped p;p.header.frame_id="world";p.header.stamp=node->now();read_pose(input,p.pose);
      geometry_msgs::msg::Twist velocity;input>>velocity.linear.x>>velocity.linear.y>>velocity.linear.z
        >>velocity.angular.x>>velocity.angular.y>>velocity.angular.z;
      if(!controller.motion_->hasRoute())continue;
      bool error=false;geometry_msgs::msg::Twist command;
      try {command=controller.computeVelocityCommands(p,velocity).twist;}catch(const std::exception &) {error=true;}
      const auto &goal=controller.state_->goal_pose.position;
      out<<stamp<<','<<std::hypot(goal.x-p.pose.position.x,goal.y-p.pose.position.y)<<','
        <<std::hypot(command.linear.x,command.linear.y)<<','<<command.linear.x<<','<<command.linear.y<<','
        <<command.angular.z<<','<<controller.motion_->tracker_->exec_time_<<','<<controller.goal_braking_<<','<<error<<'\n';
    } else throw std::runtime_error("Unknown recorded controller event");
    if(!input)throw std::runtime_error("Malformed recorded controller event");
  }
  controller.cleanup();rclcpp::shutdown();return 0;
}
