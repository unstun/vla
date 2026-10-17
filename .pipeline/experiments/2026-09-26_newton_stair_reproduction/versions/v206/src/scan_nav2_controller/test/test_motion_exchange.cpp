#include <gtest/gtest.h>
#include <scan_nav2_controller/motion_exchange.hpp>
#include <thread>

using scan_nav2_controller::MotionExchange;

static nav_msgs::msg::Path route(double x=1.)
{
  nav_msgs::msg::Path p;p.header.frame_id="world";
  geometry_msgs::msg::PoseStamped pose;pose.pose.position.x=x;pose.pose.orientation.w=1.;
  p.poses={pose,pose};return p;
}

TEST(MotionExchange, CopiesInputsAndDeliversEachOutputOnce)
{
  MotionExchange exchange;auto input=route();
  const auto generation=exchange.setRoute(input,true);
  input.poses.back().pose.position.x=99;
  EXPECT_DOUBLE_EQ(exchange.input().route->poses.back().pose.position.x,1.);
  scan_planner_msgs::msg::Bspline spline;spline.traj_id=7;
  ASSERT_TRUE(exchange.publish(generation,spline));spline.traj_id=99;
  auto output=exchange.take();ASSERT_TRUE(output);EXPECT_EQ(output->spline->traj_id,7);
  EXPECT_FALSE(exchange.take());
}
TEST(MotionExchange, LatestRouteAndResultReplaceRatherThanAccumulate)
{
  MotionExchange exchange;uint64_t generation=0;
  for(int i=0;i<1000;++i) generation=exchange.setRoute(route(i),i==0);
  EXPECT_DOUBLE_EQ(exchange.input().route->poses.back().pose.position.x,999);
  for(int i=0;i<1000;++i) {
    scan_planner_msgs::msg::Bspline spline;spline.traj_id=i;
    EXPECT_TRUE(exchange.publish(generation,spline));
  }
  EXPECT_EQ(exchange.take()->spline->traj_id,999);EXPECT_FALSE(exchange.take());
}
TEST(MotionExchange, IdenticalRefreshKeepsGenerationButChangesInputRevision)
{
  MotionExchange exchange;
  const auto generation=exchange.setRoute(route(),true);
  const auto first=exchange.input();
  EXPECT_EQ(exchange.setRoute(route(),false),generation);
  EXPECT_GT(exchange.input().revision,first.revision);
  EXPECT_EQ(exchange.input().reset,first.reset);
}
TEST(MotionExchange, CancelAndNewRouteRejectLateSolverAndFreezeResults)
{
  MotionExchange exchange;const auto old=exchange.setRoute(route(),true);
  scan_planner_msgs::msg::Bspline spline;spline.traj_id=5;
  ASSERT_TRUE(exchange.publish(old,spline));exchange.cancel();
  EXPECT_FALSE(exchange.take());EXPECT_FALSE(exchange.publish(old,spline));
  const auto cancel_reset=exchange.input().reset;
  const auto fresh=exchange.setRoute(route(),true);
  exchange.setRoute(route(),false); // Cannot erase a pending cancellation/new-goal reset.
  EXPECT_GT(exchange.input().reset,cancel_reset);
  EXPECT_FALSE(exchange.publish(old,spline));
  exchange.feedback(old,true,5);EXPECT_FALSE(exchange.input().feedback.frozen);
  exchange.feedback(fresh,true,6);EXPECT_TRUE(exchange.input().feedback.frozen);
  EXPECT_EQ(exchange.input().feedback.trajectory,6);
}
TEST(MotionExchange, ChangedRoutePreservesPendingSolveOutputAndFeedbackForSameGoal)
{
  MotionExchange exchange;const auto old=exchange.setRoute(route(),true);
  scan_planner_msgs::msg::Bspline completed;completed.traj_id=4;
  ASSERT_TRUE(exchange.publish(old,completed));exchange.feedback(old,true,4);
  const auto previous=exchange.input();
  auto next=route();next.poses.front().pose.position.y=.5;
  const auto generation=exchange.setRoute(next,false);
  EXPECT_EQ(old,generation);
  EXPECT_EQ(exchange.input().revision,previous.revision+1);
  EXPECT_EQ(exchange.input().reset,previous.reset);
  EXPECT_TRUE(exchange.input().feedback.frozen);
  EXPECT_EQ(exchange.input().feedback.trajectory,4);
  EXPECT_EQ(exchange.take()->spline->traj_id,4);
  EXPECT_DOUBLE_EQ(exchange.input().route->poses.front().pose.position.y,.5);
  scan_planner_msgs::msg::Bspline spline;
  EXPECT_TRUE(exchange.publish(old,spline));EXPECT_TRUE(exchange.publish(generation,spline));
}
TEST(MotionExchange, ConcurrentCancelCannotResurrectWorkerOutput)
{
  MotionExchange exchange;const auto old=exchange.setRoute(route(),true);
  std::atomic<bool> running{true};
  std::thread worker([&] {
    scan_planner_msgs::msg::Bspline spline;
    while(running.load()) {exchange.publish(old,spline);exchange.input();}
  });
  for(int i=0;i<200;++i) {exchange.cancel();exchange.setRoute(route(),true);}
  running=false;worker.join();
  EXPECT_FALSE(exchange.take());
}
TEST(MotionExchange, SolverCrossingOrdinaryRefreshPublishesItsCompletedSpline)
{
  MotionExchange exchange;exchange.setRoute(route(),true);
  std::atomic<bool> started{false},release{false},accepted{false};
  std::thread worker([&] {
    const auto input=exchange.input();started=true;
    while(!release.load())std::this_thread::yield();
    scan_planner_msgs::msg::Bspline result;result.traj_id=17;
    accepted=exchange.publish(input.generation,result);
  });
  while(!started.load())std::this_thread::yield();
  auto changed=route();changed.poses.front().pose.position.y=.2;
  exchange.setRoute(changed,false);release=true;worker.join();
  ASSERT_TRUE(accepted.load());ASSERT_TRUE(exchange.take());
}
