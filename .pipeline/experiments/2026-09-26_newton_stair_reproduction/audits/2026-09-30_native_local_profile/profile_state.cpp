#include <plan_env/local_hotspot_profile.h>
#include <iomanip>
#include <iostream>

namespace local_profile {
bool active = false;
std::array<Record, 12> records{};
void start() { records = {}; active = true; }
void stop() { active = false; }
void report() {
  const char *names[] = {"plan_from_current", "rebound_attempt", "rebound_optimize",
      "combined_cost", "distance_cost", "collision_rebound", "astar",
      "reactive_occupancy", "raw_contributors", "footprint_support", "terrain_decide", "deboor"};
  for (std::size_t i = 0; i < records.size(); ++i)
    std::cout << "LOCAL_PROFILE name=" << names[i] << " calls=" << records[i].calls
              << " inclusive_wall_s=" << std::setprecision(12) << records[i].elapsed_ns / 1e9 << '\n';
}
}
