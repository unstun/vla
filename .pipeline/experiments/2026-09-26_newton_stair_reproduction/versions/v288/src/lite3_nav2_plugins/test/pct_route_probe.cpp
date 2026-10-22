// Fixed-input regression probe, not a navigation executable.
#include <lite3_nav2_plugins/pct_route_planner.hpp>
#include <fstream>
#include <iomanip>
#include <iostream>

int main(int argc,char **argv)
{
  if(argc!=11) return 64;
  std::ofstream output(argv[10]);output<<std::setprecision(17);
  try {
    lite3_nav2::PCTRoutePlanner planner(argv[1],std::stod(argv[2]),std::stoi(argv[3])!=0);
    const Eigen::Vector3d start(std::stod(argv[4]),std::stod(argv[5]),std::stod(argv[6]));
    const Eigen::Vector3d goal(std::stod(argv[7]),std::stod(argv[8]),std::stod(argv[9]));
    output<<planner.poseToIndex(start).transpose()<<"\n"<<planner.poseToIndex(goal).transpose()<<"\n";
    for(const auto &p:planner.plan(start,goal)) output<<p.transpose()<<"\n";
    return 0;
  } catch(const std::exception &error) {
    output<<"ERROR "<<error.what()<<"\n";std::cerr<<error.what()<<"\n";return 2;
  }
}
