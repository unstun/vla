// New static candidates from original recorded body poses; original request is absent.
#include <lite3_nav2_plugins/pct_route_planner.hpp>
#include <lite3_nav2_plugins/route_policy.hpp>
#include <lite3_nav2_plugins/shared_traversability.hpp>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iomanip>
namespace fs=std::filesystem;
int main(int argc,char **argv) {
 const fs::path input=std::getenv("LATE_INPUT"),out=std::getenv("LATE_OUTPUT");fs::create_directories(out);
 auto field=std::make_shared<reactive_stair::EnvironmentalField>("/work/fixtures/building/environment225.env","10040917858432847476");
 auto support=std::make_shared<reactive_stair::StaticSupportField>("/work/fixtures/building/native.support","1404261889151999461");
 lite3_nav2::PCTRoutePlanner pct("/work/fixtures/building/native_original.pct",.3);pct.setEnvironmentalField(field);pct.setStaticSupport(support);
 geometry_msgs::msg::PoseStamped goal;goal.header.frame_id="world";auto &p=goal.pose.position;auto &q=goal.pose.orientation;
 std::ifstream target(input/"goal_canonical.txt");target>>p.x>>p.y>>p.z>>q.x>>q.y>>q.z>>q.w;
 if(!target)throw std::runtime_error("Missing canonical goal");
 std::ofstream summary(out/"summary.csv"),bad(out/"rejected_poses.csv");
 summary<<std::setprecision(17)<<"input,index,body_ns,observer_clock_ns,x,y,z,layer,grid_y,grid_x,route_poses,samples,rejected,error\n";
 bad<<std::setprecision(17)<<"input,index,body_ns,sample,x,y,z,yaw,verdict\n";
 for(const auto name:{"pre104_controls.txt","starts.txt"}) {
  std::ifstream in(input/name);int index;int64_t stamp,clock,wall;
  geometry_msgs::msg::PoseStamped start;start.header.frame_id="world";auto &s=start.pose.position;auto &r=start.pose.orientation;
  while(in>>index>>stamp>>clock>>wall>>s.x>>s.y>>s.z>>r.x>>r.y>>r.z>>r.w) {
   const Eigen::Vector3d xyz(s.x,s.y,s.z),last(p.x,p.y,p.z);const auto cell=pct.poseToIndex(xyz);
   int rejected=0,n=0,poses_count=0;std::string error;
   try {
    lite3_nav2::RoutePolicy policy;policy.begin("late-candidate",goal,false);
    const auto route=policy.plan(start,goal,[&]{return rclcpp::Time(clock,RCL_ROS_TIME);},[&]{return pct.plan(xyz,last,false);});
    const auto samples=lite3_nav2::sampleReference(route,start.pose);poses_count=route.poses.size();
    for(const auto &pose:samples){double yaw=lite3_nav2::planarYaw(pose);auto v=support->assess(pose.position.x,pose.position.y,pose.position.z,yaw);
     if(v!=reactive_stair::Verdict::Free){++rejected;bad<<name<<','<<index<<','<<stamp<<','<<n<<','<<pose.position.x<<','<<pose.position.y<<','<<pose.position.z<<','<<yaw<<','<<int(v)<<'\n';}++n;}
   }catch(const std::exception&e){error=e.what();}
   summary<<name<<','<<index<<','<<stamp<<','<<clock<<','<<s.x<<','<<s.y<<','<<s.z<<','<<cell.x()<<','<<cell.y()<<','<<cell.z()<<','<<poses_count<<','<<n<<','<<rejected<<','<<error<<'\n';summary.flush();bad.flush();
  }
 }
}
