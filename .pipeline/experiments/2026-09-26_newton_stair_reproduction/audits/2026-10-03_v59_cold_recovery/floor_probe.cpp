// Static floor-admission witness using the unchanged decoder and drop predicate.
#include <plan_env/grid_map.h>
#include <plan_env/evidence_floor_fill.h>
#include <rcl/time.h>
#include <fstream>
#include <iomanip>
sensor_msgs::msg::PointCloud2 ground(const char *path) {
  std::ifstream f(path,std::ios::binary);sensor_msgs::msg::PointCloud2 m;
  m.data=std::vector<uint8_t>(std::istreambuf_iterator<char>(f),{});
  if(m.data.empty())throw std::runtime_error("Missing pinned floor input");
  m.header.frame_id="world";m.header.stamp.sec=1;m.point_step=16;m.height=1;
  m.width=m.data.size()/16;m.row_step=m.data.size();m.is_dense=true;
  for(int i=0;i<4;++i){sensor_msgs::msg::PointField x;x.name=std::vector<std::string>{"x","y","z","intensity"}[i];x.offset=4*i;x.datatype=x.FLOAT32;x.count=1;m.fields.push_back(x);}return m;
}
int main(int argc,char **argv) {
  rclcpp::init(argc,argv);auto node=std::make_shared<rclcpp::Node>("scan_planner_node");
  GridMap map;map.initMap(node.get());map.occ_timer_->cancel();map.vis_timer_->cancel();
  auto *handle=node->get_clock()->get_clock_handle();
  if(rcl_enable_ros_time_override(handle)!=RCL_RET_OK||rcl_set_ros_time_override(handle,1000000000)!=RCL_RET_OK)throw std::runtime_error("clock");
  map.reactiveTomogramCallback(std::make_shared<sensor_msgs::msg::PointCloud2>(ground("/archive/versions/v36/tests/attempt09/v33_stand/converted_inputs/ground.f32")));
  map.reactiveSurfaceGroundCallback(std::make_shared<sensor_msgs::msg::PointCloud2>(ground("/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32")));
  map.reactivePhysicalFloorCallback(std::make_shared<sensor_msgs::msg::PointCloud2>(ground("/archive/versions/v59/assets/physical_floor.f32")));
  const auto *physical=map.qualifiedPhysicalFloor();if(!physical)throw std::runtime_error("physical identity");
  const auto &nav=map.reactive_navigation_ground_, &surface=map.reactive_surface_ground_;
  const Eigen::Vector3d query(7.8930848900711448,-6.3857622930026983,3.3410456462612168);
  const double level=query.z()-map.reactive_parameters_.body_clearance_m;
  reactive_stair::Cell2 target{int(std::floor((query.x()-nav.origin_x_m)/nav.resolution_m)),int(std::floor((query.y()-nav.origin_y_m)/nav.resolution_m))};
  const double step=reactive_stair::StepScoreParameters{}.critical_height_m, radius=map.mp_.double_cylinder_radius_;
  std::cout<<std::setprecision(17)<<"V59_FLOOR target="<<target.x<<","<<target.y<<" level="<<level<<" radius="<<radius<<" step="<<step<<" nav_origin="<<nav.origin_x_m<<","<<nav.origin_y_m<<"\n";
  for(const auto &entry:surface.cells) {
    const double x=surface.origin_x_m+(entry.first.x+.5)*surface.resolution_m;
    const double y=surface.origin_y_m+(entry.first.y+.5)*surface.resolution_m;
    if(int(std::floor((x-nav.origin_x_m)/nav.resolution_m))!=target.x || int(std::floor((y-nav.origin_y_m)/nav.resolution_m))!=target.y)continue;
    for(const auto &candidate:entry.second)if(std::abs(candidate.elevation_m-level)<map.reactive_parameters_.body_height_tolerance_m) {
      std::cout<<"V59_FLOOR candidate="<<candidate.elevation_m<<" evidence_cell="<<entry.first.x<<","<<entry.first.y<<"\n";
      const int reach=int(std::ceil(radius/nav.resolution_m))+1;
      for(int dx=-reach;dx<=reach;++dx)for(int dy=-reach;dy<=reach;++dy) {
        const double gx=std::max(0,std::abs(dx)-1)*nav.resolution_m,gy=std::max(0,std::abs(dy)-1)*nav.resolution_m;
        if(gx*gx+gy*gy>radius*radius+1e-12)continue;
        reactive_stair::Cell2 neighbor{entry.first.x+dx,entry.first.y+dy};
        if(!reactive_stair::physicalFloorDrop(*physical,surface,neighbor,candidate.elevation_m,step))continue;
        const double px=surface.origin_x_m+(neighbor.x+.5)*surface.resolution_m,py=surface.origin_y_m+(neighbor.y+.5)*surface.resolution_m;
        reactive_stair::Cell2 cell;reactive_stair::physicalFloorIndex(*physical,px,py,cell);
        const auto found=physical->cells.find(cell);
        std::cout<<"V59_FLOOR guard_drop offset="<<dx<<","<<dy<<" xy="<<px<<","<<py<<" floors=";
        if(found!=physical->cells.end())for(const auto &f:found->second)std::cout<<"("<<f.elevation_m<<","<<f.traversal_cost<<")";
        std::cout<<"\n";
      }
    }
  }
  rclcpp::shutdown();
}
