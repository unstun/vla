#pragma once
#include <plan_env/callback_exception.h>
#include <lite3_nav2_interfaces/srv/check_traversability.hpp>

namespace scan_nav2_controller {
template<class Work>
void nativeQueryCallback(const rclcpp::Logger &logger,
    lite3_nav2_interfaces::srv::CheckTraversability::Response &reply,Work &&work) noexcept {
  scan_runtime::callbackBoundary(logger,"check_traversability",std::forward<Work>(work),[&] {
    reply.ready=false;reply.verdicts.clear();reply.message="native_query_exception";
  });
}
} // namespace scan_nav2_controller
