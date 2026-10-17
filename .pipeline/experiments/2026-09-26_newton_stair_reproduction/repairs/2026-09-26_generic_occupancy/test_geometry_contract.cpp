#include <plan_env/reactive_collision.h>
#include <plan_env/raw_return_classification.h>
#include <plan_env/known_lite3_trunk.h>
#include <iostream>
#include <stdexcept>

using namespace reactive_stair;

void require(bool value, const char* message) {
  if (!value) throw std::runtime_error(message);
}

int main() {
  Parameters parameters;
  parameters.body_clearance_m = .3;
  CollisionDecision decision(parameters);
  Query query{"world", 10., .025, .025, .3, true};
  NonTerrainVoxel cloud{Occupancy::Free, "scan_lidar_cloud", "world", 10.};
  require(decision.decide(query, cloud) == Verdict::MissingInput, "missing terrain must block");
  TerrainSnapshot terrain;
  terrain.source_id = "measured_support";
  terrain.frame = "world";
  terrain.stamp_s = 10.;
  terrain.resolution_m = .05;
  terrain.cells[{0, 0}] = {{Support::Flat, 0.}};
  require(decision.acceptTerrain(terrain), "terrain rejected");
  // This is the old failure: a complete geometric query needs no person batch.
  require(decision.decide(query, cloud) == Verdict::Free, "fresh supported free geometry depends on missing person tracks");
  cloud.occupancy = Occupancy::Occupied;
  require(decision.decide(query, cloud) == Verdict::StaticObstacle, "unclassified measured obstacle must block immediately");
  cloud.occupancy = Occupancy::Unknown;
  require(decision.decide(query, cloud) == Verdict::UnknownObstacle, "unknown cannot become free");
  cloud.occupancy = Occupancy::Free;
  cloud.stamp_s = 9.74;
  require(decision.decide(query, cloud) == Verdict::StaleInput, "stale cloud must block");
  cloud.stamp_s = 10.1;
  require(decision.decide(query, cloud) == Verdict::StaleInput, "future cloud must block");
  cloud.stamp_s = 10.;
  cloud.source_id.clear();
  require(decision.decide(query, cloud) == Verdict::MissingInput, "missing cloud provenance must block");
  cloud.source_id = "scan_lidar_cloud";
  query.in_map = false;
  require(decision.decide(query, cloud) == Verdict::OutOfMap, "outside map must block");
  query.in_map = true;
  query.x_m = .125;
  require(decision.decide(query, cloud) == Verdict::UnknownSupport, "unsupported location cannot become free");
  require(!mayWaiveRawContributor(true, true, false), "terrain must not erase current nonterrain");
  require(!mayWaiveRawContributor(true, false, true), "terrain must not erase historical nonterrain");
  require(mayWaiveRawContributor(true, false, false), "positive terrain classification should work");
  const auto inside = [](double x, double y, double z, double stamp = 10.) {
    return knownNavigationFootprintInterior(x, y, z, 10., stamp, .25, .18);
  };
  require(inside(.18, .2, .01), "current navigation footprint blind spot must be initialized");
  require(!inside(.45, 0., .01), "forward unobserved space must remain unknown");
  require(!inside(0., .26, .01), "side unobserved space must remain unknown");
  require(!inside(0., 0., .10), "vertical space outside the body slice must remain unknown");
  require(!inside(0., 0., .01, 9.8), "stale body pose cannot initialize a footprint");
  require(!inside(0., 0., .01, 10.1), "future body pose cannot initialize a footprint");
  require(measuredTrunkQuery(Occupancy::Unknown, false, true) == Occupancy::Free,
          "current unobstructed footprint must be queryable");
  require(measuredTrunkQuery(Occupancy::Unknown, true, true) == Occupancy::Unknown,
          "inflated obstacle must beat footprint initialization");
  require(measuredTrunkQuery(Occupancy::Occupied, false, true) == Occupancy::Occupied,
          "measured occupancy must beat footprint initialization");
  require(measuredTrunkQuery(Occupancy::Unknown, false, false) == Occupancy::Unknown,
          "unknown outside current footprint must remain blocked");
  std::cout << "geometry-only collision contract: PASS\n";
}
