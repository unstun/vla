// Read native decoded support snapshots and exact floor-fill drop predicates.
#include "v84/recording.h"
#include <plan_env/evidence_floor_fill.h>
int main(int argc,char **argv) {
  rclcpp::init(argc,argv);auto node=std::make_shared<rclcpp::Node>("scan_planner_node");
  node->declare_parameter<bool>("grid_map.asynchronous_mapping",false);
  node->set_parameter(rclcpp::Parameter("grid_map.asynchronous_mapping",false));
  GridMap map;initialize_map(map,*node,"/audit/input");
  const auto &s=map.supportState();const auto &e=s.reactive_surface_ground_;const auto &n=s.reactive_navigation_ground_;
  const auto *p=map.qualifiedPhysicalFloor();if(!p)throw std::runtime_error("No qualified physical floor");
  const double radius=map.mapState().mp_.double_cylinder_radius_,step=reactive_stair::StepScoreParameters{}.critical_height_m;
  std::cout<<std::setprecision(17)<<"PARAM radius="<<radius<<" step="<<step<<" tolerance="<<s.reactive_parameters_.body_height_tolerance_m<<'\n';
  for(const auto &point:std::vector<Eigen::Vector3d>{{7.86705351,-3.89496040,1.88007748},{7.9422,-3.66529,1.83772}}) {
    reactive_stair::Cell2 target{int(std::floor((point.x()-n.origin_x_m)/n.resolution_m)),int(std::floor((point.y()-n.origin_y_m)/n.resolution_m))};
    std::cout<<"BODY "<<point.transpose()<<" nav_cell="<<target.x<<','<<target.y<<'\n';
    for(const auto &entry:e.cells) {
      int ix,iy;reactive_stair::evidenceFillIndex(e.origin_x_m+(entry.first.x+.5)*e.resolution_m,n.origin_x_m,n.resolution_m,ix);
      reactive_stair::evidenceFillIndex(e.origin_y_m+(entry.first.y+.5)*e.resolution_m,n.origin_y_m,n.resolution_m,iy);
      if(ix!=target.x||iy!=target.y)continue;
      for(const auto &candidate:entry.second) {
        if(std::abs(candidate.elevation_m-(point.z()-.30))>.3)continue;
        std::cout<<"CANDIDATE "<<entry.first.x<<','<<entry.first.y<<" level="<<candidate.elevation_m<<'\n';
        int rejected=0;double closest=1e9;
        const int reach=int(std::ceil(radius/e.resolution_m))+1;
        for(int dx=-reach;dx<=reach;++dx)for(int dy=-reach;dy<=reach;++dy) {
          double gx=std::max(0,std::abs(dx)-1)*e.resolution_m,gy=std::max(0,std::abs(dy)-1)*e.resolution_m;
          if(gx*gx+gy*gy>radius*radius+1e-12)continue;
          reactive_stair::Cell2 cell{entry.first.x+dx,entry.first.y+dy};
          if(!reactive_stair::physicalFloorDrop(*p,e,cell,candidate.elevation_m,step))continue;
          ++rejected;closest=std::min(closest,std::hypot(gx,gy));
          const double x=e.origin_x_m+(cell.x+.5)*e.resolution_m,y=e.origin_y_m+(cell.y+.5)*e.resolution_m;
          reactive_stair::Cell2 pc;reactive_stair::physicalFloorIndex(*p,x,y,pc);
          std::cout<<"DROP xy="<<x<<','<<y<<" square_gap="<<std::hypot(gx,gy)<<" floors=";
          auto f=p->cells.find(pc);if(f!=p->cells.end())for(const auto &v:f->second)std::cout<<v.elevation_m<<':'<<v.traversal_cost<<';';
          std::cout<<'\n';
        }
        std::cout<<"DROP_SUMMARY count="<<rejected<<" closest_square_gap="<<closest<<'\n';
      }
    }
  }
  rclcpp::shutdown();return 0;
}
