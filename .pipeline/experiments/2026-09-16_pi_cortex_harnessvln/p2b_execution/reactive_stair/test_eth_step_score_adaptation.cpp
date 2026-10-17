#include <plan_env/eth_step_score_adaptation.h>
#include <plan_env/raw_return_classification.h>

#include <cassert>
#include <cmath>
#include <iostream>

using namespace reactive_stair;

TerrainSnapshot grid(int side = 11) {
  TerrainSnapshot terrain;
  terrain.source_id = "pct_selected_ground_fixture";
  terrain.frame = "world";
  terrain.stamp_s = 1.0;
  terrain.resolution_m = 0.1;
  terrain.origin_x_m = 0.0;
  terrain.origin_y_m = 0.0;
  for (int x = 0; x < side; ++x)
    for (int y = 0; y < side; ++y)
      terrain.cells[{x, y}] = {{Support::Stair, 0.0}};
  return terrain;
}

int main() {
  assert(std::abs(ethSecondPassScore(0.4, 1, 0.26, 4) - (1.0 - 0.1 / 0.26)) < 1e-12);
  assert(ethSecondPassScore(0.18, 0, 0.26, 4) == 1.0);
  assert(ethSecondPassScore(0.4, 4, 0.26, 4) == 0.0);

  const auto flat = precomputeEthStyleStepScores(grid());
  assert(flat.support.cells.at({5, 5})[0].support == Support::Flat);
  assert(flat.scores.at({5, 5})[0].known);
  assert(flat.scores.at({5, 5})[0].first_pass_height_m == 0.0);
  assert(flat.scores.at({5, 5})[0].score == 1.0);
  assert(flat.support.cells.at({0, 0})[0].support == Support::Unknown); // incomplete window

  auto stairs = grid();
  for (auto &entry : stairs.cells)
    if (entry.first.x >= 5) entry.second[0].elevation_m = 0.18;
  const auto stair_result = precomputeEthStyleStepScores(stairs);
  assert(stair_result.support.cells.at({4, 5})[0].support == Support::Stair);
  assert(stair_result.support.cells.at({5, 5})[0].support == Support::Stair);
  assert(stair_result.support.cells.at({8, 5})[0].support == Support::Flat);
  assert(stair_result.scores.at({8, 5})[0].score == 1.0);
  assert(selectedGroundReturn(stair_result.support, 0.85, 0.55, 0.18, 0.05));

  auto tall_box = grid();
  tall_box.cells[{5, 5}][0].elevation_m = 0.50;
  const auto box_result = precomputeEthStyleStepScores(tall_box);
  assert(!std::isfinite(box_result.scores.at({5, 5})[0].first_pass_height_m));
  assert(box_result.support.cells.at({5, 5})[0].support == Support::Unknown);
  assert(!selectedGroundReturn(box_result.support, 0.55, 0.55, 0.50, 0.05));
  assert(!mayWaiveRawContributor(false, true, true)); // box remains nonterrain

  auto thin_wall = grid();
  for (int y = 0; y < 11; ++y) thin_wall.cells[{5, y}][0].elevation_m = 0.50;
  const auto wall_result = precomputeEthStyleStepScores(thin_wall);
  assert(wall_result.support.cells.at({5, 5})[0].support == Support::Unknown);
  assert(!selectedGroundReturn(wall_result.support, 0.55, 0.55, 0.50, 0.05));
  // The conservative label change must never make either obstacle traversable.
  for (const auto &terrain : {box_result.support, wall_result.support}) {
    Parameters parameters;
    parameters.body_clearance_m = .35;
    CollisionDecision decision(parameters);
    assert(decision.acceptTerrain(terrain));
    assert(decision.acceptTracks({"current_empty_fixture", "world", 1., true, {}}));
    assert(decision.decide({"world", 1., .55, .55, .85, true},
                          {Occupancy::Free, "observed_fixture", "world", 1.}) != Verdict::Free);
  }

  auto missing = grid();
  missing.cells.erase({5, 5});
  const auto missing_result = precomputeEthStyleStepScores(missing);
  assert(missing_result.support.cells.at({4, 5})[0].support == Support::Unknown);
  assert(missing_result.support.cells.find({5, 5}) == missing_result.support.cells.end());

  auto wrong_resolution = grid();
  wrong_resolution.resolution_m = 0.05;
  const auto wrong_resolution_result = precomputeEthStyleStepScores(wrong_resolution);
  assert(wrong_resolution_result.support.cells.at({5, 5})[0].support == Support::Unknown);

  auto ambiguous = grid();
  ambiguous.cells[{4, 5}] = {{Support::Stair, -0.1}, {Support::Stair, 0.1}};
  const auto ambiguous_result = precomputeEthStyleStepScores(ambiguous);
  assert(ambiguous_result.support.cells.at({5, 5})[0].support == Support::Unknown);

  auto layered = grid();
  for (auto &entry : layered.cells)
    entry.second.push_back({Support::Stair, 1.0 + (entry.first.x >= 5 ? 0.18 : 0.0)});
  const auto layered_result = precomputeEthStyleStepScores(layered);
  assert(layered_result.support.cells.at({5, 5})[0].support == Support::Flat);
  assert(layered_result.support.cells.at({5, 5})[1].support == Support::Stair);
  assert(layered_result.support.cells.at({8, 5})[1].support == Support::Flat);

  std::cout << "ETH-style two-pass adaptation fixtures: PASS\n";
}
