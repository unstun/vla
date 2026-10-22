#include <plan_env/static_support.h>
#include <plan_env/static_solid.h>
#include <plan_env/support_gap_mask.h>
#include <iostream>
#include <fstream>
#include <iomanip>
#include <cmath>
int main(int argc,char **argv) {
  if(argc!=3)return 2;
  reactive_stair::StaticSupportField support("/work/fixtures/building/native.support","15212154834549674106");
  reactive_stair::StaticSolidField solid(std::getenv("RAW_FIELD"),std::getenv("RAW_FNV"));
  if(support.radius()!=.35||solid.radius()!=.35||support.offset()!=solid.offset())return 3;
  std::ifstream in(argv[1]);std::ofstream out(argv[2]);std::string id;double x,y,z,yaw;
  out<<std::setprecision(17)<<"id,support_verdict,edge_margin,solid_margin\n";
  while(in>>id>>x>>y>>z>>yaw) {
    const auto verdict=support.assess(x,y,z,yaw);double gap=.15;
    if(!support.gapMask())throw std::runtime_error("Missing authoritative support gap field");
    for(double sign:{-1.,1.}) {
      std::array<double,2> gradient;
      gap=std::min(gap,support.gapMask()->clearanceMargin(x+sign*support.offset()*std::cos(yaw),
        y+sign*support.offset()*std::sin(yaw),z-support.bodyClearance(),.15,gradient));
    }
    out<<id<<','<<int(verdict)<<','<<gap<<','<<solid.assess({x,y,z},yaw).margin<<'\n';
  }
  return in.eof()?0:4;
}
