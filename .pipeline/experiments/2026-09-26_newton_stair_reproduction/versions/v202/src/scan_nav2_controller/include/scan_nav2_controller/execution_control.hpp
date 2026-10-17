#pragma once

#include <string>

namespace scan_nav2_controller
{
// The server owns velocity publication; this hook only clears plugin execution.
class ExecutionControl
{
public:
  virtual ~ExecutionControl() = default;
  virtual void stop(const std::string &reason) = 0;
  virtual bool terminalPhase() const = 0;
};
}  // namespace scan_nav2_controller
