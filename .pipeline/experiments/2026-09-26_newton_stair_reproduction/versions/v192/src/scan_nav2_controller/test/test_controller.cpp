#include <gtest/gtest.h>
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
    ASSERT_TRUE(wait([&] { return spline->get_subscription_count()>0 && commands->get_publisher_count()>0; }));
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
    ASSERT_TRUE(wait([&] { return !dispatched.empty(); }));
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
    ASSERT_TRUE(wait([&] { return !received.empty() && received.back().linear.x>0; }));
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

TEST_F(PluginTest, DirectPathAndNativeSplinePublishStandardTwist) { moving(); }

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
TEST_F(PluginTest, NoPlanThrowsAndFirstSplineWaitPublishesZero)
{
  EXPECT_THROW(plugin->computeVelocityCommands(pose(),{}),nav2_core::PlannerException);
  plan();
  EXPECT_EQ(plugin->computeVelocityCommands(pose(),{}).twist,geometry_msgs::msg::Twist());
  ASSERT_TRUE(wait([&] {return !received.empty();}));
  EXPECT_EQ(received.back(),geometry_msgs::msg::Twist());
  EXPECT_DOUBLE_EQ(actual->bspline_timeout_s_,5.0);
  actual->route_sent_at_=parent->now()-rclcpp::Duration::from_seconds(5.1);
  EXPECT_THROW(plugin->computeVelocityCommands(pose(),{}),nav2_core::PlannerException);
}
TEST_F(PluginTest, FreshSplineImmediatelyReplacesTrajectoryAndResetsTimeout)
{
  moving();
  auto next=std::make_shared<sm::Bspline>(curve());next->traj_id=2;
  for(auto &p:next->pos_pts)p.x+=1;
  actual->terminal_timeout_started_=true;
  actual->onSpline(next);
  EXPECT_EQ(actual->tracker_->traj_id_,2);
  EXPECT_FALSE(actual->terminal_timeout_started_);
  EXPECT_GT(plugin->computeVelocityCommands(pose(),{}).twist.linear.x,0);
}
TEST_F(PluginTest, EmergencySplineClearsAndPublishesZeroThenAcceptsReplacement)
{
  moving();
  auto message=std::make_shared<sm::Bspline>(curve());message->emergency_stop=true;
  actual->onSpline(message);
  EXPECT_FALSE(actual->tracker_->haveTrajectory());
  ASSERT_TRUE(wait([&]{return !received.empty() && received.back()==geometry_msgs::msg::Twist();}));
  message->emergency_stop=false;message->traj_id=2;
  actual->onSpline(message);
  EXPECT_TRUE(actual->tracker_->haveTrajectory());
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
}
TEST_F(PluginTest, InvalidPoseAndVelocityPublishZero)
{
  moving();
  auto bad=pose();bad.header.frame_id="other";
  EXPECT_THROW(plugin->computeVelocityCommands(bad,{}),nav2_core::PlannerException);
  bad=pose();bad.pose.orientation.w=2;
  EXPECT_THROW(plugin->computeVelocityCommands(bad,{}),nav2_core::PlannerException);
  geometry_msgs::msg::Twist velocity;velocity.angular.z=std::numeric_limits<double>::quiet_NaN();
  EXPECT_THROW(plugin->computeVelocityCommands(pose(),velocity),nav2_core::PlannerException);
  ASSERT_TRUE(wait([&]{return !received.empty() && received.back()==geometry_msgs::msg::Twist();}));
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
  EXPECT_TRUE(goal->isGoalReached(at.pose,at.pose,{}));
  velocity.angular.z=0.1;EXPECT_FALSE(goal->isGoalReached(at.pose,at.pose,velocity));
  goal->reset();EXPECT_FALSE(goal->isGoalReached(at.pose,at.pose,{}));
}
TEST_F(PluginTest, SameGoalRefreshRetainsCurveNewGoalClearsIt)
{
  moving();auto next=route;next.poses.insert(next.poses.begin()+1,pose(2));
  plugin->setPlan(next);EXPECT_TRUE(actual->tracker_->haveTrajectory());
  next.poses.back().pose.position.y+=1;
  plugin->setPlan(next);EXPECT_FALSE(actual->tracker_->haveTrajectory());
  EXPECT_FALSE(actual->tracker_->goal_position_latched_);
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
  moving();actual->stop("action_cancelled");
  EXPECT_FALSE(actual->has_active_plan_);EXPECT_FALSE(actual->tracker_->haveTrajectory());
  actual->onSpline(std::make_shared<sm::Bspline>(curve()));
  EXPECT_FALSE(actual->tracker_->haveTrajectory());
  EXPECT_THROW(plugin->computeVelocityCommands(pose(),{}),nav2_core::PlannerException);
  plugin->setPlan(route);actual->onSpline(std::make_shared<sm::Bspline>(curve()));
  plugin->deactivate();plugin->activate();
  EXPECT_THROW(plugin->computeVelocityCommands(pose(),{}),nav2_core::PlannerException);
}
TEST_F(PluginTest, NoIndependentTrackingCommandTimer)
{
  moving();EXPECT_EQ(actual->tracker_->cmd_timer_,nullptr);
  EXPECT_EQ(actual->tracker_->raw_cmd_pub_,nullptr);
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
