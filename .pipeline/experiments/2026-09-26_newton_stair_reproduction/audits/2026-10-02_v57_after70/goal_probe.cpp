// Offline observer replay. Link the frozen native search and map unchanged.
#include <path_searching/dyn_a_star.h>
#include <rcl/time.h>
#include <rclcpp/serialization.hpp>
#include <fstream>
#include <iomanip>
#include <cstring>
#include <stdexcept>

template<class T> T decode(const std::vector<char>& bytes) {
  rclcpp::SerializedMessage data(bytes.size());auto &raw=data.get_rcl_serialized_message();
  std::memcpy(raw.buffer,bytes.data(),bytes.size());raw.buffer_length=bytes.size();
  T msg;rclcpp::Serialization<T>().deserialize_message(&data,&msg);return msg;
}
sensor_msgs::msg::PointCloud2 ground(const char *path) {
  std::ifstream f(path,std::ios::binary);sensor_msgs::msg::PointCloud2 m;
  m.data=std::vector<uint8_t>(std::istreambuf_iterator<char>(f),{});
  if(m.data.empty())throw std::runtime_error("Missing pinned ground");
  m.header.frame_id="world";m.header.stamp.sec=1;m.point_step=16;m.height=1;
  m.width=m.data.size()/16;m.row_step=m.data.size();m.is_dense=true;
  for(int i=0;i<4;++i){sensor_msgs::msg::PointField x;x.name=std::vector<std::string>{"x","y","z","intensity"}[i];x.offset=4*i;x.datatype=x.FLOAT32;x.count=1;m.fields.push_back(x);}return m;
}
std::string xyz(const Eigen::Vector3d&p) {
  std::ostringstream s;s<<std::setprecision(17)<<"["<<p.x()<<","<<p.y()<<","<<p.z()<<"]";return s.str();
}
int main(int argc,char**argv) {
  const std::string run=argv[1];rclcpp::init(argc,argv);
  auto node=std::make_shared<rclcpp::Node>("scan_planner_node");
  auto map=std::make_shared<GridMap>();map->initMap(node.get());map->occ_timer_->cancel();map->vis_timer_->cancel();
  auto clock=[&](int64_t ns){auto*h=node->get_clock()->get_clock_handle();
    if(rcl_enable_ros_time_override(h)!=RCL_RET_OK||rcl_set_ros_time_override(h,ns)!=RCL_RET_OK)throw std::runtime_error("Clock override failed");};
  clock(1000000000);
  map->reactiveTomogramCallback(std::make_shared<sensor_msgs::msg::PointCloud2>(ground("/archive/versions/v36/tests/attempt09/v33_stand/converted_inputs/ground.f32")));
  map->reactiveSurfaceGroundCallback(std::make_shared<sensor_msgs::msg::PointCloud2>(ground("/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32")));
  map->reactivePhysicalFloorCallback(std::make_shared<sensor_msgs::msg::PointCloud2>(ground("/archive/versions/v57/assets/physical_floor.f32")));
  AStar search;search.initGridMap(map,Eigen::Vector3i(100,100,100));
  search.use_upstream_search_plane=node->declare_parameter<bool>("manager.use_upstream_search_plane",false);
  search.goal_approach_max_iterations=node->declare_parameter<int>("manager.goal_approach_max_iterations",1000);
  const double tolerance=node->declare_parameter<double>("fsm.goal_neighbor_tolerance",.5);
  if(!search.use_upstream_search_plane||search.goal_approach_max_iterations!=50||tolerance!=1.)throw std::runtime_error("Configuration mismatch");
  std::ifstream stream("/attempt/"+run+".bin",std::ios::binary);
  std::ofstream results("/attempt/"+run+"_native.jsonl");results<<std::setprecision(17);
  int cases=0;
  while(true){uint8_t type;int64_t ns;uint32_t size;
    if(!stream.read(reinterpret_cast<char*>(&type),1))break;
    stream.read(reinterpret_cast<char*>(&ns),8);stream.read(reinterpret_cast<char*>(&size),4);
    std::vector<char> bytes(size);stream.read(bytes.data(),size);if(!stream)throw std::runtime_error("Truncated event stream");clock(ns);
    if(type==0)map->slidingMapFrameCallback(std::make_shared<nav_msgs::msg::Odometry>(decode<nav_msgs::msg::Odometry>(bytes)));
    else if(type==1)map->sensorPoseCallback(std::make_shared<nav_msgs::msg::Odometry>(decode<nav_msgs::msg::Odometry>(bytes)));
    else if(type==2)map->cloudCallback(std::make_shared<sensor_msgs::msg::PointCloud2>(decode<sensor_msgs::msg::PointCloud2>(bytes)));
    else if(type==5){uint32_t id;double values[6];std::memcpy(&id,bytes.data(),4);std::memcpy(values,bytes.data()+4,48);++cases;
      const Eigen::Vector3d start(values[0],values[1],values[2]),goal(values[3],values[4],values[5]);
      const double now=ns*1e-9,cloud_age=now-map->reactive_cloud_stamp_s_,body_age=now-map->reactive_body_stamp_s_;
      if(cloud_age<0||cloud_age>.25||body_age<0||body_age>.25||!map->physicalFloorReady())throw std::runtime_error("Probe inputs are not current/qualified");
      for(int repeat=0;repeat<2;++repeat){
        const auto rejected=search.goal_region_rejections;const auto before=map->planning_profile_.values;
        const double cpu=reactive_stair::PlanningProfile::cpuMs();const auto wall=std::chrono::steady_clock::now();
        ASTAR_RET result;
        {GridMap::RawContributorCacheScope cache(*map);result=search.AstarSearch(map->getResolution(),start,goal,true,tolerance);}
        const double wall_ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-wall).count();
        const double cpu_ms=reactive_stair::PlanningProfile::cpuMs()-cpu;
        size_t reached=0,closed=0;double nearest=std::numeric_limits<double>::infinity();
        Eigen::Vector3d lo=Eigen::Vector3d::Constant(1e30),hi=-lo;
        for(int x=0;x<100;++x)for(int y=0;y<100;++y)for(int z=0;z<100;++z){auto*n=search.GridNodeMap_[x][y][z];
          if(n->rounds!=search.rounds_)continue;++reached;closed+=n->state==GridNode::CLOSEDSET;
          const auto p=search.Index2Coord(n->index);nearest=std::min(nearest,(p-goal).norm());lo=lo.cwiseMin(p);hi=hi.cwiseMax(p);}
        Eigen::Vector3i a,b;bool pool=search.Coord2Index(start,a)&&search.Coord2Index(goal,b);
        Eigen::Vector3d lower,upper;const bool bounds=map->bodyCenterBounds(lower,upper);
        const double yaw=std::atan2(goal.y()-start.y(),goal.x()-start.x());
        results<<"{\"case\":"<<id<<",\"repeat\":"<<repeat<<",\"sim_s\":"<<now<<",\"start\":"<<xyz(start)<<",\"goal\":"<<xyz(goal)
          <<",\"pool_valid\":"<<pool<<",\"start_index\":"<<xyz(a.cast<double>())<<",\"goal_index\":"<<(pool?xyz(b.cast<double>()):"null")
          <<",\"return_code\":"<<int(result)<<",\"path_points\":"<<search.getPath().size()<<",\"wall_ms\":"<<wall_ms<<",\"cpu_ms\":"<<cpu_ms
          <<",\"proof_rejections\":"<<(search.goal_region_rejections-rejected)<<",\"reached\":"<<reached<<",\"closed\":"<<closed
          <<",\"nearest_reached_goal_m\":"<<(reached?std::to_string(nearest):"null")<<",\"reached_min\":"<<(reached?xyz(lo):"null")<<",\"reached_max\":"<<(reached?xyz(hi):"null")
          <<",\"bounds\":"<<bounds<<",\"body_lower\":"<<xyz(lower)<<",\"body_upper\":"<<xyz(upper)
          <<",\"goal_occupancy\":"<<map->getInflateOccupancy(goal,yaw)<<",\"cloud_age\":"<<cloud_age<<",\"body_age\":"<<body_age<<"}\n";
        results.flush();
      }
    }
  }
  if(cases!=10)throw std::runtime_error("Missing cases");rclcpp::shutdown();
}
