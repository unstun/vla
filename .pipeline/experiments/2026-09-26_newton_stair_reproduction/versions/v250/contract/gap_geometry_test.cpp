#include <plan_env/support_gap_mask.h>
#include <cassert>
#include <cstdio>
#include <limits>
#include <unistd.h>
int main() {
  const std::string file="/tmp/gap_continuous_"+std::to_string(getpid());
  const std::string bytes="0 0 0\n";uint64_t h=14695981039346656037ULL;
  for(unsigned char c:bytes){h^=c;h*=1099511628211ULL;}
  {std::ofstream out(file);out<<bytes;}
  reactive_stair::SupportGapMask gap(file,std::to_string(h),.35);
  assert(gap.blocks(.399,0.,0.));
  assert(gap.blocks(.4,0.,0.)); // Exact .35 radius contact remains refused.
  assert(!gap.blocks(.401,0.,0.)); // Same target bin; different physical centre.
  assert(!gap.blocks(.299,.399,0.));
  assert(gap.blocks(.297,.297,0.));
  assert(!gap.blocks(.01,.01,.3));
  assert(gap.blocks(std::numeric_limits<double>::quiet_NaN(),0.,0.));
  // Within every target cell, broad-phase binning must equal exact point to
  // the unchanged uncertain source square. Exercise both signs and borders.
  for(int ix=-600;ix<=600;++ix)for(int iy=-600;iy<=600;++iy) {
    const double x=ix*.001,y=iy*.001;
    const double dx=std::max(std::abs(x)-.05,0.),dy=std::max(std::abs(y)-.05,0.);
    assert(gap.blocks(x,y,0.)==(dx*dx+dy*dy<=.35*.35+1e-12));
  }
  std::array<double,2> gradient;
  assert(std::abs(gap.penetrationMargin(.39,0.,0.,gradient)+.01)<1e-12);
  assert(std::abs(gradient[0]-1.)<1e-12&&gradient[1]==0.);
  const double e=1e-5;
  std::array<double,2> ignored;
  assert(std::abs((gap.penetrationMargin(.39+e,0.,0.,ignored)-gap.penetrationMargin(.39-e,0.,0.,ignored))/(2*e)-gradient[0])<1e-8);
  assert(gap.penetrationMargin(.401,0.,0.,gradient)==0.);
  bool denied=false;try{reactive_stair::SupportGapMask bad(file,"0",.35);}catch(...){denied=true;}
  assert(denied);std::remove(file.c_str());
}
