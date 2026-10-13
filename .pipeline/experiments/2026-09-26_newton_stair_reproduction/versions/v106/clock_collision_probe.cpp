#include "../v84/recording.h"

int main(int argc, char **argv) {
  rclcpp::init(argc,argv);
  const fs::path input=std::getenv("V106_INPUT"),output=std::getenv("V106_OUTPUT");
  rclcpp::Node node("scan_planner_node");
  GridMap map;initialize_map(map,node,input);
  std::ifstream listing(input/"scans.txt");
  std::ofstream results(output);
  int index;int64_t stamp,later_stamp;std::string body,sensor,cloud,later_body;
  int cases=0,flips=0,aligned_free=0,stale_blocked=0;
  while(listing>>index>>stamp>>body>>sensor>>cloud>>later_stamp>>later_body) {
    RecordedScan scan{index,stamp,
      std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/body)),
      std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/sensor)),
      std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/cloud,false))};
    scan.body->header.stamp=scan.sensor->header.stamp=scan.cloud->header.stamp=rclcpp::Time(stamp,RCL_ROS_TIME);
    apply_scan(map,node,scan);
    auto pose=std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/later_body));
    pose->header.stamp=rclcpp::Time(later_stamp,RCL_ROS_TIME);
    map.slidingMapFrameCallback(pose);
    const auto &p=pose->pose.pose.position;const auto &q=pose->pose.pose.orientation;
    const Eigen::Vector3d point(p.x,p.y,p.z);
    const double body_yaw=std::atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z));
    const std::string before=map_digest(map);
    for(double yaw:{body_yaw,-0.777421452592,-1.163093227593}) {
      set_clock(node,stamp);
      const int behind=map.getInflateOccupancy(point,yaw);
      set_clock(node,later_stamp);
      const int aligned=map.getInflateOccupancy(point,yaw);
      set_clock(node,later_stamp+100000001LL);
      const int stale=map.getInflateOccupancy(point,yaw);
      ++cases;flips+=behind!=0 && aligned==0;aligned_free+=aligned==0;stale_blocked+=stale!=0;
      results<<std::setprecision(17)<<"{\"scan\":"<<index<<",\"cloud_stamp_ns\":"<<stamp
        <<",\"body_stamp_ns\":"<<later_stamp<<",\"yaw\":"<<yaw<<",\"clock_behind_blocked\":"<<behind
        <<",\"clock_aligned_blocked\":"<<aligned<<",\"body_stale_blocked\":"<<stale<<"}\n";
    }
    if(map_digest(map)!=before)throw std::runtime_error("Query comparison changed original map evidence");
  }
  if(!listing.eof() || cases!=60)throw std::runtime_error("Incomplete replay");
  std::cout<<"V106_CLOCK_COLLISION cases="<<cases<<" flips="<<flips<<" aligned_free="<<aligned_free
    <<" stale_blocked="<<stale_blocked<<std::endl;
  rclcpp::shutdown();
  return flips>0 && aligned_free>0 && stale_blocked==cases?0:2;
}
