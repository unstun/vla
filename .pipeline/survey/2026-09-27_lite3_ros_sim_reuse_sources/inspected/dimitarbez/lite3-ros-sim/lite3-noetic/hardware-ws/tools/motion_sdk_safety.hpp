#pragma once

#include <cstdint>

inline bool RobotStateRequiresStop(std::uint32_t basic_state,
                                   std::uint32_t error_flags) {
  return basic_state == 8 || error_flags != 0;
}
