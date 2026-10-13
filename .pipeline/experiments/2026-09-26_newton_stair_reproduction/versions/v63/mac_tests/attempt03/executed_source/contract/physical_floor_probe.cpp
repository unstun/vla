#include <plan_env/evidence_floor_fill.h>
#include <plan_env/eth_step_score_adaptation.h>
#include <type_traits>
#include <iostream>
#include <stdexcept>
using namespace reactive_stair;
static_assert(!std::is_convertible<PhysicalFloorSnapshot,TerrainSnapshot>::value,"physical floor has no traversal/obstacle authority");
int main() {
 TerrainSnapshot nav,evidence;nav.source_id="nav";nav.frame="world";nav.stamp_s=1;nav.resolution_m=.1;evidence=nav;evidence.source_id="selected";
 PhysicalFloorSnapshot physical;physical.source_id="presence";physical.frame="world";physical.stamp_s=1;physical.resolution_m=.1;
 for(int x=-6;x<=6;++x)for(int y=-6;y<=6;++y){nav.cells[{x,y}]={{Support::Flat,1}};evidence.cells[{x,y}]={{Support::Flat,1}};physical.cells[{x,y}]={{1,0}};}
 const Cell2 central{0,0},rejected{0,4};nav.cells[central]={{Support::Flat,0}};nav.cells[rejected]={{Support::Flat,0}};evidence.cells[rejected]={{Support::Flat,0}};physical.cells[rejected]={{0,0},{1,50}};
 int checks=0;auto check=[&](bool ok,const char *name){if(!ok)throw std::runtime_error(name);std::cout<<"V56_PHYSICAL_CHECK "<<name<<" PASS\n";++checks;};
 auto has=[&](const TerrainSnapshot &s,Cell2 c,double z){auto it=s.cells.find(c);if(it==s.cells.end())return false;for(auto &l:it->second)if(std::abs(l.elevation_m-z)<1e-9)return true;return false;};
 auto filled=[&](const PhysicalFloorSnapshot *p){return addGuardedEvidenceFloor(nav,&evidence,.12,.26,.35,nullptr,p);};
 auto selected=filled(nullptr);auto corrected=filled(&physical);
 check(!has(selected,central,1),"selected_cost_filter_neighbor_reproduces_false_drop");
 check(has(corrected,central,1),"physical_neighbor_presence_preserves_selected_central_floor");
 check(!has(corrected,rejected,1),"cost_50_physical_central_cell_never_granted_traversal");
 check(!has(evidence,rejected,1),"selected_input_remains_unchanged");
 auto score=precomputeEthStyleStepScores(corrected,{},&evidence,&physical);
 check(nearestSurface(score.support.cells.at(central),1,.12)>=0,"selected_central_score_with_valid_neighbor_presence");
 check(nearestSurface(score.support.cells.at(rejected),1,.12)<0,"physical_cost_50_cell_not_added_to_scored_support");
 double height=0;check(physicalFloorHeight(physical,nav,rejected,1,.26,height)&&height==1,"neighbor_cost_metadata_is_presence_only");
 auto negative=physical;negative.cells[rejected]={{0,0}};check(!has(filled(&negative),central,1),"true_drop_retains_original_guard");
 negative=physical;negative.cells.erase(rejected);check(!has(filled(&negative),central,1),"missing_floor_retains_guard");
 negative=physical;negative.cells[rejected]={{.9,50},{1.1,50}};check(!has(filled(&negative),central,1),"ambiguous_nearest_floor_rejected");
 negative=physical;negative.cells[rejected]={{0,0},{3,50}};check(!has(filled(&negative),central,1),"unrelated_level_does_not_fill_drop");
 negative=physical;negative.frame="other";check(!has(filled(&negative),central,1),"wrong_frame_no_new_grant");
 negative=physical;negative.resolution_m=.2;check(!has(filled(&negative),central,1),"wrong_resolution_no_new_grant");
 negative=physical;negative.cells[rejected]={{NAN,50}};check(!has(filled(&negative),central,1),"malformed_floor_no_new_grant");
 negative=physical;negative.cells[rejected]={{1,-1}};check(!has(filled(&negative),central,1),"invalid_cost_metadata_no_new_grant");
 negative=physical;negative.cells[rejected]={{1.27,50}};check(!physicalFloorHeight(negative,nav,rejected,1,.26,height),"too_tall_step_not_associated");
 // Full collision predicate retains all obstacle/unknown/staleness/bounds gates.
 Parameters params;params.terrain_max_age_s=100;params.robot_radius_m=0;params.body_clearance_m=.3;CollisionDecision decision(params);check(decision.acceptTerrain(score.support),"only_selected_scored_terrain_is_accepted");
 Query q;q.frame="world";q.stamp_s=1.1;q.in_map=true;q.x_m=.05;q.y_m=.05;q.z_m=1.3;NonTerrainVoxel obstacle;obstacle.frame="world";obstacle.source_id="lidar";obstacle.stamp_s=1.1;obstacle.occupancy=Occupancy::Free;
 check(decision.decide(q,obstacle)==Verdict::Free,"qualified_selected_central_floor_supported");
 obstacle.occupancy=Occupancy::Occupied;check(decision.decide(q,obstacle)==Verdict::StaticObstacle,"physical_floor_cannot_waive_static_or_ceiling_obstacle");
 obstacle.occupancy=Occupancy::Unknown;check(decision.decide(q,obstacle)==Verdict::UnknownObstacle,"physical_floor_cannot_waive_unknown_scan");
 obstacle.occupancy=Occupancy::Free;obstacle.stamp_s=.1;check(decision.decide(q,obstacle)==Verdict::StaleInput,"physical_floor_cannot_waive_stale_scan");
 obstacle.stamp_s=1.1;q.in_map=false;check(decision.decide(q,obstacle)==Verdict::OutOfMap,"physical_floor_cannot_waive_map_bounds");
 q.in_map=true;q.y_m=.45;check(decision.decide(q,obstacle)!=Verdict::Free,"cost_rejected_central_query_remains_rejected");
 std::cout<<"V56_PHYSICAL_PASSED checks="<<checks<<"\n";
}
