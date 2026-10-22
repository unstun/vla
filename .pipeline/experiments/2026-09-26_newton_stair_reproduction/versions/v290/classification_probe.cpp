#include "v84/recording.h"
#include <plan_env/raw_return_classification.h>

int main(int argc,char **argv) {
  rclcpp::init(argc,argv);rclcpp::NodeOptions options;
  options.parameter_overrides({rclcpp::Parameter("grid_map.asynchronous_mapping",false)});
  auto node=std::make_shared<rclcpp::Node>("scan_planner_node",options);
  auto map=std::make_shared<GridMap>();initialize_map(*map,*node,"/work/fixtures/building");
  const auto *physical=map->qualifiedPhysicalFloor();
  if(!physical)throw std::runtime_error("Missing qualified physical floor");
  std::ifstream input(std::getenv("CLASSIFICATION_INPUT"));
  std::ofstream output(std::getenv("CLASSIFICATION_OUTPUT"));
  output<<"stamp_s,x,y,z,current_ground,physical_height_match,surface_gap_m,physical_gap_m\n"<<std::setprecision(17);
  const auto gap=[](const auto &terrain,const Eigen::Vector3d &p) {
    const int x=std::floor((p.x()-terrain.origin_x_m)/terrain.resolution_m);
    const int y=std::floor((p.y()-terrain.origin_y_m)/terrain.resolution_m);
    const auto found=terrain.cells.find({x,y});double d=1e9;
    if(found!=terrain.cells.end())for(const auto &s:found->second)if(std::abs(p.z()-s.elevation_m)<std::abs(d))d=p.z()-s.elevation_m;
    return d;
  };
  double stamp;Eigen::Vector3d point;
  while(input>>stamp>>point.x()>>point.y()>>point.z()) {
    output<<stamp<<','<<point.x()<<','<<point.y()<<','<<point.z()<<','<<map->reactiveTerrainReturn(point)<<','
      <<(std::abs(gap(*physical,point))<=map->mapState().reactive_terrain_band_m_)<<','
      <<gap(map->supportState().reactive_surface_ground_,point)<<','<<gap(*physical,point)<<'\n';
  }
  rclcpp::shutdown();return 0;
}
