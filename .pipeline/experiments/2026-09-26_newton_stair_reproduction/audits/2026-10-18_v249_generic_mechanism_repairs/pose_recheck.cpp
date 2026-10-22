// Evaluate the identical reconstructed rejected poses; do not recreate a route.
#include <plan_env/static_support.h>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <iostream>
int main(int argc,char **argv) {
 if(argc!=3)throw std::runtime_error("Expected input and output CSV paths");
 reactive_stair::StaticSupportField support("/work/fixtures/building/native.support","1404261889151999461");
 std::ifstream input(argv[1]);std::ofstream output(argv[2]);std::string line;
 if(!input||!output)throw std::runtime_error("Cannot open pose files");
 std::getline(input,line);output<<line<<",new_verdict,gap_margin\n"<<std::setprecision(17);
 size_t checked=0,remaining=0;
 while(std::getline(input,line)) {
  std::vector<std::string> fields;std::istringstream row(line);std::string field;
  while(std::getline(row,field,','))fields.push_back(field);
  if(fields.size()!=9)throw std::runtime_error("Invalid reconstructed pose row");
  const double x=std::stod(fields[4]),y=std::stod(fields[5]),z=std::stod(fields[6]),yaw=std::stod(fields[7]);
  auto v=support.assess(x,y,z,yaw);auto gap=support.gapConstraint(x,y,z,yaw);
  output<<line<<','<<int(v)<<','<<gap.margin<<'\n';++checked;remaining+=v!=reactive_stair::Verdict::Free;
 }
 std::cout<<"{\"checked\":"<<checked<<",\"remaining_rejected\":"<<remaining<<",\"physics_steps\":0}\n";
 return remaining?1:0;
}
