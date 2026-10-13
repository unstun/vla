#include "../v84/recording.h"
#include <scan_nav2_controller/native_validation.hpp>
#include <future>

void require(bool condition,const char *message) {if(!condition)throw std::runtime_error(message);}
int main(int argc,char **argv) {
  rclcpp::init(argc,argv);auto node=std::make_shared<rclcpp::Node>("scan_planner_node");
  auto control=std::make_shared<rclcpp::Node>("independent_controller_clock");
  const fs::path input=std::getenv("V114_INPUT");GridMap map;initialize_map(map,*node,input);
  std::ifstream listing(input/"scans.txt");int index;int64_t stamp,later;std::string body,sensor,cloud,later_body;
  nav_msgs::msg::Odometry::SharedPtr last;
  sensor_msgs::msg::PointCloud2::SharedPtr last_cloud;
  nav_msgs::msg::Odometry::SharedPtr last_sensor;
  while(listing>>index>>stamp>>body>>sensor>>cloud>>later>>later_body) {
    RecordedScan scan{index,stamp,std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/body)),
      std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/sensor)),
      std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/cloud,false))};
    scan.body->header.stamp=scan.sensor->header.stamp=scan.cloud->header.stamp=rclcpp::Time(stamp,RCL_ROS_TIME);
    apply_scan(map,*node,scan);last=scan.body;last_cloud=scan.cloud;last_sensor=scan.sensor;
  }
  geometry_msgs::msg::PoseStamped pose;pose.header=last->header;pose.pose=last->pose.pose;
  set_clock(*control,stamp);const auto &p=pose.pose.position;
  std::vector<std::pair<Eigen::Vector3d,double>> points;
  std::vector<int> expected;
  for(double dx:{-0.3,0.0,0.3})for(double dy:{-0.3,0.0,0.3})for(double yaw:{-1.4,0.0,1.4}) {
    points.push_back({Eigen::Vector3d(p.x+dx,p.y+dy,p.z),yaw});
    expected.push_back(map.getInflateOccupancy(points.back().first,yaw));
  }
  const auto digest=map_digest(map);map.startAsyncMapping();auto context=map.async_mapping_;
  auto lease=map.snapshotQuery(control->get_clock(),pose);require(bool(lease),"missing query lease");
  for(size_t i=0;i<points.size();++i)require(lease->view->getInflateOccupancy(points[i].first,points[i].second)==expected[i],"query differs from original native map");
  require(map_digest(*lease->view)==digest && map_digest(map)==digest,"read-only query mutated map");
  auto pointer=map.read_state_;auto revision=lease->view->mapRevision();
  std::promise<void> entered;auto ready=entered.get_future();
  auto publisher=std::async(std::launch::async,[&] {
    entered.set_value();std::lock_guard<std::mutex> lock(context->publication_mutex);return true;
  });ready.wait();const bool pinned=publisher.wait_for(std::chrono::milliseconds(20))==std::future_status::timeout;
  lease.reset();require(publisher.get() && pinned,"query did not pin publication");
  require(!context->stopping && map.read_state_==pointer,"view destruction stopped writer or adopted planner state");
  Eigen::MatrixXd controls(3,4);for(int i=0;i<4;++i)controls.col(i)=Eigen::Vector3d(p.x,p.y,p.z);
  scan_planner::UniformBspline curve(controls,3,1.0);
  auto proof=scan_nav2_controller::validateNativeCurve(map,control->get_clock(),pose,curve,0.0);
  require(proof.clear && rclcpp::Time(proof.stamp).nanoseconds()==stamp && proof.observation_stamp_s==map.observationStamp() && proof.local_map_revision==int64_t(revision),"actual native full curve validation failed");
  Eigen::MatrixXd outside(3,4);for(int i=0;i<4;++i)outside.col(i)=Eigen::Vector3d(p.x+100.0,p.y,p.z);
  scan_planner::UniformBspline blocked(outside,3,1.0);
  require(!scan_nav2_controller::validateNativeCurve(map,control->get_clock(),pose,blocked,0.0).clear,"out-of-map trajectory accepted");
  // Native node clock can be behind; only the controller's actual clock governs this view.
  set_clock(*node,stamp-500000000LL);
  require(scan_nav2_controller::validateNativeCurve(map,control->get_clock(),pose,curve,0.0).clear,"query used other node clock");
  auto bad=pose;bad.header.stamp=rclcpp::Time(stamp+1);require(!map.snapshotQuery(control->get_clock(),bad),"future body accepted");
  bad=pose;bad.header.stamp=rclcpp::Time(stamp-100000001LL);require(!map.snapshotQuery(control->get_clock(),bad),"stale body accepted");
  bad=pose;bad.header.frame_id="wrong";require(!map.snapshotQuery(control->get_clock(),bad),"wrong frame accepted");
  bad=pose;bad.pose.orientation.w=std::numeric_limits<double>::quiet_NaN();require(!map.snapshotQuery(control->get_clock(),bad),"invalid rotation accepted");
  set_clock(*control,stamp+251000000LL);bad=pose;bad.header.stamp=control->now();
  require(!scan_nav2_controller::validateNativeCurve(map,control->get_clock(),bad,curve,0.0).clear,"stale observation renewed by fresh body");
  set_clock(*control,stamp);lease=map.snapshotQuery(control->get_clock(),pose);
  context->failed=true;require(!lease->view->mapperHealthy(),"snapshot ignored writer fault");context->failed=false;lease.reset();
  // Verify the actual mapper still accepts and publishes a subsequent original cloud.
  stamp+=1000000;set_clock(*node,stamp);last->header.stamp=last_sensor->header.stamp=last_cloud->header.stamp=rclcpp::Time(stamp);
  map.slidingMapFrameCallback(last);map.sensorPoseCallback(last_sensor);map.cloudCallback(last_cloud);
  bool progressed=false;
  for(int i=0;i<500;++i) {
    {auto publication=map.beginPublication();progressed=map.mapRevision()>revision;}
    if(progressed)break;std::this_thread::sleep_for(std::chrono::milliseconds(2));
  }
  require(progressed,"query lease prevented subsequent actual writer progress");
  map.stopAsyncMapping();rclcpp::shutdown();
  std::cout<<"V114_QUERY_VIEW_PASS 27_equivalent_queries immutable_map private_clock exact_proof future_stale_frame_quaternion_rejected stale_observation_blocked fault_visible publication_pinned writer_continues"<<std::endl;
}
