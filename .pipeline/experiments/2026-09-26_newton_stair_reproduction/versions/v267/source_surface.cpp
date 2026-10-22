// Experimental component only; no ROS/planner integration.
#include <boost/geometry.hpp>
#include <boost/geometry/index/rtree.hpp>
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <stdexcept>
#include <vector>

namespace surface {
namespace bg=boost::geometry;
namespace bgi=boost::geometry::index;
using V=std::array<double,3>;
using Poly=std::vector<V>;
using Triangle=std::array<V,3>;
using Point=bg::model::point<double,3,bg::cs::cartesian>;
using Box=bg::model::box<Point>;
using Item=std::pair<Box,size_t>;
using Tree=bgi::rtree<Item,bgi::quadratic<16>>;
constexpr double eps=1e-10, radius=.35, offset=.18, target=.15;
V sub(V a,const V &b){for(int i=0;i<3;++i)a[i]-=b[i];return a;}
V cross(const V &a,const V &b){return {{a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]}};}
double dot(const V &a,const V &b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
Point point(const V &p){return Point(p[0],p[1],p[2]);}
Box bounds(const Poly &p){
  V lo={{1e100,1e100,1e100}},hi={{-1e100,-1e100,-1e100}};
  for(const auto &a:p)for(int j=0;j<3;++j){lo[j]=std::min(lo[j],a[j]);hi[j]=std::max(hi[j],a[j]);}
  return Box(point(lo),point(hi));
}
Poly clip(const Poly &p,const V &n,double d,bool inside=true){
  Poly out;if(p.empty())return out;
  for(size_t i=0;i<p.size();++i){const auto &a=p[i],&b=p[(i+1)%p.size()];
    const double da=dot(n,a)-d,db=dot(n,b)-d;
    const bool ia=inside?da<=0.:da>=0.,ib=inside?db<=0.:db>=0.;
    if(ia)out.push_back(a);
    if(ia!=ib){V q;for(int j=0;j<3;++j)q[j]=a[j]+(b[j]-a[j])*da/(da-db);out.push_back(q);}
  }return out;
}
double area(const Poly &p){
  if(p.size()<3)return 0.;double a=0.;
  for(size_t i=1;i+1<p.size();++i)a+=(p[i][0]-p[0][0])*(p[i+1][1]-p[0][1])-(p[i][1]-p[0][1])*(p[i+1][0]-p[0][0]);
  return std::abs(a)*.5;
}
struct Halfspace {V n;double d;};
struct Cap {Box box;std::vector<Halfspace> planes;};
std::vector<Poly> remove(const Poly &poly,const Cap &cap){
  Poly pending=poly;std::vector<Poly> out;
  for(const auto &h:cap.planes){
    double lo=1e100,hi=-1e100;
    for(const auto &p:pending){const double d=dot(h.n,p)-h.d;lo=std::min(lo,d);hi=std::max(hi,d);}
    if(hi<=eps)continue;
    if(lo>eps){out.push_back(pending);break;}
    auto outside=clip(pending,h.n,h.d,false);if(!outside.empty())out.push_back(std::move(outside));
    pending=clip(pending,h.n,h.d);if(pending.empty())break;
  }return out;
}
double projectedDistance(double x,double y,const Poly &p){
  if(p.empty())return 1e100;
  double best=1e100;bool positive=false,negative=false;
  for(size_t i=0;i<p.size();++i){const auto &a=p[i],&b=p[(i+1)%p.size()];
    const double vx=b[0]-a[0],vy=b[1]-a[1],wx=x-a[0],wy=y-a[1];
    const double side=vx*wy-vy*wx;positive|=side>0.;negative|=side<0.;
    const double len=vx*vx+vy*vy,u=len>0?std::clamp((wx*vx+wy*vy)/len,0.,1.):0.;
    best=std::min(best,std::hypot(wx-u*vx,wy-u*vy));
  }
  if(area(p)>eps&&!(positive&&negative))return 0.;
  return best;
}
class Field {
 public:
  explicit Field(const std::string &path){
    std::ifstream f(path,std::ios::binary|std::ios::ate);if(!f)throw std::runtime_error("Missing finite source triangles");
    const auto bytes=f.tellg();if(bytes<=0||bytes%static_cast<std::streamoff>(sizeof(Triangle)))throw std::runtime_error("Invalid source triangle size");
    tri_.resize(size_t(bytes)/sizeof(Triangle));f.seekg(0);f.read(reinterpret_cast<char*>(tri_.data()),bytes);
    if(!f)throw std::runtime_error("Incomplete source triangles");
    std::vector<Item> items;normals_.reserve(tri_.size());
    for(size_t i=0;i<tri_.size();++i){const auto &t=tri_[i];
      for(const auto &p:t)for(double x:p)if(!std::isfinite(x))throw std::runtime_error("Nonfinite source triangle");
      V n=cross(sub(t[1],t[0]),sub(t[2],t[0]));double length=std::sqrt(dot(n,n));for(double &v:n)v/=std::max(length,1e-30);normals_.push_back(n);
      items.emplace_back(bounds(Poly(t.begin(),t.end())),i);
    }tree_=Tree(items.begin(),items.end());
  }
  double assess(double x,double y,double ground,double yaw)const {
    for(double v:{x,y,ground,yaw})if(!std::isfinite(v))throw std::runtime_error("Nonfinite source query");
    double answer=target;
    for(int side:{-1,1})answer=std::min(answer,cylinder(x+side*offset*std::cos(yaw),y+side*offset*std::sin(yaw),ground));
    return answer;
  }
 private:
  std::vector<size_t> candidates(const Box &box)const {
    std::vector<Item> found;tree_.query(bgi::intersects(box),std::back_inserter(found));std::vector<size_t> ids;
    for(const auto &i:found)ids.push_back(i.second);std::sort(ids.begin(),ids.end());return ids;
  }
  bool occupied(double x,double y,double g,double zlo,double zhi)const {
    const auto ids=candidates(Box(Point(x,y,-1e10),Point(x,y,1e10)));
    std::map<double,int,std::greater<double>> events;double terrain=-1e100;
    for(size_t i:ids){const auto &t=tri_[i];const auto u=sub(t[1],t[0]),v=sub(t[2],t[0]);
      const double d=u[0]*v[1]-u[1]*v[0];if(std::abs(d)<1e-14)continue;
      const double a=((x-t[0][0])*v[1]-(y-t[0][1])*v[0])/d,b=(u[0]*(y-t[0][1])-u[1]*(x-t[0][0]))/d;
      if(a< -eps||b< -eps||a+b>1.+eps)continue;
      const double z=t[0][2]+a*u[2]+b*v[2];const bool up=normals_[i][2]>0.;events[z]+=up?1:-1;
      if(up&&std::abs(z-g)<.26)terrain=std::max(terrain,z);
    }
    int winding=0;double previous=1e100;
    for(const auto &e:events){
      if(winding>0&&std::min(previous,zhi)>std::max({e.first,zlo,terrain})+eps)return true;
      winding+=e.second;previous=e.first;
    }
    return winding>0&&std::min(previous,zhi)>std::max(zlo,terrain)+eps;
  }
  double cylinder(double x,double y,double ground)const {
    const double reach=radius+target,zlo=ground+.3-.55,zhi=ground+.3+.35;
    const auto caps_ids=candidates(Box(Point(x-reach,y-reach,ground-.26),Point(x+reach,y+reach,ground+.26)));
    std::vector<Cap> caps;
    for(size_t i:caps_ids){
      if(normals_[i][2]<=32.*std::numeric_limits<float>::epsilon())continue;
      const auto &t=tri_[i];Poly p=clip(Poly(t.begin(),t.end()),{{0.,0.,-1.}},-(ground-.26));p=clip(p,{{0.,0.,1.}},ground+.26);
      if(area(p)<=eps)continue;Cap cap;cap.box=bounds(p);
      bg::set<bg::min_corner,2>(cap.box,-1e100); // Finite XY cap covers material below its height.
      for(size_t k=0;k<p.size();++k){const auto e=sub(p[(k+1)%p.size()],p[k]);V n={{e[1],-e[0],0.}};cap.planes.push_back({n,dot(n,p[k])});}
      const V n=cross(sub(t[1],t[0]),sub(t[2],t[0]));cap.planes.push_back({n,dot(n,t[0])});caps.push_back(std::move(cap));
    }
    double answer=target;
    const auto ids=candidates(Box(Point(x-reach,y-reach,zlo),Point(x+reach,y+reach,zhi)));
    for(size_t i:ids){const auto &t=tri_[i];Poly p(t.begin(),t.end());
      for(const auto &h:std::vector<Halfspace>{{{{1.,0.,0.}},x+reach},{{{-1.,0.,0.}},-(x-reach)},{{{0.,1.,0.}},y+reach},{{{0.,-1.,0.}},-(y-reach)},{{{0.,0.,1.}},zhi},{{{0.,0.,-1.}},-zlo}}){p=clip(p,h.n,h.d);if(p.empty())break;}
      if(p.empty())continue;std::vector<Poly> parts{p};
      for(const auto &cap:caps){std::vector<Poly> next;
        for(const auto &part:parts){if(!bg::intersects(bounds(part),cap.box))next.push_back(part);
          else{auto remainder=remove(part,cap);next.insert(next.end(),std::make_move_iterator(remainder.begin()),std::make_move_iterator(remainder.end()));}}
        parts=std::move(next);if(parts.empty())break;
      }
      for(const auto &part:parts)answer=std::min(answer,projectedDistance(x,y,part)-radius);
      if(answer<=-radius)return -radius;
    }
    if(occupied(x,y,ground,zlo,zhi))return -radius;
    return answer;
  }
  std::vector<Triangle> tri_;std::vector<V> normals_;Tree tree_;
};
} // namespace surface

int main(int argc,char **argv){
  if(argc!=2)throw std::runtime_error("source triangle binary required");
  const surface::Field field(argv[1]);double x,y,g,yaw;size_t queries=0;
  std::cout<<std::setprecision(17);const auto begin=std::chrono::steady_clock::now();
  while(std::cin>>x>>y>>g>>yaw){std::cout<<field.assess(x,y,g,yaw)<<'\n';++queries;}
  if(!std::cin.eof())throw std::runtime_error("Invalid query stream");
  std::cerr<<"queries="<<queries<<" wall_s="<<std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count()<<'\n';
}
