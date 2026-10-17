#include <plan_env/eth_step_score_adaptation.h>

#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <vector>

using reactive_stair::Cell2;
using reactive_stair::Support;
using reactive_stair::SurfaceCell;
using reactive_stair::TerrainSnapshot;

struct Anchor { double x, y, z; };

int main() {
  size_t count = 0;
  if (!(std::cin >> count) || count == 0 || count > 1000000) return 2;
  TerrainSnapshot terrain;
  terrain.source_id = "pinned_building_pct_selected_cells";
  terrain.frame = "world";
  terrain.stamp_s = 1.0;
  terrain.resolution_m = 0.1;
  for (size_t n = 0; n < count; ++n) {
    int x = 0, y = 0;
    double z = 0.0;
    if (!(std::cin >> x >> y >> z)) return 3;
    terrain.cells[{x, y}].push_back({Support::Stair, z});
  }
  const auto scored = reactive_stair::precomputeEthStyleStepScores(terrain);
  // These are the pinned scan_07 reference-path anchors, ground height in world.
  const std::vector<Anchor> anchors = {
      {-5.5, 5.5, .10}, {-5.5, 4.5, .30}, {-5.5, 3.5, .40},
      {-5.5, 2.5, .55}, {-5.5, 1.5, .70}, {-5.5, .5, .85},
      {-5.5, -.5, 1.00}, {-5.5, -1.5, 1.20}, {-5.5, -2.5, 1.40},
      {-5.5, -3.5, 1.55}, {-5.5, -4.5, 1.55}};
  constexpr double center_x = 1.4546852111816406;
  constexpr double center_y = -0.3868112564086914;
  constexpr int offset_x = 94, offset_y = 92;
  int blocked = 0, total = 0, longest_blocked = 0, blocked_run = 0;
  for (int segment = 0; segment < 10; ++segment) {
    for (int step = 0; step < 10; ++step) {
      const double t = step / 10.0;
      const Anchor q{anchors[segment].x,
                     anchors[segment].y * (1 - t) + anchors[segment + 1].y * t,
                     anchors[segment].z * (1 - t) + anchors[segment + 1].z * t};
      const int gx = static_cast<int>(std::round((q.x - center_x) / .1)) + offset_x;
      const int gy = static_cast<int>(std::round((q.y - center_y) / .1)) + offset_y;
      int accepted = 0, candidate = 0;
      double closest = std::numeric_limits<double>::infinity();
      for (int dx = -2; dx <= 2; ++dx)
        for (int dy = -2; dy <= 2; ++dy) {
          const Cell2 key{gx + dx, gy + dy};
          const auto found = scored.support.cells.find(key);
          if (found == scored.support.cells.end()) continue;
          const double wx = (key.x - offset_x) * .1 + center_x;
          const double wy = (key.y - offset_y) * .1 + center_y;
          if (std::hypot(wx - q.x, wy - q.y) > .20) continue;
          for (const SurfaceCell &surface : found->second) {
            if (std::abs(surface.elevation_m - q.z) > .12) continue;
            ++candidate;
            if (surface.support == Support::Flat || surface.support == Support::Stair) {
              ++accepted;
              closest = std::min(closest, std::hypot(wx - q.x, wy - q.y));
            }
          }
        }
      ++total;
      if (accepted == 0) {
        ++blocked;
        ++blocked_run;
        longest_blocked = std::max(longest_blocked, blocked_run);
      } else blocked_run = 0;
      std::cout << "y=" << q.y << " expected_z=" << q.z << " candidates=" << candidate
                << " supported=" << accepted << " nearest_m=" << closest << '\n';
    }
  }
  std::cout << "samples=" << total << " blocked=" << blocked
            << " longest_blocked_samples=" << longest_blocked << '\n';
  return 0;
}
