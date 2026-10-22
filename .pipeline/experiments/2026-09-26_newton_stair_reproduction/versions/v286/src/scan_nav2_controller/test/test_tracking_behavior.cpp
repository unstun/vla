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
