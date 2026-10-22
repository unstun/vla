// Recorded-input diagnostic only. It never advances the simulator.
#include "v84/recording.h"
#include <path_searching/dyn_a_star.h>

int main(int argc,char **argv) {
  rclcpp::init(argc,argv);
  rclcpp::NodeOptions options;
  options.parameter_overrides({rclcpp::Parameter("grid_map.asynchronous_mapping",false)});
  auto node=std::make_shared<rclcpp::Node>("scan_planner_node",options);
  auto map=std::make_shared<GridMap>();initialize_map(*map,*node,"/work/fixtures/building");
  const fs::path input=std::getenv("CAPTURE_INPUT"),output=std::getenv("CAPTURE_OUTPUT");
  fs::create_directories(output);
  AStar search;search.initGridMap(map,{100,100,100});search.use_upstream_search_plane=true;
  struct Check {int index;Eigen::Vector3d start,goal,query;};
  std::vector<Check> checks;std::ifstream requests(input/"requests.txt");Check c;
  while(requests>>c.index>>c.start.x()>>c.start.y()>>c.start.z()>>c.goal.x()>>c.goal.y()>>c.goal.z()
      >>c.query.x()>>c.query.y()>>c.query.z())checks.push_back(c);
  std::ifstream scans(input/"scans.txt");int index;int64_t stamp;std::string bf,sf,cf;
  std::ofstream summary(output/"search.csv");summary<<"index,start_verdict,target_verdict,result,points,terrain,exact_start,exact_end,wall_s\n";
  std::ofstream contributors(output/"contributors.csv");contributors<<"scan,qx,qy,qz,x,y,z,log_odds,terrain,current_nonterrain,historical_nonterrain\n";
  summary<<std::setprecision(17);contributors<<std::setprecision(17);
  while(scans>>index>>stamp>>bf>>sf>>cf) {
    RecordedScan s{index,stamp,std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/bf)),
      std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/sf)),
      std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/cf,false))};
    s.body->header.stamp=s.sensor->header.stamp=s.cloud->header.stamp=rclcpp::Time(stamp,RCL_ROS_TIME);
    apply_scan(*map,*node,s);
    for(const auto &request:checks)if(request.index==index) {
      const auto begin=std::chrono::steady_clock::now();
      const auto result=search.AstarSearch(map->getResolution(),request.start,request.goal,true);
      const auto path=search.getPath();
      const double elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count();
      const double yaw=std::atan2(request.goal.y()-request.start.y(),request.goal.x()-request.start.x());
      summary<<index<<','<<int(map->liveTraversability(request.start,yaw))<<','<<int(map->liveTraversability(request.goal,yaw))
        <<','<<int(result)<<','<<path.size()<<','<<search.terrain_search_<<','
        <<(!path.empty()&&(path.front()-request.start).norm()<1e-8)<<','
        <<(!path.empty()&&(path.back()-request.goal).norm()<1e-8)<<','<<elapsed<<'\n';summary.flush();
      std::ofstream curve(output/("path_"+std::to_string(index)+".csv"));curve<<"x,y,z\n"<<std::setprecision(17);
      for(const auto &p:path)curve<<p.x()<<','<<p.y()<<','<<p.z()<<'\n';
      if(!map->isInMap(request.query))continue;
      Eigen::Vector3i id;map->posToIndex(request.query,id);
      const auto &state=map->mapState();
      for(const auto &offset:state.md_.inflate_offsets_) {
        const Eigen::Vector3i source=id-offset;
        if(!map->isInMap(source))continue;
        const double odds=state.md_.occupancy_buffer_[map->toAddress(source)];
        if(odds<=state.mp_.min_occupancy_log_)continue;
        Eigen::Vector3d p;map->indexToPos(source,p);
        const auto key=std::make_tuple(source.x(),source.y(),source.z());
        contributors<<index<<','<<request.query.x()<<','<<request.query.y()<<','<<request.query.z()<<','
          <<p.x()<<','<<p.y()<<','<<p.z()<<','<<odds<<','<<state.reactive_terrain_hits_.count(key)<<','
          <<state.reactive_nonterrain_hits_.count(key)<<','<<state.reactive_nonterrain_history_.count(key)<<'\n';
      }
      contributors.flush();
    }
  }
  if(!scans.eof()||checks.empty())throw std::runtime_error("Invalid captured search fixture");
  rclcpp::shutdown();return 0;
}
