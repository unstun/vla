// Compare the retained soft atlas with the unchanged authoritative support view.
#include <plan_env/environmental_field.h>
#include <plan_env/static_support.h>
#include <plan_env/support_gap_mask.h>
#include <iostream>
#include <fstream>
#include <iomanip>
#include <cmath>
int main(int argc,char **argv){
 if(argc!=2)return 2;
 reactive_stair::EnvironmentalField env("/work/fixtures/building/environment225.env","10040917858432847476");
 reactive_stair::StaticSupportField hard("/work/fixtures/building/native.support","15212154834549674106");
 std::ifstream in(argv[1]);std::string id;double x,y,z,yaw;std::cout<<std::setprecision(17);
 while(in>>id>>x>>y>>z>>yaw){
  const Eigen::Vector3d p(x,y,z);const auto combined=env.assess(p,yaw,hard.gapMask()),atlas=env.assess(p,yaw);
  double gap=.15;for(double sign:{-1.,1.}){std::array<double,2> gradient;gap=std::min(gap,hard.gapMask()->clearanceMargin(x+sign*hard.offset()*std::cos(yaw),y+sign*hard.offset()*std::sin(yaw),z-hard.bodyClearance(),.15,gradient));}
  std::cout<<"{\"case_id\":\""<<id<<"\",\"ENV_edge_m\":"<<combined.edge_margin<<",\"atlas_only_edge_m\":"<<atlas.edge_margin<<",\"support_gap_extra_margin_m\":"<<gap<<",\"hard_support_verdict\":"<<int(hard.assess(x,y,z,yaw))<<",\"hard_radius_m\":"<<hard.radius()<<"}\n";
 }
 return in.eof()?0:2;
}
