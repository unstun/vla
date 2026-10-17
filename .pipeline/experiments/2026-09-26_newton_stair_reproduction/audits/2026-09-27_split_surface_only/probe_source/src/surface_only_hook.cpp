// Diagnostic ELF method replacement, not a production source edit.
#include <plan_env/grid_map.h>
#include <plan_env/raw_return_classification.h>
#include <map>
#include <iostream>
static std::map<const GridMap*, reactive_stair::TerrainSnapshot> originals;
static size_t old_accepts=0, extended_accepts=0, rejects=0;
struct Report {~Report(){std::cout<<"[SURFACE-HOOK] selected="<<old_accepts<<" extra_floor="<<extended_accepts<<" rejected="<<rejects<<std::endl;}} report;
void retainNavigationGround(const GridMap* map){originals[map]=map->reactive_ground_;}
bool GridMap::reactiveTerrainReturn(const Eigen::Vector3d &point) const {
  const auto saved=originals.find(this);
  if(saved==originals.end()) throw std::runtime_error("Missing original ground for diagnostic classifier");
  if(reactive_stair::selectedGroundReturn(saved->second,point.x(),point.y(),point.z(),reactive_terrain_band_m_)){++old_accepts;return true;}
  const auto &t=reactive_ground_;
  if(!point.allFinite()||t.cells.empty()) {++rejects;return false;}
  const reactive_stair::Cell2 key{int(std::floor((point.x()-t.origin_x_m)/t.resolution_m)),int(std::floor((point.y()-t.origin_y_m)/t.resolution_m))};
  auto found=t.cells.find(key);
  if(found!=t.cells.end()) for(const auto &surface:found->second)
    if((surface.support==reactive_stair::Support::Flat||surface.support==reactive_stair::Support::Stair)&&std::abs(point.z()-surface.elevation_m)<=reactive_terrain_band_m_){++extended_accepts;return true;}
  ++rejects;return false;
}
