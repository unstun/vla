#define reactive_stair previous_gap
#include "v250/source/src/plan_env/include/plan_env/support_gap_mask.h"
#undef reactive_stair
#include <plan_env/support_gap_mask.h>
#include <array>
#include <cassert>
#include <iostream>
#include <random>
int main(int argc,char **argv) {
  assert(argc==3);
  previous_gap::SupportGapMask previous(argv[1],argv[2],.35);
  reactive_stair::SupportGapMask current(argv[1],argv[2],.35);
  std::ifstream in(argv[1]);std::vector<std::array<double,3>> sources;std::array<double,3> p;
  while(in>>p[0]>>p[1]>>p[2])sources.push_back(p);
  std::mt19937 random(251);std::uniform_real_distribution<double> offset(-1.,1.),height(-.3,.3);
  int mismatch=0;constexpr int count=40000;
  for(int i=0;i<count;++i){const auto &a=sources[random()%sources.size()];const double x=a[0]+offset(random),y=a[1]+offset(random),z=a[2]+height(random);
    const bool before=previous.blocks(x,y,z),after=current.blocks(x,y,z);
    if(before!=after){++mismatch;if(mismatch<4)std::cerr<<x<<' '<<y<<' '<<z<<' '<<before<<' '<<after<<'\n';}
  }
  std::cout<<"{\"queries\":"<<count<<",\"hard_domain_mismatches\":"<<mismatch<<",\"radius_m\":0.35,\"physics_steps\":0}\n";
  return mismatch?1:0;
}
