#include <gtest/gtest.h>
#include <plan_manage/scan_replan_fsm.h>
#include <bspline_opt/full_trajectory_collision.h>
#include <plan_env/reactive_collision.h>
#include <scan_nav2_controller/controller.hpp>
#include <scan_nav2_controller/tracking_node.hpp>
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
    parent->declare_parameter("SCAN.bspline_timeout",5.0); // Original test timing; new recovery cases override below.
    parent->declare_parameter("SCAN.trajectory_starvation_timeout",5.0);
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
    ASSERT_TRUE(wait([&] { return actual->motion_->route_pub_->get_subscription_count()>0; }));
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
  geometry_msgs::msg::TwistStamped settledCommand(
      const geometry_msgs::msg::PoseStamped &body,const geometry_msgs::msg::Twist &velocity={})
  {
    geometry_msgs::msg::TwistStamped command;
    const int64_t start=parent->now().nanoseconds();
    for(int tick=0;tick<=40;++tick) {
      for (const auto &clock : {parent->get_clock(),actual->motion_->tracker_->get_clock()}) {
        EXPECT_EQ(rcl_enable_ros_time_override(clock->get_clock_handle()),RCL_RET_OK);
        EXPECT_EQ(rcl_set_ros_time_override(clock->get_clock_handle(),start+tick*33333333LL),RCL_RET_OK);
      }
      command=plugin->computeVelocityCommands(body,velocity);
    }
    return command;
  }
  void moving()
  {
    plan(); injectSpline(std::make_shared<sm::Bspline>(curve()));
    ASSERT_TRUE(wait([&] {
      return settledCommand(pose(),geometry_msgs::msg::Twist()).twist.linear.x>0;
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
      EXPECT_EQ(rcl_enable_ros_time_override(actual->motion_->tracker_->get_clock()->get_clock_handle()),RCL_RET_OK);
      EXPECT_EQ(rcl_set_ros_time_override(actual->motion_->tracker_->get_clock()->get_clock_handle(),stamp),RCL_RET_OK);
      plugin->computeVelocityCommands(at,geometry_msgs::msg::Twist());
      if(tick<100) EXPECT_FALSE(goal->isGoalReached(at.pose,at.pose,geometry_msgs::msg::Twist()));
    }
  }
  void injectSpline(sm::Bspline::ConstSharedPtr message)
  {
    if (!message) return;
    actual->motion_->exchange_->publish(actual->motion_->generation_,*message);
    actual->motion_->update();
  }
  void expiredCornerStub(bool reverse=false)
  {
    for (const auto &clock : {parent->get_clock(),actual->motion_->tracker_->get_clock()}) {
      ASSERT_EQ(rcl_enable_ros_time_override(clock->get_clock_handle()),RCL_RET_OK);
      ASSERT_EQ(rcl_set_ros_time_override(clock->get_clock_handle(),19000000000LL),RCL_RET_OK);
    }
    auto end=pose();end.pose.position.y=4.0;
    route.poses={pose(-1.0),pose(),end};route.header.stamp=parent->now();
    plugin->setPlan(route);
    auto stub=std::make_shared<sm::Bspline>(curve());stub->reverse_motion=reverse;
    for (size_t i=0;i<stub->pos_pts.size();++i)
      stub->pos_pts[i].x=i<3 ? (reverse ? 0.05 : -0.05) : 0.0;
    injectSpline(stub);
    ASSERT_TRUE(actual->motion_->tracker_->haveTrajectory());
    actual->motion_->tracker_->exec_time_=actual->motion_->tracker_->traj_duration_;
    EXPECT_LT(actual->motion_->tracker_->traj_[1].evaluateDeBoorT(actual->motion_->tracker_->exec_time_).head<2>().squaredNorm(),1e-4);
  }
  geometry_msgs::msg::Twist cornerCommand(double yaw)
  {
    auto body=pose();body.pose.orientation.z=std::sin(yaw/2);body.pose.orientation.w=std::cos(yaw/2);
    return settledCommand(body,geometry_msgs::msg::Twist()).twist;
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
  EXPECT_FALSE(actual->motion_->tracker_->route_lookahead_heading_enabled_);
  EXPECT_EQ(cornerCommand(0.0),geometry_msgs::msg::Twist());
  bool used=true;
  EXPECT_DOUBLE_EQ(actual->motion_->tracker_->estimateDesiredYaw(actual->motion_->tracker_->traj_duration_,
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

class StarvationTest : public PluginTest
{
protected:
  int64_t origin;
  void SetUp() override {
    PluginTest::SetUp();
    actual->motion_->trajectory_starvation_timeout_s_=0.75;
    origin=parent->now().nanoseconds();
    at(0);
  }
  void at(double seconds) {
    for (const auto &clock : {parent->get_clock(),actual->motion_->tracker_->get_clock()}) {
      ASSERT_EQ(rcl_enable_ros_time_override(clock->get_clock_handle()),RCL_RET_OK);
      ASSERT_EQ(rcl_set_ros_time_override(clock->get_clock_handle(),origin+int64_t(seconds*1e9)),RCL_RET_OK);
    }
  }
  void expiredCornerStub() {
    PluginTest::expiredCornerStub();
    origin=parent->now().nanoseconds(); // Parent fixture uses a fixed 19 s clock.
  }
};

TEST_F(StarvationTest, ExpiredStoppedCurveMustReachOrdinaryRecovery)
{
  expiredCornerStub();
  EXPECT_NO_THROW(plugin->computeVelocityCommands(pose(),{}));
  ASSERT_TRUE(actual->motion_->tracker_->expired_braking_);
  at(.74); EXPECT_NO_THROW(plugin->computeVelocityCommands(pose(),{}));
  at(.76); EXPECT_THROW(plugin->computeVelocityCommands(pose(),{}),nav2_core::PlannerException);
  EXPECT_FALSE(actual->motion_->hasRoute());
}

TEST_F(StarvationTest, RepeatedEmergencyAndSameRouteDoNotRenewDeadline)
{
  plan();injectSpline(std::make_shared<sm::Bspline>(curve()));
  auto stop=std::make_shared<sm::Bspline>(curve());stop->emergency_stop=true;
  injectSpline(stop);
  at(.5);plugin->setPlan(route);injectSpline(stop);
  EXPECT_NO_THROW(plugin->computeVelocityCommands(pose(),{}));
  at(.76);EXPECT_THROW(plugin->computeVelocityCommands(pose(),{}),nav2_core::PlannerException);
}

TEST_F(StarvationTest, FreshExecutableCurveClearsExpiredWait)
{
  expiredCornerStub();plugin->computeVelocityCommands(pose(),{});
  at(.6);auto fresh=std::make_shared<sm::Bspline>(curve());fresh->traj_id=20;injectSpline(fresh);
  at(.8);EXPECT_NO_THROW(plugin->computeVelocityCommands(pose(),{}));
  EXPECT_TRUE(actual->motion_->hasRoute());
  EXPECT_FALSE(actual->motion_->waiting_for_spline_);
}

TEST_F(StarvationTest, ActiveCurveAndTurningAreNotStarvation)
{
  plan();injectSpline(std::make_shared<sm::Bspline>(curve()));
  auto body=pose();body.pose.orientation.w=0.;body.pose.orientation.z=1.;
  for(double t : {0.,.5,1.,1.5}) {
    at(t);EXPECT_NO_THROW(plugin->computeVelocityCommands(body,{}));
  }
  EXPECT_TRUE(actual->motion_->hasRoute());
  EXPECT_FALSE(actual->motion_->tracker_->expired_braking_);
}

TEST_F(StarvationTest, GoalStandingDoesNotBecomeOrdinaryStarvation)
{
  plan();
  for(double t : {0.,.8,2.}) {
    at(t);EXPECT_NO_THROW(plugin->computeVelocityCommands(route.poses.back(),{}));
  }
  EXPECT_TRUE(actual->terminalPhase());
}

TEST_F(StarvationTest, FinalYawAlignmentClearsOldExpiredCurveWait)
{
  expiredCornerStub();plugin->computeVelocityCommands(pose(),{});
  auto body=route.poses.back();body.pose.orientation.w=0.;body.pose.orientation.z=1.;
  for(double t : {.5,1.,1.5}) {
    at(t);EXPECT_NO_THROW(plugin->computeVelocityCommands(body,{}));
  }
  EXPECT_TRUE(actual->motion_->hasRoute());
  EXPECT_FALSE(actual->motion_->waiting_for_spline_);
}

TEST_F(StarvationTest, NewGoalRestoresOriginalAdmissionBudget)
{
  plan();injectSpline(std::make_shared<sm::Bspline>(curve()));
  at(.7);route.poses.back()=pose(9);plugin->setPlan(route);
  at(1.5);EXPECT_NO_THROW(plugin->computeVelocityCommands(pose(),{}));
  at(5.71);EXPECT_THROW(plugin->computeVelocityCommands(pose(),{}),nav2_core::PlannerException);
}

TEST_F(StarvationTest, ConsecutivePlannerFailuresRequestOnceWhileCurveRemainsExecutable)
{
  std::vector<std_msgs::msg::Header> requests;
  auto sub=io->create_subscription<std_msgs::msg::Header>("/scan/replan_request",10,
    [&](std_msgs::msg::Header::ConstSharedPtr h){requests.push_back(*h);});
  ASSERT_TRUE(wait([&]{return sub->get_publisher_count()>0;}));
  plan();injectSpline(std::make_shared<sm::Bspline>(curve()));
  auto exchange=actual->motion_->exchange_;const auto input=exchange->input();
  exchange->planningResult(input.generation,input.revision,false,origin);
  exchange->planningResult(input.generation,input.revision,false,origin+200000000);
  at(.7);plugin->computeVelocityCommands(pose(),{});rclcpp::spin_some(io);EXPECT_TRUE(requests.empty());
  at(.8);plugin->computeVelocityCommands(pose(),{});
  ASSERT_TRUE(wait([&]{return requests.size()==1;}));
  EXPECT_EQ(requests[0],route.header);
  EXPECT_TRUE(actual->motion_->hasRoute());EXPECT_TRUE(actual->motion_->tracker_->haveTrajectory());
  at(.9);plugin->computeVelocityCommands(pose(),{});rclcpp::spin_some(io);EXPECT_EQ(requests.size(),1u);
  route.header.stamp=parent->now();plugin->setPlan(route);
  EXPECT_FALSE(exchange->planning());EXPECT_GT(exchange->input().revision,input.revision);
  EXPECT_EQ(exchange->input().generation,input.generation);
  EXPECT_TRUE(actual->motion_->tracker_->haveTrajectory());
}

TEST_F(StarvationTest, SuccessfulLocalRoundSuppressesGlobalRequest)
{
  plan();injectSpline(std::make_shared<sm::Bspline>(curve()));
  auto e=actual->motion_->exchange_;const auto i=e->input();
  e->planningResult(i.generation,i.revision,false,origin);
  e->planningResult(i.generation,i.revision,true,origin+500000000);
  at(.8);plugin->computeVelocityCommands(pose(),{});
  EXPECT_FALSE(actual->motion_->replan_requested_);EXPECT_TRUE(actual->motion_->hasRoute());
}

TEST_F(RouteHeadingTest, ExpiredStoppedStubNeverCommandsNonterminalPureYaw)
{
  expiredCornerStub();
  auto *actual=dynamic_cast<scan_nav2_controller::Controller *>(plugin.get());
  ASSERT_NE(actual,nullptr);
  ASSERT_TRUE(actual->motion_->tracker_->route_lookahead_heading_enabled_);
  EXPECT_DOUBLE_EQ(actual->motion_->tracker_->route_lookahead_dist_,0.5);
  const double middle=(actual->motion_->tracker_->goal_yaw_tolerance_+actual->motion_->tracker_->heading_error_threshold_)/2;
  for (double error : {M_PI/2,middle}) {
    const auto command=cornerCommand(M_PI/2-error);
    EXPECT_DOUBLE_EQ(command.linear.x,0.0);EXPECT_DOUBLE_EQ(command.linear.y,0.0);
    EXPECT_DOUBLE_EQ(command.linear.z,0.0);EXPECT_DOUBLE_EQ(command.angular.z,0.0);
    bool used=false;
    EXPECT_NEAR(actual->motion_->tracker_->estimateDesiredYaw(actual->motion_->tracker_->traj_duration_,
      Eigen::Vector3d(0,0,0.42),&used),M_PI/2,1e-9);
    EXPECT_TRUE(used);EXPECT_TRUE(actual->motion_->has_active_plan_);
  }
  EXPECT_EQ(cornerCommand(M_PI/2-actual->motion_->tracker_->goal_yaw_tolerance_/2),geometry_msgs::msg::Twist());
}

TEST_F(RouteHeadingTest, SameGoalRefreshPreservesReferenceButExpiredStubDoesNotTurn)
{
  expiredCornerStub();
  auto *actual=dynamic_cast<scan_nav2_controller::Controller *>(plugin.get());
  ASSERT_NE(actual,nullptr);
  EXPECT_DOUBLE_EQ(cornerCommand(0.0).angular.z,0.0);
  auto &tracker=*actual->motion_->tracker_;
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
  EXPECT_DOUBLE_EQ(cornerCommand(0.0).angular.z,0.0);
}

TEST_F(RouteHeadingTest, ReverseStubKeepsOriginalBodyHeading)
{
  expiredCornerStub(true);
  auto *actual=dynamic_cast<scan_nav2_controller::Controller *>(plugin.get());
  ASSERT_NE(actual,nullptr);ASSERT_TRUE(actual->motion_->tracker_->reverse_motion_);
  EXPECT_EQ(cornerCommand(0.0),geometry_msgs::msg::Twist());
  double yaw=0.0;EXPECT_FALSE(actual->motion_->tracker_->estimateRouteLookaheadYaw(Eigen::Vector3d(0,0,0.42),yaw));
}

TEST_F(RouteHeadingTest, ExpiredUTurnStubRetainsHeadingEstimateWithoutActuation)
{
  expiredCornerStub();
  auto *actual=dynamic_cast<scan_nav2_controller::Controller *>(plugin.get());
  ASSERT_NE(actual,nullptr);
  route.poses={pose(-1.0),pose(),pose(-2.0),route.poses.back()};
  plugin->setPlan(route);
  const auto command=cornerCommand(0.0);
  EXPECT_DOUBLE_EQ(command.linear.x,0.0);EXPECT_DOUBLE_EQ(command.linear.y,0.0);
  EXPECT_DOUBLE_EQ(command.angular.z,0.0);
  double yaw=0.0;ASSERT_TRUE(actual->motion_->tracker_->estimateRouteLookaheadYaw(Eigen::Vector3d(0,0,0.42),yaw));
  EXPECT_NEAR(std::abs(yaw),M_PI,1e-9);
}

TEST_F(RouteHeadingTest, FinalGoalCaptureOwnsYawBeforeAndAfterLatch)
{
  expiredCornerStub();
  auto *actual=dynamic_cast<scan_nav2_controller::Controller *>(plugin.get());
  ASSERT_NE(actual,nullptr);auto &tracker=*actual->motion_->tracker_;
  auto body=pose();body.pose.position=route.poses.back().pose.position;
  body.pose.orientation.z=std::sin(-0.4/2);body.pose.orientation.w=std::cos(-0.4/2);
  auto odom=std::make_shared<nav_msgs::msg::Odometry>();odom->pose.pose=body.pose;
  tracker.odomCallback(odom);
  double yaw=0.0;ASSERT_FALSE(tracker.goal_position_latched_);
  EXPECT_FALSE(tracker.estimateRouteLookaheadYaw(Eigen::Vector3d(0,0,0.42),yaw));
  const auto command=settledCommand(body,geometry_msgs::msg::Twist()).twist;
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
    EXPECT_NEAR(settledCommand(body,{}).twist.angular.z,tracker.kp_yaw_*error,1e-9);
    EXPECT_FALSE(actual->state_->goal_reached);
    EXPECT_FALSE(goal->isGoalReached(body.pose,route.poses.back().pose,{}));
  }
  geometry_msgs::msg::Twist rotating;rotating.angular.z=0.1;
  set_error(0.11);
  EXPECT_EQ(settledCommand(body,rotating).twist,geometry_msgs::msg::Twist());
  EXPECT_TRUE(actual->state_->goal_reached);
  EXPECT_FALSE(goal->isGoalReached(body.pose,route.poses.back().pose,{})); // Last measured body still moving.
  plugin->setPlan(route); // Same-goal replans preserve the braking latch too.
  EXPECT_TRUE(actual->state_->goal_reached);
  goal->reset(); // The pinned ControllerServer does this after every setPlan().
  EXPECT_FALSE(actual->state_->goal_reached);
  EXPECT_TRUE(actual->goal_braking_);
  set_error(0.16);
  EXPECT_EQ(settledCommand(body,rotating).twist,geometry_msgs::msg::Twist());
  EXPECT_FALSE(goal->isGoalReached(body.pose,route.poses.back().pose,rotating));
  EXPECT_EQ(settledCommand(body,{}).twist,geometry_msgs::msg::Twist());
  EXPECT_FALSE(goal->isGoalReached(body.pose,route.poses.back().pose,{}));
  completeStand(body);
  EXPECT_TRUE(goal->isGoalReached(body.pose,route.poses.back().pose,{}));
  set_error(0.26);
  EXPECT_GT(settledCommand(body,{}).twist.angular.z,0.0);
  EXPECT_FALSE(actual->state_->goal_reached);
  set_error(0.20);
  EXPECT_GT(settledCommand(body,{}).twist.angular.z,0.0);
  set_error(0.11);settledCommand(body,{});
  body.pose.position.x+=0.26;
  settledCommand(body,{});
  EXPECT_FALSE(actual->state_->goal_reached);
  body.pose.position=route.poses.back().pose.position;
  settledCommand(body,{});
  body.pose.position.z+=0.21;
  settledCommand(body,{});
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
  EXPECT_FALSE(actual->motion_->has_active_plan_);
}
TEST_F(PluginTest, NoPlanThrowsAndFirstSplineWaitReturnsZero)
{
  EXPECT_THROW(settledCommand(pose(),{}),nav2_core::PlannerException);
  plan();
  EXPECT_EQ(settledCommand(pose(),{}).twist,geometry_msgs::msg::Twist());
  EXPECT_TRUE(received.empty());
  EXPECT_DOUBLE_EQ(actual->motion_->bspline_timeout_s_,5.0);
  EXPECT_TRUE(actual->motion_->waiting_for_spline_);
  const auto first_wait=actual->motion_->waiting_for_spline_since_;
  plugin->setPlan(route);
  EXPECT_EQ(actual->motion_->waiting_for_spline_since_,first_wait);
  actual->motion_->waiting_for_spline_since_=parent->now()-rclcpp::Duration::from_seconds(5.1);
  plugin->setPlan(route);
  EXPECT_THROW(settledCommand(pose(),{}),nav2_core::PlannerException);
  EXPECT_FALSE(actual->motion_->has_active_plan_);
  EXPECT_FALSE(actual->motion_->waiting_for_spline_);

  plan();
  actual->motion_->waiting_for_spline_=false;
  plugin->setPlan(route);
  EXPECT_TRUE(actual->motion_->waiting_for_spline_);
  actual->motion_->waiting_for_spline_=false;
  EXPECT_EQ(settledCommand(pose(),{}).twist,geometry_msgs::msg::Twist());
  EXPECT_TRUE(actual->motion_->waiting_for_spline_);
}
TEST_F(PluginTest, FreshSplineImmediatelyReplacesTrajectoryAndResetsTimeout)
{
  moving();
  auto next=std::make_shared<sm::Bspline>(curve());next->traj_id=2;
  for(auto &p:next->pos_pts)p.x+=1;

  injectSpline(next);
  EXPECT_EQ(actual->motion_->tracker_->traj_id_,2);
  EXPECT_FALSE(actual->motion_->waiting_for_spline_);

  EXPECT_GT(settledCommand(pose(),{}).twist.linear.x,0);
}
TEST_F(PluginTest, EmergencySplineClearsAndReturnsZeroThenAcceptsReplacement)
{
  moving();
  auto message=std::make_shared<sm::Bspline>(curve());message->emergency_stop=true;
  actual->motion_->waiting_for_spline_since_=parent->now()-rclcpp::Duration::from_seconds(60);
  actual->motion_->tracker_->goal_position_latched_=true;

  injectSpline(message);
  EXPECT_TRUE(actual->motion_->waiting_for_spline_);
  EXPECT_FALSE(actual->motion_->tracker_->goal_position_latched_);

  EXPECT_LT((parent->now()-actual->motion_->waiting_for_spline_since_).seconds(),1.0);
  EXPECT_EQ(settledCommand(pose(),{}).twist,geometry_msgs::msg::Twist());
  const auto waiting=actual->motion_->waiting_for_spline_since_;
  injectSpline(message);
  plugin->setPlan(route);
  EXPECT_EQ(actual->motion_->waiting_for_spline_since_,waiting);
  actual->motion_->waiting_for_spline_since_=parent->now()-rclcpp::Duration::from_seconds(5.1);
  injectSpline(message);
  EXPECT_THROW(settledCommand(pose(),{}),nav2_core::PlannerException);
  EXPECT_FALSE(actual->motion_->has_active_plan_);
  plan();
  EXPECT_FALSE(actual->motion_->tracker_->haveTrajectory());
  EXPECT_TRUE(received.empty());
  message->emergency_stop=false;message->traj_id=2;
  injectSpline(message);
  EXPECT_TRUE(actual->motion_->tracker_->haveTrajectory());
  EXPECT_FALSE(actual->motion_->waiting_for_spline_);
}
TEST_F(PluginTest, MalformedSplinesNeverReachEvaluator)
{
  plan();
  injectSpline(nullptr);
  for(int kind=0;kind<6;++kind) {
    auto message=std::make_shared<sm::Bspline>(curve());
    if(kind==0)message->order=2;
    if(kind==1)message->pos_pts.clear();
    if(kind==2)message->knots.pop_back();
    if(kind==3)message->knots[4]=message->knots[1];
    if(kind==4)message->pos_pts.front().x=std::numeric_limits<double>::infinity();
    if(kind==5)message->start_time.nanosec=1000000000u;
    EXPECT_NO_THROW(injectSpline(message));
    EXPECT_FALSE(actual->motion_->tracker_->haveTrajectory());
  }
  // A valid trajectory producing nonfinite commands fails immediately, even
  // within the initial wait budget; it is not treated as an absent spline.
  injectSpline(std::make_shared<sm::Bspline>(curve()));
  actual->motion_->tracker_->kp_yaw_=std::numeric_limits<double>::quiet_NaN();
  try {
    settledCommand(pose(),{});
    FAIL() << "Invalid sampled command was accepted";
  } catch (const nav2_core::PlannerException &error) {
    EXPECT_STREQ(error.what(),"Native SCAN trajectory sample invalid");
  }
  EXPECT_FALSE(actual->motion_->has_active_plan_);
  EXPECT_FALSE(actual->motion_->tracker_->haveTrajectory());
}
TEST_F(PluginTest, InvalidPoseAndVelocityThrowForServerToStop)
{
  moving();
  auto bad=pose();bad.header.frame_id="other";
  EXPECT_THROW(settledCommand(bad,{}),nav2_core::PlannerException);
  bad=pose();bad.pose.orientation.w=2;
  EXPECT_THROW(settledCommand(bad,{}),nav2_core::PlannerException);
  geometry_msgs::msg::Twist velocity;velocity.angular.z=std::numeric_limits<double>::quiet_NaN();
  EXPECT_THROW(settledCommand(pose(),velocity),nav2_core::PlannerException);
  EXPECT_TRUE(received.empty());
}
TEST_F(PluginTest, GoalRequiresHeightYawAndMeasuredStoppedVelocity)
{
  moving();
  auto at=route.poses.back();
  at.pose.position.z+=0.3;settledCommand(at,{});
  EXPECT_FALSE(goal->isGoalReached(at.pose,route.poses.back().pose,{}));
  at=route.poses.back();at.pose.orientation.z=std::sin(0.4);at.pose.orientation.w=std::cos(0.4);
  settledCommand(at,{});
  EXPECT_FALSE(goal->isGoalReached(at.pose,route.poses.back().pose,{}));
  at=route.poses.back();geometry_msgs::msg::Twist velocity;velocity.linear.x=0.1;
  EXPECT_EQ(settledCommand(at,velocity).twist,geometry_msgs::msg::Twist());
  EXPECT_FALSE(goal->isGoalReached(at.pose,at.pose,velocity));
  settledCommand(at,{});
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
  plugin->setPlan(next);EXPECT_TRUE(actual->motion_->tracker_->haveTrajectory());
  next.poses.back().pose.position.y+=1;
  plugin->setPlan(next);EXPECT_FALSE(actual->motion_->tracker_->haveTrajectory());
  EXPECT_FALSE(actual->motion_->tracker_->goal_position_latched_);
  EXPECT_TRUE(actual->motion_->waiting_for_spline_);
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
  moving();actual->motion_->waiting_for_spline_=true;
  actual->stop("action_cancelled");
  EXPECT_FALSE(actual->motion_->waiting_for_spline_);
  EXPECT_FALSE(actual->motion_->has_active_plan_);EXPECT_FALSE(actual->motion_->tracker_->haveTrajectory());
  injectSpline(std::make_shared<sm::Bspline>(curve()));
  EXPECT_FALSE(actual->motion_->tracker_->haveTrajectory());
  EXPECT_THROW(settledCommand(pose(),{}),nav2_core::PlannerException);
  plugin->setPlan(route);injectSpline(std::make_shared<sm::Bspline>(curve()));
  actual->motion_->waiting_for_spline_=true;
  plugin->deactivate();
  EXPECT_FALSE(actual->motion_->waiting_for_spline_);
  plugin->activate();
  EXPECT_THROW(settledCommand(pose(),{}),nav2_core::PlannerException);
}
TEST_F(PluginTest, NoIndependentTrackingCommandTimer)
{
  moving();EXPECT_EQ(actual->motion_->tracker_->cmd_timer_,nullptr);
  EXPECT_EQ(actual->motion_->tracker_->raw_cmd_pub_,nullptr);
}

TEST_F(PluginTest, TerminalTimeoutFailsWithoutExecutionFeedback)
{
  plan();auto at=route.poses.back();
  EXPECT_EQ(settledCommand(at,{}).twist,geometry_msgs::msg::Twist());
  EXPECT_TRUE(actual->terminalPhase());
  EXPECT_FALSE(goal->isGoalReached(at.pose,at.pose,{}));
  actual->state_->completion.entered_wall_=scan_nav2_controller::TerminalCompletion::Clock::now()-11s;
  try {
    settledCommand(at,{});
    FAIL()<<"Missing terminal feedback must time out";
  } catch(const nav2_core::PlannerException &error) {
    EXPECT_STREQ(error.what(),"terminal_settle_timeout");
    EXPECT_NE(dynamic_cast<const scan_nav2_controller::TerminalSettleTimeout *>(&error),nullptr);
  }
  actual->stop("nav2_server_stop");EXPECT_FALSE(actual->terminalPhase());
}

TEST_F(PluginTest, SameGoalRefreshRetainsHoldAndNewGoalResetsIt)
{
  plan();auto at=route.poses.back();settledCommand(at,{});
  completeStand(at);ASSERT_TRUE(goal->isGoalReached(at.pose,at.pose,{}));
  plugin->setPlan(route);goal->reset();
  // Refresh is immediate; advancing a simulated ramp here would intentionally
  // expire the unchanged 250 ms physical-state lease before this assertion.
  plugin->computeVelocityCommands(at,{});
  EXPECT_TRUE(goal->isGoalReached(at.pose,at.pose,{}));
  route.poses.back().pose.position.x+=1.;plugin->setPlan(route);
  EXPECT_FALSE(actual->terminalPhase());EXPECT_FALSE(goal->isGoalReached(at.pose,at.pose,{}));
}

TEST_F(PluginTest, TypedRosExecutionFeedbackReachesControllerCache)
{
  using Execution=lite3_nav2_interfaces::msg::RobotExecutionState;
  auto publisher=io->create_publisher<Execution>("/quad_0/execution_state",10);
  ASSERT_TRUE(wait([&]{return publisher->get_subscription_count()>0;}));
  plan();settledCommand(route.poses.back(),{});
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
  plugin->deactivate();actual->motion_->native_worker_enabled_=true;
  parent->declare_parameter("SCAN.native_planner_config",std::string(TEST_NATIVE_CONFIG));
  for (int cycle=0;cycle<3;++cycle) {
  plugin->activate();
  ASSERT_TRUE(wait([&]{return actual->motion_->route_pub_->get_subscription_count()==1;}));
  EXPECT_EQ(io->count_publishers("/nav2_scan/terrain_slice"),0u);
  const auto names=io->get_node_names();
  EXPECT_NE(std::find(names.begin(),names.end(),"/quad_0/scan_planner_node"),names.end());
  plan();
  const auto revision=actual->motion_->exchange_->input().revision;
  ASSERT_TRUE(wait([&]{return actual->motion_->exchange_->applied_revision.load()==revision;}));
  EXPECT_EQ(spline->get_subscription_count(),0u);
  plugin->deactivate();
  }
}


TEST_F(PluginTest, ObservationTopicsCannotInjectControlState)
{
  plan();
  auto fake_route=io->create_publisher<nav_msgs::msg::Path>("/pct_path",rclcpp::QoS(1).reliable().transient_local());
  auto fake_freeze=io->create_publisher<std_msgs::msg::Bool>("/quad_0/planning/go2_execution_frozen",10);
  auto foreign=route;foreign.poses.back().pose.position.x=100;
  const auto revision=actual->motion_->exchange_->input().revision;
  fake_route->publish(foreign);spline->publish(curve());
  std_msgs::msg::Bool freeze;freeze.data=true;fake_freeze->publish(freeze);
  EXPECT_FALSE(wait([&]{return actual->motion_->tracker_->haveTrajectory();},0.1));
  EXPECT_EQ(spline->get_subscription_count(),0u);
  EXPECT_EQ(fake_freeze->get_subscription_count(),0u);
  EXPECT_EQ(actual->motion_->exchange_->input().revision,revision);
  EXPECT_EQ(actual->motion_->tracker_->reference_path_,route);
  EXPECT_EQ(settledCommand(pose(),{}).twist,geometry_msgs::msg::Twist());
  injectSpline(std::make_shared<sm::Bspline>(curve()));
  EXPECT_GT(settledCommand(pose(),{}).twist.linear.x,0);
}

TEST_F(PluginTest, CancellationAndNewGoalRejectLateNativeSpline)
{
  moving();
  const auto old_generation=actual->motion_->generation_;
  actual->stop("test_cancel");
  EXPECT_FALSE(actual->motion_->exchange_->publish(old_generation,curve()));
  route.poses.back().pose.position.x+=2;plugin->setPlan(route);
  EXPECT_FALSE(actual->motion_->exchange_->publish(old_generation,curve()));
  EXPECT_EQ(settledCommand(pose(),{}).twist,geometry_msgs::msg::Twist());
  EXPECT_FALSE(actual->motion_->tracker_->haveTrajectory());
  injectSpline(std::make_shared<sm::Bspline>(curve()));
  EXPECT_GT(settledCommand(pose(),{}).twist.linear.x,0);
}

TEST_F(PluginTest, NativeDirectInterfaceFeedsTrackerAndKeepsObservations)
{
  plan();
  rclcpp::NodeOptions options;
  options.arguments({"--ros-args","--params-file",TEST_NATIVE_CONFIG});
  auto node=std::make_shared<rclcpp::Node>("scan_planner_node",options);
  scan_planner::SCANReplanFSM fsm;
  int boundaries=0;
  const auto exchange=actual->motion_->exchange_;
  const auto generation=actual->motion_->generation_;
  scan_planner::SCANReplanFSM::DirectIO direct;
  direct.before_work=[&]{++boundaries;};
  direct.spline=[&](const sm::Bspline &message){EXPECT_TRUE(exchange->publish(generation,message));};
  fsm.init(node.get(),nullptr,direct);
  EXPECT_EQ(fsm.path_sub_,nullptr);EXPECT_EQ(fsm.go2_execution_frozen_sub_,nullptr);
  fsm.setReferencePath(std::make_shared<nav_msgs::msg::Path>(route));
  ASSERT_NE(fsm.deferred_path_,nullptr); // No sensor/odom fixture: pending, not admitted.
  fsm.execFSMCallback();fsm.checkCollisionCallback();EXPECT_EQ(boundaries,2);
  std::vector<sm::Bspline> observed;
  auto observer=io->create_subscription<sm::Bspline>(fsm.bspline_pub_->get_topic_name(),10,
    [&](sm::Bspline::ConstSharedPtr message){observed.push_back(*message);});
  ASSERT_TRUE(wait([&]{return fsm.bspline_pub_->get_subscription_count()>0;}));
  auto completed=curve();completed.traj_id=42;
  fsm.publishSpline(completed);actual->motion_->update();
  ASSERT_TRUE(wait([&]{return !observed.empty();}));
  EXPECT_EQ(observed.back(),completed);EXPECT_TRUE(actual->motion_->tracker_->haveTrajectory());
  EXPECT_EQ(actual->motion_->tracker_->traj_id_,42);
  EXPECT_GT(settledCommand(pose(),{}).twist.linear.x,0);
  auto &native=fsm.planner_manager_->local_data_;
  native.traj_id_=42;
  fsm.setExecutionFeedback(true,41);EXPECT_FALSE(fsm.go2_execution_frozen_);
  fsm.setExecutionFeedback(true,42);EXPECT_TRUE(fsm.go2_execution_frozen_);
  native.traj_id_=43;
  fsm.setExecutionFeedback(true,42);EXPECT_FALSE(fsm.go2_execution_frozen_);
  fsm.cancelReference();
  EXPECT_EQ(fsm.deferred_path_,nullptr);EXPECT_FALSE(fsm.have_target_);
  EXPECT_FALSE(fsm.have_requested_goal_pose_);EXPECT_DOUBLE_EQ(native.duration_,0);
  EXPECT_FALSE(fsm.go2_execution_frozen_);
  // Emergency uses the same direct output boundary, then clears the tracker.
  completed.emergency_stop=true;fsm.publishSpline(completed);actual->motion_->update();
  EXPECT_FALSE(actual->motion_->tracker_->haveTrajectory());
  EXPECT_EQ(settledCommand(pose(),{}).twist,geometry_msgs::msg::Twist());
}

TEST_F(PluginTest, IdenticalRefreshUpdatesReferenceWithoutPublishingOrStopping)
{
  moving();
  const auto count = dispatched.size();
  const auto trajectory = actual->motion_->tracker_->traj_[0].getControlPoint();
  for (int i=0; i<3; ++i) {
    route.header.stamp=parent->now();
    for (auto &p : route.poses) p.header.stamp=parent->now();
    plugin->setPlan(route);
  }
  EXPECT_FALSE(wait([&] { return dispatched.size()>count; },0.15));
  EXPECT_EQ(actual->motion_->tracker_->reference_path_,route);
  EXPECT_TRUE(actual->motion_->tracker_->haveTrajectory());
  EXPECT_TRUE(actual->motion_->tracker_->traj_[0].getControlPoint().isApprox(trajectory,0.0));
  EXPECT_GT(settledCommand(pose(),geometry_msgs::msg::Twist()).twist.linear.x,0);
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
  injectSpline(emergency);
  ASSERT_TRUE(actual->motion_->waiting_for_spline_);
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

TEST_F(PluginTest, OuterTerminalBrakeUsesSameRampAndStillRequiresPhysicalHold)
{
  moving();auto previous=actual->motion_->tracker_->sampled_command_;
  ASSERT_GT(previous.linear.x,.5);
  const auto at=route.poses.back();
  int64_t time=parent->now().nanoseconds();
  for(int tick=0;tick<60;++tick) {
    time+=20000000LL;
    for(const auto &clock : {parent->get_clock(),actual->motion_->tracker_->get_clock()}) {
      EXPECT_EQ(rcl_enable_ros_time_override(clock->get_clock_handle()),RCL_RET_OK);
      EXPECT_EQ(rcl_set_ros_time_override(clock->get_clock_handle(),time),RCL_RET_OK);
    }
    const auto command=plugin->computeVelocityCommands(at,{}).twist;
    EXPECT_LE(std::abs(command.linear.x-previous.linear.x),.04+1e-9);
    if(tick==0) EXPECT_GT(command.linear.x,0.);
    EXPECT_FALSE(goal->isGoalReached(at.pose,at.pose,{}));
    previous=command;
  }
  EXPECT_EQ(previous,geometry_msgs::msg::Twist());
  EXPECT_TRUE(actual->terminalPhase());
  EXPECT_TRUE(actual->motion_->exchange_->input().feedback.frozen);
  completeStand(at);EXPECT_TRUE(goal->isGoalReached(at.pose,at.pose,{}));
}

TEST_F(PluginTest, SameGoalRefreshKeepsCompletedResultUntilControllerConsumesIt)
{
  moving();const auto generation=actual->motion_->generation_;
  auto result=curve();result.traj_id=42;
  ASSERT_TRUE(actual->motion_->exchange_->publish(generation,result));
  auto refreshed=route;refreshed.poses.insert(refreshed.poses.begin()+1,pose(2.));
  plugin->setPlan(refreshed);
  EXPECT_EQ(actual->motion_->generation_,generation);
  actual->motion_->update();EXPECT_EQ(actual->motion_->tracker_->traj_id_,42);
  EXPECT_TRUE(actual->motion_->hasRoute());
}

TEST_F(RouteHeadingTest, AlignedOffCenterCaptureKeepsPositionCorrection)
{
  expiredCornerStub();
  auto body=pose();body.pose=route.poses.back().pose;body.pose.position.x-=.1;
  const auto cmd=settledCommand(body,{}).twist;
  EXPECT_GT(std::hypot(cmd.linear.x,cmd.linear.y),.03);
  EXPECT_FALSE(actual->state_->goal_reached);EXPECT_FALSE(actual->terminalPhase());
  body.pose=route.poses.back().pose;
  EXPECT_EQ(settledCommand(body,{}).twist,geometry_msgs::msg::Twist());
  EXPECT_TRUE(actual->state_->goal_reached);
}

TEST_F(RouteHeadingTest, GaitSwayOffsetsDoNotBlockTerminalPd) {
  for(double offset:{.024,.05,.10}) {
    expiredCornerStub();auto body=pose();body.pose=route.poses.back().pose;
    body.pose.position.x-=offset;
    EXPECT_TRUE(actual->withinGoalPosition(body.pose));
    EXPECT_EQ(settledCommand(body,{}).twist,geometry_msgs::msg::Twist());
    EXPECT_TRUE(actual->terminalPhase());
    completeStand(body);EXPECT_TRUE(goal->isGoalReached(body.pose,body.pose,{}));
  }
}

TEST_F(PluginTest, AlignedButOffCenterGoalCannotBypassTrackerCorrection) {
  moving();
  auto body=pose(7.93);
  const auto command=settledCommand(body).twist;
  EXPECT_GT(command.linear.x,.03);
  EXPECT_FALSE(actual->goal_braking_);
  EXPECT_FALSE(actual->state_->goal_reached);
  EXPECT_FALSE(goal->isGoalReached(body.pose,route.poses.back().pose,{}));
  body.pose.position.x=7.96;
  EXPECT_EQ(settledCommand(body).twist,geometry_msgs::msg::Twist());
  EXPECT_TRUE(actual->goal_braking_);
  body.pose.position.x=7.91;
  EXPECT_EQ(settledCommand(body).twist,geometry_msgs::msg::Twist());
  completeStand(body);
  EXPECT_TRUE(goal->isGoalReached(body.pose,route.poses.back().pose,{}));
}

TEST_F(PluginTest, EmergencyCannotTurnMissingTrajectoryIntoGoalArrival) {
  moving();
  auto emergency=std::make_shared<sm::Bspline>(curve());emergency->emergency_stop=true;
  injectSpline(emergency);
  EXPECT_EQ(settledCommand(route.poses.back()).twist,geometry_msgs::msg::Twist());
  EXPECT_FALSE(actual->terminalPhase());
}
