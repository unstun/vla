#include <gtest/gtest.h>
#include <scan_nav2_controller/controller.hpp>
#include <pluginlib/class_loader.hpp>
#include <nav2_core/exceptions.hpp>
#include <chrono>
#include <functional>
#include <limits>
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
    if (routeLookaheadEnabled())
      parent->declare_parameter("SCAN.route_lookahead_heading_enabled",true);
    io=std::make_shared<rclcpp::Node>("test_scan_inputs");
    controller_loader=std::make_unique<pluginlib::ClassLoader<nav2_core::Controller>>("nav2_core","nav2_core::Controller");
    goal_loader=std::make_unique<pluginlib::ClassLoader<nav2_core::GoalChecker>>("nav2_core","nav2_core::GoalChecker");
    goal=goal_loader->createSharedInstance("scan_nav2_controller/GoalChecker");
    goal->initialize(parent,"goal_checker"); // Foxy initializes this before controllers.
    plugin=controller_loader->createSharedInstance("scan_nav2_controller/Controller");
    plugin->configure(parent,"SCAN",nullptr,nullptr);
    output=dynamic_cast<scan_nav2_controller::CommandOutput *>(plugin.get());
    ASSERT_NE(output,nullptr);
    output->bindOutputOwner();
    plugin->activate();
    binding=io->create_publisher<sm::P2BRoute>("/nav2_scan/route_binding",10);
    spline=io->create_publisher<sm::Bspline>("/quad_0/planning/bspline",10);
    safety=io->create_publisher<sm::P2BExecutionSafety>("/quad_0/planning/execution_safety",10);
    cancel=io->create_publisher<sm::P2BCancel>("/p2b/scan_cancel",10);
    stopped=io->create_publisher<sm::P2BStopEvidence>("/nav2_scan/stop_evidence",10);
    commands=io->create_subscription<sm::P2BStampedTwist>("/quad_0/raw_scan_cmd_vel",20,
      [this](sm::P2BStampedTwist::ConstSharedPtr msg) { received.push_back(*msg); });
    routes=io->create_subscription<sm::P2BRoute>("/p2b/route",10,
      [this](sm::P2BRoute::ConstSharedPtr msg) { dispatched.push_back(*msg); });
    ASSERT_TRUE(wait([&] { return binding->get_subscription_count()>0 && spline->get_subscription_count()>0 &&
      safety->get_subscription_count()>0 && stopped->get_subscription_count()>0; }));
    route.run_id="test"; route.epoch=1; route.request_id="request"; route.goal_id="goal";
    route.route_id="route"; route.command_id="command"; route.generation=1;
    route.map_epoch="map"; route.map_revision=1; route.has_goal_pose=true;
    route.goal_pose.position.x=8; route.goal_pose.position.z=0.42; route.goal_pose.orientation.w=1;
    route.path.header.frame_id="world"; route.path.header.stamp=parent->now();
    route.path.poses={pose(0),pose(7.5)};
  }
  void TearDown() override
  {
    if (plugin) { plugin->deactivate(); plugin->cleanup(); } plugin.reset(); goal.reset();
    output=nullptr; controller_loader.reset(); goal_loader.reset(); io.reset(); parent.reset();
  }
  bool wait(const std::function<bool()> &predicate,double seconds=2.0)
  {
    const auto end=std::chrono::steady_clock::now()+std::chrono::duration<double>(seconds);
    while(std::chrono::steady_clock::now()<end) {
      rclcpp::spin_some(io);
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
  template<class T> void identity(T &m)
  {
    m.run_id=route.run_id; m.epoch=route.epoch; m.request_id=route.request_id; m.goal_id=route.goal_id;
    m.route_id=route.route_id; m.command_id=route.command_id; m.generation=route.generation;
    m.map_epoch=route.map_epoch; m.map_revision=route.map_revision;
  }
  void plan()
  {
    route.path.header.stamp=parent->now(); binding->publish(route);
    ASSERT_TRUE(wait([&] { try { plugin->setPlan(route.path); return true; } catch(const nav2_core::PlannerException &) { return false; } }));
    ASSERT_TRUE(wait([&] { return !dispatched.empty(); }));
    EXPECT_EQ(dispatched.back(),route);
  }
  sm::Bspline curve()
  {
    sm::Bspline m; identity(m); m.order=3; m.traj_id=1; m.start_time=parent->now();
    for(int i=0;i<6;++i) { geometry_msgs::msg::Point p; p.x=0.4*i; p.z=0.42; m.pos_pts.push_back(p); }
    for(int i=-3;i<7;++i) m.knots.push_back(i);
    return m;
  }
  void sendSafety(bool clear=true,double age=0.0)
  {
    sm::P2BExecutionSafety m; identity(m.binding); m.binding.consumer="native_safety";
    m.binding.traj_id=1; m.clear=clear; m.stamp=parent->now();
    m.observation_stamp_s=parent->now().seconds()-age; m.local_map_revision=1;
    safety->publish(m);
  }
  void moving()
  {
    plan(); auto m=curve(); spline->publish(m);
    ASSERT_TRUE(wait([&] {
      sendSafety();
      auto v=plugin->computeVelocityCommands(pose(),geometry_msgs::msg::Twist());
      if(v.twist.linear.x>0) { output->publishCommand(v); return true; }
      return false;
    }));
    ASSERT_TRUE(wait([&] { return !received.empty() && received.back().twist.linear.x>0; }));
    EXPECT_EQ(received.back().command_id,route.command_id);
    EXPECT_EQ(received.back().map_revision,route.map_revision);
    EXPECT_EQ(received.back().traj_id,1);
  }
  void proof(bool measured=true)
  {
    sm::P2BStopEvidence m; identity(m.admission); m.stamp=parent->now();
    m.admission.consumer="controller"; m.admission.status="stopped";
    m.admission.hold_confirmed=true; m.admission.measured_stillness_confirmed=measured;
    stopped->publish(m);
    wait([] { return false; },0.03);
  }
  void expiredCornerStub(bool reverse=false)
  {
    auto *actual=dynamic_cast<scan_nav2_controller::Controller *>(plugin.get());
    ASSERT_NE(actual,nullptr);
    for (const auto &clock : {parent->get_clock(),actual->tracker_->get_clock()}) {
      ASSERT_EQ(rcl_enable_ros_time_override(clock->get_clock_handle()),RCL_RET_OK);
      ASSERT_EQ(rcl_set_ros_time_override(clock->get_clock_handle(),19000000000LL),RCL_RET_OK);
    }
    route.goal_pose=pose().pose;route.goal_pose.position.y=4.0;
    auto end=pose();end.pose.position.y=4.0;
    route.path.poses={pose(-1.0),pose(),end};route.path.header.stamp=parent->now();
    actual->onBinding(std::make_shared<sm::P2BRoute>(route));
    plugin->setPlan(route.path);
    auto stub=std::make_shared<sm::Bspline>(curve());stub->reverse_motion=reverse;
    for (size_t i=0;i<stub->pos_pts.size();++i)
      stub->pos_pts[i].x=i<3 ? (reverse ? 0.05 : -0.05) : 0.0;
    actual->onSpline(stub);
    auto clear=std::make_shared<sm::P2BExecutionSafety>();identity(clear->binding);
    clear->binding.consumer="native_safety";clear->binding.traj_id=stub->traj_id;
    clear->clear=true;clear->stamp=parent->now();clear->observation_stamp_s=parent->now().seconds();
    clear->local_map_revision=1;actual->onSafety(clear);
    ASSERT_TRUE(actual->tracker_->receive_traj_);
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
  scan_nav2_controller::CommandOutput *output{nullptr};
  rclcpp::Publisher<sm::P2BRoute>::SharedPtr binding;
  rclcpp::Publisher<sm::Bspline>::SharedPtr spline;
  rclcpp::Publisher<sm::P2BExecutionSafety>::SharedPtr safety;
  rclcpp::Publisher<sm::P2BCancel>::SharedPtr cancel;
  rclcpp::Publisher<sm::P2BStopEvidence>::SharedPtr stopped;
  rclcpp::Subscription<sm::P2BStampedTwist>::SharedPtr commands;
  rclcpp::Subscription<sm::P2BRoute>::SharedPtr routes;
  sm::P2BRoute route;
  std::vector<sm::P2BStampedTwist> received;
  std::vector<sm::P2BRoute> dispatched;
};

TEST_F(PluginTest, RequiresExactRouteBinding)
{
  EXPECT_THROW(plugin->setPlan(route.path),nav2_core::PlannerException);
  binding->publish(route); wait([] { return false; },0.03);
  auto changed=route.path; changed.poses.back().pose.position.z+=0.01;
  EXPECT_THROW(plugin->setPlan(changed),nav2_core::PlannerException);
}
TEST_F(PluginTest, RealPluginTracksNativeSplineAndTagsOutput) { moving(); }

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
    EXPECT_TRUE(used);EXPECT_FALSE(actual->state_->stopping);
  }
  EXPECT_EQ(cornerCommand(M_PI/2-actual->tracker_->goal_yaw_tolerance_/2),geometry_msgs::msg::Twist());
}

TEST_F(RouteHeadingTest, SameOwnerRefreshChangesHeadingAndPreservesGoalLatch)
{
  expiredCornerStub();
  auto *actual=dynamic_cast<scan_nav2_controller::Controller *>(plugin.get());
  ASSERT_NE(actual,nullptr);
  EXPECT_GT(cornerCommand(0.0).angular.z,0.0);
  auto &tracker=*actual->tracker_;
  const Eigen::Vector3d original_goal=tracker.goal_pos_;
  const double original_yaw=tracker.goal_yaw_;
  tracker.goal_xy_reached_=true;
  auto turn=pose();turn.pose.position.y=-2.0;
  route.path.poses={pose(-1.0),pose(),turn,route.path.poses.back()};
  actual->onBinding(std::make_shared<sm::P2BRoute>(route));plugin->setPlan(route.path);
  EXPECT_EQ(tracker.goal_route_->path,route.path);
  EXPECT_TRUE(tracker.goal_xy_reached_);
  EXPECT_DOUBLE_EQ((tracker.goal_pos_-original_goal).norm(),0.0);
  EXPECT_DOUBLE_EQ(tracker.goal_yaw_,original_yaw);
  double yaw=0.0;EXPECT_FALSE(tracker.estimateRouteLookaheadYaw(Eigen::Vector3d(0,0,0.42),yaw));
  tracker.goal_xy_reached_=false;
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
  route.path.poses={pose(-1.0),pose(),pose(-2.0),route.path.poses.back()};
  actual->onBinding(std::make_shared<sm::P2BRoute>(route));plugin->setPlan(route.path);
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
  auto body=pose();body.pose.position=route.goal_pose.position;
  body.pose.orientation.z=std::sin(-0.4/2);body.pose.orientation.w=std::cos(-0.4/2);
  auto odom=std::make_shared<nav_msgs::msg::Odometry>();odom->pose.pose=body.pose;
  tracker.odomCallback(odom);
  double yaw=0.0;ASSERT_FALSE(tracker.goal_xy_reached_);
  EXPECT_FALSE(tracker.estimateRouteLookaheadYaw(Eigen::Vector3d(0,0,0.42),yaw));
  const auto command=plugin->computeVelocityCommands(body,geometry_msgs::msg::Twist()).twist;
  EXPECT_DOUBLE_EQ(command.linear.x,0.0);EXPECT_DOUBLE_EQ(command.linear.y,0.0);
  EXPECT_NEAR(command.angular.z,tracker.kp_yaw_*0.4,1e-9);
  EXPECT_TRUE(tracker.goal_xy_reached_);
  EXPECT_FALSE(tracker.estimateRouteLookaheadYaw(Eigen::Vector3d(0,0,0.42),yaw));
}
TEST_F(PluginTest, UnvalidatedReplacementPreservesStillFreshExecutingCurve)
{
  moving();
  auto *actual=dynamic_cast<scan_nav2_controller::Controller *>(plugin.get());ASSERT_NE(actual,nullptr);
  auto next=std::make_shared<sm::Bspline>(curve());next->traj_id=2;
  actual->onSpline(next);
  auto command=plugin->computeVelocityCommands(pose(),geometry_msgs::msg::Twist());
  EXPECT_GT(command.twist.linear.x,0.0);output->publishCommand(command);
  ASSERT_TRUE(wait([&] {return !received.empty();}));EXPECT_EQ(received.back().traj_id,1);
  auto proof=std::make_shared<sm::P2BExecutionSafety>();identity(proof->binding);
  proof->binding.traj_id=2;proof->binding.consumer="native_safety";proof->clear=true;
  proof->stamp=parent->now();proof->observation_stamp_s=parent->now().seconds();proof->local_map_revision=1;
  actual->onSafety(proof);
  auto fresh=plugin->computeVelocityCommands(pose(),geometry_msgs::msg::Twist());
  EXPECT_GT(fresh.twist.linear.x,0.0);output->publishCommand(fresh);
  ASSERT_TRUE(wait([&] {return received.back().traj_id==2;}));
}
TEST_F(PluginTest, ReplacementBetweenComputeAndPublishDropsOldCommandWithoutCancelling)
{
  std::vector<sm::P2BAdmission> admissions;
  auto ack=io->create_subscription<sm::P2BAdmission>("/p2b/scan_admission",10,
    [&](sm::P2BAdmission::ConstSharedPtr m) { admissions.push_back(*m); });
  moving();
  auto old=plugin->computeVelocityCommands(pose(),geometry_msgs::msg::Twist());
  ASSERT_GT(old.twist.linear.x,0.0);
  auto replacement=curve();replacement.traj_id=2;spline->publish(replacement);
  sm::P2BExecutionSafety ready;identity(ready.binding);ready.binding.traj_id=2;
  ready.binding.consumer="native_safety";ready.clear=true;ready.local_map_revision=1;
  ready.stamp=parent->now();ready.observation_stamp_s=parent->now().seconds();safety->publish(ready);
  ASSERT_TRUE(wait([&] {return std::any_of(admissions.begin(),admissions.end(),
    [](const auto &a) {return a.traj_id==2 && a.consumer=="controller" && a.status=="accepted";});}));
  received.clear();output->publishCommand(old);
  ASSERT_TRUE(wait([&] {return !received.empty();}));
  EXPECT_EQ(received.back().twist,geometry_msgs::msg::Twist());
  EXPECT_EQ(received.back().traj_id,2);
  sm::P2BExecutionSafety proof;identity(proof.binding);proof.binding.traj_id=2;
  proof.binding.consumer="native_safety";proof.clear=true;proof.local_map_revision=1;
  ASSERT_TRUE(wait([&] {
    proof.stamp=parent->now();proof.observation_stamp_s=parent->now().seconds();safety->publish(proof);
    auto next=plugin->computeVelocityCommands(pose(),geometry_msgs::msg::Twist());
    if(next.twist.linear.x>0) {output->publishCommand(next);return true;}return false;
  },0.08));
  ASSERT_TRUE(wait([&] {return received.back().traj_id==2 && received.back().twist.linear.x>0;}));
}
TEST_F(PluginTest, RepeatedAdmittedPathIsIdempotentButChangedPathNeedsBinding)
{
  plan();
  EXPECT_NO_THROW(plugin->setPlan(route.path));
  auto changed=route.path;
  changed.poses.back().pose.position.x+=0.1;
  EXPECT_THROW(plugin->setPlan(changed),nav2_core::PlannerException);
  output->stop("test_cancel");
  EXPECT_THROW(plugin->setPlan(route.path),nav2_core::PlannerException);
}
TEST_F(PluginTest, CancelBeforeSetPlanRevokesPendingBindingAndAcknowledgesHold)
{
  std::vector<sm::P2BAdmission> replies;
  auto sub=io->create_subscription<sm::P2BAdmission>("/p2b/scan_admission",10,
    [&](sm::P2BAdmission::ConstSharedPtr m) { replies.push_back(*m); });
  std::vector<sm::P2BRoute> ready;
  auto ready_sub=io->create_subscription<sm::P2BRoute>("/nav2_scan/binding_ready",10,
    [&](sm::P2BRoute::ConstSharedPtr m) { ready.push_back(*m); });
  binding->publish(route);
  ASSERT_TRUE(wait([&] { return !ready.empty(); }));
  sm::P2BCancel request; identity(request); request.reason="before_execution";
  cancel->publish(request);
  ASSERT_TRUE(wait([&] { return !replies.empty(); }));
  EXPECT_TRUE(replies.back().hold_confirmed);
  EXPECT_FALSE(replies.back().measured_stillness_confirmed);
  EXPECT_THROW(plugin->setPlan(route.path),nav2_core::PlannerException);
}
TEST_F(PluginTest, NoIndependentCommandTimer)
{
  plan(); spline->publish(curve()); sendSafety();
  wait([] { return false; },0.08);
  EXPECT_TRUE(received.empty());
}
TEST_F(PluginTest, RepeatedCancelAfterAdmissionBeforeSplineReacknowledgesHold)
{
  std::vector<sm::P2BAdmission> replies;
  auto sub=io->create_subscription<sm::P2BAdmission>("/p2b/scan_admission",10,
    [&](sm::P2BAdmission::ConstSharedPtr m) { replies.push_back(*m); });
  plan();
  sm::P2BCancel request; identity(request); request.reason="before_first_spline";
  cancel->publish(request);
  ASSERT_TRUE(wait([&] { return !replies.empty(); }));
  wait([] { return false; },0.03);
  replies.clear();
  cancel->publish(request);
  ASSERT_TRUE(wait([&] { return !replies.empty(); },0.2));
  EXPECT_EQ(replies.back().command_id,route.command_id);
  EXPECT_TRUE(replies.back().hold_confirmed);
  EXPECT_FALSE(replies.back().measured_stillness_confirmed);
  EXPECT_FALSE(goal->isGoalReached(pose(8).pose,route.goal_pose,geometry_msgs::msg::Twist()));
}
TEST_F(PluginTest, CancelLatchesAndRejectsLateTrajectory)
{
  moving(); sm::P2BCancel m; identity(m); m.reason="test_cancel"; cancel->publish(m);
  ASSERT_TRUE(wait([&] { return !received.empty() && received.back().twist.linear.x==0; }));
  spline->publish(curve()); sendSafety(); wait([] { return false; },0.03);
  EXPECT_EQ(plugin->computeVelocityCommands(pose(),geometry_msgs::msg::Twist()).twist,geometry_msgs::msg::Twist());
  route.generation=2; route.path.header.stamp=parent->now(); binding->publish(route);
  wait([] { return false; },0.03);
  EXPECT_THROW(plugin->setPlan(route.path),nav2_core::PlannerException);
}
TEST_F(PluginTest, GoalRequiresRequestedHeightYawAndPhysicalEvidence)
{
  moving();
  EXPECT_FALSE(goal->isGoalReached(pose(7.5).pose,route.path.poses.back().pose,geometry_msgs::msg::Twist()));
  sendSafety(); wait([] { return false; },0.01);
  EXPECT_EQ(plugin->computeVelocityCommands(pose(8),geometry_msgs::msg::Twist()).twist,geometry_msgs::msg::Twist());
  EXPECT_FALSE(goal->isGoalReached(pose(8).pose,geometry_msgs::msg::Pose(),geometry_msgs::msg::Twist()));
  proof(false); EXPECT_FALSE(goal->isGoalReached(pose(8).pose,geometry_msgs::msg::Pose(),geometry_msgs::msg::Twist()));
  proof(true); EXPECT_TRUE(goal->isGoalReached(pose(8).pose,geometry_msgs::msg::Pose(),geometry_msgs::msg::Twist()));
  EXPECT_FALSE(goal->isGoalReached(pose(8,0.72).pose,geometry_msgs::msg::Pose(),geometry_msgs::msg::Twist()));
  auto turned=pose(8); turned.pose.orientation.w=std::cos(0.5); turned.pose.orientation.z=std::sin(0.5);
  EXPECT_FALSE(goal->isGoalReached(turned.pose,geometry_msgs::msg::Pose(),geometry_msgs::msg::Twist()));
}
TEST_F(PluginTest, OldObservationCannotBeRestampedByFreshSafetyMessage)
{
  moving(); sendSafety(true,0.4); wait([] { return false; },0.03);
  EXPECT_THROW(plugin->computeVelocityCommands(pose(),geometry_msgs::msg::Twist()),nav2_core::PlannerException);
}
TEST_F(PluginTest, SafetyProducerStallStopsOutput)
{
  moving(); wait([] { return false; },0.13);
  EXPECT_THROW(plugin->computeVelocityCommands(pose(),geometry_msgs::msg::Twist()),nav2_core::PlannerException);
}
TEST_F(PluginTest, PendingCurvesCannotRefreshTheExecutingProof)
{
  moving();auto *actual=dynamic_cast<scan_nav2_controller::Controller *>(plugin.get());
  for(int id=2;id<5;++id) {
    auto next=std::make_shared<sm::Bspline>(curve());next->traj_id=id;actual->onSpline(next);
    wait([] {return false;},0.045);
  }
  EXPECT_THROW(plugin->computeVelocityCommands(pose(),geometry_msgs::msg::Twist()),nav2_core::PlannerException);
}
TEST_F(PluginTest, ProofBeforeCurvePreservesSourceTimesAndExactPair)
{
  moving();auto *actual=dynamic_cast<scan_nav2_controller::Controller *>(plugin.get());
  auto proof=std::make_shared<sm::P2BExecutionSafety>();identity(proof->binding);
  proof->binding.consumer="native_safety";proof->binding.traj_id=2;proof->clear=true;
  proof->stamp=parent->now();proof->observation_stamp_s=parent->now().seconds();
  actual->onSafety(proof);
  EXPECT_EQ(actual->tracker_->traj_id_,1);
  auto next=std::make_shared<sm::Bspline>(curve());next->traj_id=2;actual->onSpline(next);
  EXPECT_EQ(actual->tracker_->traj_id_,2);EXPECT_EQ(actual->safety_->stamp,proof->stamp);
  EXPECT_EQ(actual->safety_->observation_stamp_s,proof->observation_stamp_s);
  EXPECT_GT(plugin->computeVelocityCommands(pose(),geometry_msgs::msg::Twist()).twist.linear.x,0.0);
}
TEST_F(PluginTest, StaleOrWrongOwnerReplacementProofCannotActivateCurve)
{
  moving();auto *actual=dynamic_cast<scan_nav2_controller::Controller *>(plugin.get());
  auto next=std::make_shared<sm::Bspline>(curve());next->traj_id=2;actual->onSpline(next);
  auto proof=std::make_shared<sm::P2BExecutionSafety>();identity(proof->binding);
  proof->binding.consumer="native_safety";proof->binding.traj_id=2;proof->clear=true;
  proof->stamp=parent->now();proof->observation_stamp_s=parent->now().seconds()-.251;
  actual->onSafety(proof);EXPECT_EQ(actual->tracker_->traj_id_,1);
  proof=std::make_shared<sm::P2BExecutionSafety>(*proof);proof->binding.map_revision+=1;
  proof->stamp=parent->now();proof->observation_stamp_s=parent->now().seconds();actual->onSafety(proof);
  EXPECT_EQ(actual->tracker_->traj_id_,1);
}
TEST_F(PluginTest, OutputCannotBeSubstitutedOrReplayed)
{
  moving(); sendSafety(); wait([] { return false; },0.01);
  auto v=plugin->computeVelocityCommands(pose(),geometry_msgs::msg::Twist()); v.twist.linear.x+=0.01;
  output->publishCommand(v);
  EXPECT_EQ(plugin->computeVelocityCommands(pose(),geometry_msgs::msg::Twist()).twist,geometry_msgs::msg::Twist());
}
TEST_F(PluginTest, InvalidBodyCannotReachTracker)
{
  moving(); auto p=pose(); p.pose.position.z=std::numeric_limits<double>::quiet_NaN();
  EXPECT_THROW(plugin->computeVelocityCommands(p,geometry_msgs::msg::Twist()),nav2_core::PlannerException);
}
TEST_F(PluginTest, IdenticalNanosecondBodyStampIsNotFuture)
{
  const auto clock=parent->get_clock()->get_clock_handle();
  ASSERT_EQ(rcl_enable_ros_time_override(clock),RCL_RET_OK);
  ASSERT_EQ(rcl_set_ros_time_override(clock,19000000000LL),RCL_RET_OK);
  plan();
  // Exact stamp captured by the v97 original Newton run; the previous
  // sec + 1e-9 * nanosec conversion rounded above ROS Time::seconds().
  ASSERT_EQ(rcl_set_ros_time_override(clock,19940670013LL),RCL_RET_OK);
  EXPECT_NO_THROW(plugin->computeVelocityCommands(pose(),geometry_msgs::msg::Twist()));
}
TEST_F(PluginTest, OneNanosecondFutureBodyIsStillRejected)
{
  const auto clock=parent->get_clock()->get_clock_handle();
  ASSERT_EQ(rcl_enable_ros_time_override(clock),RCL_RET_OK);
  ASSERT_EQ(rcl_set_ros_time_override(clock,19000000000LL),RCL_RET_OK);
  plan();
  ASSERT_EQ(rcl_set_ros_time_override(clock,19940670013LL),RCL_RET_OK);
  auto p=pose();p.header.stamp=rclcpp::Time(19940670014LL,RCL_ROS_TIME);
  EXPECT_THROW(plugin->computeVelocityCommands(p,geometry_msgs::msg::Twist()),nav2_core::PlannerException);
}
TEST_F(PluginTest, BodyBeyondOriginalHundredMillisecondLimitIsStillRejected)
{
  const auto clock=parent->get_clock()->get_clock_handle();
  ASSERT_EQ(rcl_enable_ros_time_override(clock),RCL_RET_OK);
  ASSERT_EQ(rcl_set_ros_time_override(clock,19000000000LL),RCL_RET_OK);
  plan();
  ASSERT_EQ(rcl_set_ros_time_override(clock,19940670013LL),RCL_RET_OK);
  auto p=pose();p.header.stamp=rclcpp::Time(19840670012LL,RCL_ROS_TIME);
  EXPECT_THROW(plugin->computeVelocityCommands(p,geometry_msgs::msg::Twist()),nav2_core::PlannerException);
}
TEST_F(PluginTest, FuturePoseUsesFreshDueSourceWithoutRestamping)
{
  auto *actual=dynamic_cast<scan_nav2_controller::Controller *>(plugin.get());
  const auto parent_clock=parent->get_clock()->get_clock_handle();
  const auto tracker_clock=actual->tracker_->get_clock()->get_clock_handle();
  ASSERT_EQ(rcl_enable_ros_time_override(parent_clock),RCL_RET_OK);
  ASSERT_EQ(rcl_enable_ros_time_override(tracker_clock),RCL_RET_OK);
  const int64_t original=83100959778LL, now=83120948792LL, future=83130943298LL;
  ASSERT_EQ(rcl_set_ros_time_override(parent_clock,original),RCL_RET_OK);
  ASSERT_EQ(rcl_set_ros_time_override(tracker_clock,original),RCL_RET_OK);
  moving();
  ASSERT_EQ(rcl_set_ros_time_override(parent_clock,now),RCL_RET_OK);
  ASSERT_EQ(rcl_set_ros_time_override(tracker_clock,now),RCL_RET_OK);
  auto incoming=pose(7.0);incoming.header.stamp=rclcpp::Time(future,RCL_ROS_TIME);
  geometry_msgs::msg::TwistStamped command;
  EXPECT_NO_THROW(command=plugin->computeVelocityCommands(incoming,geometry_msgs::msg::Twist()));
  EXPECT_GT(command.twist.linear.x,0.0);
  EXPECT_DOUBLE_EQ(actual->tracker_->odom_pos_.x(),0.0);
  EXPECT_DOUBLE_EQ(actual->ticket_body_stamp_s_,rclcpp::Time(original,RCL_ROS_TIME).seconds());
  // Once its original time is due, the queued measurement can be selected.
  ASSERT_EQ(rcl_set_ros_time_override(parent_clock,future+10000000),RCL_RET_OK);
  ASSERT_EQ(rcl_set_ros_time_override(tracker_clock,future+10000000),RCL_RET_OK);
  incoming=pose(6.0);incoming.header.stamp=rclcpp::Time(future+20000000,RCL_ROS_TIME);
  EXPECT_NO_THROW(plugin->computeVelocityCommands(incoming,geometry_msgs::msg::Twist()));
  EXPECT_DOUBLE_EQ(actual->tracker_->odom_pos_.x(),7.0);
  EXPECT_DOUBLE_EQ(actual->ticket_body_stamp_s_,rclcpp::Time(future,RCL_ROS_TIME).seconds());
}
TEST_F(PluginTest, FutureQueueCannotExtendBodyFreshness)
{
  auto *actual=dynamic_cast<scan_nav2_controller::Controller *>(plugin.get());
  const auto clock=parent->get_clock()->get_clock_handle();
  ASSERT_EQ(rcl_enable_ros_time_override(clock),RCL_RET_OK);
  ASSERT_EQ(rcl_set_ros_time_override(clock,19000000000LL),RCL_RET_OK);
  plan();EXPECT_NO_THROW(plugin->computeVelocityCommands(pose(),geometry_msgs::msg::Twist()));
  ASSERT_EQ(rcl_set_ros_time_override(clock,19100000001LL),RCL_RET_OK);
  auto future=pose();future.header.stamp=rclcpp::Time(19200000000LL,RCL_ROS_TIME);
  EXPECT_THROW(plugin->computeVelocityCommands(future,geometry_msgs::msg::Twist()),nav2_core::PlannerException);
  EXPECT_TRUE(actual->state_->stopping);
}
TEST_F(PluginTest, CachedBodyDoesNotHideInvalidIncomingFrame)
{
  moving();auto invalid=pose();invalid.header.frame_id="foreign";
  EXPECT_THROW(plugin->computeVelocityCommands(invalid,geometry_msgs::msg::Twist()),nav2_core::PlannerException);
}
TEST_F(PluginTest, MalformedSplineIsRejectedWithoutEvaluatorCrash)
{
  plan(); auto m=curve(); m.knots[4]=m.knots[3]; spline->publish(m);
  ASSERT_TRUE(wait([&] { return !received.empty(); }));
  EXPECT_EQ(received.back().twist,geometry_msgs::msg::Twist());
}
TEST_F(PluginTest, LifecycleDeactivateStopsAndDoesNotGrantOnActivate)
{
  moving(); plugin->deactivate(); plugin->activate();
  EXPECT_EQ(plugin->computeVelocityCommands(pose(),geometry_msgs::msg::Twist()).twist,geometry_msgs::msg::Twist());
}

TEST_F(PluginTest, StockControllerServerCannotAuthorizeOutput)
{
  plugin->cleanup();
  plugin->configure(parent,"SCAN",nullptr,nullptr);
  plugin->activate();
  ASSERT_TRUE(wait([&] { return binding->get_subscription_count()>0; }));
  plan();
  EXPECT_THROW(plugin->computeVelocityCommands(pose(),geometry_msgs::msg::Twist()),nav2_core::PlannerException);
}
TEST_F(PluginTest, DelayedOutputTicketIsRejectedAtPublication)
{
  moving(); sendSafety(); wait([] { return false; },0.01);
  auto v=plugin->computeVelocityCommands(pose(),geometry_msgs::msg::Twist());
  wait([] { return false; },0.12);
  output->publishCommand(v);
  EXPECT_EQ(plugin->computeVelocityCommands(pose(),geometry_msgs::msg::Twist()).twist,geometry_msgs::msg::Twist());
}
TEST_F(PluginTest, FreshTicketCannotRenewItsOlderBodySample)
{
  moving();sendSafety();wait([] { return false; },0.01);
  auto p=pose();p.header.stamp=rclcpp::Time(parent->now().nanoseconds()-80000000LL);
  auto command=plugin->computeVelocityCommands(p,geometry_msgs::msg::Twist());
  ASSERT_GT(command.twist.linear.x,0.0);
  // Proof and ticket remain valid; only the original body sample expires.
  wait([] { return false; },0.04);output->publishCommand(command);
  auto actual=dynamic_cast<scan_nav2_controller::Controller *>(plugin.get());
  EXPECT_TRUE(actual->state_->stopping);
}
TEST_F(PluginTest, WrongIdentityCancelDoesNotStopCurrentOwner)
{
  moving(); sm::P2BCancel m; identity(m); ++m.map_revision; cancel->publish(m);
  sendSafety(); wait([] { return false; },0.03);
  EXPECT_GT(plugin->computeVelocityCommands(pose(),geometry_msgs::msg::Twist()).twist.linear.x,0.0);
}
TEST_F(PluginTest, PreTrajectorySafetyDoesNotCancelAnUnstartedPlan)
{
  plan(); sm::P2BExecutionSafety message; identity(message.binding);
  message.binding.consumer="native_safety"; message.binding.traj_id=0;
  message.stamp=parent->now(); message.clear=false; safety->publish(message);
  wait([] { return false; },0.03);
  EXPECT_EQ(plugin->computeVelocityCommands(pose(),geometry_msgs::msg::Twist()).twist,geometry_msgs::msg::Twist());
  EXPECT_TRUE(received.empty());
}

TEST_F(PluginTest, PluginOwnsRealNativePlannerLifecycle)
{
  plugin->deactivate();
  parent->set_parameter(rclcpp::Parameter("SCAN.native_worker_enabled",true));
  const char *native_config=std::getenv("V86_NATIVE_PARAMS");
  parent->declare_parameter("SCAN.native_planner_config",std::string(native_config ? native_config : TEST_NATIVE_CONFIG));
  plugin->activate();
  ASSERT_TRUE(wait([&] {
    const auto names=io->get_node_names();
    return std::find(names.begin(),names.end(),"/quad_0/scan_planner_node")!=names.end();
  }));
  EXPECT_TRUE(received.empty());
  plugin->deactivate();
}

TEST_F(PluginTest, OriginalBindingStampCanExpireBeforeTheAction)
{
  const auto origin=parent->now().nanoseconds();
  route.path.header.stamp=rclcpp::Time(origin,RCL_ROS_TIME);
  const auto clock=parent->get_clock()->get_clock_handle();
  ASSERT_EQ(rcl_enable_ros_time_override(clock),RCL_RET_OK);
  ASSERT_EQ(rcl_set_ros_time_override(clock,origin+1900000000LL),RCL_RET_OK);
  bool acknowledged=false;
  auto subscription=io->create_subscription<sm::P2BRoute>("/nav2_scan/binding_ready",10,
    [&](sm::P2BRoute::ConstSharedPtr message) { acknowledged=(*message==route); });
  ASSERT_TRUE(wait([&] { binding->publish(route); return acknowledged; }));
  ASSERT_EQ(rcl_set_ros_time_override(clock,origin+2100000000LL),RCL_RET_OK);
  EXPECT_THROW(plugin->setPlan(route.path),nav2_core::PlannerException);
}

// Real plugin callback ordering: native safety revokes output between Nav2 ticks.
// Nav2 must observe failure on the next tick, without waiting for no-progress.
TEST_F(PluginTest, NegativeSafetyTriggersRecoveryOnNextTick)
{
  moving();
  auto *actual=dynamic_cast<scan_nav2_controller::Controller *>(plugin.get());
  ASSERT_NE(actual,nullptr);
  auto negative=std::make_shared<sm::P2BExecutionSafety>(); identity(negative->binding);
  negative->binding.consumer="native_safety"; negative->binding.traj_id=1;
  negative->stamp=parent->now();negative->observation_stamp_s=parent->now().seconds();
  negative->clear=false;actual->onSafety(negative);
  ASSERT_TRUE(actual->state_->stopping);
  EXPECT_THROW(plugin->computeVelocityCommands(pose(),geometry_msgs::msg::Twist()),nav2_core::PlannerException);
  spline->publish(curve());sendSafety();wait([] {return false;},0.02);
  EXPECT_THROW(plugin->computeVelocityCommands(pose(),geometry_msgs::msg::Twist()),nav2_core::PlannerException);
  const auto old=route;
  route.generation=2;route.command_id="second";route.path.header.stamp=parent->now();
  actual->onBinding(std::make_shared<sm::P2BRoute>(route));
  EXPECT_THROW(plugin->setPlan(route.path),nav2_core::PlannerException);
  route=old;proof(true);route.generation=2;route.command_id="second";
  route.path.header.stamp=parent->now();
  actual->onBinding(std::make_shared<sm::P2BRoute>(route));
  EXPECT_NO_THROW(plugin->setPlan(route.path));
  EXPECT_EQ(actual->state_->route->generation,2);
  EXPECT_FALSE(actual->state_->stopping);
  EXPECT_NO_THROW(plugin->computeVelocityCommands(pose(),geometry_msgs::msg::Twist()));
}
TEST_F(PluginTest, NegativeCandidateProofTriggersRecoveryInAdmissionTick)
{
  plan();
  auto *actual=dynamic_cast<scan_nav2_controller::Controller *>(plugin.get());ASSERT_NE(actual,nullptr);
  auto negative=std::make_shared<sm::P2BExecutionSafety>();identity(negative->binding);
  negative->binding.consumer="native_safety";negative->binding.traj_id=1;
  negative->stamp=parent->now();negative->observation_stamp_s=parent->now().seconds();
  negative->clear=false;actual->onSafety(negative);
  ASSERT_FALSE(actual->state_->stopping);
  actual->onSpline(std::make_shared<sm::Bspline>(curve()));
  ASSERT_TRUE(actual->state_->stopping);
  EXPECT_THROW(plugin->computeVelocityCommands(pose(),geometry_msgs::msg::Twist()),nav2_core::PlannerException);
}

TEST_F(PluginTest, GoalCaptureKeepsYawMarginForMeasuredStopDwell)
{
  moving();
  auto *actual=dynamic_cast<scan_nav2_controller::Controller *>(plugin.get());
  ASSERT_NE(actual,nullptr);
  auto p=pose(8);p.pose.orientation.z=std::sin(-0.21/2);p.pose.orientation.w=std::cos(-0.21/2);
  sendSafety();wait([] {return false;},0.01);
  auto turn=plugin->computeVelocityCommands(p,geometry_msgs::msg::Twist());
  EXPECT_GT(turn.twist.angular.z,0.0);EXPECT_DOUBLE_EQ(turn.twist.linear.x,0.0);
  EXPECT_FALSE(actual->state_->stopping);
  EXPECT_DOUBLE_EQ(actual->state_->yaw_tolerance,0.25);
  p=pose(8);p.pose.orientation.z=std::sin(-0.10/2);p.pose.orientation.w=std::cos(-0.10/2);
  EXPECT_EQ(plugin->computeVelocityCommands(p,geometry_msgs::msg::Twist()).twist,geometry_msgs::msg::Twist());
  EXPECT_TRUE(actual->state_->stopping);
  EXPECT_FALSE(goal->isGoalReached(p.pose,route.goal_pose,geometry_msgs::msg::Twist()));
  proof(true);
  auto drifted=pose(8);drifted.pose.orientation.z=std::sin(-0.21/2);drifted.pose.orientation.w=std::cos(-0.21/2);
  EXPECT_TRUE(goal->isGoalReached(drifted.pose,route.goal_pose,geometry_msgs::msg::Twist()));
  drifted.pose.orientation.z=std::sin(-0.27/2);drifted.pose.orientation.w=std::cos(-0.27/2);
  EXPECT_FALSE(goal->isGoalReached(drifted.pose,route.goal_pose,geometry_msgs::msg::Twist()));
}

TEST_F(PluginTest, ShortReversePrefixMovesBackwardWithoutTurning) {
 plan();auto m=curve();m.reverse_motion=true;
 for(size_t i=0;i<m.pos_pts.size();++i)m.pos_pts[i].x=i<3?0.0:-0.05;
 for(auto &k:m.knots)k*=0.25;
 spline->publish(m);geometry_msgs::msg::TwistStamped command;
 ASSERT_TRUE(wait([&]{sendSafety();command=plugin->computeVelocityCommands(pose(),geometry_msgs::msg::Twist());return std::abs(command.twist.linear.x)>1e-7 || std::abs(command.twist.angular.z)>0.01;}));
 EXPECT_LT(command.twist.linear.x,0.0);EXPECT_NEAR(command.twist.angular.z,0.0,1e-6);
 output->publishCommand(command);
 auto *actual=dynamic_cast<scan_nav2_controller::Controller *>(plugin.get());ASSERT_NE(actual,nullptr);
 EXPECT_TRUE(actual->tracker_->reverse_motion_);
 auto forward=std::make_shared<sm::Bspline>(m);forward->traj_id=2;forward->reverse_motion=false;forward->start_time=parent->now();
 for(size_t i=0;i<forward->pos_pts.size();++i)forward->pos_pts[i].x=i<3?0.0:0.05;
 actual->onSpline(forward);auto safe=std::make_shared<sm::P2BExecutionSafety>();identity(safe->binding);safe->binding.consumer="native_safety";safe->binding.traj_id=2;safe->clear=true;safe->stamp=parent->now();safe->observation_stamp_s=parent->now().seconds();actual->onSafety(safe);
 EXPECT_FALSE(actual->tracker_->reverse_motion_);
}
TEST_F(PluginTest, LongReverseModeSplineRejected) {
 moving();auto bad=std::make_shared<sm::Bspline>(curve());bad->traj_id=2;bad->reverse_motion=true;
 auto *actual=dynamic_cast<scan_nav2_controller::Controller *>(plugin.get());ASSERT_NE(actual,nullptr);actual->onSpline(bad);
 EXPECT_TRUE(actual->state_->stopping);
 EXPECT_EQ(plugin->computeVelocityCommands(pose(),geometry_msgs::msg::Twist()).twist,geometry_msgs::msg::Twist());
}
