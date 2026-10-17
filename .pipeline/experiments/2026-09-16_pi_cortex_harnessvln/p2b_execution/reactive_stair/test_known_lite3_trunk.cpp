#include <plan_env/known_lite3_trunk.h>
#include <cassert>
#include <iostream>
using namespace reactive_stair;

int main() {
  assert(knownLite3TrunkInterior(0.18, 0.049, 0.0, 1.73, 1.73));
  assert(knownLite3TrunkInterior(-0.18, 0.0, 0.05, 1.73, 1.72));
  assert(!knownLite3TrunkInterior(0.251, 0, 0, 1.73, 1.73));
  assert(!knownLite3TrunkInterior(0.18, 0.051, 0, 1.73, 1.73));
  assert(!knownLite3TrunkInterior(0, 0, 0.071, 1.73, 1.73));
  assert(!knownLite3TrunkInterior(0, 0, 0, 1.73, 1.60));
  assert(!knownLite3TrunkInterior(0, 0, 0, 1.73, 1.74));
  assert(measuredTrunkQuery(Occupancy::Unknown, false, true) == Occupancy::Free);
  assert(measuredTrunkQuery(Occupancy::Unknown, true, true) == Occupancy::Unknown);
  assert(measuredTrunkQuery(Occupancy::Unknown, false, false) == Occupancy::Unknown);
  assert(measuredTrunkQuery(Occupancy::Occupied, false, true) == Occupancy::Occupied);
  Parameters p;
  p.body_clearance_m = 0.35;
  CollisionDecision decision(p);
  TerrainSnapshot terrain;
  terrain.source_id = "ground"; terrain.frame = "world";
  terrain.stamp_s = 1.73; terrain.resolution_m = 0.1;
  terrain.cells[{0, 0}].push_back({Support::Flat, 0.0});
  TrackSnapshot tracks{"sensor", "world", 1.73, true, {}};
  assert(decision.acceptTerrain(terrain) && decision.acceptTracks(tracks));
  Query q{"world", 1.73, 0.05, 0.05, 0.35, true};
  NonTerrainVoxel ego{measuredTrunkQuery(Occupancy::Unknown, false, true), "lidar_and_current_ego", "world", 1.73};
  assert(decision.decide(q, ego) == Verdict::Free);
  tracks.tracks.push_back({"person", 1.73, 0.05, 0.05, 0.3});
  assert(decision.acceptTracks(tracks));
  assert(decision.decide(q, ego) == Verdict::Person);
  q.stamp_s = 2.0;
  assert(decision.decide(q, ego) == Verdict::StaleInput);
  std::cout << "current exact trunk known; external unknown, inflated hit, person, stale inputs blocked\n";
}
