#pragma once

#include <string>
#include <nav2_core/exceptions.hpp>

namespace scan_nav2_controller
{
class TerminalSettleTimeout : public nav2_core::PlannerException {
public:
  TerminalSettleTimeout(): nav2_core::PlannerException("terminal_settle_timeout") {}
};

// The server owns velocity publication; this hook only clears plugin execution.
class ExecutionControl
{
public:
  virtual ~ExecutionControl() = default;
  virtual void stop(const std::string &reason) = 0;
  virtual bool terminalPhase() const = 0;
};
}  // namespace scan_nav2_controller
