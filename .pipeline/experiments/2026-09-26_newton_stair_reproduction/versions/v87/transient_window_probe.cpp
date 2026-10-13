#include "../v84/recording.h"

// Synthetic obstacle visible only in the early observations, not asserted to
// have occurred in the recorded trial. Run native probabilistic fusion after
// admission through the actual v87 queue implementation.
int main(int argc,char **argv)
{
  rclcpp::init(argc,argv);
  const fs::path input=std::getenv("V87_INPUT");
  const auto base=read_scans(input).front();
  rclcpp::Node node("scan_planner_node");
  int cases=0;
  for(int last_ms:{9,650}) for(const std::string mode:{"fifo","latest","window"}) {
    GridMap map; initialize_map(map,node,input);
    set_clock(node,base.stamp); map.sensorPoseCallback(base.sensor);
    const Eigen::Vector3d obstacle(1.2,0,1.0),other(0,1.2,1.0);
    const Eigen::Vector3d world=map.mapState().md_.ray_pos_+map.mapState().md_.ray_q_*obstacle;
    if(map.reactiveTerrainReturn(world)) throw std::runtime_error("Obstacle overlaps classified support");
    GridMap buffer; buffer.node_=&node; buffer.async_mapping_=std::make_shared<GridMap::AsyncMapping>();
    const auto context=buffer.async_mapping_;
    context->nav2_window=mode!="fifo";
    context->observation_policy.persistence_s=mode=="latest" ? 0.0 : 0.5;
    std::map<int64_t,RecordedScan> offered;
    for(int i=1;i<=9;++i) {
      RecordedScan scan{i,base.stamp+(i==9 ? last_ms : i)*1000000LL,
        std::make_shared<nav_msgs::msg::Odometry>(*base.body),
        std::make_shared<nav_msgs::msg::Odometry>(*base.sensor),
        std::make_shared<sensor_msgs::msg::PointCloud2>(*base.cloud)};
      scan.body->header.stamp=scan.sensor->header.stamp=scan.cloud->header.stamp=rclcpp::Time(scan.stamp,RCL_ROS_TIME);
      scan.cloud->width=scan.cloud->height=1; scan.cloud->row_step=scan.cloud->point_step;
      scan.cloud->data.resize(scan.cloud->point_step);
      const auto point=i==9 ? other : obstacle;
      const float xyz[]={float(point.x()),float(point.y()),float(point.z())};
      std::memcpy(scan.cloud->data.data(),xyz,sizeof(xyz));
      offered.emplace(scan.stamp,scan);
      set_clock(node,scan.stamp);
      buffer.enqueueMapping({1,scan.stamp,nullptr,scan.cloud});
    }
    for(const auto &input:context->queue) apply_scan(map,node,offered.at(input.stamp_ns));
    const bool occupied=map.getOccupancy(world)==1;
    const bool expected=mode=="fifo" || (mode=="window" && last_ms==9);
    if(occupied!=expected) throw std::runtime_error("Unexpected transient-obstacle result");
    std::cout<<"V87_TRANSIENT {\"mode\":\""<<mode<<"\",\"last_frame_ms\":"<<last_ms
      <<",\"retained\":"<<context->queue.size()<<",\"obstacle_occupied\":"<<(occupied ? "true" : "false")
      <<",\"synthetic_negative\":true}"<<std::endl;
    ++cases;
  }
  std::cout<<"V87_TRANSIENT_CHECKS "<<cases<<std::endl;
  rclcpp::shutdown();
}
