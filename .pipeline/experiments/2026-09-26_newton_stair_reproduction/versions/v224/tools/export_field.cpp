#include "v84/recording.h"
#include <pcl/io/pcd_io.h>
#include <plan_env/environmental_field.h>
#include <set>

// Offline export uses the production snapshot decoder and terrain classifier.
int main(int argc,char **argv) {
  rclcpp::init(argc,argv);auto node=std::make_shared<rclcpp::Node>("scan_planner_node");
  node->declare_parameter<bool>("grid_map.asynchronous_mapping",false);
  node->set_parameter(rclcpp::Parameter("grid_map.asynchronous_mapping",false));
  GridMap map;initialize_map(map,*node,std::getenv("REPLAY_INPUT"));
  const auto &state=map.mapState();const auto &evidence=map.supportState().reactive_surface_ground_;
  const auto *physical=map.qualifiedPhysicalFloor();if(!physical)throw std::runtime_error("Missing physical floor");
  const double resolution=evidence.resolution_m,target=.15,radius=state.mp_.double_cylinder_radius_;
  const auto scores=reactive_stair::precomputeEthStyleStepScores(evidence,{},&evidence,physical);
  struct Record{int x,y;double z,edge,terrain;};std::vector<Record> records;
  const double range=radius+target+2*resolution;const int reach=int(std::ceil(range/resolution))+1;
  for(const auto &entry:evidence.cells)for(size_t layer=0;layer<entry.second.size();++layer) {
    const auto &surface=entry.second[layer];double margin=range;
    for(int dx=-reach;dx<=reach;++dx)for(int dy=-reach;dy<=reach;++dy) {
      const double gap=std::hypot(std::max(0,std::abs(dx)-1)*resolution,std::max(0,std::abs(dy)-1)*resolution);
      if(gap>=margin)continue;
      if(reactive_stair::physicalFloorDrop(*physical,evidence,{entry.first.x+dx,entry.first.y+dy},surface.elevation_m,.26))margin=gap;
    }
    const auto &score=scores.scores.at(entry.first)[layer];
    records.push_back({entry.first.x,entry.first.y,surface.elevation_m,margin,score.known&&std::isfinite(score.score)?std::clamp(1.-score.score,0.,1.):1.});
  }
  pcl::PointCloud<pcl::PointXYZ> points;
  if(pcl::io::loadPCDFile(std::getenv("STATIC_PCD"),points)!=0)throw std::runtime_error("Static PCD unavailable");
  const double voxel=.05;std::map<std::tuple<int,int,int>,std::pair<double,double>> solid;
  size_t terrain=0;
  for(const auto &p:points) {
    if(!std::isfinite(p.x)||!std::isfinite(p.y)||!std::isfinite(p.z))throw std::runtime_error("Nonfinite static point");
    if(map.reactiveTerrainReturn(Eigen::Vector3d(p.x,p.y,p.z))){++terrain;continue;}
    double associated=-1e100;reactive_stair::Cell2 cell;
    if(reactive_stair::physicalFloorIndex(*physical,p.x,p.y,cell)) {
      const auto found=physical->cells.find(cell);
      if(found!=physical->cells.end()) {
        // Volume depth is set by the collision envelope, not the step-height capability.
        const double depth=state.mp_.obstacles_inflation_z_up+target+std::sqrt(3.)*voxel*.5;
        double nearest=depth;
        for(const auto &floor:found->second) {
          const double delta=floor.elevation_m-p.z;
          if(delta>=0. && delta<nearest) {nearest=delta;associated=floor.elevation_m;}
        }
      }
    }
    const auto key=std::make_tuple(int(std::floor(p.x/voxel)),int(std::floor(p.y/voxel)),int(std::floor(p.z/voxel)));
    const auto inserted=solid.emplace(key,std::make_pair(associated,associated));
    if(!inserted.second) {
      auto &range=inserted.first->second;
      if(associated<-1e90 || range.first<-1e90)range={-1e100,-1e100};
      else {range.first=std::min(range.first,associated);range.second=std::max(range.second,associated);}
    }
  }
  const fs::path output=std::getenv("ENVIRONMENT_OUTPUT");if(fs::exists(output))throw std::runtime_error("Preserve previous export");
  std::ofstream out(output);out<<std::setprecision(17)<<"ENV224B "<<resolution<<' '<<evidence.origin_x_m<<' '<<evidence.origin_y_m<<' '
    <<radius<<' '<<state.mp_.double_cylinder_offset_<<' '<<state.mp_.obstacles_inflation_z_up<<' '
    <<state.mp_.obstacles_inflation_z_down<<' '<<map.supportState().reactive_parameters_.body_clearance_m<<' '<<target<<' '<<voxel*.5<<'\n';
  out<<"F "<<records.size()<<'\n';for(const auto &r:records)out<<r.x<<' '<<r.y<<' '<<r.z<<' '<<r.edge<<' '<<r.terrain<<'\n';
  out<<"O "<<solid.size()<<'\n';for(const auto &p:solid)out<<(std::get<0>(p.first)+.5)*voxel<<' '<<(std::get<1>(p.first)+.5)*voxel<<' '<<(std::get<2>(p.first)+.5)*voxel<<' '<<p.second.first<<' '<<p.second.second<<'\n';
  std::cout<<"ENVIRONMENT_EXPORT floors="<<records.size()<<" pcd_points="<<points.size()<<" classified_terrain="<<terrain<<" solid_voxels="<<solid.size()<<" physics_steps=0\n";
  rclcpp::shutdown();
}
