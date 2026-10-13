#include <plan_env/support_gap_mask.h>
#include <array>
#include <iostream>
int main(int argc,char**argv) {
  if(argc!=6)throw std::runtime_error("mask hash radius points output required");
  reactive_stair::SupportGapMask mask(argv[1],argv[2],std::stod(argv[3]));
  std::ifstream input(argv[4],std::ios::binary);std::ofstream output(argv[5],std::ios::binary);
  if(!input||!output)throw std::runtime_error("missing IO");
  std::array<double,3> p;
  while(input.read(reinterpret_cast<char*>(p.data()),sizeof(p))) {
    char blocked=mask.blocks(p[0],p[1],p[2]);output.write(&blocked,1);
  }
  if(!input.eof()||input.gcount())throw std::runtime_error("partial point");
}
