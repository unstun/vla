from pathlib import Path
import shutil,json
B=Path('.pipeline/experiments/2026-09-26_newton_stair_reproduction');N=B/'runtime/scan78_physical_floor_presence_v56';V=B/'versions/v56';H=N/'src/plan_env/include/plan_env'
(H/'physical_floor_presence.h').write_text('''#ifndef P2B_PHYSICAL_FLOOR_PRESENCE_H
#define P2B_PHYSICAL_FLOOR_PRESENCE_H

// A floor's existence is independent of its traversal score. This type has no
// Support label and cannot be passed to CollisionDecision or LiDAR classification.
#include <plan_env/reactive_collision.h>
#include <limits>

namespace reactive_stair {
struct PhysicalFloorCell { double elevation_m; double traversal_cost; };
struct PhysicalFloorSnapshot {
  std::string source_id, frame;
  double stamp_s{0.0}, resolution_m{0.0}, origin_x_m{0.0}, origin_y_m{0.0};
  std::map<Cell2, std::vector<PhysicalFloorCell>> cells;
};
inline bool physicalFloorMetadata(const PhysicalFloorSnapshot &value) {
  return !value.source_id.empty() && !value.frame.empty() && std::isfinite(value.stamp_s) &&
      value.stamp_s > 0.0 && std::isfinite(value.resolution_m) && value.resolution_m > 0.0 &&
      std::isfinite(value.origin_x_m) && std::isfinite(value.origin_y_m) && !value.cells.empty();
}
inline bool validPhysicalFloor(const PhysicalFloorSnapshot &value) {
  if (!physicalFloorMetadata(value)) return false;
  for (const auto &entry : value.cells) {
    if (entry.second.empty()) return false;
    for (const auto &floor : entry.second)
      if (!std::isfinite(floor.elevation_m) || !std::isfinite(floor.traversal_cost) || floor.traversal_cost < 0.0) return false;
  }
  return true;
}
inline bool physicalFloorIndex(const PhysicalFloorSnapshot &value, double x, double y, Cell2 &cell) {
  if (!physicalFloorMetadata(value)) return false;
  const double ix = std::floor((x-value.origin_x_m)/value.resolution_m);
  const double iy = std::floor((y-value.origin_y_m)/value.resolution_m);
  if (!std::isfinite(ix) || !std::isfinite(iy) || ix < std::numeric_limits<int>::min() ||
      ix > std::numeric_limits<int>::max() || iy < std::numeric_limits<int>::min() || iy > std::numeric_limits<int>::max()) return false;
  cell = {static_cast<int>(ix), static_cast<int>(iy)}; return true;
}
// Same nearest-height and ambiguity contract as selected terrain, without a Support label.
inline int nearestPhysicalFloor(const std::vector<PhysicalFloorCell> &floors, double level, double maximum_distance) {
  if (!std::isfinite(level) || !std::isfinite(maximum_distance) || maximum_distance < 0.0) return -1;
  int selected=-1; double best=std::numeric_limits<double>::infinity(); bool ambiguous=false;
  for (size_t i=0;i<floors.size();++i) {
    if (!std::isfinite(floors[i].elevation_m) || !std::isfinite(floors[i].traversal_cost) || floors[i].traversal_cost<0.0) return -1;
    const double distance=std::abs(floors[i].elevation_m-level);
    if (distance+1e-9<best) {best=distance; selected=static_cast<int>(i); ambiguous=false;}
    else if (std::abs(distance-best)<=1e-9) ambiguous=true;
  }
  return ambiguous || best>maximum_distance ? -1 : selected;
}
inline bool physicalFloorHeight(const PhysicalFloorSnapshot &physical, const TerrainSnapshot &input,
                                const Cell2 &cell, double level, double maximum_distance, double &height) {
  Cell2 physical_cell;
  if (!physicalFloorIndex(physical, input.origin_x_m+(cell.x+0.5)*input.resolution_m,
                          input.origin_y_m+(cell.y+0.5)*input.resolution_m, physical_cell)) return false;
  const auto found=physical.cells.find(physical_cell); if(found==physical.cells.end()) return false;
  const int nearest=nearestPhysicalFloor(found->second,level,maximum_distance); if(nearest<0) return false;
  height=found->second[nearest].elevation_m; return true;
}
inline bool physicalFloorDrop(const PhysicalFloorSnapshot &physical, const TerrainSnapshot &input,
                              const Cell2 &cell, double level, double step) {
  Cell2 physical_cell;
  if (!physicalFloorIndex(physical,input.origin_x_m+(cell.x+0.5)*input.resolution_m,
                          input.origin_y_m+(cell.y+0.5)*input.resolution_m,physical_cell)) return true;
  const auto found=physical.cells.find(physical_cell); if(found==physical.cells.end()) return true;
  if (nearestPhysicalFloor(found->second,level,step)>=0) return false;
  // Preserve the existing higher-only solid-wall interpretation. Ambiguous
  // nearby levels and genuinely lower/missing floors remain conservative.
  for (const auto &floor:found->second)
    if (!std::isfinite(floor.elevation_m) || std::abs(floor.elevation_m-level)<=step || floor.elevation_m<level-step) return true;
  return false;
}
} // namespace reactive_stair
#endif
''')
p=H/'evidence_floor_fill.h';s=p.read_text().replace('#include <plan_env/reactive_collision.h>','#include <plan_env/reactive_collision.h>\n#include <plan_env/physical_floor_presence.h>')
s=s.replace('EvidenceFloorFill *summary = nullptr) {','EvidenceFloorFill *summary = nullptr,\n                                               const PhysicalFloorSnapshot *physical = nullptr) {',1)
s=s.replace('  fill.evidence_used = true;','''  fill.evidence_used = true;
  const PhysicalFloorSnapshot *presence = physical && validPhysicalFloor(*physical) &&
      physical->frame == evidence->frame && std::abs(physical->resolution_m-evidence->resolution_m)<=1e-9 ? physical : nullptr;''',1)
s=s.replace('  const auto drop = [&](const Cell2 &cell, double level) {','''  const auto drop = [&](const Cell2 &cell, double level) {
    if (presence) return physicalFloorDrop(*presence, *evidence, cell, level, step_m);''',1);p.write_text(s)
p=H/'eth_step_score_adaptation.h';s=p.read_text().replace('#include "reactive_collision.h"','#include "reactive_collision.h"\n#include "physical_floor_presence.h"')
s=s.replace('double maximum_layer_distance_m, double &height_m) {','double maximum_layer_distance_m, double &height_m,\n                                  const PhysicalFloorSnapshot *physical = nullptr) {',1)
s=s.replace('  if (!evidence) return false;','  if (physical) return physicalFloorHeight(*physical, input, cell, elevation_m, maximum_layer_distance_m, height_m);\n  if (!evidence) return false;',1)
s=s.replace('const TerrainSnapshot *evidence = nullptr) {','const TerrainSnapshot *evidence = nullptr,\n    const PhysicalFloorSnapshot *physical = nullptr) {',1)
marker='  // ETH pass 1:';a=s.index(marker);s=s[:a]+'''  const PhysicalFloorSnapshot *usable_physical =
      physical && validPhysicalFloor(*physical) && physical->frame==input.frame &&
      std::abs(physical->resolution_m-input.resolution_m)<=1e-9 ? physical : nullptr;

'''+s[a:]
s=s.replace('parameters.critical_height_m, height))','parameters.critical_height_m, height, usable_physical))').replace('parameters.critical_height_m, evidence_height))','parameters.critical_height_m, evidence_height, usable_physical))');p.write_text(s)
p=H/'grid_map.h';s=p.read_text().replace('  void reactiveSurfaceGroundCallback','''  void reactivePhysicalFloorCallback(sensor_msgs::msg::PointCloud2::ConstSharedPtr msg);
  reactive_stair::PhysicalFloorSnapshot decodePhysicalFloor(sensor_msgs::msg::PointCloud2::ConstSharedPtr msg) const;
  const reactive_stair::PhysicalFloorSnapshot *qualifiedPhysicalFloor() const;
  bool physicalFloorReady() const;
  void rescorePhysicalFloorChange();
  void reactiveSurfaceGroundCallback''',1)
s=s.replace('  reactive_stair::TerrainSnapshot reactive_surface_ground_;','''  reactive_stair::TerrainSnapshot reactive_surface_ground_;
  reactive_stair::PhysicalFloorSnapshot reactive_physical_floor_;
  std::string reactive_physical_floor_topic_, physical_floor_source_id_, physical_floor_surface_source_id_, physical_floor_navigation_source_id_;
  double physical_floor_origin_x_m_{0.0}, physical_floor_origin_y_m_{0.0}, physical_floor_resolution_m_{0.1};
  bool physical_floor_decoded_valid_{false};
  rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr reactive_physical_floor_sub_;''',1);p.write_text(s)
p=N/'src/plan_env/src/grid_map.cpp';s=p.read_text();marker='  load_parameter(node_, "grid_map.reactive_cloud_max_age"';a=s.index(marker);s=s[:a]+'''  load_parameter(node_, "grid_map.reactive_physical_floor_topic", reactive_physical_floor_topic_, string(""));
  load_parameter(node_, "grid_map.physical_floor_source_id", physical_floor_source_id_, string(""));
  load_parameter(node_, "grid_map.physical_floor_surface_source_id", physical_floor_surface_source_id_, string(""));
  load_parameter(node_, "grid_map.physical_floor_navigation_source_id", physical_floor_navigation_source_id_, string(""));
  load_parameter(node_, "grid_map.physical_floor_origin_x", physical_floor_origin_x_m_, 0.0);
  load_parameter(node_, "grid_map.physical_floor_origin_y", physical_floor_origin_y_m_, 0.0);
  load_parameter(node_, "grid_map.physical_floor_resolution", physical_floor_resolution_m_, 0.1);
  if (!reactive_physical_floor_topic_.empty() && (physical_floor_source_id_.empty() ||
      physical_floor_surface_source_id_.empty() || physical_floor_navigation_source_id_.empty() ||
      !std::isfinite(physical_floor_origin_x_m_) || !std::isfinite(physical_floor_origin_y_m_) ||
      !std::isfinite(physical_floor_resolution_m_) || physical_floor_resolution_m_ != reactive_tomogram_resolution_m_))
    throw std::runtime_error("Configured physical floor requires pinned source and grid metadata");
'''+s[a:]
marker='  reactive_dynamic_sub_';a=s.find(marker)
# Place the static input beside the original selected-surface subscription.
anchor='        std::bind(&GridMap::reactiveSurfaceGroundCallback, this, std::placeholders::_1));'
a=s.index(anchor)+len(anchor);s=s[:a]+'''
  if (!reactive_physical_floor_topic_.empty())
    reactive_physical_floor_sub_ = node_->create_subscription<sensor_msgs::msg::PointCloud2>(
        reactive_physical_floor_topic_, rclcpp::QoS(rclcpp::KeepLast(1)).reliable().transient_local(),
        std::bind(&GridMap::reactivePhysicalFloorCallback, this, std::placeholders::_1));
'''+s[a:];p.write_text(s)
p=H/'scan_reactive_grid_methods.inc';s=p.read_text()
s=s.replace('mp_.double_cylinder_radius_, &fill);','mp_.double_cylinder_radius_, &fill, qualifiedPhysicalFloor());',1)
s=s.replace('precomputeEthStyleStepScores(terrain, {}, &reactive_surface_ground_)','precomputeEthStyleStepScores(terrain, {}, &reactive_surface_ground_, qualifiedPhysicalFloor())')
s=s.replace('reactive_ground_, {}, &reactive_surface_ground_);','reactive_ground_, {}, &reactive_surface_ground_, qualifiedPhysicalFloor());')
s=s.replace('  if (reactive_surface_ground_topic_.empty()) return true;','  if (!physicalFloorReady()) return false;\n  if (reactive_surface_ground_topic_.empty()) return true;',1)
a=s.index('reactive_stair::TerrainSnapshot GridMap::supportGround')
s=s[:a]+'''reactive_stair::PhysicalFloorSnapshot GridMap::decodePhysicalFloor(sensor_msgs::msg::PointCloud2::ConstSharedPtr msg) const {
  if (!msg || msg->header.frame_id!=mp_.frame_id_ || msg->height!=1 || msg->width==0 || msg->is_bigendian ||
      msg->point_step!=16 || msg->fields.size()!=4 || uint64_t(msg->width)*16!=msg->row_step || uint64_t(msg->row_step)!=msg->data.size()) return {};
  uint32_t offset=0;
  for(const char *name:{"x","y","z","intensity"}) {
    bool found=false;for(const auto &field:msg->fields)
      if(field.name==name && field.datatype==sensor_msgs::msg::PointField::FLOAT32 && field.count==1 && field.offset==offset)found=true;
    if(!found)return {};offset+=4;
  }
  uint64_t fingerprint=UINT64_C(14695981039346656037);
  for(uint8_t value:msg->data){fingerprint^=value;fingerprint*=UINT64_C(1099511628211);}
  reactive_stair::PhysicalFloorSnapshot physical;
  physical.source_id="pct_physical_floor/fnv64/"+std::to_string(fingerprint);
  physical.frame=msg->header.frame_id;physical.stamp_s=rclcpp::Time(msg->header.stamp).seconds();
  physical.resolution_m=reactive_tomogram_resolution_m_;
  if(physical.source_id!=physical_floor_source_id_ || !std::isfinite(physical.stamp_s) || physical.stamp_s<=0.0 ||
     !std::isfinite(physical.resolution_m) || physical.resolution_m<=0.0 || !std::isfinite(reactive_tomogram_z_offset_m_))return {};
  pcl::PointCloud<pcl::PointXYZI> points;pcl::fromROSMsg(*msg,points);
  double minimum_x=std::numeric_limits<double>::infinity(), minimum_y=minimum_x;
  for(const auto &point:points.points) {
    if(!std::isfinite(point.x)||!std::isfinite(point.y)||!std::isfinite(point.z)||!std::isfinite(point.intensity)||point.intensity<0.0)return {};
    minimum_x=std::min(minimum_x,double(point.x));minimum_y=std::min(minimum_y,double(point.y));
  }
  physical.origin_x_m=minimum_x-physical.resolution_m/2.0;physical.origin_y_m=minimum_y-physical.resolution_m/2.0;
  if(physical.origin_x_m!=physical_floor_origin_x_m_ || physical.origin_y_m!=physical_floor_origin_y_m_ || physical.resolution_m!=physical_floor_resolution_m_)return {};
  // Metadata is available now; do not rescan all cells inside per-cell lookup helpers.
  for(const auto &point:points.points) {
    const double ix=std::floor((double(point.x)-physical.origin_x_m)/physical.resolution_m);
    const double iy=std::floor((double(point.y)-physical.origin_y_m)/physical.resolution_m);
    if(!std::isfinite(ix)||!std::isfinite(iy)||ix<std::numeric_limits<int>::min()||ix>std::numeric_limits<int>::max()||
       iy<std::numeric_limits<int>::min()||iy>std::numeric_limits<int>::max())return {};
    physical.cells[{int(ix),int(iy)}].push_back({double(point.z)-reactive_tomogram_z_offset_m_,double(point.intensity)});
  }
  return reactive_stair::validPhysicalFloor(physical) ? physical : reactive_stair::PhysicalFloorSnapshot{};
}

const reactive_stair::PhysicalFloorSnapshot *GridMap::qualifiedPhysicalFloor() const {
  const double now=node_->now().seconds();
  if(reactive_physical_floor_topic_.empty() || !physical_floor_decoded_valid_ ||
     reactive_physical_floor_.source_id!=physical_floor_source_id_ ||
     reactive_navigation_ground_.source_id!=physical_floor_navigation_source_id_ ||
     reactive_surface_ground_.source_id!=physical_floor_surface_source_id_ ||
     reactive_navigation_ground_.frame!=mp_.frame_id_ || reactive_surface_ground_.frame!=mp_.frame_id_ ||
     !reactive_stair::fresh(now,reactive_physical_floor_.stamp_s,reactive_parameters_.terrain_max_age_s) ||
     !reactive_stair::fresh(now,reactive_navigation_ground_.stamp_s,reactive_parameters_.terrain_max_age_s) ||
     !reactive_stair::fresh(now,reactive_surface_ground_.stamp_s,reactive_parameters_.terrain_max_age_s))return nullptr;
  return &reactive_physical_floor_;
}

bool GridMap::physicalFloorReady() const {
  return reactive_physical_floor_topic_.empty() || qualifiedPhysicalFloor()!=nullptr;
}

void GridMap::rescorePhysicalFloorChange() {
  reactive_ground_=supportGround(reactive_navigation_ground_);
  auto scored=reactive_stair::precomputeEthStyleStepScores(reactive_ground_, {}, &reactive_surface_ground_, qualifiedPhysicalFloor());
  if(reactive_decision_.acceptTerrain(scored.support)) {
    reactive_terrain_=scored.support;reactive_step_result_=std::move(scored);
  }
}

void GridMap::reactivePhysicalFloorCallback(sensor_msgs::msg::PointCloud2::ConstSharedPtr msg) {
  invalidateRawContributorCache(); // Borrowed terrain pointers must not survive rescoring.
  reactive_physical_floor_=decodePhysicalFloor(msg);
  physical_floor_decoded_valid_=reactive_stair::validPhysicalFloor(reactive_physical_floor_);
  reactive_terrain_hits_.clear();reactive_cloud_ready_=false;reactive_pending_cloud_=false;
  // All retained nonterrain history remains conservative. This input never labels a LiDAR hit.
  rescorePhysicalFloorChange();
}

'''+s[a:];p.write_text(s)
# Asset metadata binds producer, roles and exact source identity; binary stays remote.
metadata=json.loads(Path('.trellis/tasks/10-02-newton-v55-floor-presence/physical_asset_preview.json').read_text());metadata['preview_storage_root']=metadata['absolute_root'];metadata['absolute_root']='/home/sun/vla_exec/vla/'+str(V/'assets');metadata['regeneration']='Run derive_physical_floor.py --output <new remote asset directory>; exact pinned input SHA and producer assertions are required.';(V/'physical_floor_input.json').write_text(json.dumps(metadata,indent=2)+'\n')
p=V/'building_planner.yaml';s=p.read_text();params={'grid_map.reactive_physical_floor_topic':'/pct_physical_floor','grid_map.physical_floor_source_id':metadata['physical_source_id'],'grid_map.physical_floor_surface_source_id':metadata['selected_surface_source_id'],'grid_map.physical_floor_navigation_source_id':metadata['navigation_source_id'],'grid_map.physical_floor_origin_x':metadata['physical_origin_x_m'],'grid_map.physical_floor_origin_y':metadata['physical_origin_y_m'],'grid_map.physical_floor_resolution':metadata['physical_resolution_m']};s=s.replace('  ros__parameters:\n','  ros__parameters:\n'+''.join('    '+k+': '+str(v)+'\n' for k,v in params.items()),1);p.write_text(s)
shutil.copyfile('.trellis/tasks/10-02-newton-v55-floor-presence/derive_physical_floor.py',V/'derive_physical_floor.py')
(V/'PLAN.md').write_text('# v56 physical floor presence\n\nApproved D3, parent qualified frozen v55. Physical-floor existence uses a distinct typed snapshot without Support labels, only for neighbor drop/height association. Exact pinned input/source/grid identities and original static freshness are required. Existing selected <=20 navigation/evidence bytes, central traversal, LiDAR terrain classification, step/drop limits, footprint, PVA/yaw/goal and stop protocol remain unchanged. Missing/mismatched/stale configured physical input rejects admission; absent optional input preserves original behavior. Native safety and sequential corner/reserve gates precede two approved idle-host 90-s Building recordings.\n')
print(json.dumps({'v56_role_asset_points':metadata['files']['physical_floor.f32']['points'],'central_traversal_source_unchanged':True}))
