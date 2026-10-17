#include "reactive_collision.h"

#include <cassert>
#include <cmath>
#include <iostream>
#include <limits>

using namespace reactive_stair;

int main() {
  const Parameters parameters;
  CollisionDecision decision(parameters);
  Query query{"world", 10.0, 0.525, 0.525, 0.50, true};
  NonTerrainVoxel clear{Occupancy::Free, "classified_obstacle_source", "world", 10.0};
  assert(decision.decide(query, clear) == Verdict::MissingInput);

  TerrainSnapshot terrain;
  terrain.source_id = "elevation_source";
  terrain.frame = "world";
  terrain.stamp_s = 10.0;
  terrain.resolution_m = 0.05;
  // Every cell of a wide tread gets its own support value, including the
  // interior 0.5 m away from a nosing. No query-time height-jump window.
  for (int x = 0; x < 22; ++x) {
    for (int y = 0; y < 22; ++y) {
      terrain.cells[{x, y}] = {{Support::Stair, 0.10}};
    }
  }
  terrain.cells[{0, 0}] = {{Support::Flat, 0.0}};
  terrain.cells[{2, 2}] = {{Support::Unsupported, 0.0}};
  terrain.cells[{10, 10}].push_back({Support::Stair, 2.10});
  assert(decision.acceptTerrain(terrain));
  TrackSnapshot tracks{"tracker", "world", 10.0, true, {}};
  assert(decision.acceptTracks(tracks));
  assert(decision.decide(query, clear) == Verdict::Free);
  Query stale_terrain = query;
  stale_terrain.stamp_s = 10.51;
  NonTerrainVoxel fresh_obstacle = clear;
  fresh_obstacle.stamp_s = 10.51;
  TrackSnapshot refreshed_tracks = tracks;
  refreshed_tracks.stamp_s = 10.51;
  assert(decision.acceptTracks(refreshed_tracks));
  assert(decision.decide(stale_terrain, fresh_obstacle) == Verdict::StaleInput);
  assert(decision.acceptTracks(tracks));
  Query upper = query;
  upper.z_m = 2.50;
  assert(decision.decide(upper, clear) == Verdict::Free);
  TerrainSnapshot shifted = terrain;
  shifted.origin_x_m = 0.5;
  shifted.origin_y_m = 0.5;
  assert(decision.acceptTerrain(shifted));
  Query shifted_query = query;
  shifted_query.x_m += 0.5;
  shifted_query.y_m += 0.5;
  assert(decision.decide(shifted_query, clear) == Verdict::Free);
  assert(decision.acceptTerrain(terrain));

  Query flat{"world", 10.0, 0.025, 0.025, 0.4, true};
  assert(decision.decide(flat, clear) == Verdict::Free);
  Query unsupported{"world", 10.0, 0.125, 0.125, 0.4, true};
  assert(decision.decide(unsupported, clear) == Verdict::UnsupportedTerrain);

  // A box or thin wall is blocked by classified nonterrain occupancy even on
  // a supported tread. No shape or small-height exception exists here.
  NonTerrainVoxel box{Occupancy::Occupied, "classified_obstacle_source", "world", 10.0};
  assert(decision.decide(query, box) == Verdict::StaticObstacle);
  NonTerrainVoxel thin_wall = box;
  assert(decision.decide(query, thin_wall) == Verdict::StaticObstacle);
  assert(decision.decide(query, {Occupancy::Unknown, "classified_obstacle_source", "world", 10.0}) ==
         Verdict::UnknownObstacle);
  Query outside = query;
  outside.in_map = false;
  assert(decision.decide(outside, clear) == Verdict::OutOfMap);
  Query no_support = query;
  no_support.x_m = 1.125;
  assert(decision.decide(no_support, clear) == Verdict::UnknownSupport);
  Query wrong_height = query;
  wrong_height.z_m = 1.0;
  assert(decision.decide(wrong_height, clear) == Verdict::WrongHeight);

  tracks.tracks = {{"a", 10.0, query.x_m, query.y_m, 0.2},
                   {"b", 10.0, 0.9, 0.9, 0.2}};
  assert(decision.acceptTracks(tracks));
  assert(decision.decide(query, clear) == Verdict::Person);
  assert(decision.decide(query, box) == Verdict::Person);
  Query near_footprint = query;
  near_footprint.x_m -= 0.44;
  assert(decision.decide(near_footprint, clear) == Verdict::Person);
  Query second = query;
  second.x_m = 0.9;
  second.y_m = 0.9;
  assert(decision.decide(second, clear) == Verdict::Person);
  Query stale = query;
  stale.stamp_s = 10.26;
  assert(decision.decide(stale, {Occupancy::Free, "classified_obstacle_source", "world", 10.26}) ==
         Verdict::StaleInput);
  // A complete, fresh empty observation clears the old tracks. An omitted or
  // invalid batch never acts as a clearing observation.
  TrackSnapshot clearing{"tracker", "world", 10.1, true, {}};
  assert(decision.acceptTracks(clearing));
  query.stamp_s = 10.1;
  clear.stamp_s = 10.1;
  assert(decision.decide(query, clear) == Verdict::Free);
  TrackSnapshot incomplete{"tracker", "world", 10.2, false, {}};
  assert(!decision.acceptTracks(incomplete));
  assert(decision.decide(query, clear) == Verdict::MissingInput);
  TrackSnapshot future{"tracker", "world", 10.2, true, {}};
  assert(decision.acceptTracks(future));
  assert(decision.decide(query, clear) == Verdict::StaleInput);
  assert(decision.acceptTracks(clearing));
  TrackSnapshot duplicate{"tracker", "world", 10.1, true,
                          {{"a", 10.1, 0.0, 0.0, 0.2}, {"a", 10.1, 1.0, 1.0, 0.2}}};
  assert(!decision.acceptTracks(duplicate));
  assert(decision.decide(query, clear) == Verdict::MissingInput);

  // The contract has no velocity field. Moving an observed center only
  // changes occupancy after an accepted current snapshot arrives.
  assert(decision.acceptTracks(tracks));
  assert(decision.decide(query, clear) == Verdict::Person);
  tracks.stamp_s = 10.1;
  tracks.tracks = {{"a", 10.1, 0.0, 0.0, 0.2}};
  assert(decision.acceptTracks(tracks));
  assert(decision.decide(query, clear) == Verdict::Free);
  query.frame = "odom";
  assert(decision.decide(query, clear) == Verdict::MissingInput);
  query.frame = "world";
  query.x_m = std::numeric_limits<double>::quiet_NaN();
  assert(decision.decide(query, clear) == Verdict::InvalidQuery);
  query.x_m = 1e100;
  assert(decision.decide(query, clear) == Verdict::InvalidQuery);

  std::cout << "reactive collision contract: PASS\n";
}
