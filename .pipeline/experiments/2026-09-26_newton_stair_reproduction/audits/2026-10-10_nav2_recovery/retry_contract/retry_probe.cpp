#include <behaviortree_cpp_v3/bt_factory.h>
#include <rclcpp/rclcpp.hpp>
#include <std_srvs/srv/trigger.hpp>
#include <atomic>
#include <chrono>
#include <fstream>
#include <iostream>
#include <sstream>
#include <thread>

// Real installed RecoveryNode and WaitForScanStop, synthetic navigation and
// stop-service result. Physical stop evidence is checked separately.
int main(int argc, char **argv) {
  if (argc != 5) throw std::runtime_error("Expected two plugins, fixture XML and retry budget");
  rclcpp::init(argc, argv);
  const int budget = std::stoi(argv[4]);
  auto node = std::make_shared<rclcpp::Node>("recovery_budget_fixture");
  std::atomic<int> stop_calls{0};
  std::atomic<bool> stop_proved{true};
  auto service = node->create_service<std_srvs::srv::Trigger>("/lite3_nav2/wait_stopped",
    [&](const std::shared_ptr<std_srvs::srv::Trigger::Request>,
        std::shared_ptr<std_srvs::srv::Trigger::Response> response) {
      ++stop_calls;
      response->success = stop_proved.load();
    });
  rclcpp::executors::SingleThreadedExecutor executor;
  executor.add_node(node);
  std::thread worker([&] { executor.spin(); });
  std::ifstream input(argv[3]); std::stringstream xml; xml << input.rdbuf();
  int all_passed = 1;
  for (int mode = 0; mode < 3; ++mode) {
    int attempts = 0;
    bool order_ok = true;
    stop_calls = 0; stop_proved = mode != 2;
    BT::BehaviorTreeFactory factory;
    factory.registerFromPlugin(argv[1]);
    factory.registerFromPlugin(argv[2]);
    factory.registerSimpleAction("NavigationFixture", [&](BT::TreeNode &) {
      // Every second and later attempt must follow a successful stop response.
      if (attempts > 0 && (!stop_proved || stop_calls.load() != attempts)) order_ok = false;
      ++attempts;
      return mode == 0 && attempts == 4 ? BT::NodeStatus::SUCCESS : BT::NodeStatus::FAILURE;
    });
    auto tree = factory.createTreeFromText(xml.str());
    std::this_thread::sleep_for(std::chrono::milliseconds(500));
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(15);
    auto status = tree.tickRoot();
    while (status == BT::NodeStatus::RUNNING && std::chrono::steady_clock::now() < deadline) {
      std::this_thread::sleep_for(std::chrono::milliseconds(5));
      status = tree.tickRoot();
    }
    const bool expect_success = mode == 0 && budget >= 3;
    const int expected_attempts = mode == 2 ? 1 : (expect_success ? 4 : budget + 1);
    const int expected_stops = mode == 2 ? 1 : expected_attempts - 1;
    bool passed = order_ok && attempts == expected_attempts && stop_calls == expected_stops &&
      status == (expect_success ? BT::NodeStatus::SUCCESS : BT::NodeStatus::FAILURE);
    all_passed &= passed;
    std::cout << "RETRY_CASE mode=" << mode << " passed=" << passed
              << " success=" << (status == BT::NodeStatus::SUCCESS)
              << " attempts=" << attempts << " stops=" << stop_calls << " order_ok=" << order_ok << std::endl;
    tree.haltTree();
  }
  executor.cancel(); worker.join(); rclcpp::shutdown();
  return all_passed ? 0 : 1;
}
