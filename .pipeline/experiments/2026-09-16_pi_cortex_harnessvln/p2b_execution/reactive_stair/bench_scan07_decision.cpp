#include <plan_env/eth_step_score_adaptation.h>
#include <plan_env/raw_return_classification.h>

#include <algorithm>
#include <chrono>
#include <iostream>
#include <set>
#include <tuple>
#include <vector>

using namespace reactive_stair;
using Clock = std::chrono::steady_clock;

int main() {
  TerrainSnapshot terrain;
  terrain.source_id = "synthetic_pct_benchmark";
  terrain.frame = "world";
  terrain.stamp_s = 1000.0;
  terrain.resolution_m = 0.1;
  for (int x = 0; x < 101; ++x)
    for (int y = 0; y < 101; ++y)
      terrain.cells[{x, y}] = {{Support::Stair, x >= 50 ? 0.18 : 0.0}};
  const auto precompute_start = Clock::now();
  auto scored = precomputeEthStyleStepScores(terrain);
  const auto precompute_end = Clock::now();

  Parameters parameters;
  parameters.terrain_max_age_s = 86400.0;
  CollisionDecision decision(parameters);
  if (!decision.acceptTerrain(scored.support) ||
      !decision.acceptTracks({"synthetic_empty_tracks", "world", 1000.0, true, {}}))
    return 2;
  Query query{"world", 1000.0, 7.05, 5.05, 0.58, true};
  NonTerrainVoxel obstacle{Occupancy::Free, "synthetic_lidar", "world", 1000.0};
  std::set<std::tuple<int, int, int>> terrain_hits;
  for (int n = 0; n < 500; ++n) terrain_hits.insert({n, 0, 0});
  std::vector<double> elapsed_us;
  elapsed_us.reserve(1000);
  int free_count = 0;
  for (int iteration = 0; iteration < 1000; ++iteration) {
    const auto start = Clock::now();
    bool classified = true;
    for (int n = 0; n < 500; ++n) {
      const auto key = std::make_tuple(n, 0, 0);
      classified &= mayWaiveRawContributor(terrain_hits.count(key) != 0, false, false);
    }
    if (classified && decision.decide(query, obstacle) == Verdict::Free) ++free_count;
    const auto end = Clock::now();
    elapsed_us.push_back(std::chrono::duration<double, std::micro>(end - start).count());
  }
  std::sort(elapsed_us.begin(), elapsed_us.end());
  std::cout << "synthetic_pct_cells=10201 precompute_ms="
            << std::chrono::duration<double, std::milli>(precompute_end - precompute_start).count()
            << " synthetic_queries=1000 contributors_per_query=500"
            << " p95_us=" << elapsed_us[949]
            << " max_us=" << elapsed_us.back()
            << " free_count=" << free_count << "\n";
  // This excludes ROS, GridMap buffer access, raycasting, other callbacks,
  // and scheduler effects; it is not the 50 ms safety timer measurement.
  return free_count == 1000 ? 0 : 3;
}
