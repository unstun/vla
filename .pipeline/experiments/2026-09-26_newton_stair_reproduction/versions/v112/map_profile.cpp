#include "../v84/recording.h"
#include <time.h>
static double cpu_ms(){timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);return t.tv_sec*1000.0+t.tv_nsec/1e6;}
int main(int argc,char **argv) {
  rclcpp::init(argc,argv);rclcpp::Node node("scan_planner_node");GridMap map;
  const fs::path input=std::getenv("V112_INPUT"),output=std::getenv("V112_OUTPUT");
  initialize_map(map,node,input);std::ofstream rows(output);
  rows<<std::setprecision(17);
  std::ifstream list(input/"scans.txt");int index;int64_t stamp;std::string body,sensor,cloud;
  if(std::getenv("V112_SYNTHETIC")) {
    for(int phase=0;phase<14;++phase) {
      for(int k=0;k<200;++k) {
        auto &state=map.mutableMapState();
        Eigen::Vector3i id=state.mp_.map_bound_min_idx_+Eigen::Vector3i((k*37+phase)%state.mp_.map_voxel_num_.x(),
          (k*17+phase*3)%state.mp_.map_voxel_num_.y(),(k*11+phase*7)%state.mp_.map_voxel_num_.z());
        map.applyOccupancyUpdate(id,state.mp_.clamp_max_log_);auto key=std::make_tuple(id.x(),id.y(),id.z());
        state.reactive_terrain_hits_.insert(key);state.reactive_nonterrain_history_.insert(key);
        if(k%3==0)map.applyOccupancyUpdate(id,state.mp_.clamp_min_log_);
      }
      Eigen::Vector3d center;map.indexToPos(map.mapState().mp_.map_origin_idx_,center);
      const Eigen::Vector3d shift=phase==12?Eigen::Vector3d(11,-11,6):Eigen::Vector3d(phase%2?-.31:.29,phase%3?.27:-.26,phase%4?0:.23);
      const auto begin=std::chrono::steady_clock::now();const double cpu=cpu_ms();map.updateSlidingMap(center+shift);
      rows<<"{\"phase\":"<<phase<<",\"wall_ms\":"<<std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-begin).count()
        <<",\"cpu_ms\":"<<cpu_ms()-cpu<<",\"state_sha256\":\""<<map_digest(map)<<"\"}\n";
    }
    rclcpp::shutdown();return 0;
  }
  while(list>>index>>stamp>>body>>sensor>>cloud) {
    RecordedScan s{index,stamp,std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/body)),
      std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/sensor)),
      std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/cloud,false))};
    s.body->header.stamp=s.sensor->header.stamp=s.cloud->header.stamp=rclcpp::Time(stamp,RCL_ROS_TIME);
    set_clock(node,stamp);const auto before=map.planning_profile_.values;
    auto begin=std::chrono::steady_clock::now();double cpu=cpu_ms();
    map.slidingMapFrameCallback(s.body);map.sensorPoseCallback(s.sensor);
    const double pose_ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-begin).count(),pose_cpu=cpu_ms()-cpu;
    begin=std::chrono::steady_clock::now();cpu=cpu_ms();map.cloudCallback(s.cloud);
    const double cloud_ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-begin).count(),cloud_cpu=cpu_ms()-cpu;
    if(!map.mapState().reactive_cloud_ready_)throw std::runtime_error("Recorded cloud not applied");
    rows<<"{\"index\":"<<index<<",\"stamp_ns\":"<<stamp<<",\"pose_ms\":"<<pose_ms<<",\"pose_cpu_ms\":"<<pose_cpu
      <<",\"cloud_ms\":"<<cloud_ms<<",\"cloud_cpu_ms\":"<<cloud_cpu<<",\"profile\":"<<map.planning_profile_.since(before)
      <<",\"state_sha256\":\""<<map_digest(map)<<"\"}\n";
  }
  rclcpp::shutdown();
}
