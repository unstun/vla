#include "v84/recording.h"
#include <pluginlib/class_list_macros.hpp>
#undef PLUGINLIB_EXPORT_CLASS
#define PLUGINLIB_EXPORT_CLASS(...)
#include PCT_PLANNER_SOURCE
#undef PLUGINLIB_EXPORT_CLASS
#include <atomic>
#include <thread>

// Diagnostic source-included PCT class; production integration remains the
// separate installed-plugin admission probe. This captures the graph before
// the main thread receives the rejection and rebuilds repair constraints.
int main(int argc,char **argv) {
  rclcpp::init(argc,argv);auto node=std::make_shared<rclcpp::Node>("scan_planner_node");
  node->declare_parameter<bool>("grid_map.asynchronous_mapping",false);
  node->set_parameter(rclcpp::Parameter("grid_map.asynchronous_mapping",false));
  GridMap map;initialize_map(map,*node,std::getenv("REPLAY_INPUT"));
  const auto print_layers=[&](const Eigen::Vector3d &body,double yaw) {
    const auto &raw=map.supportState().reactive_ground_;
    const auto *physical=map.qualifiedPhysicalFloor();
    for(int site:{0,-1,1}) {
      const auto p=(body+site*map.mapState().mp_.double_cylinder_offset_*Eigen::Vector3d(std::cos(yaw),std::sin(yaw),0.)).eval();
      const reactive_stair::Cell2 cell{int(std::floor((p.x()-raw.origin_x_m)/raw.resolution_m)),int(std::floor((p.y()-raw.origin_y_m)/raw.resolution_m))};
      const auto layers=map.terrainCellLayers(cell);
      std::cout<<"HEIGHT_SITE site="<<site<<" xyz="<<p.transpose()<<" nav_origin="<<raw.origin_x_m<<','<<raw.origin_y_m<<" cell="<<cell.x<<','<<cell.y;
      if(layers.raw&&layers.scored)for(size_t k=0;k<layers.raw->size();++k)
        std::cout<<" layer="<<k<<':'<<(*layers.raw)[k].elevation_m<<':'<<int((*layers.scored)[k].support)<<':'<<std::abs(body.z()-.3-(*layers.raw)[k].elevation_m);
      reactive_stair::Cell2 pc;
      if(physical&&reactive_stair::physicalFloorIndex(*physical,p.x(),p.y(),pc)) {
        std::cout<<" physical_cell="<<pc.x<<','<<pc.y;const auto f=physical->cells.find(pc);
        if(f!=physical->cells.end())for(const auto &floor:f->second)std::cout<<" physical_z="<<floor.elevation_m;
      }
      std::cout<<'\n';
    }
    const auto d=map.physicalSupportDiagnostic(body);
    std::cout<<"HEIGHT_ASSOC physical="<<d.physical_floor<<" navigation_present="<<d.navigation_present<<" edge="<<d.edge_blocked<<" floor="<<d.floor_z<<" gap="<<d.square_gap_m<<'\n';
  };
  geometry_msgs::msg::PoseStamped start,goal;start.header.frame_id=goal.header.frame_id="world";
  start.pose.orientation.w=goal.pose.orientation.w=1.;
  std::ifstream endpoints(std::getenv("ROUTE_ENDPOINTS"));endpoints>>start.pose.position.x>>start.pose.position.y>>start.pose.position.z>>goal.pose.position.x>>goal.pose.position.y>>goal.pose.position.z;
  std::atomic<lite3_nav2::PCTPlanner *> active{nullptr};unsigned request_number=0;bool shared=false;
  using Service=lite3_nav2_interfaces::srv::CheckTraversability;
  const fs::path output=std::getenv("PROBE_OUTPUT");fs::create_directories(output);
  auto service=node->create_service<Service>("/scan/check_traversability",[&](const std::shared_ptr<Service::Request> request,std::shared_ptr<Service::Response> reply) {
    ++request_number;reply->ready=true;reply->map_revision=1;std::vector<size_t> bad;
    for(size_t i=0;i<request->poses.size();++i) {
      const auto &p=request->poses[i];const auto verdict=map.staticTraversability({p.position.x,p.position.y,p.position.z},lite3_nav2::planarYaw(p));
      reply->verdicts.push_back(uint8_t(verdict));if(verdict!=reactive_stair::Verdict::Free)bad.push_back(i);
    }
    if(request_number!=3)return;
    auto &pct=*active.load()->planner_;std::vector<Eigen::Vector3d> points{{start.pose.position.x,start.pose.position.y,start.pose.position.z}};
    for(const auto &p:pct.planner_.get_path_finder().GetPathPoints())points.emplace_back((p.y-pct.nx_/2)*pct.resolution_+pct.cx_,(p.x-pct.ny_/2)*pct.resolution_+pct.cy_,p.height+pct.reference_height_);
    lite3_nav2::RoutePolicy trace;const auto path=trace.plan(start,goal,[&]{return node->now();},[&]{return points;});
    const auto samples=lite3_nav2::sampleReference(path,start.pose);
    if(samples!=request->poses)throw std::runtime_error("Final graph reconstruction differs from actual query samples");
    std::ofstream csv(output/(shared?"shared_repaired_graph.csv":"legacy_repaired_graph.csv"));csv<<std::setprecision(17)<<"x,y,z,yaw\n";
    for(const auto &p:path.poses)csv<<p.pose.position.x<<','<<p.pose.position.y<<','<<p.pose.position.z<<','<<lite3_nav2::planarYaw(p.pose)<<'\n';
    size_t sample_index=0;auto previous=start.pose;
    for(size_t segment=0;segment<path.poses.size();++segment) {
      const auto &next=path.poses[segment].pose;const Eigen::Vector3d a(previous.position.x,previous.position.y,previous.position.z),b(next.position.x,next.position.y,next.position.z);
      const double turn=std::abs(std::remainder(lite3_nav2::planarYaw(next)-lite3_nav2::planarYaw(previous),2*M_PI));
      const size_t n=std::max<size_t>(1,size_t(std::ceil(std::max((b-a).norm()/.025,turn/.05))));
      for(size_t j=0;j<n;++j,++sample_index)if(std::find(bad.begin(),bad.end(),sample_index)!=bad.end()) {
        const auto &p=request->poses[sample_index];std::cout<<std::setprecision(17)<<"HEIGHT_ORIGIN shared="<<shared<<" sample="<<sample_index<<" segment="<<segment<<" u="<<double(j)/n<<" from="<<a.transpose()<<" to="<<b.transpose()<<" pose="<<p.position.x<<','<<p.position.y<<','<<p.position.z<<" yaw="<<lite3_nav2::planarYaw(p)<<'\n';
        print_layers({p.position.x,p.position.y,p.position.z},lite3_nav2::planarYaw(p));
      }
      previous=next;
    }
  });
  rclcpp::executors::SingleThreadedExecutor executor;executor.add_node(node);std::thread thread([&]{executor.spin();});
  for(bool mode:{false,true}) {
    shared=mode;request_number=0;rclcpp::NodeOptions options;options.use_global_arguments(false);
    auto parent=std::make_shared<rclcpp_lifecycle::LifecycleNode>(mode?"height_shared":"height_legacy",options);
    parent->declare_parameter("PCT.map_bundle",std::string(std::getenv("PCT_INPUT")));parent->declare_parameter("PCT.shared_traversability",true);
    if(mode){parent->declare_parameter("PCT.environmental_path",std::string(std::getenv("ENVIRONMENT_INPUT")));parent->declare_parameter("PCT.environmental_fnv64",std::string(std::getenv("ENVIRONMENT_FNV")));}
    lite3_nav2::PCTPlanner planner;planner.configure(parent,"PCT",nullptr,nullptr);planner.activate();active=&planner;
    try{planner.createPlan(start,goal);}catch(const std::exception &e){std::cout<<"HEIGHT_RESULT shared="<<mode<<" error="<<e.what()<<std::endl;}
    active=nullptr;planner.deactivate();planner.cleanup();
  }
  executor.cancel();thread.join();rclcpp::shutdown();
}
