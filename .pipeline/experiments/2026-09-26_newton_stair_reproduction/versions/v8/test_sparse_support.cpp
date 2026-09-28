#include <plan_env/eth_step_score_adaptation.h>
#include <plan_env/raw_return_classification.h>
#include <iostream>
#include <stdexcept>

using namespace reactive_stair;
void require(bool ok, const char *reason) {
  if (!ok) throw std::runtime_error(reason);
}
TerrainSnapshot grid() {
  TerrainSnapshot t;
  t.source_id="measured_ground_fixture"; t.frame="world";
  t.stamp_s=10.; t.resolution_m=.1;
  for(int x=0;x<11;++x) for(int y=0;y<11;++y)
    t.cells[{x,y}]={{Support::Stair,0.}};
  return t;
}
int main() {
  auto sparse=grid(); sparse.cells.erase({5,5});
  auto scored=precomputeEthStyleStepScores(sparse);
  require(scored.support.cells.at({4,5})[0].support==Support::Flat,
          "missing adjacent cell invalidates measured flat support");
  require(!scored.support.cells.count({5,5}),"absent queried support was fabricated");
  Parameters p; p.body_clearance_m=.3;
  CollisionDecision decision(p); require(decision.acceptTerrain(scored.support),"terrain rejected");
  NonTerrainVoxel free{Occupancy::Free,"measured_cloud","world",10.};
  require(decision.decide({"world",10.,.55,.55,.3,true},free)==Verdict::UnknownSupport,
          "actual unsupported hole was cleared");
  require(decision.decide({"world",10.,.45,.55,.3,true},free)==Verdict::Free,
          "observed sparse-neighbor support is blocked");
  for(bool wall:{false,true}) {
    auto t=grid();
    for(auto &entry:t.cells)
      if(entry.first.x==5 && (wall||entry.first.y==5)) entry.second[0].elevation_m=.5;
    auto result=precomputeEthStyleStepScores(t);
    require(result.support.cells.at({5,5})[0].support==Support::Unknown,
            "over-height box/wall became support");
    require(!selectedGroundReturn(result.support,.55,.55,.5,.05),"box/wall became terrain return");
  }
  auto ambiguous=grid(); ambiguous.cells[{4,5}]={{Support::Stair,-.1},{Support::Stair,.1}};
  require(precomputeEthStyleStepScores(ambiguous).support.cells.at({5,5})[0].support==Support::Unknown,
          "ambiguous floor association cleared");
  auto stairs=grid();
  for(auto &entry:stairs.cells) if(entry.first.x>=5)entry.second[0].elevation_m=.18;
  auto result=precomputeEthStyleStepScores(stairs);
  require(result.support.cells.at({4,5})[0].support==Support::Stair,"supported riser rejected");
  require(result.support.cells.at({8,5})[0].support==Support::Flat,"tread interior rejected");
  require(!mayWaiveRawContributor(true,true,false),"current obstacle cleared by terrain");
  require(!mayWaiveRawContributor(true,false,true),"historical obstacle cleared by terrain");
  free.occupancy=Occupancy::Occupied;
  require(decision.decide({"world",10.,.45,.55,.3,true},free)==Verdict::StaticObstacle,"generic obstacle cleared");
  free.occupancy=Occupancy::Unknown;
  require(decision.decide({"world",10.,.45,.55,.3,true},free)==Verdict::UnknownObstacle,"unknown obstacle cleared");
  free.occupancy=Occupancy::Free; free.stamp_s=9.;
  require(decision.decide({"world",10.,.45,.55,.3,true},free)==Verdict::StaleInput,"stale cloud cleared");
  std::cout<<"sparse support and obstacle negatives: PASS\n";
}
