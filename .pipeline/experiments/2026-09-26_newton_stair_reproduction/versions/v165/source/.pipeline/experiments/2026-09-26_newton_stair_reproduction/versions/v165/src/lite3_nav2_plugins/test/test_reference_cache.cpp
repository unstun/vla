#include <gtest/gtest.h>
#include "../src/bind_route.cpp"
TEST(ReferenceCache, ExactGeometryAndOriginalStampOnlyForSameGoal) {
 BT::BehaviorTreeFactory factory;
 factory.registerNodeType<lite3_nav2::RememberGlobalPath>("RememberGlobalPath");
 factory.registerNodeType<lite3_nav2::RestoreGlobalPath>("RestoreGlobalPath");
 auto bb=BT::Blackboard::create();geometry_msgs::msg::PoseStamped goal;goal.header.frame_id="world";goal.pose.position.x=9;goal.pose.orientation.w=1;
 nav_msgs::msg::Path path;path.header.frame_id="world";path.header.stamp.sec=7;path.poses={goal,goal};path.poses[0].pose.position.x=1;
 bb->set("goal",goal);bb->set("candidate",path);
 auto save=factory.createTreeFromText(R"(<root main_tree_to_execute="Main"><BehaviorTree ID="Main"><RememberGlobalPath goal="{goal}" path="{candidate}"/></BehaviorTree></root>)",bb);
 auto restore=factory.createTreeFromText(R"(<root main_tree_to_execute="Main"><BehaviorTree ID="Main"><RestoreGlobalPath goal="{goal}" path="{restored}"/></BehaviorTree></root>)",bb);
 EXPECT_EQ(restore.tickRoot(),BT::NodeStatus::FAILURE);
 EXPECT_EQ(save.tickRoot(),BT::NodeStatus::SUCCESS);
 path.poses[0].pose.position.x=100;bb->set("candidate",path);
 EXPECT_EQ(restore.tickRoot(),BT::NodeStatus::SUCCESS);
 auto recovered=bb->get<nav_msgs::msg::Path>("restored");EXPECT_DOUBLE_EQ(recovered.poses[0].pose.position.x,1);EXPECT_EQ(recovered.header.stamp.sec,7);
 goal.pose.position.x=10;bb->set("goal",goal);EXPECT_EQ(restore.tickRoot(),BT::NodeStatus::FAILURE);
}
TEST(ReferenceCache, InvalidNewPathDoesNotBecomeACachedReference) {
 BT::BehaviorTreeFactory factory;factory.registerNodeType<lite3_nav2::RememberGlobalPath>("RememberGlobalPath");
 auto bb=BT::Blackboard::create();geometry_msgs::msg::PoseStamped goal;goal.header.frame_id="world";goal.pose.orientation.w=1;nav_msgs::msg::Path path;path.header.frame_id="world";
 bb->set("goal",goal);bb->set("path",path);
 auto tree=factory.createTreeFromText(R"(<root main_tree_to_execute="Main"><BehaviorTree ID="Main"><RememberGlobalPath goal="{goal}" path="{path}"/></BehaviorTree></root>)",bb);
 EXPECT_EQ(tree.tickRoot(),BT::NodeStatus::FAILURE);lite3_nav2::GlobalReference saved;EXPECT_FALSE(bb->get("lite3_previous_pct_reference",saved));
}
