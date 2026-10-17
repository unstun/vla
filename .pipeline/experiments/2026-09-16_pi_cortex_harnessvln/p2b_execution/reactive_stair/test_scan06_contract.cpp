#include <plan_env/raw_return_classification.h>

#include <cassert>
#include <iostream>

using namespace reactive_stair;

int main() {
  TerrainSnapshot terrain;
  terrain.source_id = "pct_tomogram/fnv64/test";
  terrain.frame = "world";
  terrain.stamp_s = 10.0;
  terrain.resolution_m = 0.1;
  terrain.origin_x_m = -0.05;
  terrain.origin_y_m = -0.05;
  for (int x = 0; x < 20; ++x)
    for (int y = 0; y < 20; ++y)
      terrain.cells[{x, y}] = {{Support::Stair, 0.15}};
  terrain.cells[{10, 10}].push_back({Support::Stair, 1.15});
  assert(selectedGroundReturn(terrain, 1.0, 1.0, 0.17, 0.05));
  assert(selectedGroundReturn(terrain, 1.0, 1.0, 1.17, 0.05));
  assert(selectedGroundReturn(terrain, 0.85, 0.85, 0.15, 0.05)); // tread interior
  assert(!selectedGroundReturn(terrain, 1.0, 1.0, 0.4, 0.05)); // tall box / wall
  assert(!selectedGroundReturn(terrain, 2.5, 2.5, 0.15, 0.05)); // no support
  assert(mayWaiveRawContributor(true, false, false));
  assert(!mayWaiveRawContributor(true, true, false));
  assert(!mayWaiveRawContributor(true, false, true));
  assert(!mayWaiveRawContributor(false, false, false));

  Parameters parameters;
  parameters.terrain_max_age_s = 86400.0; // versioned static PCT snapshot
  CollisionDecision decision(parameters);
  assert(decision.acceptTerrain(terrain));
  TrackSnapshot tracks{"synthetic_local_test", "world", 10.0, true, {}};
  assert(decision.acceptTracks(tracks));
  Query query{"world", 10.0, 0.85, 0.85, 0.55, true};
  NonTerrainVoxel clear{Occupancy::Free, "scan_lidar_cloud", "world", 10.0};
  assert(decision.decide(query, clear) == Verdict::Free);
  assert(decision.decide(query, {Occupancy::Occupied, "scan_lidar_cloud", "world", 10.0}) ==
         Verdict::StaticObstacle);
  tracks.tracks = {{"person-a", 10.0, 0.85, 0.85, 0.3}};
  assert(decision.acceptTracks(tracks));
  assert(decision.decide(query, clear) == Verdict::Person);
  assert(decision.decide(query, {Occupancy::Occupied, "scan_lidar_cloud", "world", 10.0}) ==
         Verdict::Person);
  tracks.stamp_s = 10.1;
  tracks.tracks = {{"person-a", 10.1, 1.7, 1.7, 0.3}};
  assert(decision.acceptTracks(tracks));
  query.stamp_s = 10.1;
  clear.stamp_s = 10.1;
  assert(decision.decide(query, clear) == Verdict::Free); // current center only
  query.stamp_s = 10.36;
  clear.stamp_s = 10.36;
  assert(decision.decide(query, clear) == Verdict::StaleInput);
  tracks = {"synthetic_local_test", "world", 10.36, true, {}};
  assert(decision.acceptTracks(tracks));
  assert(decision.decide(query, clear) == Verdict::Free); // fresh complete clearing snapshot
  tracks.complete = false;
  assert(!decision.acceptTracks(tracks));
  assert(decision.decide(query, clear) == Verdict::MissingInput);
  std::cout << "scan06 pure collision and raw-return contract: PASS\n";
}
