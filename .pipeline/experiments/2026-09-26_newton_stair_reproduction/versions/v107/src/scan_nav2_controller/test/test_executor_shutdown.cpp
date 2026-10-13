#include <gtest/gtest.h>
#include <rclcpp/rclcpp.hpp>
#include <scan_nav2_controller/executor_shutdown.hpp>
using namespace std::chrono_literals;

TEST(ExecutorShutdown, CancelsEvenWhenStopPrecedesFoxySpinEntry) {
  int argc=0;rclcpp::init(argc,nullptr);
  for (bool multi : {false,true}) {
    std::shared_ptr<rclcpp::Executor> executor;
    if(multi)executor=std::make_shared<rclcpp::executors::MultiThreadedExecutor>(rclcpp::ExecutorOptions(),2);
    else executor=std::make_shared<rclcpp::executors::SingleThreadedExecutor>();
    auto node=std::make_shared<rclcpp::Node>(multi?"multi_shutdown":"single_shutdown");
    executor->add_node(node);
    std::atomic<bool> release{false},finished{false};
    std::thread worker([&] {
      while(!release.load())std::this_thread::sleep_for(1ms);
      executor->spin();finished=true;
    });
    executor->cancel(); // Deliberately before spin; this cancellation is lost in Foxy.
    release=true;
    std::this_thread::sleep_for(30ms);
    EXPECT_FALSE(finished.load());
    const auto before=std::chrono::steady_clock::now();
    scan_nav2_controller::joinStoppedExecutor(executor,worker,finished);
    EXPECT_TRUE(finished.load());EXPECT_FALSE(worker.joinable());
    EXPECT_LT(std::chrono::steady_clock::now()-before,500ms);
    executor->remove_node(node);
  }
  // Also stop before the worker has even attempted spin().
  auto executor=std::make_shared<rclcpp::executors::SingleThreadedExecutor>();
  auto node=std::make_shared<rclcpp::Node>("delayed_shutdown");executor->add_node(node);
  std::atomic<bool> done{false};
  std::thread late([&] {std::this_thread::sleep_for(30ms);executor->spin();done=true;});
  scan_nav2_controller::joinStoppedExecutor(executor,late,done);
  EXPECT_TRUE(done.load());
  rclcpp::shutdown();
}
