#pragma once

#include <geometry_msgs/msg/twist_stamped.hpp>
#include <string>

namespace scan_nav2_controller
{
// Foxy ControllerServer calls this at its actual output/stop boundary. The stock
// Twist publisher cannot carry P2B identity; do not reconstruct identity later.
class CommandOutput
{
public:
  virtual ~CommandOutput() = default;
  virtual void bindOutputOwner() = 0;
  virtual void publishCommand(const geometry_msgs::msg::TwistStamped &command) = 0;
  virtual void stop(const std::string &reason) = 0;
};
}  // namespace scan_nav2_controller
