#include <plan_env/environmental_field.h>
#include <iostream>
#include <fstream>
#include <iomanip>
#include <stdexcept>
int main(int argc,char **argv) {
  if(argc!=5)throw std::runtime_error("field fnv input output required");
  reactive_stair::EnvironmentalField field(argv[1],argv[2]);
  if(field.radius()!=.35||field.offset()!=.18)throw std::runtime_error("Wrong body envelope");
  std::ifstream input(argv[3]);std::ofstream out(argv[4]);
  out<<std::setprecision(17)<<"time_s,x,y,z,yaw,floor_known,extra_edge_margin_m,solid_margin_m\n";
  double t,x,y,z,yaw;size_t count=0;
  while(input>>t>>x>>y>>z>>yaw){const auto a=field.assess({x,y,z},yaw);
    out<<t<<','<<x<<','<<y<<','<<z<<','<<yaw<<','<<a.floor_known<<','<<a.edge_margin<<','<<a.solid_margin<<'\n';++count;}
  if(!input.eof()||!count)throw std::runtime_error("Invalid pose stream");
  std::cout<<"BODY_MARGIN samples="<<count<<" target="<<field.target()<<" radius="<<field.radius()<<std::endl;
}
