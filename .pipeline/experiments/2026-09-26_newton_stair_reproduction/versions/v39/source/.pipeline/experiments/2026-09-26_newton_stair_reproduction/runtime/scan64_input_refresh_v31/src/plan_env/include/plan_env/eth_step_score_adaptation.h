#ifndef P2B_ETH_STEP_SCORE_ADAPTATION_H
#define P2B_ETH_STEP_SCORE_ADAPTATION_H

// Adapted from the two-pass method in ETH Zurich's StepFilter.cpp, pinned at
// 14d24c059e1c43466aadf328280adf6394d78039 (BSD-3-Clause).
// Copyright (c) 2015, Peter Fankhauser. All rights reserved.
// Original source and license: references/upstream/2026-09-23_eth_stepfilter_reference/
// Local changes: sparse selected PCT cells, nearest elevation per layer,
// ETH-style missing-neighbor skips, a V12 hard height gate, and tread support.
// This is an adaptation, not a ROS 1 filter import or parity claim.

#include "reactive_collision.h"

#include <algorithm>
#include <cmath>
#include <limits>
#include <map>
#include <utility>
#include <vector>

namespace reactive_stair {

struct StepScoreParameters {
  double expected_resolution_m = 0.10;
  double critical_height_m = 0.26;  // Local V12 capability; ETH robot config uses 0.12.
  double first_radius_m = 0.15;     // Includes the 8 adjacent 0.10 m PCT cells.
  double second_radius_m = 0.15;
  int critical_cell_number = 4;
  double stair_label_height_m = 0.04;
};

struct StepScore {
  bool known = false;
  double first_pass_height_m = std::numeric_limits<double>::quiet_NaN();
  double score = std::numeric_limits<double>::quiet_NaN();
  int critical_cells = 0;
};

struct StepScoreResult {
  TerrainSnapshot support;
  std::map<Cell2, std::vector<StepScore>> scores;
};

inline bool selectedSurface(const SurfaceCell &surface) {
  return (surface.support == Support::Flat || surface.support == Support::Stair) &&
         std::isfinite(surface.elevation_m);
}

// A nearest surface outside the existing step capability is not evidence of
// this floor. Return -1 rather than joining unrelated building levels. Missing
// or ambiguous association in a present cell keeps that local window Unknown.
inline int nearestSurface(const std::vector<SurfaceCell> &surfaces, double target_z,
                          double maximum_layer_distance_m) {
  if (!std::isfinite(target_z) || !std::isfinite(maximum_layer_distance_m) ||
      maximum_layer_distance_m < 0.0) return -1;
  int selected = -1;
  double best = std::numeric_limits<double>::infinity();
  bool ambiguous = false;
  for (size_t index = 0; index < surfaces.size(); ++index) {
    if (!selectedSurface(surfaces[index])) continue;
    const double distance = std::abs(surfaces[index].elevation_m - target_z);
    if (distance + 1e-9 < best) {
      best = distance;
      selected = static_cast<int>(index);
      ambiguous = false;
    } else if (std::abs(distance - best) <= 1e-9) {
      ambiguous = true;
    }
  }
  return ambiguous || best > maximum_layer_distance_m ? -1 : selected;
}

inline std::vector<Cell2> circleOffsets(double radius_m, double resolution_m) {
  std::vector<Cell2> offsets;
  if (!std::isfinite(radius_m) || !std::isfinite(resolution_m) ||
      radius_m < resolution_m || resolution_m <= 0.0) return offsets;
  const int limit = static_cast<int>(std::ceil(radius_m / resolution_m));
  for (int dx = -limit; dx <= limit; ++dx)
    for (int dy = -limit; dy <= limit; ++dy)
      if ((dx * dx + dy * dy) * resolution_m * resolution_m <=
          radius_m * radius_m + 1e-12)
        offsets.push_back({dx, dy});
  return offsets;
}

inline double ethSecondPassScore(double maximum_step_m, int critical_cells,
                                double critical_height_m, int critical_cell_number) {
  if (!std::isfinite(maximum_step_m) || maximum_step_m < 0.0 ||
      critical_cells < 0 || !std::isfinite(critical_height_m) ||
      critical_height_m <= 0.0 || critical_cell_number <= 0)
    return std::numeric_limits<double>::quiet_NaN();
  const double effective_step = std::min(
      maximum_step_m,
      static_cast<double>(critical_cells) / critical_cell_number * maximum_step_m);
  return effective_step < critical_height_m ?
      1.0 - effective_step / critical_height_m : 0.0;
}

// Surface evidence (the pinned /pct_ground_surface cells) only decides whether
// a present navigation neighbour that lacks this level is a possible drop. If
// the evidence cell under that neighbour's centre has an unambiguous surface
// within the step capability, the neighbour is measured ground at that height.
// Evidence never adds or scores a navigation cell.
inline bool evidenceSurfaceHeight(const TerrainSnapshot *evidence, const TerrainSnapshot &input,
                                  const Cell2 &cell, double elevation_m,
                                  double maximum_layer_distance_m, double &height_m) {
  if (!evidence) return false;
  const double x = input.origin_x_m + (static_cast<double>(cell.x) + 0.5) * input.resolution_m;
  const double y = input.origin_y_m + (static_cast<double>(cell.y) + 0.5) * input.resolution_m;
  const double ix = std::floor((x - evidence->origin_x_m) / evidence->resolution_m);
  const double iy = std::floor((y - evidence->origin_y_m) / evidence->resolution_m);
  if (!std::isfinite(ix) || !std::isfinite(iy) ||
      ix < std::numeric_limits<int>::min() || ix > std::numeric_limits<int>::max() ||
      iy < std::numeric_limits<int>::min() || iy > std::numeric_limits<int>::max()) return false;
  const auto found = evidence->cells.find({static_cast<int>(ix), static_cast<int>(iy)});
  if (found == evidence->cells.end()) return false;
  const int nearest = nearestSurface(found->second, elevation_m, maximum_layer_distance_m);
  if (nearest < 0) return false;
  height_m = found->second[nearest].elevation_m;
  return true;
}

inline StepScoreResult precomputeEthStyleStepScores(
    const TerrainSnapshot &input, const StepScoreParameters &parameters = {},
    const TerrainSnapshot *evidence = nullptr) {
  StepScoreResult result;
  result.support = input;
  const bool parameters_valid = valid(input) &&
      std::isfinite(parameters.expected_resolution_m) &&
      std::abs(input.resolution_m - parameters.expected_resolution_m) <= 1e-6 &&
      std::isfinite(parameters.critical_height_m) && parameters.critical_height_m > 0.0 &&
      std::isfinite(parameters.stair_label_height_m) && parameters.stair_label_height_m >= 0.0 &&
      parameters.critical_cell_number > 0;
  const auto first_offsets = circleOffsets(parameters.first_radius_m, input.resolution_m);
  const auto second_offsets = circleOffsets(parameters.second_radius_m, input.resolution_m);
  if (!parameters_valid || first_offsets.size() < 2 || second_offsets.size() < 2) {
    for (auto &entry : result.support.cells)
      for (auto &surface : entry.second) surface.support = Support::Unknown;
    return result;
  }
  // Unusable evidence scores exactly as without evidence.
  const TerrainSnapshot *usable_evidence =
      evidence && valid(*evidence) && evidence->frame == input.frame &&
      std::abs(evidence->resolution_m - input.resolution_m) <= 1e-9 ? evidence : nullptr;

  // ETH pass 1: maximum minus minimum elevation in the first circle.
  // ETH skips missing neighbors. A present multilevel neighbor still needs
  // an unambiguous nearby surface; do not join different building floors.
  // Without one, the neighbour is a possible drop unless the surface evidence
  // shows ground at this level there; that evidence height then counts.
  for (const auto &entry : input.cells) {
    auto &out = result.scores[entry.first];
    out.resize(entry.second.size());
    for (size_t layer = 0; layer < entry.second.size(); ++layer) {
      const auto &surface = entry.second[layer];
      if (!selectedSurface(surface)) continue;
      double minimum = std::numeric_limits<double>::infinity();
      double maximum = -std::numeric_limits<double>::infinity();
      bool complete = true;
      for (const Cell2 &offset : first_offsets) {
        const Cell2 neighbor{entry.first.x + offset.x, entry.first.y + offset.y};
        const auto cell = input.cells.find(neighbor);
        if (cell == input.cells.end()) continue; // ETH skips absent measurements.
        const int nearest = nearestSurface(cell->second, surface.elevation_m, parameters.critical_height_m);
        double height = 0.0;
        if (nearest >= 0) {
          height = cell->second[nearest].elevation_m;
        } else if (!evidenceSurfaceHeight(usable_evidence, input, neighbor, surface.elevation_m,
                                          parameters.critical_height_m, height)) {
          complete = false;
          break;
        }
        minimum = std::min(minimum, height);
        maximum = std::max(maximum, height);
      }
      if (complete) out[layer].first_pass_height_m = maximum - minimum;
    }
  }

  // ETH pass 2: max local step, count heights strictly above critical, then
  // step=min(max, count/critical_cell_number*max); score=1-step/critical.
  // ETH skips missing/invalid neighboring scores. The queried cell's own
  // first-pass height must stay below the V12 critical value. This avoids
  // ETH's soft score allowing an isolated too-tall rise.
  for (auto &entry : result.support.cells) {
    const auto &original = input.cells.at(entry.first);
    for (size_t layer = 0; layer < entry.second.size(); ++layer) {
      auto &surface = entry.second[layer];
      auto &score = result.scores[entry.first][layer];
      if (!selectedSurface(original[layer]) ||
          !std::isfinite(score.first_pass_height_m)) {
        surface.support = Support::Unknown;
        continue;
      }
      bool complete = true;
      double maximum = 0.0;
      int critical_cells = 0;
      for (const Cell2 &offset : second_offsets) {
        const Cell2 neighbor{entry.first.x + offset.x, entry.first.y + offset.y};
        const auto cell = input.cells.find(neighbor);
        if (cell == input.cells.end()) continue; // ETH skips absent measurements.
        const int nearest = nearestSurface(cell->second, original[layer].elevation_m, parameters.critical_height_m);
        if (nearest < 0) {
          // Measured evidence ground has no score; ETH skips missing scores.
          double evidence_height = 0.0;
          if (evidenceSurfaceHeight(usable_evidence, input, neighbor, original[layer].elevation_m,
                                    parameters.critical_height_m, evidence_height)) continue;
          complete = false;
          break;
        }
        const auto &neighbor_score = result.scores.at(neighbor)[nearest];
        if (!std::isfinite(neighbor_score.first_pass_height_m)) continue;
        maximum = std::max(maximum, neighbor_score.first_pass_height_m);
        if (neighbor_score.first_pass_height_m > parameters.critical_height_m)
          ++critical_cells;
      }
      if (!complete) {
        surface.support = Support::Unknown;
        continue;
      }
      score.known = true;
      score.critical_cells = critical_cells;
      score.score = ethSecondPassScore(maximum, critical_cells,
                                      parameters.critical_height_m,
                                      parameters.critical_cell_number);
      if (score.first_pass_height_m >= parameters.critical_height_m || score.score <= 0.0)
        surface.support = Support::Unsupported;
      else if (score.first_pass_height_m >= parameters.stair_label_height_m)
        surface.support = Support::Stair;
      else
        surface.support = Support::Flat;
    }
  }
  return result;
}

}  // namespace reactive_stair

#endif
