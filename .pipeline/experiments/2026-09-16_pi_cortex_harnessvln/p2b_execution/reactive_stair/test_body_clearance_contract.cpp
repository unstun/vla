#include <plan_env/reactive_collision.h>
#include <cassert>
#include <iostream>
using namespace reactive_stair;

int main() {
  TerrainSnapshot terrain;
  terrain.source_id = "walk_v1_pinned_pct";
  terrain.frame = "world"; terrain.stamp_s = 1.0; terrain.resolution_m = 0.1;
  terrain.cells[{0, 0}].push_back({Support::Stair, 0.05804443359375});
  TrackSnapshot tracks;
  tracks.source_id = "current_sensor_observation"; tracks.frame = "world";
  tracks.stamp_s = 1.0; tracks.complete = true;
  // Actual settled body height in the failed walk_v1 at this supported tread.
  Query query{"world", 1.0, 0.05, 0.05, 0.3545878231525421, true};
  NonTerrainVoxel free{Occupancy::Free, "actual_lidar", "world", 1.0};
  Parameters old;
  old.body_clearance_m = 0.0;  // Frozen planner.yaml route offset was misused.
  CollisionDecision before(old);
  assert(before.acceptTerrain(terrain) && before.acceptTracks(tracks));
  assert(before.decide(query, free) == Verdict::WrongHeight);
  Parameters fixed = old;
  fixed.body_clearance_m = 0.35;  // Separate physical body-reference contract.
  CollisionDecision after(fixed);
  assert(after.acceptTerrain(terrain) && after.acceptTracks(tracks));
  assert(after.decide(query, free) == Verdict::Free);
  NonTerrainVoxel occupied{Occupancy::Occupied, "actual_lidar", "world", 1.0};
  assert(after.decide(query, occupied) == Verdict::StaticObstacle);
  tracks.tracks.push_back({"person", 1.0, 0.05, 0.05, 0.3});
  assert(after.acceptTracks(tracks));
  assert(after.decide(query, free) == Verdict::Person);
  query.stamp_s = 2.0;
  assert(after.decide(query, free) == Verdict::StaleInput);
  std::cout << "old=WrongHeight corrected=Free occupied=blocked person=blocked stale=blocked\n";
}
