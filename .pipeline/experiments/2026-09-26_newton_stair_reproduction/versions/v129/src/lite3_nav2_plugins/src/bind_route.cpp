#include <behaviortree_cpp_v3/action_node.h>
#include <behaviortree_cpp_v3/bt_factory.h>
#include <lite3_nav2_interfaces/srv/bind_route.hpp>
#include <rclcpp/rclcpp.hpp>
#include <std_srvs/srv/trigger.hpp>

namespace lite3_nav2 {
class BindScanRoute : public BT::StatefulActionNode {
  using Service = lite3_nav2_interfaces::srv::BindRoute;
  rclcpp::Node::SharedPtr node_;
  rclcpp::Client<Service>::SharedPtr client_;
  rclcpp::executors::SingleThreadedExecutor executor_;
  rclcpp::Client<Service>::SharedFuture future_;
  std::chrono::steady_clock::time_point deadline_;
public:
  BindScanRoute(const std::string &name, const BT::NodeConfiguration &config)
    : BT::StatefulActionNode(name, config) {
    auto parent = config.blackboard->get<rclcpp::Node::SharedPtr>("node");
    rclcpp::NodeOptions options;
    options.use_global_arguments(false);
    options.parameter_overrides({rclcpp::Parameter("use_sim_time", parent->get_parameter("use_sim_time").as_bool())});
    node_ = std::make_shared<rclcpp::Node>("nav2_bind_route_client", options);
    client_ = node_->create_client<Service>("/lite3_nav2/bind_route");
    executor_.add_node(node_);
  }
  static BT::PortsList providedPorts() {
    return {BT::InputPort<geometry_msgs::msg::PoseStamped>("goal"),
      BT::InputPort<nav_msgs::msg::Path>("path"), BT::OutputPort<nav_msgs::msg::Path>("bound_path")};
  }
  BT::NodeStatus onStart() override {
    auto request = std::make_shared<Service::Request>();
    if (!getInput("goal", request->goal) || !getInput("path", request->path) || !client_->service_is_ready())
      return BT::NodeStatus::FAILURE;
    future_ = client_->async_send_request(request);
    deadline_ = std::chrono::steady_clock::now() + std::chrono::seconds(3);
    return BT::NodeStatus::RUNNING;
  }
  BT::NodeStatus onRunning() override {
    executor_.spin_some();
    if (future_.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
      const auto response = future_.get();
      if (!response->accepted) return BT::NodeStatus::FAILURE;
      setOutput("bound_path", response->binding.path);
      return BT::NodeStatus::SUCCESS;
    }
    return std::chrono::steady_clock::now() > deadline_ ? BT::NodeStatus::FAILURE : BT::NodeStatus::RUNNING;
  }
  void onHalted() override { /* The authoritative mission gateway revokes late service results. */ }
};

class WaitForScanStop : public BT::StatefulActionNode {
  using Service = std_srvs::srv::Trigger;
  rclcpp::Node::SharedPtr node_;
  rclcpp::Client<Service>::SharedPtr client_;
  rclcpp::executors::SingleThreadedExecutor executor_;
  rclcpp::Client<Service>::SharedFuture future_;
  std::chrono::steady_clock::time_point deadline_;
public:
  WaitForScanStop(const std::string &name, const BT::NodeConfiguration &config)
    : BT::StatefulActionNode(name, config) {
    rclcpp::NodeOptions options; options.use_global_arguments(false);
    node_ = std::make_shared<rclcpp::Node>("nav2_wait_stop_client", options);
    client_ = node_->create_client<Service>("/lite3_nav2/wait_stopped");
    executor_.add_node(node_);
  }
  static BT::PortsList providedPorts() { return {}; }
  BT::NodeStatus onStart() override {
    if (!client_->service_is_ready()) return BT::NodeStatus::FAILURE;
    future_ = client_->async_send_request(std::make_shared<Service::Request>());
    // The gateway may wait ten seconds for original measured-stop evidence.
    // Keep one second for returning its result; this never authorizes motion.
    deadline_ = std::chrono::steady_clock::now() + std::chrono::seconds(11);
    return BT::NodeStatus::RUNNING;
  }
  BT::NodeStatus onRunning() override {
    executor_.spin_some();
    if (future_.wait_for(std::chrono::seconds(0)) == std::future_status::ready)
      return future_.get()->success ? BT::NodeStatus::SUCCESS : BT::NodeStatus::FAILURE;
    return std::chrono::steady_clock::now() > deadline_ ? BT::NodeStatus::FAILURE : BT::NodeStatus::RUNNING;
  }
  void onHalted() override {}
};
}
BT_REGISTER_NODES(factory) {
  factory.registerNodeType<lite3_nav2::BindScanRoute>("BindScanRoute");
  factory.registerNodeType<lite3_nav2::WaitForScanStop>("WaitForScanStop");
}
