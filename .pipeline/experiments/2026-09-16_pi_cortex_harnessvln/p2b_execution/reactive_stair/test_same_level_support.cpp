#include <plan_env/eth_step_score_adaptation.h>
#include <algorithm>
#include <iostream>
#include <stdexcept>

using namespace reactive_stair;

void require(bool value, const char *message) {
  if (!value) throw std::runtime_error(message);
}

TerrainSnapshot grid() {
  TerrainSnapshot t;
  t.source_id = "same_level_fixture";
  t.frame = "world";
  t.stamp_s = 1.;
  t.resolution_m = .1;
  for (int x = 0; x < 11; ++x)
    for (int y = 0; y < 11; ++y) t.cells[{x, y}] = {{Support::Stair, .058}};
  return t;
}

void requireBlocked(const TerrainSnapshot &terrain, double ground) {
  Parameters p;
  p.body_clearance_m = .35;
  CollisionDecision decision(p);
  require(decision.acceptTerrain(terrain), "terrain acceptance failed");
  require(decision.acceptTracks({"measured_empty_fixture", "world", 1., true, {}}), "tracks acceptance failed");
  const Query q{"world", 1., .55, .55, ground + .35, true};
  const NonTerrainVoxel obstacle{Occupancy::Free, "observed_fixture", "world", 1.};
  require(decision.decide(q, obstacle) != Verdict::Free, "missing/incompatible support became free");
}

int main() {
  try {
    auto absent_lower = grid();
    absent_lower.cells[{4, 5}] = {{Support::Stair, 6.082}};
    auto result = precomputeEthStyleStepScores(absent_lower);
    require(result.support.cells.at({5, 5})[0].support == Support::Unknown,
            "upper-only neighbor was misclassified as a same-level step");
    require(!std::isfinite(result.scores.at({5, 5})[0].first_pass_height_m), "missing layer contributed a height");
    requireBlocked(result.support, .058);

    // The center's first window is complete; only its second-pass neighbor
    // has an incompatible first window. Both passes must propagate Unknown.
    auto second_window = grid();
    second_window.cells[{3, 5}] = {{Support::Stair, 6.082}};
    result = precomputeEthStyleStepScores(second_window);
    require(std::isfinite(result.scores.at({5, 5})[0].first_pass_height_m), "fixture missed second-pass boundary");
    require(result.support.cells.at({5, 5})[0].support == Support::Unknown, "second pass ignored missing same-level support");
    requireBlocked(result.support, .058);

    auto layered = grid();
    for (auto &entry : layered.cells) entry.second.push_back({Support::Stair, 6.082});
    for (int order = 0; order < 2; ++order) {
      result = precomputeEthStyleStepScores(layered);
      for (const auto &s : result.support.cells.at({5, 5})) require(s.support == Support::Flat, "layer order changed support");
      for (auto &entry : layered.cells) std::reverse(entry.second.begin(), entry.second.end());
    }

    for (double h : {.26 - 1e-6, .26, .26 + 1e-6, .5}) {
      auto step = grid();
      for (auto &entry : step.cells) entry.second[0].elevation_m = entry.first.x >= 5 ? h : 0.;
      result = precomputeEthStyleStepScores(step);
      const auto support = result.support.cells.at({5, 5})[0].support;
      if (h < .26) require(support == Support::Stair, "subcritical stair changed");
      else {
        require(support == (h == .26 ? Support::Unsupported : Support::Unknown), "critical boundary misclassified");
        requireBlocked(result.support, h);
      }
    }
    auto tie = grid();
    tie.cells[{4, 5}] = {{Support::Stair, -.042}, {Support::Stair, .158}};
    require(precomputeEthStyleStepScores(tie).support.cells.at({5, 5})[0].support == Support::Unknown, "tie became free");
    auto missing = grid();
    missing.cells.erase({4, 5});
    require(precomputeEthStyleStepScores(missing).support.cells.at({5, 5})[0].support == Support::Unknown, "missing cell became free");
#ifdef SAME_LEVEL_BOUND_FIXED
    require(nearestSurface({{Support::Stair, 6.082}}, .058, .26) == -1, "far layer association accepted");
    require(nearestSurface({{Support::Stair, .26}}, 0., .26) == 0, "critical equality lost");
    require(nearestSurface({{Support::Stair, 0.}}, NAN, .26) == -1, "invalid target accepted");
    require(nearestSurface({{Support::Stair, 0.}}, 0., -1.) == -1, "negative layer limit accepted");
    require(nearestSurface({{Support::Stair, 0.}}, 0., NAN) == -1, "invalid layer limit accepted");
#endif
    std::cout << "same-level, two-pass, order, threshold, ambiguity and collision regressions PASS\n";
    return 0;
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
