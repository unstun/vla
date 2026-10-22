#include <plan_env/environmental_field.h>
#include <plan_env/static_support.h>
#include <plan_env/static_solid.h>
#include <iostream>
#include <fstream>
#include <iomanip>
#include <stdexcept>
int main(int argc,char **argv) {
  if(argc!=9)throw std::runtime_error("environment fnv support fnv input output source_solid fnv required");
  reactive_stair::EnvironmentalField field(argv[1],argv[2]);
  reactive_stair::StaticSupportField hard(argv[3],argv[4]);
  if(field.radius()!=.35||field.offset()!=.18||hard.radius()!=.35||hard.offset()!=.18)throw std::runtime_error("Wrong envelope");
  reactive_stair::StaticSolidField solid(argv[7],argv[8]);
  if(solid.radius()!=.35||solid.offset()!=.18)throw std::runtime_error("Wrong source envelope");
  std::ifstream input(argv[5]);std::ofstream out(argv[6]);
  out<<std::setprecision(17)<<"time_s,x,y,z,yaw,floor_known,extra_edge_margin_m,solid_margin_m,static_support_verdict,static_support_free,native_source_solid_margin_m\n";
  double t,x,y,z,yaw;size_t count=0;
  while(input>>t>>x>>y>>z>>yaw){const auto a=field.assess({x,y,z},yaw,hard.gapMask());const auto v=hard.assess(x,y,z,yaw);
    out<<t<<','<<x<<','<<y<<','<<z<<','<<yaw<<','<<a.floor_known<<','<<a.edge_margin<<','<<a.solid_margin<<','<<int(v)<<','<<(v==reactive_stair::Verdict::Free)<<','<<solid.assess({x,y,z},yaw).margin<<'\n';++count;}
  if(!input.eof()||!count)throw std::runtime_error("Invalid pose stream");
  std::cout<<"BODY_MARGIN samples="<<count<<" radius="<<hard.radius()<<std::endl;
}
