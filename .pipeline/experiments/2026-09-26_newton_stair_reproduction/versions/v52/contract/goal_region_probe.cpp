#include <plan_env/goal_region_bounds.h>
#include <plan_env/astar_grid_coordinates.h>
#include <random>
#include <iostream>
#include <stdexcept>
using Eigen::Vector3d; using Eigen::Vector3i;
void require(bool ok,const char *name) { if(!ok)throw std::runtime_error(name); }
int main() {
  Vector3i pool(100,100,100), mid(50,50,50), si(20,50,20), ei(70,50,80);
  Vector3d center=Vector3d::Zero(),lo(-2,-2,-2),hi(2,2,.7),goal(1,0,1.5);
  auto possible=[&](Vector3d g,double t,Vector3d l,Vector3d h,bool plane=true) {
    return reactive_stair::goalRegionMayFit(g,t,l,h,center,.05,pool,mid,si,ei,plane); };
  require(!possible(goal,.5,lo,hi),"outside entire endpoint ball must reject");
  require(possible(Vector3d(0,0,.5),.5,lo,hi),"exact connector endpoint in box must retain search");
  require(possible(goal,1,lo,Vector3d(2,2,2)),"new map bounds must reopen search");
  require(possible(goal,1,lo,hi,false),"uncertain 3D lattice must retain search");
  require(possible(goal,0,lo,hi),"ordinary exact search must remain unchanged");
  require(possible(Vector3d::Constant(NAN),1,lo,hi),"nonfinite input must defer to native validation");
  require(possible(goal,1,Vector3d::Constant(-1e12),hi),"extreme coordinate must defer");
  // Independent exhaustive enumeration of the actual native plane and initial node.
  // Every known eligible endpoint must defeat the negative certificate.
  std::mt19937 gen(5070);std::uniform_real_distribution<double> uniform(-2,2);
  size_t eligible=0, rejected=0;
  for(int trial=0;trial<500;++trial) {
    const double step=.05+(trial%4)*.05;
    const Vector3i size(20,20,20),middle(10,10,10),start(2+trial%6,3,2+trial%7),end(15,15,17);
    const Vector3d origin(uniform(gen),uniform(gen),uniform(gen));
    auto point=[&](Vector3i p)->Vector3d{return (p-middle).cast<double>()*step+origin;};
    const Vector3d a=point(start),b=point(end),g=b+Vector3d(.03,-.01,.02);
    const Vector3d lower=origin+Vector3d(-1,-1,-.5),upper=origin+Vector3d(1,1,uniform(gen));
    const double radius=.1+(trial%5)*.17;
    bool exists=false;
    auto inside=[&](Vector3d p){return (p.array()>=lower.array()).all()&&(p.array()<=upper.array()).all();};
    if(inside(g))exists=true;
    if(inside(a)&&(a-g).norm()<=radius)exists=true;
    for(int x=0;x<size.x();++x)for(int y=0;y<size.y();++y) {
      Vector3i node(x,y,start.z());const Eigen::Vector2d delta=b.head<2>()-a.head<2>();
      if(delta.squaredNorm()>=1e-8) {
        double ratio=(point(node).head<2>()-a.head<2>()).dot(delta)/delta.squaredNorm();
        ratio=std::max(0.,std::min(1.,ratio));double z=a.z()+ratio*(b.z()-a.z());
        node.z()=static_cast<int>((z-origin.z())*(1./step)+.5)+middle.z();
      }
      if(node.z()>=0&&node.z()<size.z()&&inside(point(node))&&(point(node)-g).norm()<=radius)exists=true;
    }
    bool may=reactive_stair::goalRegionMayFit(g,radius,lower,upper,origin,step,size,middle,start,end,true);
    if(exists){++eligible;require(may,"false rejection of an original eligible endpoint");}
    if(!may)++rejected;
  }
  require(eligible>20 && rejected>20,"random fixtures must exercise both outcomes");
  std::cout<<"V50_REGION_PASSED randomized=500 eligible="<<eligible<<" rejected="<<rejected<<std::endl;
}
