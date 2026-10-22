// Independently compiled frozen v260 oracle; never a runtime planner component.
#define reactive_stair legacy260
#include <plan_env/static_support.h>
#undef reactive_stair
extern "C" void *legacy_support_create(const char *path,const char *fnv) {
  return new legacy260::StaticSupportField(path,fnv);
}
extern "C" void legacy_support_destroy(void *p) {delete static_cast<legacy260::StaticSupportField*>(p);}
extern "C" int legacy_support_query(void *p,double x,double y,double z,double yaw,double *out) {
  auto &field=*static_cast<legacy260::StaticSupportField*>(p);
  const auto gap=field.gapConstraint(x,y,z,yaw);
  out[0]=gap.blocked;out[1]=gap.margin;
  for(int i=0;i<3;++i)out[2+i]=gap.gradient[i];
  double h=0.;out[5]=field.surfaceHeight(x,y,z-.3,h);out[6]=h;
  return int(field.assess(x,y,z,yaw));
}
