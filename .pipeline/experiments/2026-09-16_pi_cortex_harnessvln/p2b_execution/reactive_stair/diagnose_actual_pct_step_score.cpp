#include <plan_env/eth_step_score_adaptation.h>

#include <chrono>
#include <iostream>

using namespace reactive_stair;

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
  const auto start = std::chrono::steady_clock::now();
  const auto result = precomputeEthStyleStepScores(terrain);
  const auto end = std::chrono::steady_clock::now();

  size_t flat = 0, stair = 0, unsupported = 0, unknown = 0;
  size_t near_step = 0, near_step_survived = 0;
  for (const auto &entry : terrain.cells) {
    const auto &scored = result.support.cells.at(entry.first);
    for (size_t layer = 0; layer < entry.second.size(); ++layer) {
      const Support support = scored[layer].support;
      if (support == Support::Flat) ++flat;
      else if (support == Support::Stair) ++stair;
      else if (support == Support::Unsupported) ++unsupported;
      else ++unknown;
      bool adjacent_step = false;
      for (const Cell2 &offset : {Cell2{-1, 0}, Cell2{1, 0}, Cell2{0, -1}, Cell2{0, 1}}) {
        const Cell2 neighbor{entry.first.x + offset.x, entry.first.y + offset.y};
        const auto found = terrain.cells.find(neighbor);
        if (found == terrain.cells.end()) continue;
        const int index = nearestSurface(found->second, entry.second[layer].elevation_m);
        if (index < 0) continue;
        const double difference = std::abs(
            found->second[index].elevation_m - entry.second[layer].elevation_m);
        if (difference >= 0.04 && difference < 0.26) {
          adjacent_step = true;
          break;
        }
      }
      if (adjacent_step) {
        ++near_step;
        if (support == Support::Flat || support == Support::Stair) ++near_step_survived;
      }
    }
  }
  if (flat + stair + unsupported + unknown != count) return 4;
  std::cout << "{\"input_selected_cells\":" << count
            << ",\"unique_xy_cells\":" << terrain.cells.size()
            << ",\"supported_flat\":" << flat
            << ",\"supported_stair_edge\":" << stair
            << ",\"supported_total\":" << flat + stair
            << ",\"unsupported\":" << unsupported
            << ",\"unknown\":" << unknown
            << ",\"step_like_adjacent_input\":" << near_step
            << ",\"step_like_adjacent_supported\":" << near_step_survived
            << ",\"precompute_ms\":"
            << std::chrono::duration<double, std::milli>(end - start).count()
            << "}\n";
  return 0;
}
