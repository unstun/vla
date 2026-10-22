// Offline-only pinned v256 oracle, with isolated C++ symbols.
#define StaticSolidField Legacy256SolidField
#include "../v256/src/plan_env/src/static_solid.cpp"
#undef StaticSolidField
extern "C" void *legacy256Create(const char *path,const char *fnv) {
  return new reactive_stair::Legacy256SolidField(path,fnv);
}
extern "C" void legacy256Destroy(void *p) {delete static_cast<reactive_stair::Legacy256SolidField*>(p);}
extern "C" bool legacy256Collides(void *p,double x,double y,double z,double yaw) {
  return static_cast<reactive_stair::Legacy256SolidField*>(p)->collides({x,y,z},yaw);
}
extern "C" bool legacy256Query(void *p,double x,double y,double z,double yaw,double *v) {
  auto &f=*static_cast<reactive_stair::Legacy256SolidField*>(p);
  auto a=f.assess({x,y,z},yaw);v[0]=a.margin;
  for(int i=0;i<4;++i)v[i+1]=a.gradient(i);
  for(int i=0;i<3;++i)v[i+5]=a.witness(i);
  return f.collides({x,y,z},yaw);
}
