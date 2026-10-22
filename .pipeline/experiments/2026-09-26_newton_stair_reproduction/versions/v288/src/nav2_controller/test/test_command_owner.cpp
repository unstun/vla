#include <gtest/gtest.h>
#include <nav2_controller/nav2_controller.hpp>
#include <scan_nav2_controller/controller.hpp>
#include <nav2_core/exceptions.hpp>
#include <thread>
#include <rcl/time.h>
#include <nav2_controller/plugins/simple_progress_checker.hpp>

using namespace std::chrono_literals;

class OutputServer : public nav2_controller::ControllerServer
{
public:
  using ControllerServer::publishVelocity;
  using ControllerServer::recordFailure;
  using ControllerServer::checkProgress;
  void releaseProgress() { progress_checker_.reset(); }
  void initializeProgress() {
    progress_checker_=std::make_shared<nav2_controller::SimpleProgressChecker>();
    progress_checker_->initialize(shared_from_this(), "progress_checker");
  }
  using ControllerServer::publishZeroVelocity;
  void attach(const nav2_core::Controller::Ptr &plugin) {
    controllers_["SCAN"]=plugin;
    current_controller_="SCAN";
    vel_publisher_=create_publisher<geometry_msgs::msg::Twist>("cmd_vel",10);
    vel_publisher_->on_activate();
  }
  void deselect() { current_controller_.clear(); }
  void disablePublisher() { vel_publisher_->on_deactivate(); }
};

class OutputTest : public ::testing::Test
{
protected:
  static void SetUpTestCase() {
    const char *args[]={"command_owner_test","--ros-args","-r","cmd_vel:=/quad_0/cmd_vel"};
    rclcpp::init(4,args);
  }
  static void TearDownTestCase() { rclcpp::shutdown(); }
  void SetUp() override {
    server=std::make_shared<OutputServer>();
    server->declare_parameter("SCAN.native_worker_enabled",false);
    plugin=std::make_shared<scan_nav2_controller::Controller>();
    plugin->configure(server,"SCAN",nullptr,nullptr);
    plugin->activate();
    server->attach(plugin);
    observer=std::make_shared<rclcpp::Node>("command_owner_observer");
    subscription=observer->create_subscription<geometry_msgs::msg::Twist>("/quad_0/cmd_vel",10,
      [this](geometry_msgs::msg::Twist::ConstSharedPtr msg) { received.push_back(*msg); });
    const auto until=std::chrono::steady_clock::now()+2s;
    while(subscription->get_publisher_count()!=1 && std::chrono::steady_clock::now()<until)
      spin();
    ASSERT_EQ(subscription->get_publisher_count(),1u);
    path.header.frame_id="world";
    geometry_msgs::msg::PoseStamped start;start.header.frame_id="world";start.pose.orientation.w=1;
    path.poses={start,start};path.poses.back().pose.position.x=8;
    plugin->setPlan(path);
  }
  void TearDown() override {
    server->releaseProgress(); // Release the fixture-created parent/checker ownership cycle.
    plugin->deactivate();plugin->cleanup();plugin.reset();server.reset();observer.reset();
  }
  void spin() { rclcpp::spin_some(observer);std::this_thread::sleep_for(5ms); }
  void expectCount(size_t count) {
    const auto until=std::chrono::steady_clock::now()+1s;
    while(received.size()<count && std::chrono::steady_clock::now()<until) spin();
    EXPECT_EQ(received.size(),count);
  }
  std::shared_ptr<OutputServer> server;
  std::shared_ptr<scan_nav2_controller::Controller> plugin;
  rclcpp::Node::SharedPtr observer;
  rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr subscription;
  nav_msgs::msg::Path path;
  std::vector<geometry_msgs::msg::Twist> received;
};

TEST_F(OutputTest, PluginReturnsWaitCommandAndServerPublishesExactlyOnce)
{
  auto command=plugin->computeVelocityCommands(path.poses.front(),geometry_msgs::msg::Twist());
  for(int i=0;i<10;++i) spin();
  EXPECT_TRUE(received.empty());
  EXPECT_EQ(command.twist,geometry_msgs::msg::Twist());
  server->publishVelocity(command);expectCount(1);
  command.twist.linear.x=.4;
  server->publishVelocity(command);expectCount(2);
  EXPECT_DOUBLE_EQ(received.back().linear.x,.4);
  for(int i=0;i<10;++i) spin();
  EXPECT_EQ(received.size(),2u);
}

TEST_F(OutputTest, ServerStopClearsSelectedPlanAndPublishesZero)
{
  geometry_msgs::msg::TwistStamped moving;moving.twist.linear.x=.4;
  server->publishVelocity(moving);expectCount(1);
  server->publishZeroVelocity();expectCount(2);
  EXPECT_EQ(received.back(),geometry_msgs::msg::Twist());
  EXPECT_THROW(plugin->computeVelocityCommands(path.poses.front(),geometry_msgs::msg::Twist()),nav2_core::PlannerException);
}

TEST_F(OutputTest, ServerStopWithoutSelectedControllerStillPublishesZero)
{
  server->deselect();server->publishZeroVelocity();expectCount(1);
  EXPECT_EQ(received.back(),geometry_msgs::msg::Twist());
  EXPECT_THROW(plugin->computeVelocityCommands(path.poses.front(),geometry_msgs::msg::Twist()),nav2_core::PlannerException);
}

TEST_F(OutputTest, InactiveServerDoesNotPublish)
{
  server->disablePublisher();
  geometry_msgs::msg::TwistStamped moving;moving.twist.linear.x=.4;
  server->publishVelocity(moving);
  server->publishZeroVelocity();
  for(int i=0;i<10;++i) spin();
  EXPECT_TRUE(received.empty());
  EXPECT_THROW(plugin->computeVelocityCommands(path.poses.front(),geometry_msgs::msg::Twist()),nav2_core::PlannerException);
}

TEST_F(OutputTest, TerminalTickExemptsExpiredMovementDeadlineAndLeavingResumesIt)
{
  server->initializeProgress();
  auto clock=server->get_clock();
  ASSERT_EQ(rcl_enable_ros_time_override(clock->get_clock_handle()),RCL_RET_OK);
  ASSERT_EQ(rcl_set_ros_time_override(clock->get_clock_handle(),1000000000LL),RCL_RET_OK);
  auto near=path.poses.back();near.pose.position.x-=.3;
  server->checkProgress(near);
  ASSERT_EQ(rcl_set_ros_time_override(clock->get_clock_handle(),12000000000LL),RCL_RET_OK);
  EXPECT_THROW(server->checkProgress(near),nav2_core::PlannerException);
  auto at=path.poses.back();
  plugin->computeVelocityCommands(at,geometry_msgs::msg::Twist());
  ASSERT_TRUE(plugin->terminalPhase());
  EXPECT_NO_THROW(server->checkProgress(at));
  // Move just outside tolerance but inside the progress movement radius.
  plugin->setPlan(path);
  EXPECT_NO_THROW(plugin->computeVelocityCommands(near,geometry_msgs::msg::Twist()));
  ASSERT_FALSE(plugin->terminalPhase());
  EXPECT_NO_THROW(server->checkProgress(near));
  ASSERT_EQ(rcl_set_ros_time_override(clock->get_clock_handle(),23000000000LL),RCL_RET_OK);
  EXPECT_THROW(server->checkProgress(near),nav2_core::PlannerException);
}

TEST_F(OutputTest, FailureCauseSurvivesStopAndIsScopedToActionUuid)
{
  using Query=lite3_nav2_interfaces::srv::FollowPathFailure;
  auto client=observer->create_client<Query>("/lite3_nav2/follow_path_failure");
  ASSERT_TRUE(client->wait_for_service(2s));
  rclcpp_action::GoalUUID id{};id[0]=1;
  server->recordFailure(id,scan_nav2_controller::TerminalSettleTimeout());
  server->publishZeroVelocity();
  auto query=[&](rclcpp_action::GoalUUID target) {
    auto req=std::make_shared<Query::Request>();req->goal_id=target;
    auto future=client->async_send_request(req);
    const auto until=std::chrono::steady_clock::now()+2s;
    while(future.wait_for(0ms)!=std::future_status::ready && std::chrono::steady_clock::now()<until) {
      rclcpp::spin_some(server->get_node_base_interface());spin();
    }
    if(future.wait_for(0ms)!=std::future_status::ready)throw std::runtime_error("query timed out");
    return future.get();
  };
  auto result=query(id);EXPECT_TRUE(result->known);EXPECT_TRUE(result->terminal_timeout);
  auto other=id;other[0]=2;
  result=query(other);EXPECT_FALSE(result->known);EXPECT_FALSE(result->terminal_timeout);
  // Same text is not the typed terminal outcome: ordinary exceptions still retry.
  server->recordFailure(other,nav2_core::PlannerException("terminal_settle_timeout"));
  result=query(other);EXPECT_TRUE(result->known);EXPECT_FALSE(result->terminal_timeout);
  result=query(id);EXPECT_FALSE(result->known);EXPECT_FALSE(result->terminal_timeout);
}
