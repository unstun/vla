#pragma once
#include <rclcpp/executor.hpp>
#include <atomic>
#include <chrono>
#include <thread>

namespace scan_nav2_controller {
// Foxy spin() sets spinning=true on entry, so a single cancel() issued before
// that entry is lost. Keep cancelling until the owned thread has left spin.
// This runs only on lifecycle teardown, never on the command/safety path.
inline void joinStoppedExecutor(const std::shared_ptr<rclcpp::Executor> &executor,
                                std::thread &thread,const std::atomic<bool> &finished) {
  if (!thread.joinable()) return;
  while (!finished.load()) {
    executor->cancel();
    std::this_thread::sleep_for(std::chrono::milliseconds(1));
  }
  thread.join();
}
}
