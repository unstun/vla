#include "lite3_nav2_plugins/recovery_bt.hpp"
#include <behaviortree_cpp_v3/bt_factory.h>
#include "lite3_nav2_plugins/plan_on_goal_change.hpp"
BT_REGISTER_NODES(factory)
{
  factory.registerNodeType<lite3_nav2::FollowPathWithFailure>("FollowPathWithFailure");
  factory.registerNodeType<lite3_nav2::RetryAllowed>("RetryAllowed");
  factory.registerNodeType<lite3_nav2::PlanOnGoalChange>("PlanOnGoalChange");
}
