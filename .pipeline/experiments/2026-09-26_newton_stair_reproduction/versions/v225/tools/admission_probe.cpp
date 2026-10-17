#include "v84/recording.h"
#include <lite3_nav2_plugins/shared_traversability.hpp>
#include <nav2_core/global_planner.hpp>
#include <pluginlib/class_loader.hpp>
#include <thread>
#include <atomic>
#include <chrono>

// Recorded-map integration only: actual plugin, repair loop, route policy and
// service client. The service delegates STATIC_ONLY to the native GridMap.
int main(int argc,char **argv) {
  rclcpp::init(argc,argv);auto node=std::make_shared<rclcpp::Node>("scan_planner_node");
  node->declare_parameter<bool>("grid_map.asynchronous_mapping",false);
  node->set_parameter(rclcpp::Parameter("grid_map.asynchronous_mapping",false));
  GridMap map;initialize_map(map,*node,std::getenv("REPLAY_INPUT"));
  using Service=lite3_nav2_interfaces::srv::CheckTraversability;
  std::atomic<unsigned> requests{0},rejected_samples{0};
  auto service=node->create_service<Service>("/scan/check_traversability",
    [&](const std::shared_ptr<Service::Request> request,std::shared_ptr<Service::Response> reply) {
      if(request->mode!=Service::Request::STATIC_ONLY)throw std::runtime_error("Probe only supports static queries");
      unsigned bad=0;reply->ready=true;reply->map_revision=1;
      for(const auto &p:request->poses) {
        const auto verdict=map.staticTraversability({p.position.x,p.position.y,p.position.z},lite3_nav2::planarYaw(p));
        if(verdict!=reactive_stair::Verdict::Free && bad<8)
          std::cout<<std::setprecision(17)<<"FIELD_ADMISSION_WITNESS request="<<requests+1
            <<" pose="<<p.position.x<<','<<p.position.y<<','<<p.position.z
            <<" yaw="<<lite3_nav2::planarYaw(p)<<" verdict="<<int(verdict)<<std::endl;
        reply->verdicts.push_back(uint8_t(verdict));bad+=verdict!=reactive_stair::Verdict::Free;
      }
      ++requests;rejected_samples+=bad;
      std::cout<<"FIELD_ADMISSION_CHECK request="<<requests<<" samples="<<request->poses.size()<<" rejected="<<bad<<std::endl;
    });
  rclcpp::executors::SingleThreadedExecutor executor;executor.add_node(node);
  std::thread thread([&]{executor.spin();});
  std::ifstream endpoints(std::getenv("ROUTE_ENDPOINTS"));Eigen::Vector3d a,b;
  endpoints>>a.x()>>a.y()>>a.z()>>b.x()>>b.y()>>b.z();
  geometry_msgs::msg::PoseStamped start,goal;start.header.frame_id=goal.header.frame_id="world";
  start.pose.orientation.w=goal.pose.orientation.w=1.;
  start.pose.position.x=a.x();start.pose.position.y=a.y();start.pose.position.z=a.z();
  goal.pose.position.x=b.x();goal.pose.position.y=b.y();goal.pose.position.z=b.z();
  pluginlib::ClassLoader<nav2_core::GlobalPlanner> loader("nav2_core","nav2_core::GlobalPlanner");
  fs::create_directories(std::getenv("PROBE_OUTPUT"));
  for(bool shared:{false,true}) {
    requests=0;rejected_samples=0;
    rclcpp::NodeOptions options;options.use_global_arguments(false);
    auto parent=std::make_shared<rclcpp_lifecycle::LifecycleNode>(shared?"shared_admission":"legacy_admission",options);
    parent->declare_parameter("PCT.map_bundle",std::string(std::getenv("PCT_INPUT")));
    parent->declare_parameter("PCT.shared_traversability",true);
    if(shared) {
      parent->declare_parameter("PCT.environmental_path",std::string(std::getenv("ENVIRONMENT_INPUT")));
      parent->declare_parameter("PCT.environmental_fnv64",std::string(std::getenv("ENVIRONMENT_FNV")));
    }
    auto planner=loader.createSharedInstance("lite3_nav2/PCTPlanner");planner->configure(parent,"PCT",nullptr,nullptr);planner->activate();
    const auto began=std::chrono::steady_clock::now();bool admitted=false;size_t points=0;std::string error;
    try {
      const auto route=planner->createPlan(start,goal);points=route.poses.size();admitted=true;
      for(const auto &p:lite3_nav2::sampleReference(route,start.pose))
        if(map.staticTraversability({p.position.x,p.position.y,p.position.z},lite3_nav2::planarYaw(p))!=reactive_stair::Verdict::Free)
          throw std::runtime_error("Published route failed independent native recheck");
      std::ofstream csv(fs::path(std::getenv("PROBE_OUTPUT"))/(shared?"shared_admitted.csv":"legacy_admitted.csv"));
      csv<<std::setprecision(17)<<"x,y,z,yaw\n";for(const auto &p:route.poses)
        csv<<p.pose.position.x<<','<<p.pose.position.y<<','<<p.pose.position.z<<','<<lite3_nav2::planarYaw(p.pose)<<'\n';
    }catch(const std::exception &e){error=e.what();if(admitted){std::cerr<<error<<std::endl;std::terminate();}}
    std::cout<<"FIELD_ADMISSION shared="<<shared<<" admitted="<<admitted<<" points="<<points<<" requests="<<requests
      <<" rejected_samples="<<rejected_samples<<" seconds="<<std::chrono::duration<double>(std::chrono::steady_clock::now()-began).count()<<" error="<<error<<std::endl;
    planner->deactivate();planner->cleanup();planner.reset();parent.reset();
  }
  executor.cancel();thread.join();rclcpp::shutdown();
}
