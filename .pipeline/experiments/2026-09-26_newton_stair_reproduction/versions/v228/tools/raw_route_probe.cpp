#include "raw_reference.h"
#include <plan_env/environmental_field.h>
#include <lite3_nav2_plugins/route_policy.hpp>
#include <lite3_nav2_plugins/shared_traversability.hpp>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <sstream>
#include <cstdlib>

int main(int argc,char **argv) {
  auto field=std::make_shared<reactive_stair::EnvironmentalField>(std::getenv("ENVIRONMENT_INPUT"),std::getenv("ENVIRONMENT_FNV"));
  void *raw=makePointField(std::getenv("RAW_FIELD"),std::getenv("RAW_FNV"),false);
  for(int arg=1;arg<argc;++arg) {
    std::ifstream input(argv[arg]);std::string line;std::getline(input,line);nav_msgs::msg::Path path;
    while(std::getline(input,line)) {
      std::replace(line.begin(),line.end(),',',' ');std::istringstream stream(line);double x,y,z,yaw;
      if(!(stream>>x>>y>>z>>yaw))throw std::runtime_error("Invalid admitted route CSV");
      geometry_msgs::msg::PoseStamped pose;pose.pose.position.x=x;pose.pose.position.y=y;pose.pose.position.z=z;
      pose.pose.orientation.z=std::sin(yaw*.5);pose.pose.orientation.w=std::cos(yaw*.5);path.poses.push_back(pose);
    }
    if(path.poses.empty())throw std::runtime_error("Missing admitted route");
    auto start=path.poses.front().pose;start.orientation.z=0.;start.orientation.w=1.;
    const auto samples=lite3_nav2::sampleReference(path,start);
    double edge=1e100,solid=1e100,error=0.,optimism=0.,total=0.;Eigen::Vector3d previous;bool first=true;
    for(const auto &pose:samples) {
      const Eigen::Vector3d p(pose.position.x,pose.position.y,pose.position.z);const double yaw=lite3_nav2::planarYaw(pose);
      double exact[4];pointAssessment(raw,p.x(),p.y(),p.z(),yaw,exact);const auto approximate=field->assess(p,yaw);
      edge=std::min(edge,exact[0]);solid=std::min(solid,exact[1]);error=std::max(error,std::abs(approximate.solid_margin-exact[1]));
      optimism=std::max(optimism,approximate.solid_margin-exact[1]);if(!first)total+=(p-previous).norm()*exact[3];previous=p;first=false;
    }
    std::cout<<std::setprecision(17)<<"RAW_ADMITTED_ROUTE file="<<argv[arg]<<" samples="<<samples.size()
      <<" raw_edge_min="<<edge<<" raw_solid_min="<<solid<<" integrated_raw_cost="<<total
      <<" max_solid_abs_error="<<error<<" max_solid_optimism="<<optimism<<'\n';
  }
  freePointField(raw);
}
