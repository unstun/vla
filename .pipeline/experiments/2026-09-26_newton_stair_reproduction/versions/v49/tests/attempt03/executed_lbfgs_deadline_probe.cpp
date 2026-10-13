#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <stdexcept>
#include <plan_env/planning_deadline.h>
static int outstanding = 0;
static void *tracked_malloc(size_t bytes) { void *p=std::malloc(bytes); if(p) ++outstanding; return p; }
static void tracked_free(void *p) { if(p) --outstanding; std::free(p); }
#define malloc tracked_malloc
#define free tracked_free
#include <bspline_opt/lbfgs.hpp>
#undef malloc
#undef free
struct Context { int calls=0, abort_at=0; };
static double cost(void *data,const double *x,double *g,int) {
  auto &c=*static_cast<Context*>(data);
  if (++c.calls==c.abort_at) throw scan_planner::PlanningTimeout("objective_or_line_search");
  const double a=x[1]-x[0]*x[0],b=1-x[0];
  g[0]=-400*x[0]*a-2*b;g[1]=200*a;
  return 100*a*a+b*b;
}
int main() {
  for(int repeat=0;repeat<1000;++repeat) for(int abort_at: {1,2,5}) {
    Context c; c.abort_at=abort_at; double x[2]={-1.2,1},f=0;
    auto settings=lbfgs::lbfgs_parameter_t{};lbfgs::lbfgs_load_default_parameters(&settings);
    bool cancelled=false;
    try { lbfgs::lbfgs_optimize(2,x,&f,cost,nullptr,nullptr,&c,&settings); }
    catch(const scan_planner::PlanningTimeout&) { cancelled=true; }
    if(!cancelled || outstanding!=0) throw std::runtime_error("aborted L-BFGS leaked workspace or missed callback");
  }
  Context c;double x[2]={-1.2,1},f=0;
  lbfgs::lbfgs_optimize(2,x,&f,cost,nullptr,nullptr,&c,nullptr);
  if(outstanding!=0 || f>1e-6) throw std::runtime_error("normal optimizer cleanup or convergence changed");
  std::puts("V49_LBFGS_PASSED cancellation_cases=3000 outstanding=0");
}
