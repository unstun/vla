#include <gtest/gtest.h>
#include <plan_manage/scan_replan_fsm.h>
#include <bspline_opt/full_trajectory_collision.h>
#include <plan_env/reactive_collision.h>
#include <scan_nav2_controller/controller.hpp>
#include <pluginlib/class_loader.hpp>
#include <nav2_core/exceptions.hpp>
#include <chrono>
#include <functional>
#include <limits>
#include <thread>
#include <rcl/time.h>

using namespace std::chrono_literals;
namespace sm=scan_planner_msgs::msg;

class PluginTest : public ::testing::Test
{
protected:
  static void SetUpTestCase() { int argc=0; rclcpp::init(argc,nullptr); }
  static void TearDownTestCase() { rclcpp::shutdown(); }
  virtual bool routeLookaheadEnabled() const { return false; }
  void SetUp() override
  {
    parent=std::make_shared<rclcpp_lifecycle::LifecycleNode>("test_nav2_scan");
    parent->declare_parameter("SCAN.native_worker_enabled",false);
    parent->declare_parameter("SCAN.route_lookahead_heading_enabled",routeLookaheadEnabled());
    io=std::make_shared<rclcpp::Node>("test_scan_inputs");
    controller_loader=std::make_unique<pluginlib::ClassLoader<nav2_core::Controller>>("nav2_core","nav2_core::Controller");
    goal_loader=std::make_unique<pluginlib::ClassLoader<nav2_core::GoalChecker>>("nav2_core","nav2_core::GoalChecker");
    goal=goal_loader->createSharedInstance("scan_nav2_controller/GoalChecker");
    goal->initialize(parent,"goal_checker");
    plugin=controller_loader->createSharedInstance("scan_nav2_controller/Controller");
    plugin->configure(parent,"SCAN",nullptr,nullptr);
    actual=dynamic_cast<scan_nav2_controller::Controller *>(plugin.get());
    ASSERT_NE(actual,nullptr);
    plugin->activate();
    spline=io->create_publisher<sm::Bspline>("/quad_0/planning/bspline",10);
    commands=io->create_subscription<geometry_msgs::msg::Twist>("/quad_0/cmd_vel",20,
      [this](geometry_msgs::msg::Twist::ConstSharedPtr msg) { received.push_back(*msg); });
    routes=io->create_subscription<nav_msgs::msg::Path>("/pct_path",rclcpp::QoS(1).reliable().transient_local(),
      [this](nav_msgs::msg::Path::ConstSharedPtr msg) { dispatched.push_back(*msg); });
    ASSERT_TRUE(wait([&] { return spline->get_subscription_count()>0; }));
    route.header.frame_id="world"; route.header.stamp=parent->now();
    route.poses={pose(0),pose(8)};
  }
  void TearDown() override
  {
    if (plugin) { plugin->deactivate(); plugin->cleanup(); }
    actual=nullptr; plugin.reset(); goal.reset();
    controller_loader.reset(); goal_loader.reset(); io.reset(); parent.reset();
  }
  bool wait(const std::function<bool()> &predicate,double seconds=2.0)
  {
    const auto end=std::chrono::steady_clock::now()+std::chrono::duration<double>(seconds);
    while(std::chrono::steady_clock::now()<end) {
      rclcpp::spin_some(io);
      if (actual) actual->spinBridge();
      if(predicate()) return true;
      std::this_thread::sleep_for(5ms);
    }
    return false;
  }
  geometry_msgs::msg::PoseStamped pose(double x=0,double z=0.42)
  {
    geometry_msgs::msg::PoseStamped p; p.header.frame_id="world"; p.header.stamp=parent->now();
    p.pose.position.x=x; p.pose.position.z=z; p.pose.orientation.w=1; return p;
  }
  void plan()
  {
    route.header.stamp=parent->now(); plugin->setPlan(route);
    ASSERT_TRUE(wait([&] { return !dispatched.empty() && dispatched.back()==route; }));
    EXPECT_EQ(dispatched.back(),route);
  }
  sm::Bspline curve()
  {
    sm::Bspline m; m.order=3; m.traj_id=1; m.start_time=parent->now();
    for(int i=0;i<6;++i) { geometry_msgs::msg::Point p; p.x=0.4*i; p.z=0.42; m.pos_pts.push_back(p); }
    for(int i=-3;i<7;++i) m.knots.push_back(i);
    return m;
  }
  void moving()
  {
    plan(); spline->publish(curve());
    ASSERT_TRUE(wait([&] {
      return plugin->computeVelocityCommands(pose(),geometry_msgs::msg::Twist()).twist.linear.x>0;
    }));
    EXPECT_EQ(commands->get_publisher_count(),0u);
    EXPECT_TRUE(received.empty());
  }
  void completeStand(const geometry_msgs::msg::PoseStamped &at)
  {
    const auto clock=parent->get_clock();
    const int64_t start=clock->now().nanoseconds();
    ASSERT_EQ(rcl_enable_ros_time_override(clock->get_clock_handle()),RCL_RET_OK);
    for(int tick=0;tick<=100;++tick) {
      const auto stamp=start+tick*20000000LL;
      ASSERT_EQ(rcl_set_ros_time_override(clock->get_clock_handle(),stamp),RCL_RET_OK);
      auto sample=std::make_shared<lite3_nav2_interfaces::msg::RobotExecutionState>();
      sample->header.frame_id="base_link";sample->header.stamp=parent->now();
      sample->simulation_time_ns=stamp;sample->state_sequence=tick+1;sample->run_epoch_ns=500;
      sample->stance_mode=sample->FIXED_STAND;sample->policy_owns_joints=false;
      sample->navigation_ready=true;
      actual->onExecution(sample);
      plugin->computeVelocityCommands(at,geometry_msgs::msg::Twist());
      if(tick<100) EXPECT_FALSE(goal->isGoalReached(at.pose,at.pose,geometry_msgs::msg::Twist()));
    }
  }
  void expiredCornerStub(bool reverse=false)
  {
    for (const auto &clock : {parent->get_clock(),actual->tracker_->get_clock()}) {
      ASSERT_EQ(rcl_enable_ros_time_override(clock->get_clock_handle()),RCL_RET_OK);
      ASSERT_EQ(rcl_set_ros_time_override(clock->get_clock_handle(),19000000000LL),RCL_RET_OK);
    }
    auto end=pose();end.pose.position.y=4.0;
    route.poses={pose(-1.0),pose(),end};route.header.stamp=parent->now();
    plugin->setPlan(route);
    auto stub=std::make_shared<sm::Bspline>(curve());stub->reverse_motion=reverse;
    for (size_t i=0;i<stub->pos_pts.size();++i)
      stub->pos_pts[i].x=i<3 ? (reverse ? 0.05 : -0.05) : 0.0;
    actual->onSpline(stub);
    ASSERT_TRUE(actual->tracker_->haveTrajectory());
    actual->tracker_->exec_time_=actual->tracker_->traj_duration_;
    EXPECT_LT(actual->tracker_->traj_[1].evaluateDeBoorT(actual->tracker_->exec_time_).head<2>().squaredNorm(),1e-4);
  }
  geometry_msgs::msg::Twist cornerCommand(double yaw)
  {
    auto body=pose();body.pose.orientation.z=std::sin(yaw/2);body.pose.orientation.w=std::cos(yaw/2);
    return plugin->computeVelocityCommands(body,geometry_msgs::msg::Twist()).twist;
  }
  rclcpp_lifecycle::LifecycleNode::SharedPtr parent;
  rclcpp::Node::SharedPtr io;
  std::unique_ptr<pluginlib::ClassLoader<nav2_core::Controller>> controller_loader;
  std::unique_ptr<pluginlib::ClassLoader<nav2_core::GoalChecker>> goal_loader;
  std::shared_ptr<nav2_core::Controller> plugin;
  std::shared_ptr<nav2_core::GoalChecker> goal;
  scan_nav2_controller::Controller *actual{nullptr};
  rclcpp::Publisher<sm::Bspline>::SharedPtr spline;
  rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr commands;
  rclcpp::Subscription<nav_msgs::msg::Path>::SharedPtr routes;
  nav_msgs::msg::Path route;
  std::vector<geometry_msgs::msg::Twist> received;
  std::vector<nav_msgs::msg::Path> dispatched;
};

TEST_F(PluginTest, DirectPathAndNativeSplineReturnTwistWithoutPublishing) { moving(); }

TEST_F(PluginTest, RouteHeadingDefaultsOffAtExpiredStoppedStub)
{
  expiredCornerStub();
  auto *actual=dynamic_cast<scan_nav2_controller::Controller *>(plugin.get());
  ASSERT_NE(actual,nullptr);
  EXPECT_FALSE(parent->get_parameter("SCAN.route_lookahead_heading_enabled").as_bool());
  EXPECT_FALSE(actual->tracker_->route_lookahead_heading_enabled_);
  EXPECT_EQ(cornerCommand(0.0),geometry_msgs::msg::Twist());
  bool used=true;
  EXPECT_DOUBLE_EQ(actual->tracker_->estimateDesiredYaw(actual->tracker_->traj_duration_,
    Eigen::Vector3d(0,0,0.42),&used),0.0);
  EXPECT_FALSE(used);
}

TEST_F(PluginTest, RouteLookaheadDistanceMustBeFiniteAndPositive)
{
  for (double distance : {0.0,-0.5,std::numeric_limits<double>::infinity(),
                         std::numeric_limits<double>::quiet_NaN()}) {
    rclcpp::NodeOptions options;
    options.parameter_overrides({rclcpp::Parameter("route_lookahead_dist",distance)});
    EXPECT_THROW(std::make_shared<scan_planner::TrackingNode>(options),std::runtime_error);
  }
}

class RouteHeadingTest : public PluginTest
{
protected:
  bool routeLookaheadEnabled() const override { return true; }
};

TEST_F(RouteHeadingTest, ExpiredStoppedStubTurnsThroughBothHeadingBands)
{
  expiredCornerStub();
  auto *actual=dynamic_cast<scan_nav2_controller::Controller *>(plugin.get());
  ASSERT_NE(actual,nullptr);
  ASSERT_TRUE(actual->tracker_->route_lookahead_heading_enabled_);
  EXPECT_DOUBLE_EQ(actual->tracker_->route_lookahead_dist_,0.5);
  const double middle=(actual->tracker_->goal_yaw_tolerance_+actual->tracker_->heading_error_threshold_)/2;
  for (double error : {M_PI/2,middle}) {
    const auto command=cornerCommand(M_PI/2-error);
    EXPECT_DOUBLE_EQ(command.linear.x,0.0);EXPECT_DOUBLE_EQ(command.linear.y,0.0);
    EXPECT_DOUBLE_EQ(command.linear.z,0.0);EXPECT_GT(command.angular.z,0.0);
    bool used=false;
    EXPECT_NEAR(actual->tracker_->estimateDesiredYaw(actual->tracker_->traj_duration_,
      Eigen::Vector3d(0,0,0.42),&used),M_PI/2,1e-9);
    EXPECT_TRUE(used);EXPECT_TRUE(actual->has_active_plan_);
  }
  EXPECT_EQ(cornerCommand(M_PI/2-actual->tracker_->goal_yaw_tolerance_/2),geometry_msgs::msg::Twist());
}

TEST_F(RouteHeadingTest, SameGoalRefreshChangesHeadingAndPreservesGoalLatch)
{
  expiredCornerStub();
  auto *actual=dynamic_cast<scan_nav2_controller::Controller *>(plugin.get());
  ASSERT_NE(actual,nullptr);
  EXPECT_GT(cornerCommand(0.0).angular.z,0.0);
  auto &tracker=*actual->tracker_;
  const Eigen::Vector3d original_goal=tracker.goal_pos_;
  const double original_yaw=tracker.goal_yaw_;
  tracker.goal_position_latched_=true;
  auto turn=pose();turn.pose.position.y=-2.0;
  route.poses={pose(-1.0),pose(),turn,route.poses.back()};
  plugin->setPlan(route);
  EXPECT_EQ(tracker.reference_path_,route);
  EXPECT_TRUE(tracker.goal_position_latched_);
  EXPECT_DOUBLE_EQ((tracker.goal_pos_-original_goal).norm(),0.0);
  EXPECT_DOUBLE_EQ(tracker.goal_yaw_,original_yaw);
  double yaw=0.0;EXPECT_FALSE(tracker.estimateRouteLookaheadYaw(Eigen::Vector3d(0,0,0.42),yaw));
  tracker.goal_position_latched_=false;
  EXPECT_LT(cornerCommand(0.0).angular.z,0.0);
}

TEST_F(RouteHeadingTest, ReverseStubKeepsOriginalBodyHeading)
{
  expiredCornerStub(true);
  auto *actual=dynamic_cast<scan_nav2_controller::Controller *>(plugin.get());
  ASSERT_NE(actual,nullptr);ASSERT_TRUE(actual->tracker_->reverse_motion_);
  EXPECT_EQ(cornerCommand(0.0),geometry_msgs::msg::Twist());
  double yaw=0.0;EXPECT_FALSE(actual->tracker_->estimateRouteLookaheadYaw(Eigen::Vector3d(0,0,0.42),yaw));
}

TEST_F(RouteHeadingTest, PillarUTurnUsesForwardRouteBeyondExpiredStub)
{
  expiredCornerStub();
  auto *actual=dynamic_cast<scan_nav2_controller::Controller *>(plugin.get());
  ASSERT_NE(actual,nullptr);
  route.poses={pose(-1.0),pose(),pose(-2.0),route.poses.back()};
  plugin->setPlan(route);
  const auto command=cornerCommand(0.0);
  EXPECT_DOUBLE_EQ(command.linear.x,0.0);EXPECT_DOUBLE_EQ(command.linear.y,0.0);
  EXPECT_GT(command.angular.z,0.0);
  double yaw=0.0;ASSERT_TRUE(actual->tracker_->estimateRouteLookaheadYaw(Eigen::Vector3d(0,0,0.42),yaw));
  EXPECT_NEAR(std::abs(yaw),M_PI,1e-9);
}

TEST_F(RouteHeadingTest, FinalGoalCaptureOwnsYawBeforeAndAfterLatch)
{
  expiredCornerStub();
  auto *actual=dynamic_cast<scan_nav2_controller::Controller *>(plugin.get());
  ASSERT_NE(actual,nullptr);auto &tracker=*actual->tracker_;
  auto body=pose();body.pose.position=route.poses.back().pose.position;
  body.pose.orientation.z=std::sin(-0.4/2);body.pose.orientation.w=std::cos(-0.4/2);
  auto odom=std::make_shared<nav_msgs::msg::Odometry>();odom->pose.pose=body.pose;
  tracker.odomCallback(odom);
  double yaw=0.0;ASSERT_FALSE(tracker.goal_position_latched_);
  EXPECT_FALSE(tracker.estimateRouteLookaheadYaw(Eigen::Vector3d(0,0,0.42),yaw));
  const auto command=plugin->computeVelocityCommands(body,geometry_msgs::msg::Twist()).twist;
  EXPECT_DOUBLE_EQ(command.linear.x,0.0);EXPECT_DOUBLE_EQ(command.linear.y,0.0);
  EXPECT_NEAR(command.angular.z,tracker.kp_yaw_*0.4,1e-9);
  EXPECT_TRUE(tracker.goal_position_latched_);
  EXPECT_FALSE(tracker.estimateRouteLookaheadYaw(Eigen::Vector3d(0,0,0.42),yaw));
  EXPECT_DOUBLE_EQ(actual->state_->yaw_tolerance,0.25);
  EXPECT_DOUBLE_EQ(tracker.goal_yaw_tolerance_,0.125);
  const auto set_error=[&](double error) {
    body.pose.orientation.z=std::sin(-error/2);body.pose.orientation.w=std::cos(-error/2);
  };
  for (double error : {0.249,0.20,0.126}) {
    set_error(error);
    EXPECT_NEAR(plugin->computeVelocityCommands(body,{}).twist.angular.z,tracker.kp_yaw_*error,1e-9);
    EXPECT_FALSE(actual->state_->goal_reached);
    EXPECT_FALSE(goal->isGoalReached(body.pose,route.poses.back().pose,{}));
  }
  geometry_msgs::msg::Twist rotating;rotating.angular.z=0.1;
  set_error(0.11);
  EXPECT_EQ(plugin->computeVelocityCommands(body,rotating).twist,geometry_msgs::msg::Twist());
  EXPECT_TRUE(actual->state_->goal_reached);
  EXPECT_FALSE(goal->isGoalReached(body.pose,route.poses.back().pose,{})); // Last measured body still moving.
  plugin->setPlan(route); // Same-goal replans preserve the braking latch too.
  EXPECT_TRUE(actual->state_->goal_reached);
  goal->reset(); // The pinned ControllerServer does this after every setPlan().
  EXPECT_FALSE(actual->state_->goal_reached);
  EXPECT_TRUE(actual->goal_braking_);
  set_error(0.16);
  EXPECT_EQ(plugin->computeVelocityCommands(body,rotating).twist,geometry_msgs::msg::Twist());
  EXPECT_FALSE(goal->isGoalReached(body.pose,route.poses.back().pose,rotating));
  EXPECT_EQ(plugin->computeVelocityCommands(body,{}).twist,geometry_msgs::msg::Twist());
  EXPECT_FALSE(goal->isGoalReached(body.pose,route.poses.back().pose,{}));
  completeStand(body);
  EXPECT_TRUE(goal->isGoalReached(body.pose,route.poses.back().pose,{}));
  set_error(0.26);
  EXPECT_GT(plugin->computeVelocityCommands(body,{}).twist.angular.z,0.0);
  EXPECT_FALSE(actual->state_->goal_reached);
  set_error(0.20);
  EXPECT_GT(plugin->computeVelocityCommands(body,{}).twist.angular.z,0.0);
  set_error(0.11);plugin->computeVelocityCommands(body,{});
  body.pose.position.x+=0.26;
  plugin->computeVelocityCommands(body,{});
  EXPECT_FALSE(actual->state_->goal_reached);
  body.pose.position=route.poses.back().pose.position;
  plugin->computeVelocityCommands(body,{});
  body.pose.position.z+=0.21;
  plugin->computeVelocityCommands(body,{});
  EXPECT_FALSE(actual->state_->goal_reached);
}

TEST_F(PluginTest, RejectsEmptyNonfiniteUnnormalizedAndWrongFramePaths)
{
  auto bad=route; bad.poses.clear(); EXPECT_THROW(plugin->setPlan(bad),nav2_core::PlannerException);
  bad=route; bad.header.frame_id="map"; EXPECT_THROW(plugin->setPlan(bad),nav2_core::PlannerException);
  bad=route; bad.poses.front().pose.position.x=std::numeric_limits<double>::quiet_NaN();
  EXPECT_THROW(plugin->setPlan(bad),nav2_core::PlannerException);
  bad=route; bad.poses.back().pose.orientation.w=2;
  EXPECT_THROW(plugin->setPlan(bad),nav2_core::PlannerException);
  bad=route; bad.poses.front().header.frame_id="other";
  EXPECT_THROW(plugin->setPlan(bad),nav2_core::PlannerException);
  EXPECT_FALSE(actual->has_active_plan_);
}
TEST_F(PluginTest, NoPlanThrowsAndFirstSplineWaitReturnsZero)
{
  EXPECT_THROW(plugin->computeVelocityCommands(pose(),{}),nav2_core::PlannerException);
  plan();
  EXPECT_EQ(plugin->computeVelocityCommands(pose(),{}).twist,geometry_msgs::msg::Twist());
  EXPECT_TRUE(received.empty());
  EXPECT_DOUBLE_EQ(actual->bspline_timeout_s_,5.0);
  EXPECT_TRUE(actual->waiting_for_spline_);
  const auto first_wait=actual->waiting_for_spline_since_;
  plugin->setPlan(route);
  EXPECT_EQ(actual->waiting_for_spline_since_,first_wait);
  actual->waiting_for_spline_since_=parent->now()-rclcpp::Duration::from_seconds(5.1);
  actual->route_sent_at_=actual->waiting_for_spline_since_;
  plugin->setPlan(route);
  EXPECT_EQ(actual->waiting_for_spline_since_,actual->route_sent_at_);
  EXPECT_THROW(plugin->computeVelocityCommands(pose(),{}),nav2_core::PlannerException);
  EXPECT_FALSE(actual->has_active_plan_);
  EXPECT_FALSE(actual->waiting_for_spline_);
  EXPECT_FALSE(actual->terminal_timeout_started_);
  plan();
  actual->waiting_for_spline_=false;
  plugin->setPlan(route);
  EXPECT_TRUE(actual->waiting_for_spline_);
  actual->waiting_for_spline_=false;
  EXPECT_EQ(plugin->computeVelocityCommands(pose(),{}).twist,geometry_msgs::msg::Twist());
  EXPECT_TRUE(actual->waiting_for_spline_);
}
TEST_F(PluginTest, FreshSplineImmediatelyReplacesTrajectoryAndResetsTimeout)
{
  moving();
  auto next=std::make_shared<sm::Bspline>(curve());next->traj_id=2;
  for(auto &p:next->pos_pts)p.x+=1;
  actual->terminal_timeout_started_=true;
  actual->onSpline(next);
  EXPECT_EQ(actual->tracker_->traj_id_,2);
  EXPECT_FALSE(actual->waiting_for_spline_);
  EXPECT_FALSE(actual->terminal_timeout_started_);
  EXPECT_GT(plugin->computeVelocityCommands(pose(),{}).twist.linear.x,0);
}
TEST_F(PluginTest, EmergencySplineClearsAndReturnsZeroThenAcceptsReplacement)
{
  moving();
  auto message=std::make_shared<sm::Bspline>(curve());message->emergency_stop=true;
  actual->waiting_for_spline_since_=parent->now()-rclcpp::Duration::from_seconds(60);
  actual->route_sent_at_=actual->waiting_for_spline_since_;
  actual->tracker_->goal_position_latched_=true;
  actual->terminal_timeout_started_=true;
  actual->onSpline(message);
  EXPECT_TRUE(actual->waiting_for_spline_);
  EXPECT_FALSE(actual->tracker_->goal_position_latched_);
  EXPECT_FALSE(actual->terminal_timeout_started_);
  EXPECT_LT((parent->now()-actual->waiting_for_spline_since_).seconds(),1.0);
  EXPECT_EQ(plugin->computeVelocityCommands(pose(),{}).twist,geometry_msgs::msg::Twist());
  const auto waiting=actual->waiting_for_spline_since_;
  actual->onSpline(message);
  plugin->setPlan(route);
  EXPECT_EQ(actual->waiting_for_spline_since_,waiting);
  actual->waiting_for_spline_since_=parent->now()-rclcpp::Duration::from_seconds(5.1);
  actual->route_sent_at_=actual->waiting_for_spline_since_;
  actual->onSpline(message);
  EXPECT_THROW(plugin->computeVelocityCommands(pose(),{}),nav2_core::PlannerException);
  EXPECT_FALSE(actual->has_active_plan_);
  plan();
  EXPECT_FALSE(actual->tracker_->haveTrajectory());
  EXPECT_TRUE(received.empty());
  message->emergency_stop=false;message->traj_id=2;
  actual->onSpline(message);
  EXPECT_TRUE(actual->tracker_->haveTrajectory());
  EXPECT_FALSE(actual->waiting_for_spline_);
}
TEST_F(PluginTest, MalformedSplinesNeverReachEvaluator)
{
  plan();
  actual->onSpline(nullptr);
  for(int kind=0;kind<6;++kind) {
    auto message=std::make_shared<sm::Bspline>(curve());
    if(kind==0)message->order=2;
    if(kind==1)message->pos_pts.clear();
    if(kind==2)message->knots.pop_back();
    if(kind==3)message->knots[4]=message->knots[1];
    if(kind==4)message->pos_pts.front().x=std::numeric_limits<double>::infinity();
    if(kind==5)message->start_time.nanosec=1000000000u;
    EXPECT_NO_THROW(actual->onSpline(message));
    EXPECT_FALSE(actual->tracker_->haveTrajectory());
  }
  // A valid trajectory producing nonfinite commands fails immediately, even
  // within the initial wait budget; it is not treated as an absent spline.
  actual->onSpline(std::make_shared<sm::Bspline>(curve()));
  actual->tracker_->kp_yaw_=std::numeric_limits<double>::quiet_NaN();
  try {
    plugin->computeVelocityCommands(pose(),{});
    FAIL() << "Invalid sampled command was accepted";
  } catch (const nav2_core::PlannerException &error) {
    EXPECT_STREQ(error.what(),"Native SCAN trajectory sample invalid");
  }
  EXPECT_FALSE(actual->has_active_plan_);
  EXPECT_FALSE(actual->tracker_->haveTrajectory());
}
TEST_F(PluginTest, InvalidPoseAndVelocityThrowForServerToStop)
{
  moving();
  auto bad=pose();bad.header.frame_id="other";
  EXPECT_THROW(plugin->computeVelocityCommands(bad,{}),nav2_core::PlannerException);
  bad=pose();bad.pose.orientation.w=2;
  EXPECT_THROW(plugin->computeVelocityCommands(bad,{}),nav2_core::PlannerException);
  geometry_msgs::msg::Twist velocity;velocity.angular.z=std::numeric_limits<double>::quiet_NaN();
  EXPECT_THROW(plugin->computeVelocityCommands(pose(),velocity),nav2_core::PlannerException);
  EXPECT_TRUE(received.empty());
}
TEST_F(PluginTest, GoalRequiresHeightYawAndMeasuredStoppedVelocity)
{
  moving();
  auto at=route.poses.back();
  at.pose.position.z+=0.3;plugin->computeVelocityCommands(at,{});
  EXPECT_FALSE(goal->isGoalReached(at.pose,route.poses.back().pose,{}));
  at=route.poses.back();at.pose.orientation.z=std::sin(0.4);at.pose.orientation.w=std::cos(0.4);
  plugin->computeVelocityCommands(at,{});
  EXPECT_FALSE(goal->isGoalReached(at.pose,route.poses.back().pose,{}));
  at=route.poses.back();geometry_msgs::msg::Twist velocity;velocity.linear.x=0.1;
  EXPECT_EQ(plugin->computeVelocityCommands(at,velocity).twist,geometry_msgs::msg::Twist());
  EXPECT_FALSE(goal->isGoalReached(at.pose,at.pose,velocity));
  plugin->computeVelocityCommands(at,{});
  EXPECT_FALSE(goal->isGoalReached(at.pose,at.pose,{}));
  completeStand(at);
  EXPECT_TRUE(goal->isGoalReached(at.pose,at.pose,{}));
  velocity.angular.z=0.1;EXPECT_FALSE(goal->isGoalReached(at.pose,at.pose,velocity));
  auto live=at.pose;live.position.x+=0.3;
  EXPECT_FALSE(goal->isGoalReached(live,at.pose,{}));
  live=at.pose;live.position.z+=0.21;
  EXPECT_FALSE(goal->isGoalReached(live,at.pose,{}));
  live=at.pose;live.orientation.z=std::sin(0.26/2);live.orientation.w=std::cos(0.26/2);
  EXPECT_FALSE(goal->isGoalReached(live,at.pose,{}));
  live=at.pose;live.position.x=std::numeric_limits<double>::quiet_NaN();
  EXPECT_FALSE(goal->isGoalReached(live,at.pose,{}));
  live=at.pose;live.orientation.w=2.0;
  EXPECT_FALSE(goal->isGoalReached(live,at.pose,{}));
  goal->reset();EXPECT_FALSE(goal->isGoalReached(at.pose,at.pose,{}));
}
TEST_F(PluginTest, SameGoalRefreshRetainsCurveNewGoalClearsIt)
{
  moving();auto next=route;next.poses.insert(next.poses.begin()+1,pose(2));
  plugin->setPlan(next);EXPECT_TRUE(actual->tracker_->haveTrajectory());
  next.poses.back().pose.position.y+=1;
  plugin->setPlan(next);EXPECT_FALSE(actual->tracker_->haveTrajectory());
  EXPECT_FALSE(actual->tracker_->goal_position_latched_);
  EXPECT_TRUE(actual->waiting_for_spline_);
}
TEST_F(PluginTest, TransientPathIsDeliveredToLateSubscriber)
{
  plan();nav_msgs::msg::Path received_path;
  auto late=io->create_subscription<nav_msgs::msg::Path>("/pct_path",rclcpp::QoS(1).reliable().transient_local(),
    [&](nav_msgs::msg::Path::ConstSharedPtr p){received_path=*p;});
  ASSERT_TRUE(wait([&]{return !received_path.poses.empty();}));
  EXPECT_EQ(received_path,route);
}
TEST_F(PluginTest, StopAndDeactivateClearTrajectoryAndRequireNewPlan)
{
  moving();actual->waiting_for_spline_=true;actual->terminal_timeout_started_=true;
  actual->stop("action_cancelled");
  EXPECT_FALSE(actual->waiting_for_spline_);EXPECT_FALSE(actual->terminal_timeout_started_);
  EXPECT_FALSE(actual->has_active_plan_);EXPECT_FALSE(actual->tracker_->haveTrajectory());
  actual->onSpline(std::make_shared<sm::Bspline>(curve()));
  EXPECT_FALSE(actual->tracker_->haveTrajectory());
  EXPECT_THROW(plugin->computeVelocityCommands(pose(),{}),nav2_core::PlannerException);
  plugin->setPlan(route);actual->onSpline(std::make_shared<sm::Bspline>(curve()));
  actual->waiting_for_spline_=true;actual->terminal_timeout_started_=true;
  plugin->deactivate();
  EXPECT_FALSE(actual->waiting_for_spline_);EXPECT_FALSE(actual->terminal_timeout_started_);
  plugin->activate();
  EXPECT_THROW(plugin->computeVelocityCommands(pose(),{}),nav2_core::PlannerException);
}
TEST_F(PluginTest, NoIndependentTrackingCommandTimer)
{
  moving();EXPECT_EQ(actual->tracker_->cmd_timer_,nullptr);
  EXPECT_EQ(actual->tracker_->raw_cmd_pub_,nullptr);
}

TEST_F(PluginTest, TerminalTimeoutFailsWithoutExecutionFeedback)
{
  plan();auto at=route.poses.back();
  EXPECT_EQ(plugin->computeVelocityCommands(at,{}).twist,geometry_msgs::msg::Twist());
  EXPECT_TRUE(actual->terminalPhase());
  EXPECT_FALSE(goal->isGoalReached(at.pose,at.pose,{}));
  actual->state_->completion.entered_wall_=scan_nav2_controller::TerminalCompletion::Clock::now()-11s;
  try {
    plugin->computeVelocityCommands(at,{});
    FAIL()<<"Missing terminal feedback must time out";
  } catch(const nav2_core::PlannerException &error) {
    EXPECT_STREQ(error.what(),"terminal_settle_timeout");
  }
  actual->stop("nav2_server_stop");EXPECT_FALSE(actual->terminalPhase());
}

TEST_F(PluginTest, SameGoalRefreshRetainsHoldAndNewGoalResetsIt)
{
  plan();auto at=route.poses.back();plugin->computeVelocityCommands(at,{});
  completeStand(at);ASSERT_TRUE(goal->isGoalReached(at.pose,at.pose,{}));
  plugin->setPlan(route);goal->reset();plugin->computeVelocityCommands(at,{});
  EXPECT_TRUE(goal->isGoalReached(at.pose,at.pose,{}));
  route.poses.back().pose.position.x+=1.;plugin->setPlan(route);
  EXPECT_FALSE(actual->terminalPhase());EXPECT_FALSE(goal->isGoalReached(at.pose,at.pose,{}));
}

TEST_F(PluginTest, TypedRosExecutionFeedbackReachesControllerCache)
{
  using Execution=lite3_nav2_interfaces::msg::RobotExecutionState;
  auto publisher=io->create_publisher<Execution>("/quad_0/execution_state",10);
  ASSERT_TRUE(wait([&]{return publisher->get_subscription_count()>0;}));
  plan();plugin->computeVelocityCommands(route.poses.back(),{});
  Execution sample;sample.header.frame_id="base_link";sample.header.stamp=parent->now();
  sample.simulation_time_ns=parent->now().nanoseconds();
  sample.header.stamp=rclcpp::Time(sample.simulation_time_ns);
  sample.state_sequence=1;sample.run_epoch_ns=800;sample.stance_mode=sample.FIXED_STAND;
  sample.navigation_ready=true;sample.policy_owns_joints=false;
  publisher->publish(sample);
  ASSERT_TRUE(wait([&]{return actual->state_->completion.has_sample_;}));
  EXPECT_EQ(actual->state_->completion.last_sequence_,1u);
  EXPECT_FALSE(goal->isGoalReached(route.poses.back().pose,route.poses.back().pose,{}));
}
TEST_F(PluginTest, NativeWorkerLifecycleReceivesDirectPath)
{
  plugin->deactivate();actual->native_worker_enabled_=true;
  parent->declare_parameter("SCAN.native_planner_config",std::string(TEST_NATIVE_CONFIG));
  plugin->activate();
  ASSERT_TRUE(wait([&]{return actual->route_pub_->get_subscription_count()>=2;}));
  const auto names=io->get_node_names();
  EXPECT_NE(std::find(names.begin(),names.end(),"/quad_0/scan_planner_node"),names.end());
  plan();
  plugin->deactivate();
}


TEST_F(PluginTest, IdenticalRefreshUpdatesReferenceWithoutPublishingOrStopping)
{
  moving();
  const auto count = dispatched.size();
  const auto trajectory = actual->tracker_->traj_[0].getControlPoint();
  for (int i=0; i<3; ++i) {
    route.header.stamp=parent->now();
    for (auto &p : route.poses) p.header.stamp=parent->now();
    plugin->setPlan(route);
  }
  EXPECT_FALSE(wait([&] { return dispatched.size()>count; },0.15));
  EXPECT_EQ(actual->tracker_->reference_path_,route);
  EXPECT_TRUE(actual->tracker_->haveTrajectory());
  EXPECT_TRUE(actual->tracker_->traj_[0].getControlPoint().isApprox(trajectory,0.0));
  EXPECT_GT(plugin->computeVelocityCommands(pose(),geometry_msgs::msg::Twist()).twist.linear.x,0);
}

TEST_F(PluginTest, ChangedGeometryAndWaitingRecoveryPublishImmediately)
{
  moving();
  size_t count=dispatched.size();
  route.poses.front().pose.position.y=0.1;
  plugin->setPlan(route);
  ASSERT_TRUE(wait([&] { return dispatched.size()>count; }));
  count=dispatched.size();
  route.poses.front().pose.orientation.z=std::sin(0.1);
  route.poses.front().pose.orientation.w=std::cos(0.1);
  plugin->setPlan(route);
  ASSERT_TRUE(wait([&] { return dispatched.size()>count; }));
  count=dispatched.size();
  auto emergency=std::make_shared<sm::Bspline>(curve()); emergency->emergency_stop=true;
  actual->onSpline(emergency);
  ASSERT_TRUE(actual->waiting_for_spline_);
  plugin->setPlan(route);
  ASSERT_TRUE(wait([&] { return dispatched.size()>count; }));
  EXPECT_EQ(dispatched.back(),route);
}

TEST_F(PluginTest, FreezeAccountingRebasesEveryTrajectoryGeneration)
{
  scan_planner::SCANReplanFSM fsm;
  auto fsm_node=std::make_shared<rclcpp::Node>("freeze_generation_test");
  fsm.node_=fsm_node.get();
  auto clock=fsm.node_->get_clock();
  ASSERT_EQ(rcl_enable_ros_time_override(clock->get_clock_handle()),RCL_RET_OK);
  ASSERT_EQ(rcl_set_ros_time_override(clock->get_clock_handle(),10000000000LL),RCL_RET_OK);
  fsm.planner_manager_=std::make_unique<scan_planner::SCANPlannerManager>();
  auto &info=fsm.planner_manager_->local_data_;
  info.traj_id_=1; info.start_time_=rclcpp::Time(9,0,RCL_ROS_TIME);
  fsm.go2_execution_frozen_=true;
  fsm.last_freeze_update_time_=rclcpp::Time(9,980000000,RCL_ROS_TIME);
  fsm.updateLocalTrajTimeFreeze();
  EXPECT_EQ(info.start_time_,rclcpp::Time(9,0,RCL_ROS_TIME));
  ASSERT_EQ(rcl_set_ros_time_override(clock->get_clock_handle(),10030000000LL),RCL_RET_OK);
  info.traj_id_=2; info.start_time_=clock->now();
  fsm.updateLocalTrajTimeFreeze();
  EXPECT_DOUBLE_EQ((clock->now()-info.start_time_).seconds(),0.0);
  ASSERT_EQ(rcl_set_ros_time_override(clock->get_clock_handle(),10040000000LL),RCL_RET_OK);
  fsm.updateLocalTrajTimeFreeze();
  EXPECT_DOUBLE_EQ((clock->now()-info.start_time_).seconds(),0.0);
  fsm.go2_execution_frozen_=false;
  ASSERT_EQ(rcl_set_ros_time_override(clock->get_clock_handle(),10050000000LL),RCL_RET_OK);
  fsm.updateLocalTrajTimeFreeze();
  EXPECT_NEAR((clock->now()-info.start_time_).seconds(),0.01,1e-9);
}

TEST_F(PluginTest, FreezeClampDoesNotRepairGenuinelyFutureInput)
{
  scan_planner::SCANReplanFSM fsm;
  auto fsm_node=std::make_shared<rclcpp::Node>("freeze_clamp_test");
  fsm.node_=fsm_node.get();
  auto clock=fsm.node_->get_clock();
  ASSERT_EQ(rcl_enable_ros_time_override(clock->get_clock_handle()),RCL_RET_OK);
  ASSERT_EQ(rcl_set_ros_time_override(clock->get_clock_handle(),10000000000LL),RCL_RET_OK);
  fsm.planner_manager_=std::make_unique<scan_planner::SCANPlannerManager>();
  auto &info=fsm.planner_manager_->local_data_;
  info.traj_id_=fsm.last_freeze_traj_id_=1;
  info.start_time_=rclcpp::Time(9,990000000,RCL_ROS_TIME);
  fsm.last_freeze_update_time_=rclcpp::Time(9,970000000,RCL_ROS_TIME);
  fsm.go2_execution_frozen_=true;
  fsm.updateLocalTrajTimeFreeze();
  EXPECT_EQ(info.start_time_,clock->now());
  info.start_time_=rclcpp::Time(10,30000000,RCL_ROS_TIME);
  fsm.updateLocalTrajTimeFreeze();
  EXPECT_LT((clock->now()-info.start_time_).seconds(),0.0);
  Eigen::MatrixXd controls=Eigen::MatrixXd::Zero(3,6);
  scan_planner::UniformBspline spline(controls,3,1.0);
  const auto checked=reactive_stair::checkFullCubicTrajectory(spline,-0.03,0.05,0.1,
    [](const auto&,const auto&,const auto&) { return 0.0; },
    [](const auto&,double) { return false; });
  EXPECT_FALSE(checked.clear());
}

TEST_F(PluginTest, ExpiredSplineAndRepeatedFailureUseMeasuredStart)
{
  scan_planner::SCANReplanFSM fsm;
  auto fsm_node=std::make_shared<rclcpp::Node>("measured_start_test");
  fsm.node_=fsm_node.get();
  auto clock=fsm.node_->get_clock();
  ASSERT_EQ(rcl_enable_ros_time_override(clock->get_clock_handle()),RCL_RET_OK);
  ASSERT_EQ(rcl_set_ros_time_override(clock->get_clock_handle(),10000000000LL),RCL_RET_OK);
  fsm.planner_manager_=std::make_unique<scan_planner::SCANPlannerManager>();
  auto &info=fsm.planner_manager_->local_data_;
  // No spline is installed: sampling it would fail. Both branches must use odometry.
  info.start_time_=rclcpp::Time(9,0,RCL_ROS_TIME); info.duration_=1.0;
  fsm.odom_pos_=Eigen::Vector3d(1,2,3); fsm.odom_vel_=Eigen::Vector3d(0.01,0.02,0.12);
  fsm.replan_fail_count_=0; fsm.setStartStateFromOdomOrCurrentTraj();
  EXPECT_EQ(fsm.start_pt_,fsm.odom_pos_); EXPECT_EQ(fsm.start_vel_,fsm.odom_vel_);
  EXPECT_EQ(fsm.start_acc_,Eigen::Vector3d::Zero());
  info.duration_=2.0; fsm.replan_fail_count_=3;
  fsm.setStartStateFromOdomOrCurrentTraj();
  EXPECT_EQ(fsm.start_vel_,fsm.odom_vel_);
}

TEST_F(PluginTest, CloudJitterBudgetRetainsGeometryAndRejectsStaleOrFuture)
{
  using namespace reactive_stair;
  EXPECT_DOUBLE_EQ(Parameters().obstacle_max_age_s,0.25); // generic default preserved
  Parameters p; p.obstacle_max_age_s=0.35;
  CollisionDecision decision(p);
  TerrainSnapshot terrain; terrain.source_id="terrain"; terrain.frame="world";
  terrain.stamp_s=10.0; terrain.resolution_m=1.0;
  terrain.cells[{0,0}]={{Support::Flat,0.0}};
  ASSERT_TRUE(decision.acceptTerrain(terrain));
  Query q; q.frame="world"; q.stamp_s=10.3; q.x_m=q.y_m=0.1; q.z_m=0.4; q.in_map=true;
  NonTerrainVoxel obstacle; obstacle.source_id="lidar"; obstacle.frame="world";
  obstacle.stamp_s=10.0; obstacle.occupancy=Occupancy::Free;
  for (double age : {0.2748,0.2998,0.35}) {
    q.stamp_s=age; obstacle.stamp_s=terrain.stamp_s=0.0;
    ASSERT_TRUE(decision.acceptTerrain(terrain));
    EXPECT_EQ(decision.decide(q,obstacle),Verdict::Free);
    obstacle.occupancy=Occupancy::Occupied;
    EXPECT_EQ(decision.decide(q,obstacle),Verdict::StaticObstacle);
    obstacle.occupancy=Occupancy::Free;
  }
  q.stamp_s=0.350000001; EXPECT_EQ(decision.decide(q,obstacle),Verdict::StaleInput);
  q.stamp_s=0.1; obstacle.stamp_s=0.100000001;
  EXPECT_EQ(decision.decide(q,obstacle),Verdict::StaleInput);
  obstacle.stamp_s=0; terrain.cells[{0,0}]={{Support::Unsupported,0.0}};
  ASSERT_TRUE(decision.acceptTerrain(terrain));
  EXPECT_EQ(decision.decide(q,obstacle),Verdict::UnsupportedTerrain);
}


TEST_F(PluginTest, EmergencyReplanIgnoresVerticalSteppingButKeepsHoverStop)
{
  rclcpp::NodeOptions options;
  options.arguments({"--ros-args", "--params-file", TEST_NATIVE_CONFIG});
  auto fsm_node=std::make_shared<rclcpp::Node>("scan_planner_node",options);
  scan_planner::SCANReplanFSM fsm;
  fsm.init(fsm_node.get());
  EXPECT_DOUBLE_EQ(fsm_node->get_parameter("grid_map.reactive_cloud_max_age").as_double(),0.35);
  fsm.have_odom_=true; fsm.odom_pos_=Eigen::Vector3d(0,0,0.4);
  fsm.odom_orient_=Eigen::Quaterniond::Identity();
  fsm.flag_escape_emergency_=false; fsm.need_hover_stop_=false;
  fsm.exec_state_=scan_planner::SCANReplanFSM::EMERGENCY_STOP;
  fsm.odom_vel_=Eigen::Vector3d(0.1,0,0.5);
  fsm.execFSMCallback();
  EXPECT_EQ(fsm.exec_state_,scan_planner::SCANReplanFSM::GEN_NEW_TRAJ);
  fsm.exec_state_=scan_planner::SCANReplanFSM::EMERGENCY_STOP;
  fsm.odom_vel_=Eigen::Vector3d(0.16,0,0);
  fsm.execFSMCallback();
  EXPECT_EQ(fsm.exec_state_,scan_planner::SCANReplanFSM::EMERGENCY_STOP);
  fsm.need_hover_stop_=true; fsm.odom_vel_=Eigen::Vector3d(0,0,0.5);
  fsm.execFSMCallback();
  EXPECT_EQ(fsm.exec_state_,scan_planner::SCANReplanFSM::EMERGENCY_STOP);
  fsm.odom_vel_.setZero(); fsm.execFSMCallback();
  EXPECT_EQ(fsm.exec_state_,scan_planner::SCANReplanFSM::WAIT_TARGET);
}
