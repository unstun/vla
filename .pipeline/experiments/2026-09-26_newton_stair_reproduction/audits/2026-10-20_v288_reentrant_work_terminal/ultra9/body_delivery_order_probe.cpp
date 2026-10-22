// Read-only diagnosis using the frozen production BodyTimeBuffer.
#include <plan_env/body_time_buffer.h>
#include <condition_variable>
#include <iostream>
#include <mutex>
#include <thread>

int main() {
  scan_input_time::BodyTimeBuffer buffer;
  std::recursive_mutex work;
  std::mutex phase_mutex;
  std::condition_variable phase;
  bool older_taken = false, older_ok = true;
  auto message = [](int sec) {
    auto value = std::make_shared<nav_msgs::msg::Odometry>();
    value->header.stamp.sec = sec;
    return value;
  };
  // Model an executor that has taken an older message before entering the
  // registered callback guard, while refreshSensorInputs owns the work lock.
  std::unique_lock<std::recursive_mutex> current_callback(work);
  std::thread waiting_callback([&] {
    auto older = message(1);
    { std::lock_guard<std::mutex> lock(phase_mutex); older_taken = true; }
    phase.notify_one();
    std::lock_guard<std::recursive_mutex> callback_guard(work);
    older_ok = buffer.push(older);
  });
  { std::unique_lock<std::mutex> lock(phase_mutex); phase.wait(lock,[&]{return older_taken;}); }
  const bool drained_newer_ok = buffer.push(message(2));
  current_callback.unlock();
  waiting_callback.join();
  std::lock_guard<std::recursive_mutex> final_callback(work);
  const bool subsequent_newer_ok = buffer.push(message(3));
  const bool reproduced = drained_newer_ok && !older_ok && !subsequent_newer_ok &&
      buffer.error() == "regressed_body_source_stamp";
  std::cout << "{\"modeled_delivery_latch_reproduced\":" << (reproduced?"true":"false")
            << ",\"newer_then_waiting_older_then_newer\":[" << drained_newer_ok << ","
            << older_ok << "," << subsequent_newer_ok << "],\"error\":\""
            << buffer.error() << "\",\"physics_steps\":0}\n";
  return reproduced ? 0 : 1;
}
