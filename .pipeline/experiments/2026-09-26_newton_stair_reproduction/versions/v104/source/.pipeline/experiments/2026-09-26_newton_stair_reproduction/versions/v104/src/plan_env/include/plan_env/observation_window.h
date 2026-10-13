#pragma once

#include <cmath>
#include <cstdint>
#include <stdexcept>

namespace scan_observation_window
{
// Admission semantics follow Foxy ObservationBuffer::purgeStaleObservations.
// Original source: navigation2@a947ab5656e46ae3aa1afdf95e1706a16e478974.
// Queue ownership, exact pose pairing and once-only fusion remain native SCAN.
struct Policy
{
  double persistence_s{0.5};
  double update_hz{5.0};
  int maximum_clouds{64};

  void validate() const
  {
    if (!std::isfinite(persistence_s) || persistence_s<0 ||
        !std::isfinite(update_hz) || update_hz<=0 || update_hz>100 ||
        maximum_clouds<1 || maximum_clouds>1000)
      throw std::invalid_argument("Invalid Nav2 observation-window policy");
  }
  bool keep(int64_t source_stamp_ns, int64_t newest_stamp_ns, int64_t last_received_ns) const
  {
    if (source_stamp_ns<=0 || newest_stamp_ns<=0 || last_received_ns<=0) return false;
    if (persistence_s==0.0) return source_stamp_ns==newest_stamp_ns;
    return static_cast<long double>(last_received_ns)-source_stamp_ns<=persistence_s*1e9L;
  }
};
}  // namespace scan_observation_window
