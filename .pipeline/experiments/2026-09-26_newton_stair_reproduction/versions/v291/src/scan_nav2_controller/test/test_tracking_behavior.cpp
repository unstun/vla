#include <gtest/gtest.h>
#include <rcl/time.h>
#include <scan_nav2_controller/tracking_node.hpp>

class TrackingBehavior : public ::testing::Test
{
protected:
  static void SetUpTestCase() { int argc=0;rclcpp::init(argc,nullptr); }
  static void TearDownTestCase() { rclcpp::shutdown(); }
  void SetUp() override {
    rclcpp::NodeOptions options;options.use_global_arguments(false);
    options.parameter_overrides({rclcpp::Parameter("finish_dist",0.02)});
    node=std::make_shared<scan_planner::TrackingNode>(options);
    setClock(10000000000LL);
    body.header.frame_id="world";body.pose.position.z=.42;body.pose.orientation.w=1.;
    nav_msgs::msg::Path path;path.header.frame_id="world";path.poses={body,body};
    path.poses.back().pose.position.x=50.;node->setReferencePath(path);
    replace();
  }
  void setClock(int64_t ns) {
    stamp=ns;auto clock=node->get_clock()->get_clock_handle();
    ASSERT_EQ(rcl_enable_ros_time_override(clock),RCL_RET_OK);
    ASSERT_EQ(rcl_set_ros_time_override(clock,stamp),RCL_RET_OK);
  }
  void replace(bool expired=false,bool tiny=false,bool reverse=false) {
    auto spline=std::make_shared<scan_planner_msgs::msg::Bspline>();
    spline->order=3;spline->traj_id=++id;spline->reverse_motion=reverse;
    spline->start_time=rclcpp::Time(stamp-(expired?10000000000LL:0),RCL_ROS_TIME);
    for(int i=0;i<12;++i) {
      geometry_msgs::msg::Point p;p.x=tiny?(reverse?-.04:.04):.4*i;p.z=.42;
      spline->pos_pts.push_back(p);
    }
    for(int i=-3;i<13;++i)spline->knots.push_back(i);
    node->bsplineCallback(spline);
  }
  geometry_msgs::msg::Twist tick(double yaw=0.,int64_t dt=20000000LL) {
    setClock(stamp+dt);body.header.stamp=rclcpp::Time(stamp,RCL_ROS_TIME);
    body.pose.orientation.z=std::sin(yaw/2);body.pose.orientation.w=std::cos(yaw/2);
    return node->sample(body);
  }
  std::shared_ptr<scan_planner::TrackingNode> node;
  geometry_msgs::msg::PoseStamped body;
  int64_t stamp{0},id{0};
};

TEST_F(TrackingBehavior, TravelHeadingKeepsTranslationAndPhaseAcrossSameGoalRefresh)
{
  for(int i=0;i<60;++i)tick();
  auto previous=node->sampled_command_;
  tick(-1.01);EXPECT_FALSE(node->turning_in_place_);EXPECT_FALSE(node->executionFrozen());
  EXPECT_GT(node->sampled_command_.linear.x,0.);
  EXPECT_LE(std::abs(node->sampled_command_.linear.x-previous.linear.x),.04+1e-9);
  for(double error : {.99,.81,.79,.61,.8}) {
    replace();node->setReferencePath(node->reference_path_);
    tick(-error);EXPECT_FALSE(node->turning_in_place_);EXPECT_FALSE(node->executionFrozen());
  }
  tick(-.59);EXPECT_FALSE(node->turning_in_place_);EXPECT_FALSE(node->executionFrozen());
  for(int i=0;i<100;++i) {
    previous=node->sampled_command_;const auto cmd=tick(-(i%2?.79:.81));
    EXPECT_FALSE(node->turning_in_place_);
    EXPECT_LE(std::abs(cmd.linear.x-previous.linear.x),.04+1e-9);
    EXPECT_LE(std::abs(cmd.linear.y-previous.linear.y),.04+1e-9);
    EXPECT_LE(std::abs(cmd.angular.z-previous.angular.z),.06+1e-9);
  }
}
TEST_F(TrackingBehavior, NewSplineEveryTickDoesNotResetOutputRamp)
{
  geometry_msgs::msg::Twist previous;
  for(int i=0;i<60;++i) {
    replace();const auto cmd=tick();
    EXPECT_LE(cmd.linear.x-previous.linear.x,.02+1e-9);previous=cmd;
  }
  EXPECT_GT(previous.linear.x,.6);
}
TEST_F(TrackingBehavior, ExpiredLowSpeedTailBrakesExactlyToZeroWithoutArrival)
{
  for(int i=0;i<60;++i)tick();
  auto previous=node->sampled_command_;
  replace(true,true);
  for(int i=0;i<60;++i) {
    const auto cmd=tick();
    EXPECT_LE(std::abs(cmd.linear.x-previous.linear.x),.04+1e-9);previous=cmd;
  }
  EXPECT_EQ(previous,geometry_msgs::msg::Twist());
  EXPECT_TRUE(node->expired_braking_);EXPECT_FALSE(node->goal_position_latched_);
  EXPECT_TRUE(node->haveTrajectory());EXPECT_FALSE(node->executionFrozen());
  body.pose.position.x=-1.; // Noise cannot restart this stopped expired curve.
  EXPECT_EQ(tick(),geometry_msgs::msg::Twist());
  replace();tick();EXPECT_GT(tick().linear.x,0.);EXPECT_FALSE(node->expired_braking_);
}
TEST_F(TrackingBehavior, ActiveShortCorrectionIsNotCutOffAtPointTwo)
{
  for(bool reverse : {false,true}) {
    node->clearTrajectory();replace(false,true,reverse);
    tick();const auto cmd=tick();
    EXPECT_GT(std::abs(cmd.linear.x),0.);EXPECT_LT(std::abs(cmd.linear.x),.2);
    EXPECT_FALSE(node->expired_braking_);EXPECT_FALSE(node->goal_position_latched_);
    EXPECT_DOUBLE_EQ(node->finish_dist_,.02);
  }
}
TEST_F(TrackingBehavior, EmergencyAndCancelClearRampAndTurnStateImmediately)
{
  for(int i=0;i<60;++i)tick();
  node->turning_in_place_=true;
  auto emergency=std::make_shared<scan_planner_msgs::msg::Bspline>();
  emergency->order=3;emergency->emergency_stop=true;emergency->start_time=rclcpp::Time(stamp,RCL_ROS_TIME);
  for(int i=0;i<6;++i) {geometry_msgs::msg::Point p;p.z=.42;emergency->pos_pts.push_back(p);}
  for(int i=-3;i<7;++i)emergency->knots.push_back(i);
  node->bsplineCallback(emergency);
  EXPECT_EQ(node->sampled_command_,geometry_msgs::msg::Twist());EXPECT_FALSE(node->turning_in_place_);
  replace();EXPECT_EQ(tick(),geometry_msgs::msg::Twist());EXPECT_LE(tick().linear.x,.02+1e-9);
  node->clearTrajectory();EXPECT_EQ(node->sampled_command_,geometry_msgs::msg::Twist());
}
TEST_F(TrackingBehavior, FinalYawConvergenceStopsAllAxesInFiniteTime)
{
  body.pose.position.x=50.;
  for(int i=0;i<40;++i)tick(-.5);
  EXPECT_TRUE(node->goal_position_latched_);EXPECT_GT(node->sampled_command_.angular.z,0.);
  for(int i=0;i<40;++i)tick(0.);
  EXPECT_EQ(node->sampled_command_,geometry_msgs::msg::Twist());
}
TEST(CommandSlew, PerAxisBoundsSignReversalAndFiniteZeroCapture)
{
  scan_nav2_controller::CommandSlew slew;
  geometry_msgs::msg::Twist target,previous;target.linear.x=1.;target.linear.y=-.35;target.angular.z=1.;
  int64_t ns=10000000000LL;slew.update(target,ns);
  for(int i=0;i<600;++i) {
    if(i==100){target.linear.x=-1.;target.linear.y=.35;target.angular.z=-1.;}
    if(i==300)target={};
    const double dt=(i%2?.013:.037);ns+=static_cast<int64_t>(dt*1e9);
    const auto cmd=slew.update(target,ns);
    EXPECT_LE(std::abs(cmd.linear.x-previous.linear.x),2.*dt+1e-9);
    EXPECT_LE(std::abs(cmd.linear.y-previous.linear.y),2.*dt+1e-9);
    EXPECT_LE(std::abs(cmd.angular.z-previous.angular.z),3.*dt+1e-9);
    previous=cmd;
  }
  EXPECT_EQ(previous,geometry_msgs::msg::Twist());
  EXPECT_NEAR(slew.axis(.1,-1.,.1,1.,2.),-.05,1e-12);
  target.linear.x=1.;slew.update(target,ns+20000000LL);
  EXPECT_EQ(slew.update(target,ns-1),geometry_msgs::msg::Twist());
  EXPECT_EQ(slew.update(target,ns+1000000000LL),geometry_msgs::msg::Twist());
}
TEST_F(TrackingBehavior, InvalidLimitConfigurationIsRejected)
{
  for(const char *name : {"linear_acceleration","linear_deceleration","angular_acceleration",
                         "angular_deceleration","expired_min_walk_speed"}) {
    rclcpp::NodeOptions options;options.parameter_overrides({rclcpp::Parameter(name,0.)});
    EXPECT_THROW(scan_planner::TrackingNode bad(options),std::runtime_error);
  }
  rclcpp::NodeOptions options;
  options.parameter_overrides({rclcpp::Parameter("heading_resume_threshold",1.1)});
  EXPECT_THROW(scan_planner::TrackingNode bad(options),std::runtime_error);
}

TEST_F(TrackingBehavior, HeadingSlowsTranslationAndPhaseWithoutTravelLock) {
  for(int i=0;i<60;++i)tick(-1.6);
  EXPECT_NEAR(node->exec_time_,.6,1e-8);
  EXPECT_GT(std::hypot(node->sampled_command_.linear.x,node->sampled_command_.linear.y),.01);
  EXPECT_GT(std::abs(node->sampled_command_.angular.z),.1);
  EXPECT_FALSE(node->executionFrozen());EXPECT_FALSE(node->turning_in_place_);
  const double before=node->exec_time_;
  tick(0.);EXPECT_NEAR(node->exec_time_-before,.02,1e-8);
}
TEST_F(TrackingBehavior, HeadingScaleIsContinuousAndMonotone) {
  double previous=1.;
  for(double heading:{.59,.6,.61,.7,.8,.9,.99,1.,1.6,3.1}) {
    replace();tick(-heading);
    const double ratio=node->exec_time_/.02;
    EXPECT_GE(ratio,.5-1e-9);EXPECT_LE(ratio,previous+1e-9);previous=ratio;
  }
}

TEST_F(TrackingBehavior, TerminalYawCentersInWorldCoordinatesWithSlew)
{
  for(double yaw : {-.8, .8, 2.4}) {
    node->clearTrajectory(); replace();
    body.pose.position.x=49.90;body.pose.position.y=.04;
    geometry_msgs::msg::Twist previous;
    for(int i=0;i<60;++i) {
      const auto cmd=tick(yaw);
      EXPECT_TRUE(node->goal_position_latched_);EXPECT_TRUE(node->executionFrozen());
      EXPECT_LE(std::abs(cmd.linear.x-previous.linear.x),.04+1e-8);
      EXPECT_LE(std::abs(cmd.linear.y-previous.linear.y),.04+1e-8);
      EXPECT_LE(std::abs(cmd.angular.z-previous.angular.z),.06+1e-8);
      previous=cmd;
    }
    const auto cmd=node->sampled_command_;
    const Eigen::Vector2d world(std::cos(yaw)*cmd.linear.x-std::sin(yaw)*cmd.linear.y,
        std::sin(yaw)*cmd.linear.x+std::cos(yaw)*cmd.linear.y);
    EXPECT_GT(world.dot(Eigen::Vector2d(.10,-.04)),0.);
    EXPECT_GT(std::hypot(cmd.linear.x,cmd.linear.y),.01);
    EXPECT_LT(cmd.angular.z*yaw,0.);
    EXPECT_DOUBLE_EQ(node->exec_time_,0.);
  }
  body.pose.position.x=50.;body.pose.position.y=0.;
  for(int i=0;i<60;++i)tick(0.);
  EXPECT_EQ(node->sampled_command_,geometry_msgs::msg::Twist());
}

TEST_F(TrackingBehavior, AlignedGoalCentersBeforeInnerCaptureThenHoldsThroughSway) {
  for(double offset:{.024,.05,.10,.24}) {
    node->clearTrajectory();replace();body.pose.position.x=50.-offset;body.pose.position.y=0.;
    for(int i=0;i<60;++i)tick(0.);
    if (offset<=.05) EXPECT_EQ(node->sampled_command_,geometry_msgs::msg::Twist());
    else {EXPECT_GT(node->sampled_command_.linear.x,.01);EXPECT_FALSE(node->terminalBraking());}
    EXPECT_TRUE(node->executionFrozen());
  }
}
TEST_F(TrackingBehavior, YawCaptureHasBoundedCorrectionWithoutEdgeCrawl) {
  for(double offset:{.024,.05,.050001,.10,.24}) {
    node->clearTrajectory();replace();body.pose.position.x=50.-offset;body.pose.position.y=0.;
    for(int i=0;i<60;++i)tick(.8);
    const auto cmd=node->sampled_command_;
    EXPECT_LE(std::hypot(cmd.linear.x,cmd.linear.y),.15+1e-9);
    EXPECT_LT(cmd.angular.z,0.);
    if(offset<=.05) EXPECT_LT(std::hypot(cmd.linear.x,cmd.linear.y),1e-9);
    else {
      const Eigen::Vector2d world(std::cos(.8)*cmd.linear.x-std::sin(.8)*cmd.linear.y,
          std::sin(.8)*cmd.linear.x+std::cos(.8)*cmd.linear.y);
      EXPECT_GT(world.x(),0.);
      if(offset<.051){EXPECT_GT(world.norm(),.03);}
    }
  }
}

TEST_F(TrackingBehavior, TerminalApproachSlowsBeforeOriginalCaptureWithMatchedPhase) {
  for(double distance:{.8,.5,.28}) {
    node->clearTrajectory();replace();body.pose.position.x=50.-distance;body.pose.position.y=0.;
    const double initial_phase=node->exec_time_;
    tick();tick();
    EXPECT_GT(node->exec_time_,initial_phase);
    EXPECT_LT(node->exec_time_-initial_phase,.04);
    geometry_msgs::msg::Twist previous=node->sampled_command_;
    for(int i=0;i<60;++i) {
      const auto cmd=tick();
      EXPECT_LE(std::abs(cmd.linear.x-previous.linear.x),.04+1e-8);
      previous=cmd;
    }
    EXPECT_LE(std::hypot(previous.linear.x,previous.linear.y),node->kp_pos_*distance+1e-8);
    EXPECT_FALSE(node->goal_position_latched_);
    EXPECT_FALSE(node->expired_braking_);
  }
  body.pose.position.x=49.76;
  for(int i=0;i<60;++i)tick();
  EXPECT_TRUE(node->goal_position_latched_);
  EXPECT_GT(node->sampled_command_.linear.x,.01);
  EXPECT_FALSE(node->terminalBraking());
  EXPECT_DOUBLE_EQ(node->goal_xy_tolerance_,.25);
}

TEST_F(TrackingBehavior, OverlappingOtherFloorDoesNotApplyTerminalSlowdown) {
  node->clearTrajectory();replace();body.pose.position.x=49.5;body.pose.position.z=2.;
  tick();tick();
  EXPECT_NEAR(node->exec_time_,.04,1e-8);
  EXPECT_FALSE(node->goal_position_latched_);
}

TEST_F(TrackingBehavior, UnifiedTerminalLatchKeepsOriginalOuterTolerance) {
  body.pose.position.x=49.96;body.pose.position.y=0;
  for(int i=0;i<60;++i)tick();
  ASSERT_TRUE(node->terminalBraking());
  body.pose.position.x=49.90;
  for(int i=0;i<60;++i)tick();
  EXPECT_TRUE(node->terminalBraking());EXPECT_EQ(node->sampled_command_,geometry_msgs::msg::Twist());
  body.pose.position.x=49.74;tick();
  EXPECT_FALSE(node->terminalBraking());
  node->clearTrajectory();EXPECT_FALSE(node->terminalBraking());
}
