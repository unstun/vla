#include <gtest/gtest.h>
#include <nav2_controller/nav2_controller.hpp>
#include <scan_nav2_controller/controller.hpp>
#include <nav2_core/exceptions.hpp>
#include <thread>

using namespace std::chrono_literals;

class OutputServer : public nav2_controller::ControllerServer
{
public:
  using ControllerServer::publishVelocity;
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
