#include "v84/recording.h"
#include <scan_nav2_controller/native_validation.hpp>
#include <sstream>

scan_planner::UniformBspline read_curve(const fs::path &file) {
  std::ifstream in(file);int id,n,m;in>>id>>n>>m;
  if(!in || n<4 || m!=n+4)throw std::runtime_error("Invalid captured controller curve");
  Eigen::MatrixXd controls(3,n);Eigen::VectorXd knots(m);
  for(int i=0;i<n;++i)for(int j=0;j<3;++j)in>>controls(j,i);
  for(int i=0;i<m;++i)in>>knots[i];
  if(!in)throw std::runtime_error("Truncated controller curve");
  scan_planner::UniformBspline result(controls,3,1.);result.setKnot(knots);return result;
}
int main(int argc,char **argv) {
  rclcpp::init(argc,argv);
  const fs::path input=std::getenv("REPLAY_INPUT"),output=std::getenv("REPLAY_OUTPUT");
  std::ifstream cases(input/"maps.txt");std::ofstream out(output/"maps.tsv");
  out<<std::setprecision(17);
  std::string name;size_t total=0;
  while(cases>>name) {
    auto node=std::make_shared<rclcpp::Node>("scan_planner_node");
    node->declare_parameter<bool>("grid_map.asynchronous_mapping",false);
    node->set_parameter(rclcpp::Parameter("grid_map.asynchronous_mapping",false));
    auto control=std::make_shared<rclcpp::Node>("recorded_query_clock");
    GridMap map;initialize_map(map,*node,input);
    const auto directory=input/name;
    std::ifstream scans(directory/"scans.txt");int i;int64_t stamp;std::string body,sensor,cloud;
    size_t applied=0;
    while(scans>>i>>stamp>>body>>sensor>>cloud) {
      RecordedScan r{i,stamp,std::make_shared<nav_msgs::msg::Odometry>(read_pose(directory/body)),
        std::make_shared<nav_msgs::msg::Odometry>(read_pose(directory/sensor)),
        std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(directory/cloud,false))};
      r.body->header.stamp=r.sensor->header.stamp=r.cloud->header.stamp=rclcpp::Time(stamp,RCL_ROS_TIME);
      apply_scan(map,*node,r);++applied;
    }
    if(!scans.eof() || !applied)throw std::runtime_error("Empty/truncated scan prefix");
    const auto original_digest=map_digest(map);const double observation=map.observationStamp();
    map.startAsyncMapping();auto curve=read_curve(directory/"curve.txt");
    std::ifstream queries(directory/"queries.txt");int64_t now,body_time;double phase;std::string pose_file,label;
    while(queries>>now>>body_time>>pose_file>>phase>>label) {
      auto pose=read_pose(directory/pose_file);pose.header.stamp=rclcpp::Time(body_time,RCL_ROS_TIME);
      geometry_msgs::msg::PoseStamped body_pose;body_pose.header=pose.header;body_pose.pose=pose.pose.pose;
      set_clock(*control,now);
      auto proof=scan_nav2_controller::validateNativeCurve(map,control->get_clock(),body_pose,curve,phase);
      if(map_digest(map)!=original_digest)throw std::runtime_error("Controller query changed map");
      out<<name<<"\t"<<label<<"\t"<<applied<<"\t"<<now<<"\t"<<body_time<<"\t"<<observation
         <<"\t"<<proof.clear<<"\t"<<proof.observation_stamp_s<<"\t"<<proof.binding.message
         <<"\t"<<original_digest<<"\n";
      ++total;
    }
    if(!queries.eof())throw std::runtime_error("Truncated query");
    map.stopAsyncMapping();
  }
  if(!cases.eof() || !total)throw std::runtime_error("No map queries");
  std::cout<<"MAP_REPLAY_PASS queries="<<total<<std::endl;rclcpp::shutdown();
}
