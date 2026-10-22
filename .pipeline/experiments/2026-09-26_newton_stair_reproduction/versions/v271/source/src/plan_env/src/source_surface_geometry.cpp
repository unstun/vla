#include "source_surface_geometry.h"
// Immutable source geometry, derived from the independently checked v270 component.
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
#include <sstream>
#include <cstring>
#include <cstdint>
#include <iterator>

namespace reactive_stair { namespace source_surface {
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
inline std::string verifiedBytes(const std::string &path,const std::string &expected){
  std::ifstream input(path,std::ios::binary);
  if(!input)throw std::runtime_error("Missing source-surface dependency");
  std::string bytes((std::istreambuf_iterator<char>(input)),{});uint64_t hash=14695981039346656037ULL;
  for(unsigned char c:bytes){hash^=c;hash*=1099511628211ULL;}
  if(expected.empty()||std::to_string(hash)!=expected)throw std::runtime_error("Source-surface dependency identity mismatch");
  return bytes;
}

inline V sub(V a,const V &b){for(int i=0;i<3;++i)a[i]-=b[i];return a;}
inline V cross(const V &a,const V &b){return {{a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]}};}
inline double dot(const V &a,const V &b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
inline Point point(const V &p){return Point(p[0],p[1],p[2]);}
inline Box bounds(const Poly &p){
  V lo={{1e100,1e100,1e100}},hi={{-1e100,-1e100,-1e100}};
  for(const auto &a:p)for(int j=0;j<3;++j){lo[j]=std::min(lo[j],a[j]);hi[j]=std::max(hi[j],a[j]);}
  return Box(point(lo),point(hi));
}
inline Poly clip(const Poly &p,const V &n,double d,bool inside=true){
  Poly out;if(p.empty())return out;
  for(size_t i=0;i<p.size();++i){const auto &a=p[i],&b=p[(i+1)%p.size()];
    const double da=dot(n,a)-d,db=dot(n,b)-d;
    const bool ia=inside?da<=0.:da>=0.,ib=inside?db<=0.:db>=0.;
    if(ia)out.push_back(a);
    if(ia!=ib){V q;for(int j=0;j<3;++j)q[j]=a[j]+(b[j]-a[j])*da/(da-db);out.push_back(q);}
  }return out;
}
inline double area(const Poly &p){
  if(p.size()<3)return 0.;
  double a=0.;
  for(size_t i=1;i+1<p.size();++i)a+=(p[i][0]-p[0][0])*(p[i+1][1]-p[0][1])-(p[i][1]-p[0][1])*(p[i+1][0]-p[0][0]);
  return std::abs(a)*.5;
}
struct Halfspace {V n;double d;};
struct Cap {Box box;std::vector<Halfspace> planes;};
inline std::vector<Poly> remove(const Poly &poly,const Cap &cap){
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
inline double projectedDistance(double x,double y,const Poly &p,V *witness=nullptr){
  if(p.empty())return 1e100;
  double best=1e100;bool positive=false,negative=false;
  double xmin=1e100,ymin=1e100,xmax=-1e100,ymax=-1e100;
  for(size_t i=0;i<p.size();++i){const auto &a=p[i],&b=p[(i+1)%p.size()];
    xmin=std::min(xmin,a[0]);xmax=std::max(xmax,a[0]);ymin=std::min(ymin,a[1]);ymax=std::max(ymax,a[1]);
    const double vx=b[0]-a[0],vy=b[1]-a[1],wx=x-a[0],wy=y-a[1];
    const double side=vx*wy-vy*wx;positive|=side>0.;negative|=side<0.;
    const double len=vx*vx+vy*vy,u=len>0?std::max(0.,std::min(1.,(wx*vx+wy*vy)/len)):0.;
    const double d=std::hypot(wx-u*vx,wy-u*vy);
    if(d<best){best=d;if(witness)for(int j=0;j<3;++j)(*witness)[j]=a[j]+u*(b[j]-a[j]);}
  }
  if(area(p)>0.&&x>=xmin&&x<=xmax&&y>=ymin&&y<=ymax&&!(positive&&negative)){
    if(witness)for(size_t i=1;i+1<p.size();++i){const auto u=sub(p[i],p[0]),v=sub(p[i+1],p[0]);
      const double det=u[0]*v[1]-u[1]*v[0];if(det==0.)continue;
      double a=((x-p[0][0])*v[1]-(y-p[0][1])*v[0])/det,b=(u[0]*(y-p[0][1])-u[1]*(x-p[0][0]))/det;
      if(a< -eps||b< -eps||a+b>1.+eps)continue;
      a=std::max(0.,a);b=std::max(0.,b);const double c=std::max(0.,1.-a-b),sum=a+b+c;
      for(int j=0;j<3;++j)(*witness)[j]=(c*p[0][j]+a*p[i][j]+b*p[i+1][j])/sum;
      break;
    }
    return 0.;
  }
  return best;
}
class Kernel {
 public:
  explicit Kernel(const std::string &path,const std::string &metadata,const std::string &geometry_fnv,const std::string &metadata_fnv){
    const auto bytes=verifiedBytes(path,geometry_fnv);
    if(bytes.empty()||bytes.size()%sizeof(Triangle))throw std::runtime_error("Invalid source triangle size");
    tri_.resize(bytes.size()/sizeof(Triangle));std::memcpy(tri_.data(),bytes.data(),bytes.size());
    std::vector<Item> items;normals_.reserve(tri_.size());
    for(size_t i=0;i<tri_.size();++i){const auto &t=tri_[i];
      for(const auto &p:t)for(double x:p)if(!std::isfinite(x))throw std::runtime_error("Nonfinite source triangle");
      V n=cross(sub(t[1],t[0]),sub(t[2],t[0]));double length=std::sqrt(dot(n,n));for(double &v:n)v/=std::max(length,1e-30);normals_.push_back(n);
      items.emplace_back(bounds(Poly(t.begin(),t.end())),i);
    }tree_=Tree(items.begin(),items.end());
    std::istringstream in(verifiedBytes(metadata,metadata_fnv));std::string magic,tag;size_t faces,count;
    if(!(in>>magic>>faces>>count)||magic!="SURFACE268C"||faces!=tri_.size()||count>faces)throw std::runtime_error("Invalid source-volume certificate");
    std::vector<Item> objects;
    for(size_t k=0;k<count;++k){int id;Volume volume;
      in>>id;for(double &x:volume.low)in>>x;for(double &x:volume.high)in>>x;
      if(!in||id<0||volumes_.count(id))throw std::runtime_error("Invalid closed volume");
      for(int j=0;j<3;++j)if(!std::isfinite(volume.low[j])||!std::isfinite(volume.high[j])||volume.low[j]>volume.high[j])throw std::runtime_error("Invalid volume bounds");
      volumes_[id]=volume;objects.emplace_back(Box(point(volume.low),point(volume.high)),size_t(id));
    }
    if(!(in>>tag)||tag!="F")throw std::runtime_error("Missing source-volume faces");
    labels_.resize(faces);std::map<int,Volume> actual;
    for(size_t i=0;i<faces;++i){in>>labels_[i];const int id=labels_[i];
      if(!in||id< -1||(id>=0&&!volumes_.count(id)))throw std::runtime_error("Invalid volume face identity");
      if(id>=0){auto &v=actual[id];for(const auto &p:tri_[i])for(int j=0;j<3;++j){v.low[j]=std::min(v.low[j],p[j]);v.high[j]=std::max(v.high[j],p[j]);}
        if(normals_[i][2]>0.){
          if(normals_[i][2]<=32.*std::numeric_limits<float>::epsilon()||area(Poly(tri_[i].begin(),tri_[i].end()))<=eps)volumes_[id].terrain_complete=false;
          for(const auto &p:tri_[i])volumes_[id].min_upward_z=std::min(volumes_[id].min_upward_z,p[2]);
        }}
    }
    std::string extra;if(in>>extra)throw std::runtime_error("Trailing source-volume data");
    if(actual.size()!=volumes_.size())throw std::runtime_error("Empty certified volume");
    for(const auto &v:volumes_)if(v.second.low!=actual.at(v.first).low||v.second.high!=actual.at(v.first).high)throw std::runtime_error("Source-volume bounds mismatch");
    object_tree_=Tree(objects.begin(),objects.end());
  }
  double assess(double x,double y,double ground,double yaw,V *witness=nullptr)const {
    for(double v:{x,y,ground,yaw})if(!std::isfinite(v))throw std::runtime_error("Nonfinite source query");
    double answer=target;V closest={{0.,0.,0.}};
    for(int side:{-1,1}){
      const double value=cylinder(x+side*offset*std::cos(yaw),y+side*offset*std::sin(yaw),ground,radius,witness?&closest:nullptr);
      if(value<answer){answer=value;if(witness)*witness=closest;}
    }
    return answer;
  }
  double circleMargin(double x,double y,double ground,double query_radius)const {
    for(double v:{x,y,ground,query_radius})if(!std::isfinite(v))throw std::runtime_error("Nonfinite source circle");
    if(query_radius<=0.)throw std::runtime_error("Invalid source circle radius");
    return cylinder(x,y,ground,query_radius,nullptr,true);
  }
 private:
  std::vector<size_t> candidates(const Box &box)const {
    std::vector<Item> found;tree_.query(bgi::intersects(box),std::back_inserter(found));std::vector<size_t> ids;
    for(const auto &i:found)ids.push_back(i.second);
    std::sort(ids.begin(),ids.end());return ids;
  }
  bool terrainVolume(int id,double ground,double bottom)const {
    return id>=0&&volumes_.at(id).terrain_complete&&volumes_.at(id).min_upward_z>ground-.26&&bottom>ground-.26&&volumes_.at(id).high[2]<ground+.26;
  }
  bool occupied(double x,double y,double g,double zlo,double zhi,V *witness=nullptr)const {
    std::vector<Item> objects;object_tree_.query(bgi::intersects(Box(Point(x,y,zlo),Point(x,y,zhi))),std::back_inserter(objects));
    std::map<int,std::vector<std::pair<double,int>>> events;
    for(const auto &object:objects){const int id=int(object.second);if(!terrainVolume(id,g,zlo))events[id]={};}
    if(events.empty())return false;
    const auto ids=candidates(Box(Point(x,y,-1e10),Point(x,y,1e10)));double terrain=-1e100;
    for(size_t i:ids){const auto &t=tri_[i];const auto u=sub(t[1],t[0]),v=sub(t[2],t[0]);
      const double d=u[0]*v[1]-u[1]*v[0];if(std::abs(d)<1e-14)continue;
      const double a=((x-t[0][0])*v[1]-(y-t[0][1])*v[0])/d,b=(u[0]*(y-t[0][1])-u[1]*(x-t[0][0]))/d;
      if(a< -eps||b< -eps||a+b>1.+eps)continue;
      const double z=t[0][2]+a*u[2]+b*v[2];const bool up=normals_[i][2]>0.;
      if(normals_[i][2]>32.*std::numeric_limits<float>::epsilon()&&std::abs(z-g)<.26)terrain=std::max(terrain,z);
      const auto e=events.find(labels_[i]);if(e!=events.end())e->second.emplace_back(z,up?1:-1);
    }
    for(auto &object:events){auto &list=object.second;std::sort(list.begin(),list.end(),std::greater<std::pair<double,int>>());
      int winding=0;double previous=1e100;size_t k=0;
      while(k<list.size()){
        const double z=list[k].first;if(winding>0&&std::min(previous,zhi)>std::max({z,zlo,terrain})+eps){if(witness)*witness={{x,y,.5*(std::min(previous,zhi)+std::max({z,zlo,terrain})+eps)}};return true;}
        bool positive=false,negative=false;
        do{positive|=list[k].second>0;negative|=list[k].second<0;++k;}while(k<list.size()&&std::abs(list[k].first-z)<=eps);
        winding+=int(positive)-int(negative);previous=z;
      }
      if(winding>0&&std::min(previous,zhi)>std::max(zlo,terrain)+eps){if(witness)*witness={{x,y,.5*(std::min(previous,zhi)+std::max(zlo,terrain)+eps)}};return true;}
    }
    return false;
  }
  double cylinder(double x,double y,double ground,double query_radius=radius,V *witness=nullptr,bool stop_on_collision=false)const {
    const double radius=query_radius;
    const double reach=radius+target,zlo=ground+.3-.55,zhi=ground+.3+.35;
    const auto candidates_ids=candidates(Box(Point(x-reach,y-reach,zlo),Point(x+reach,y+reach,zhi)));
    std::vector<size_t> active;
    for(size_t i:candidates_ids){
      if(terrainVolume(labels_[i],ground,zlo))continue;
      const auto &t=tri_[i];double lo=1e100,hi=-1e100;for(const auto &p:t){lo=std::min(lo,p[2]);hi=std::max(hi,p[2]);}
      if(normals_[i][2]>32.*std::numeric_limits<float>::epsilon()&&lo>ground-.26&&hi<ground+.26&&area(Poly(t.begin(),t.end()))>eps)continue;
      active.push_back(i);
    }
    if(active.empty())return occupied(x,y,ground,zlo,zhi,witness)?-radius:target;
    const auto caps_ids=candidates(Box(Point(x-reach,y-reach,ground-.26),Point(x+reach,y+reach,ground+.26)));
    std::vector<Cap> caps;
    for(size_t i:caps_ids){
      if(normals_[i][2]<=32.*std::numeric_limits<float>::epsilon())continue;
      const auto &t=tri_[i];double lo=1e100,hi=-1e100;for(const auto &p:t){lo=std::min(lo,p[2]);hi=std::max(hi,p[2]);}
      if(hi<=ground-.26||lo>=ground+.26)continue; // Strict physical step band.
      Poly p=clip(Poly(t.begin(),t.end()),{{0.,0.,-1.}},-(ground-.26));p=clip(p,{{0.,0.,1.}},ground+.26);
      if(area(p)<=eps)continue;
      Cap cap;cap.box=bounds(p);
      bg::set<bg::min_corner,2>(cap.box,-1e100); // Finite XY cap covers material below its height.
      for(size_t k=0;k<p.size();++k){const auto e=sub(p[(k+1)%p.size()],p[k]);V n={{e[1],-e[0],0.}};cap.planes.push_back({n,dot(n,p[k])});}
      const V n=cross(sub(t[1],t[0]),sub(t[2],t[0]));cap.planes.push_back({n,dot(n,t[0])});caps.push_back(std::move(cap));
    }
    double answer=target;
    for(size_t i:active){const auto &t=tri_[i];Poly p(t.begin(),t.end());
      for(const auto &h:std::vector<Halfspace>{{{{1.,0.,0.}},x+reach},{{{-1.,0.,0.}},-(x-reach)},{{{0.,1.,0.}},y+reach},{{{0.,-1.,0.}},-(y-reach)},{{{0.,0.,1.}},zhi},{{{0.,0.,-1.}},-zlo}}){p=clip(p,h.n,h.d);if(p.empty())break;}
      if(p.empty())continue;
      std::vector<Poly> parts{p};
      for(const auto &cap:caps){std::vector<Poly> next;
        for(const auto &part:parts){if(!bg::intersects(bounds(part),cap.box))next.push_back(part);
          else{auto remainder=remove(part,cap);next.insert(next.end(),std::make_move_iterator(remainder.begin()),std::make_move_iterator(remainder.end()));}}
        parts=std::move(next);if(parts.empty())break;
      }
      for(const auto &part:parts){V closest={{0.,0.,0.}};const double value=projectedDistance(x,y,part,witness?&closest:nullptr)-radius;if(value<answer){answer=value;if(witness)*witness=closest;}}
      if(stop_on_collision&&answer<=0.)return answer;
      if(answer<=-radius)return -radius;
    }
    if(occupied(x,y,ground,zlo,zhi,witness))return -radius;
    return answer;
  }
  struct Volume{V low={{1e100,1e100,1e100}},high={{-1e100,-1e100,-1e100}};bool terrain_complete=true;double min_upward_z=1e100;};
  std::vector<Triangle> tri_;std::vector<V> normals_;Tree tree_,object_tree_;
  std::vector<int> labels_;std::map<int,Volume> volumes_;
};
struct Field::Data : Kernel {using Kernel::Kernel;};
Field::Field(const std::string &path,const std::string &metadata,const std::string &geometry_fnv,const std::string &metadata_fnv)
 : data_(new Data(path,metadata,geometry_fnv,metadata_fnv)) {}
Field::~Field()=default;
double Field::assess(double x,double y,double ground,double yaw,V *witness)const {return data_->assess(x,y,ground,yaw,witness);}
double Field::circleMargin(double x,double y,double ground,double radius)const {return data_->circleMargin(x,y,ground,radius);}
}} // namespace reactive_stair::source_surface
