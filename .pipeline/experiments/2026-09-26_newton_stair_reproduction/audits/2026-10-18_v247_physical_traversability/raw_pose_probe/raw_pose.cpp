#include "v232/tools/raw_reference.h"
#include <fstream>
#include <iomanip>
#include <stdexcept>
int main(int argc,char **argv) {
  if(argc!=5)throw std::runtime_error("field fnv input output required");
  void *field=makePointField(argv[1],argv[2],false);
  std::ifstream in(argv[3]);std::ofstream out(argv[4]);
  out<<std::setprecision(17)<<"time_s,x,y,z,yaw,raw_edge_margin_m,raw_solid_margin_m\n";
  double t,x,y,z,yaw;size_t count=0;
  while(in>>t>>x>>y>>z>>yaw){double values[4];pointAssessment(field,x,y,z,yaw,values);
    out<<t<<','<<x<<','<<y<<','<<z<<','<<yaw<<','<<values[0]<<','<<values[1]<<'\n';++count;}
  freePointField(field);
  if(!in.eof()||!count)throw std::runtime_error("Invalid pose input");
}
