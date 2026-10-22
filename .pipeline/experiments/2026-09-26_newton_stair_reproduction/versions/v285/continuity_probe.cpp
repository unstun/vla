#include <scan_nav2_controller/tracking_node.hpp>
#include <lite3_nav2_plugins/route_policy.hpp>
#include <rcl/time.h>
#include <lite3_nav2_plugins/plan_on_goal_change.hpp>
#include <behaviortree_cpp_v3/bt_factory.h>
#include <iostream>

class TestPlan : public lite3_nav2::PlanOnGoalChange {
 public:
  using lite3_nav2::PlanOnGoalChange::PlanOnGoalChange;
  void pipelineReset(){setStatus(BT::NodeStatus::IDLE);}
};
int main(int argc,char **argv) {
  rclcpp::init(argc,argv);
  unsigned coupled=0,advanced=0;
  for(int rotation=0;rotation<4;++rotation) {
    auto node=std::make_shared<scan_planner::TrackingNode>();
    auto clock=node->get_clock()->get_clock_handle();
    if(rcl_enable_ros_time_override(clock)!=RCL_RET_OK)throw std::runtime_error("Clock override failed");
    int64_t stamp=10000000000LL;
    if(rcl_set_ros_time_override(clock,stamp)!=RCL_RET_OK)throw std::runtime_error("Clock set failed");
    const double angle=rotation*M_PI/2.;
    const Eigen::Vector3d shift(.37*rotation,-.29*rotation,.42);
    const Eigen::Vector3d axis(std::cos(angle),std::sin(angle),0.);
    nav_msgs::msg::Path path;path.header.frame_id="world";
    geometry_msgs::msg::PoseStamped body;body.header=path.header;
    body.pose.position.x=shift.x();body.pose.position.y=shift.y();body.pose.position.z=shift.z();
    body.pose.orientation.z=std::sin((angle-1.6)/2);body.pose.orientation.w=std::cos((angle-1.6)/2);
    path.poses={body,body};
    path.poses.back().pose.position.x+=50*axis.x();path.poses.back().pose.position.y+=50*axis.y();
    node->setReferencePath(path);
    auto spline=std::make_shared<scan_planner_msgs::msg::Bspline>();spline->order=3;spline->traj_id=1;
    spline->start_time=rclcpp::Time(stamp,RCL_ROS_TIME);
    for(int i=0;i<12;++i) {
      geometry_msgs::msg::Point p;const Eigen::Vector3d q=shift+.4*i*axis;
      p.x=q.x();p.y=q.y();p.z=q.z();spline->pos_pts.push_back(p);
    }
    for(int i=-3;i<13;++i)spline->knots.push_back(i);
    node->bsplineCallback(spline);
    for(int i=0;i<60;++i) {
      stamp+=20000000LL;
      if(rcl_set_ros_time_override(clock,stamp)!=RCL_RET_OK)throw std::runtime_error("Clock advance failed");
      node->sample(body);
    }
    coupled+=std::hypot(node->sampled_command_.linear.x,node->sampled_command_.linear.y)>.05 &&
      std::abs(node->sampled_command_.angular.z)>.1 && !node->executionFrozen();
    advanced+=node->exec_time_>0. && node->exec_time_<.4;
  }
  unsigned plans=0;
  if(argc<2 || std::string(argv[1])!="--tracking-only") {
  BT::BehaviorTreeFactory factory;
  factory.registerSimpleAction("Plan",[&](BT::TreeNode &){++plans;return BT::NodeStatus::SUCCESS;});
  factory.registerNodeType<TestPlan>("PlanOnGoalChange");
  auto board=BT::Blackboard::create();geometry_msgs::msg::PoseStamped goal;
  goal.header.frame_id="world";goal.pose.orientation.w=1.;board->set("goal",goal);
  auto tree=factory.createTreeFromText(R"(<root main_tree_to_execute="Main"><BehaviorTree ID="Main"><PlanOnGoalChange goal="{goal}"><Plan/></PlanOnGoalChange></BehaviorTree></root>)",board);
  for(int i=0;i<100;++i) {
    tree.tickRoot();dynamic_cast<TestPlan *>(tree.rootNode())->pipelineReset();
    goal.header.stamp=rclcpp::Time(i+1);board->set("goal",goal);
  }
  if(plans!=1)throw std::runtime_error("BT status/timestamp refresh restarted global planning");
  goal.pose.position.x=1.;board->set("goal",goal);tree.tickRoot();
  if(plans!=2)throw std::runtime_error("Changed destination did not plan");
  tree.haltTree();tree.tickRoot();
  if(plans!=3)throw std::runtime_error("Explicit halt did not release plan ownership");
  }
  std::cout<<"CONTINUITY {\"coupled\":"<<coupled<<",\"phase_advanced\":"<<advanced<<",\"BT_plan_calls\":"<<plans<<",\"total\":4}\n";
  rclcpp::shutdown();
  return coupled==4&&advanced==4?0:1;
}
