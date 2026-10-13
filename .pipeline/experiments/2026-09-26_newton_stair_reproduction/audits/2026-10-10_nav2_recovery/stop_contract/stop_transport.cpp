#include <behaviortree_cpp_v3/bt_factory.h>
#include <rclcpp/rclcpp.hpp>
#include <std_srvs/srv/trigger.hpp>
#include <chrono>
#include <iostream>
#include <thread>

int main(int argc,char **argv) {
  if(argc!=2)throw std::runtime_error("Pass the exact installed BT plugin path");
  rclcpp::init(argc,argv);
  auto node=std::make_shared<rclcpp::Node>("measured_stop_transport_fixture");
  auto service=node->create_service<std_srvs::srv::Trigger>("/lite3_nav2/wait_stopped",
    [](const std::shared_ptr<std_srvs::srv::Trigger::Request>,
       std::shared_ptr<std_srvs::srv::Trigger::Response> response) {
      // Transport-only fixture. The separate Python test uses recorded physical
      // data and the real gateway wait loop; this service makes no physical claim.
      std::this_thread::sleep_for(std::chrono::milliseconds(5300));
      response->success=true;
    });
  rclcpp::executors::SingleThreadedExecutor executor;executor.add_node(node);
  std::thread worker([&]{executor.spin();});
  BT::BehaviorTreeFactory factory;factory.registerFromPlugin(argv[1]);
  auto tree=factory.createTreeFromText("<root main_tree_to_execute='Main'><BehaviorTree ID='Main'><WaitForScanStop/></BehaviorTree></root>");
  std::this_thread::sleep_for(std::chrono::milliseconds(400));
  const auto begin=std::chrono::steady_clock::now();
  auto status=tree.tickRoot();
  while(status==BT::NodeStatus::RUNNING && std::chrono::steady_clock::now()-begin<std::chrono::seconds(12)) {
    std::this_thread::sleep_for(std::chrono::milliseconds(10));status=tree.tickRoot();
  }
  const double elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count();
  std::cout<<"STOP_TRANSPORT success="<<(status==BT::NodeStatus::SUCCESS)<<" elapsed_s="<<elapsed<<std::endl;
  tree.haltTree();executor.cancel();worker.join();rclcpp::shutdown();
  return status==BT::NodeStatus::SUCCESS?0:1;
}
