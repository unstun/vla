#pragma once
#include <exception>
#include <rclcpp/rclcpp.hpp>

namespace scan_runtime {
// Must run inside the ROS callback, before Foxy's executor thread boundary.
// Failure handlers also stay contained, including a failed log/publication path.
template<class Work,class Failure>
bool callbackBoundary(const rclcpp::Logger &logger,const char *site,
    Work &&work,Failure &&failure) noexcept {
  const auto report=[&](const char *message) noexcept {
    try { RCLCPP_ERROR(logger,"native_callback_exception site=%s: %s",site,message); }
    catch (...) {}
    try { failure(); }
    catch (...) {
      try { RCLCPP_ERROR(logger,"native_callback_cleanup_exception site=%s",site); }
      catch (...) {}
    }
  };
  try {work();return true;}
  catch (const std::exception &error) {report(error.what());}
  catch (...) {report("unknown exception");}
  return false;
}
} // namespace scan_runtime
