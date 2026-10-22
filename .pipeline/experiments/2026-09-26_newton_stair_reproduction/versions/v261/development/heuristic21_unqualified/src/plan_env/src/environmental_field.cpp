#include <plan_env/environmental_field.h>
#include <plan_env/support_gap_mask.h>
#include <algorithm>
#include <cmath>
#include <fstream>
#include <limits>
#include <map>
#include <sstream>
#include <stdexcept>
#include <vector>

namespace reactive_stair {
struct EnvironmentalField::Data {
  struct Floor {double z,edge,terrain;};
  struct FloorSample {
    double edge=0.,terrain=0.;bool known=true;
    Eigen::Vector3d de=Eigen::Vector3d::Zero(),dt=Eigen::Vector3d::Zero();
  };
  double resolution,ox,oy,radius,offset,up,down,clearance,target,voxel_half;
  double hxy=0.,hz=0.,ax=0.,ay=0.,az=0.;int nx=0,ny=0,nz=0;
  int fx=0,fy=0,fnx=0,fny=0;
  std::vector<std::vector<Floor>> floors;
  std::vector<float> solid;
  // Coarse bins broaden the query envelope, never quantize an actual query.
  // Unknown floor interpolation contributes terrain=1 and edge=0.
  struct CostBound {double terrain=1.,edge=0.;};
  static constexpr double bound_xy=.5,bound_z=.1;
  int bx=0,by=0,bz=0,bnx=0,bny=0,bnz=0;
  std::vector<CostBound> cost_bounds;
  void buildCostBounds() {
    double zmin=std::numeric_limits<double>::infinity(),zmax=-zmin;
    for(const auto &cell:floors)for(const auto &f:cell){zmin=std::min(zmin,f.z);zmax=std::max(zmax,f.z);}
    const double xmin=ox+(fx+.5)*resolution,ymin=oy+(fy+.5)*resolution;
    const double xmax=xmin+(fnx-1)*resolution,ymax=ymin+(fny-1)*resolution;
    const auto safe=[](double x){return std::isfinite(x)&&std::abs(x)<std::numeric_limits<int>::max()/4.;};
    for(double x:{xmin/bound_xy,ymin/bound_xy,xmax/bound_xy,ymax/bound_xy,zmin/bound_z,zmax/bound_z})if(!safe(x))return;
    bx=int(std::floor(xmin/bound_xy));by=int(std::floor(ymin/bound_xy));bz=int(std::floor(zmin/bound_z));
    bnx=int(std::floor(xmax/bound_xy))-bx+1;bny=int(std::floor(ymax/bound_xy))-by+1;bnz=int(std::floor(zmax/bound_z))-bz+1;
    if(uint64_t(bnx)*bny*bnz>4000000)return;
    cost_bounds.resize(size_t(bnx)*bny*bnz);
    for(int x=0;x<fnx;++x)for(int y=0;y<fny;++y)for(const auto &f:floors[size_t(x)*fny+y]){
      const int a=int(std::floor((ox+(fx+x+.5)*resolution)/bound_xy))-bx;
      const int b=int(std::floor((oy+(fy+y+.5)*resolution)/bound_xy))-by;
      const int c=int(std::floor(f.z/bound_z))-bz;
      auto &value=cost_bounds[(size_t(a)*bny+b)*bnz+c];
      value.terrain=std::min(value.terrain,f.terrain);value.edge=std::max(value.edge,f.edge);
    }
  }

  FloorSample floor(double x,double y,double z) const {
    FloorSample out;
    const double gx=(x-ox)/resolution-.5,gy=(y-oy)/resolution-.5;
    if(gx<std::numeric_limits<int>::min()+1. || gx>std::numeric_limits<int>::max()-1. ||
       gy<std::numeric_limits<int>::min()+1. || gy>std::numeric_limits<int>::max()-1.) {
      out.known=false;out.terrain=1.;return out;
    }
    const int ix=int(std::floor(gx)),iy=int(std::floor(gy));
    const double u=gx-ix,v=gy-iy;
    for(int dx=0;dx<2;++dx)for(int dy=0;dy<2;++dy) {
      const double wx=dx?u:1-u,wy=dy?v:1-v,w=wx*wy;
      const Eigen::Vector3d dw((dx?1.:-1.)*wy/resolution,wx*(dy?1.:-1.)/resolution,0.);
      const int a=ix+dx-fx,b=iy+dy-fy;const Floor *selected=nullptr;
      double best=.260000001;bool tie=false;
      if(a>=0&&b>=0&&a<fnx&&b<fny)for(const auto &f:floors[size_t(a)*fny+b]) {
        const double delta=std::abs(f.z-z);
        if(delta<best-1e-9){selected=&f;best=delta;tie=false;}
        else if(std::abs(delta-best)<=1e-9)tie=true;
      }
      if(!selected||tie) {
        if(w>1e-12)out.known=false;
        out.terrain+=w;out.dt+=dw;
      } else {
        out.edge+=w*selected->edge;out.terrain+=w*selected->terrain;
        out.de+=dw*selected->edge;out.dt+=dw*selected->terrain;
      }
    }
    return out;
  }

  double margin(const Eigen::Vector3d &p,Eigen::Vector3d &gradient) const {
    gradient.setZero();if(solid.empty())return target;
    const Eigen::Vector3d g((p.x()-ax)/hxy,(p.y()-ay)/hxy,(p.z()-az)/hz);
    // Outside the declared atlas domain is penalized, never silently clamped free.
    if((g.array()<0.).any() || g.x()>nx-1 || g.y()>ny-1 || g.z()>nz-1)return -target;
    const int ix=std::min(int(std::floor(g.x())),nx-2),iy=std::min(int(std::floor(g.y())),ny-2),iz=std::min(int(std::floor(g.z())),nz-2);
    const Eigen::Vector3d u=g-Eigen::Vector3d(ix,iy,iz);double value=0.;
    for(int dx=0;dx<2;++dx)for(int dy=0;dy<2;++dy)for(int dz=0;dz<2;++dz) {
      const double wx=dx?u.x():1-u.x(),wy=dy?u.y():1-u.y(),wz=dz?u.z():1-u.z();
      const double f=solid[(size_t(ix+dx)*ny+iy+dy)*nz+iz+dz];
      value+=wx*wy*wz*f;
      gradient+=f*Eigen::Vector3d((dx?1.:-1.)*wy*wz/hxy,wx*(dy?1.:-1.)*wz/hxy,wx*wy*(dz?1.:-1.)/hz);
    }
    return value;
  }
};

EnvironmentalField::EnvironmentalField(const std::string &path,const std::string &fnv):data_(new Data) {
  std::ifstream raw(path,std::ios::binary);if(!raw)throw std::runtime_error("Missing environmental field");
  const std::string bytes((std::istreambuf_iterator<char>(raw)),{});uint64_t hash=14695981039346656037ULL;
  for(unsigned char c:bytes){hash^=c;hash*=1099511628211ULL;}
  if(fnv.empty()||std::to_string(hash)!=fnv)throw std::runtime_error("Environmental field identity mismatch");
  std::istringstream input(bytes);std::string magic;auto &d=*data_;
  if(!(input>>magic>>d.resolution>>d.ox>>d.oy>>d.radius>>d.offset>>d.up>>d.down>>d.clearance>>d.target>>d.voxel_half) ||
      magic!="ENV225"||d.resolution<=0||d.radius<=0||d.target<=0||d.offset<0||d.up<0||d.down<0||d.voxel_half<0)
    throw std::runtime_error("Invalid environmental geometry");
  for(double x:{d.resolution,d.ox,d.oy,d.radius,d.offset,d.up,d.down,d.clearance,d.target,d.voxel_half})
    if(!std::isfinite(x))throw std::runtime_error("Nonfinite environmental geometry");
  size_t count=0;char type=0;
  if(!(input>>type>>count)||type!='F'||count==0||count>10000000)throw std::runtime_error("Invalid floor count");
  std::map<std::pair<int,int>,std::vector<Data::Floor>> cells;
  int minx=std::numeric_limits<int>::max(),miny=minx,maxx=std::numeric_limits<int>::min(),maxy=maxx;
  for(size_t i=0;i<count;++i) {
    int x,y;Data::Floor f;input>>x>>y>>f.z>>f.edge>>f.terrain;
    if(!input||!std::isfinite(f.z)||!std::isfinite(f.edge)||f.edge<0||!std::isfinite(f.terrain)||f.terrain<0||f.terrain>1)
      throw std::runtime_error("Invalid floor record");
    cells[{x,y}].push_back(f);minx=std::min(minx,x);miny=std::min(miny,y);maxx=std::max(maxx,x);maxy=std::max(maxy,y);
  }
  const int64_t width=int64_t(maxx)-minx+1,height=int64_t(maxy)-miny+1;
  if(width<=0||height<=0||width>10000000||height>10000000||width*height>10000000)throw std::runtime_error("Invalid floor extent");
  d.fx=minx;d.fy=miny;d.fnx=int(width);d.fny=int(height);d.floors.resize(size_t(width)*height);
  for(auto &entry:cells)d.floors[size_t(entry.first.first-minx)*d.fny+entry.first.second-miny]=std::move(entry.second);
  d.buildCostBounds();
  if(!(input>>type>>d.hxy>>d.hz>>d.ax>>d.ay>>d.az>>d.nx>>d.ny>>d.nz)||type!='A')throw std::runtime_error("Invalid atlas header");
  for(double x:{d.hxy,d.hz,d.ax,d.ay,d.az})if(!std::isfinite(x))throw std::runtime_error("Nonfinite atlas geometry");
  if(d.nx==0&&d.ny==0&&d.nz==0) {
    std::string extra;if(input>>extra)throw std::runtime_error("Trailing empty atlas data");return;
  }
  if(d.hxy<=0||d.hz<=0||d.nx<2||d.ny<2||d.nz<2||d.nx>100000||d.ny>100000||d.nz>100000 ||
      uint64_t(d.nx)*d.ny*d.nz>200000000)throw std::runtime_error("Invalid atlas extent");
  const uint32_t endian=1;if(*reinterpret_cast<const uint8_t*>(&endian)!=1)throw std::runtime_error("Atlas requires little endian floats");
  input.ignore(std::numeric_limits<std::streamsize>::max(),'\n');
  d.solid.resize(size_t(d.nx)*d.ny*d.nz);input.read(reinterpret_cast<char*>(d.solid.data()),d.solid.size()*sizeof(float));
  if(!input||input.peek()!=std::char_traits<char>::eof())throw std::runtime_error("Atlas payload size mismatch");
  for(float v:d.solid)if(!std::isfinite(v)||std::abs(v)>d.target+1e-6)throw std::runtime_error("Invalid atlas margin");
}
EnvironmentalField::~EnvironmentalField()=default;
#define FIELD_ACCESSOR(name) double EnvironmentalField::name() const{return data_->name;}
FIELD_ACCESSOR(radius) FIELD_ACCESSOR(offset) FIELD_ACCESSOR(up) FIELD_ACCESSOR(down) FIELD_ACCESSOR(target)
double EnvironmentalField::bodyClearance() const{return data_->clearance;}
#undef FIELD_ACCESSOR

bool EnvironmentalField::surfaceHeight(double x,double y,double hint,double &height) const {
  if(!std::isfinite(x)||!std::isfinite(y)||!std::isfinite(hint))return false;
  const auto &d=*data_;const double gx=std::floor((x-d.ox)/d.resolution)-d.fx;
  const double gy=std::floor((y-d.oy)/d.resolution)-d.fy;
  if(gx<0||gy<0||gx>=d.fnx||gy>=d.fny)return false;
  const Data::Floor *selected=nullptr;double best=.260000001;bool tie=false;
  for(const auto &f:d.floors[size_t(gx)*d.fny+size_t(gy)]) {
    const double delta=std::abs(f.z-hint);
    if(delta<best-1e-9){selected=&f;best=delta;tie=false;}
    else if(std::abs(delta-best)<=1e-9)tie=true;
  }
  if(!selected||tie)return false;
  height=selected->z;return true;
}

double EnvironmentalField::connectionCostLowerBound(const Eigen::Vector3d &a,const Eigen::Vector3d &b) const {
  const auto &d=*data_;if(!a.allFinite()||!b.allFinite()||d.cost_bounds.empty())return 0.;
  // Cubic Bezier controls lie within chord_xy/3 of the endpoint box.
  // Both cylinder offsets and every bilinear floor vertex are included.
  const double reach=(b-a).head<2>().norm()/3.+d.offset+d.resolution+1e-8;
  const Eigen::Vector3d lo(std::min(a.x(),b.x())-reach,std::min(a.y(),b.y())-reach,
    std::min(a.z(),b.z())-d.clearance-.260000011);
  const Eigen::Vector3d hi(std::max(a.x(),b.x())+reach,std::max(a.y(),b.y())+reach,
    std::max(a.z(),b.z())-d.clearance+.260000011);
  int begin[3],end[3];const int origin[]={d.bx,d.by,d.bz},size[]={d.bnx,d.bny,d.bnz};
  for(int i=0;i<3;++i){
    const double scale=i==2?Data::bound_z:Data::bound_xy;
    const double low=std::floor(lo(i)/scale)-origin[i],high=std::floor(hi(i)/scale)-origin[i];
    if(high<0.||low>=size[i])return .25+1.; // Only the unknown-floor defaults.
    begin[i]=int(std::max(0.,low));end[i]=int(std::min(double(size[i]-1),high));
  }
  double terrain=1.,edge=0.;
  for(int x=begin[0];x<=end[0];++x)for(int y=begin[1];y<=end[1];++y)
    for(int z=begin[2];z<=end[2];++z){
      const auto &value=d.cost_bounds[(size_t(x)*d.bny+y)*d.bnz+z];
      terrain=std::min(terrain,value.terrain);edge=std::max(edge,value.edge);
    }
  // Bilinear terrain is convex. min(front,rear,gap) edge can only decrease
  // from the largest possible source edge minus radius. Solid cost is >=0.
  const double penalty=std::clamp((d.target-(edge+1e-9-d.radius))/d.target,0.,1.);
  terrain=std::max(0.,terrain-1e-12);
  return std::max(0.,.25*terrain*terrain+penalty*penalty-1e-12);
}

EnvironmentalAssessment EnvironmentalField::assess(const Eigen::Vector3d &body,double yaw,const SupportGapMask *gap) const {
  if(!body.allFinite()||!std::isfinite(yaw))throw std::runtime_error("Invalid environmental query");
  const auto &d=*data_;EnvironmentalAssessment out;out.floor_known=true;
  out.edge_margin=out.solid_margin=d.target;
  Eigen::Vector4d de=Eigen::Vector4d::Zero(),ds=de,dt=de;
  const Eigen::Vector3d heading(std::cos(yaw),std::sin(yaw),0.);
  const auto combine=[](double value,const Eigen::Vector4d &g,double &selected,Eigen::Vector4d &gradient,bool minimum) {
    if((minimum&&value<selected-1e-12)||(!minimum&&value>selected+1e-12)){selected=value;gradient=g;}
    else if(std::abs(value-selected)<=1e-12)gradient=.5*(gradient+g); // Symmetric tie subgradient.
  };
  for(double sign:{-1.,1.}) {
    const Eigen::Vector3d center=body+sign*d.offset*heading;
    const Eigen::Vector3d dyaw=sign*d.offset*Eigen::Vector3d(-heading.y(),heading.x(),0.);
    const auto pose_gradient=[&](const Eigen::Vector3d &g) {
      Eigen::Vector4d result;result<<g,g.dot(dyaw);return result;
    };
    const auto f=d.floor(center.x(),center.y(),body.z()-d.clearance);out.floor_known&=f.known;
    combine(f.edge-d.radius,pose_gradient(f.de),out.edge_margin,de,true);
    if(gap) {
      std::array<double,2> gradient;
      const double margin=gap->clearanceMargin(center.x(),center.y(),body.z()-d.clearance,d.target,gradient);
      combine(margin,pose_gradient(Eigen::Vector3d(gradient[0],gradient[1],0.)),out.edge_margin,de,true);
    }
    combine(f.terrain,pose_gradient(f.dt),out.terrain,dt,false);
    Eigen::Vector3d gradient;const double margin=d.margin(center,gradient);
    combine(margin,pose_gradient(gradient),out.solid_margin,ds,true);
  }
  const auto penalty=[&](double m){return std::clamp((d.target-m)/d.target,0.,1.);};
  out.edge_penalty=penalty(out.edge_margin);out.solid_penalty=penalty(out.solid_margin);
  if(out.edge_margin>0.&&out.edge_margin<d.target)out.gradient-=2*out.edge_penalty/d.target*de;
  if(out.solid_margin>0.&&out.solid_margin<d.target)out.gradient-=2*out.solid_penalty/d.target*ds;
  out.gradient+=.5*out.terrain*dt;
  return out;
}
} // namespace reactive_stair
