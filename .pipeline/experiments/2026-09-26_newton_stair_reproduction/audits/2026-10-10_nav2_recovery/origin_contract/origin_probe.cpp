#include <plan_manage/scan_replan_fsm.h>
#include <plan_env/astar_grid_coordinates.h>
#include <rcl/time.h>
#include <iomanip>
#include <iostream>
#include <limits>

int main(int argc,char **argv) {
  rclcpp::init(argc,argv);
  auto node=std::make_shared<rclcpp::Node>("scan_planner_node");
  node->declare_parameter<bool>("grid_map.asynchronous_mapping",false);
  node->set_parameter(rclcpp::Parameter("grid_map.asynchronous_mapping",false));
  auto clock=node->get_clock()->get_clock_handle();
  if(rcl_enable_ros_time_override(clock)!=RCL_RET_OK || rcl_set_ros_time_override(clock,1000000000LL)!=RCL_RET_OK)
    throw std::runtime_error("Clock override failed");
  scan_planner::SCANReplanFSM fsm;fsm.init(node.get());
  fsm.exec_timer_->cancel();fsm.safety_timer_->cancel();
  auto map=fsm.planner_manager_->grid_map_;map->occ_timer_->cancel();map->vis_timer_->cancel();
  if(map->async_mapping_)throw std::runtime_error("Probe requires deterministic input admission");
  // Empty observation is deliberate: reference admission must still reject.
  // The A* grid's actual search center witnesses which start was consumed.
  fsm.have_odom_=true;fsm.odom_pos_=Eigen::Vector3d(1,2,3);fsm.odom_vel_.setZero();
  fsm.end_pt_.setZero();fsm.end_vel_.setZero();fsm.reference_neighbor_point_.setZero();
  fsm.exec_state_=scan_planner::SCANReplanFSM::WAIT_TARGET;
  auto route=std::make_shared<scan_planner_msgs::msg::P2BRoute>();
  route->run_id="origin-probe";route->epoch=1;route->request_id="r";route->goal_id="g";
  route->route_id="path";route->command_id="command";route->generation=1;
  route->map_epoch="map";route->map_revision=1;route->has_goal_pose=true;
  route->path.header.frame_id="world";route->path.header.stamp=node->now();
  for(const auto &xyz:std::vector<Eigen::Vector3d>{fsm.odom_pos_,Eigen::Vector3d(2,2,3)}) {
    geometry_msgs::msg::PoseStamped p;p.header=route->path.header;p.pose.orientation.w=1;
    p.pose.position.x=xyz.x();p.pose.position.y=xyz.y();p.pose.position.z=xyz.z();
    route->path.poses.push_back(p);
  }
  route->goal_pose=route->path.poses.back().pose;
  auto search=fsm.planner_manager_->bspline_optimizer_rebound_->a_star_;
  Eigen::Vector3d expected;
  const Eigen::Vector3d end(2,2,3);
  for(int axis=0;axis<3;++axis)
    expected[axis]=reactive_stair::startAlignedSearchCenter(fsm.odom_pos_[axis],end[axis],map->getResolution());
  int matched=0;
  for(int mode=0;mode<2;++mode) {
    fsm.start_pt_=mode==0?Eigen::Vector3d(30,40,50):Eigen::Vector3d::Constant(std::numeric_limits<double>::quiet_NaN());
    search->center_=Eigen::Vector3d::Constant(-999);
    fsm.p2bRouteCallback(route);
    const bool used_current=(search->center_-expected).norm()<1e-9;
    matched+=used_current;
    if(fsm.have_target_)throw std::runtime_error("Unknown map was incorrectly admitted");
    std::cout<<std::setprecision(17)<<"ORIGIN_CASE mode="<<mode<<" used_current="<<used_current
      <<" center="<<search->center_.transpose()<<" expected="<<expected.transpose()<<std::endl;
  }
  auto future=std::make_shared<nav_msgs::msg::Odometry>();
  future->header.frame_id="world";future->child_frame_id="base";
  future->header.stamp=rclcpp::Time(1000000001LL,RCL_ROS_TIME);
  future->pose.pose.position.x=1.5;future->pose.pose.position.y=2;future->pose.pose.position.z=3;
  future->pose.pose.orientation.w=1;fsm.odometryCallback(future);
  for(int mode=2;mode<4;++mode) {
    if(mode==3 && rcl_set_ros_time_override(clock,1000000001LL)!=RCL_RET_OK)
      throw std::runtime_error("Clock advance failed");
    const Eigen::Vector3d due=mode==2?Eigen::Vector3d(1,2,3):Eigen::Vector3d(1.5,2,3);
    for(int axis=0;axis<3;++axis)
      expected[axis]=reactive_stair::startAlignedSearchCenter(due[axis],end[axis],map->getResolution());
    search->center_=Eigen::Vector3d::Constant(-999);
    fsm.p2bRouteCallback(route);
    const bool used_current=(search->center_-expected).norm()<1e-9;matched+=used_current;
    if(fsm.have_target_)throw std::runtime_error("Unknown map was incorrectly admitted");
    std::cout<<"ORIGIN_CASE mode="<<mode<<" used_current="<<used_current
      <<" center="<<search->center_.transpose()<<" expected="<<expected.transpose()<<std::endl;
  }
  std::cout<<"ORIGIN_RESULT matched="<<matched<<" cases=4 unknown_map_rejected=1"<<std::endl;
  rclcpp::shutdown();return matched==4?0:1;
}
