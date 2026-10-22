#include <plan_env/static_solid.h>
#include "source_surface_geometry.h"
#include <plan_env/rotation_cover.h>
#include <pcl/kdtree/kdtree_flann.h>
#include <pcl/point_types.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <fstream>
#include <limits>
#include <map>
#include <cstdint>
#include <cstring>

#include <sstream>
#include <stdexcept>

namespace reactive_stair {
// Reuses v224's source records, floor-specific material classification and KD
// grouping. Only the solid channel is evaluated; ENV225 keeps the soft objective.
struct StaticSolidField::Data {
  SolidAssessment cylinder(const Eigen::Vector3d &center,double ground,bool hard_only,double query_radius=-1.) const;
  void buildFreeIndex();
  bool freeCylinder(const Eigen::Vector3d &center) const;
  Eigen::Vector3d free_origin=Eigen::Vector3d::Zero();
  Eigen::Vector3i free_size=Eigen::Vector3i::Zero();
  std::vector<uint8_t> free_cells;
  static constexpr double free_xy_pitch=.05,free_z_pitch=.1;
  double radius,offset,up,down,clearance,target,voxel_half;
  std::shared_ptr<source_surface::Field> source;
  struct Group {
    pcl::PointCloud<pcl::PointXYZ>::Ptr cloud{new pcl::PointCloud<pcl::PointXYZ>};
    pcl::KdTreeFLANN<pcl::PointXYZ> tree{false};
    std::vector<std::array<double,4>> floors;
    double low=1e100,high=-1e100,up_low=1e100,up_high=-1e100;
    std::vector<double> ground_events;
    Eigen::Vector3d lower=Eigen::Vector3d::Constant(1e100),upper=Eigen::Vector3d::Constant(-1e100);
  };
  std::map<std::array<int,4>,std::unique_ptr<Group>> groups;
  Eigen::Vector3d index_origin=Eigen::Vector3d::Zero();
  Eigen::Vector3i index_size=Eigen::Vector3i::Zero();
  std::vector<std::vector<const Group*>> spatial_groups;
  static constexpr double index_pitch=.5;
  double groundClassRadius(const std::vector<const Group*> &list,double ground) const {
    double answer=std::numeric_limits<double>::infinity();
    for(const auto *g:list){
      const auto it=std::lower_bound(g->ground_events.begin(),g->ground_events.end(),ground);
      if(it!=g->ground_events.end())answer=std::min(answer,*it-ground);
      if(it!=g->ground_events.begin())answer=std::min(answer,ground-*std::prev(it));
      if(answer<=1e-9)return 0.;
    }
    return answer;
  }
  const std::vector<const Group*> &candidates(const Eigen::Vector3d &p) const {
    static const std::vector<const Group*> empty;
    const Eigen::Array3d cell=((p-index_origin)/index_pitch).array().floor();
    if((cell<0).any()||(cell>=index_size.cast<double>().array()).any())return empty;
    const Eigen::Vector3i i=cell.cast<int>();
    return spatial_groups[(i.x()*index_size.y()+i.y())*index_size.z()+i.z()];
  }
  void buildSpatialIndex() {
    if(groups.empty())return;
    Eigen::Vector3d lo=Eigen::Vector3d::Constant(1e100),hi=-lo;
    for(const auto &entry:groups){lo=lo.cwiseMin(entry.second->lower);hi=hi.cwiseMax(entry.second->upper);}
    const double reach=std::hypot(radius,.5*(up+down))+target+std::sqrt(3.)*voxel_half;
    // Recall allowance only: bound the original PCL float query-centre radius
    // compensation over the entire potentially relevant source neighbourhood.
    const double expand=reach+16.*std::numeric_limits<float>::epsilon()*(std::max(lo.norm(),hi.norm())+reach+1.);
    index_origin=((lo.array()-expand)/index_pitch).floor().matrix()*index_pitch;
    const Eigen::Array3d dims=((hi.array()+expand-index_origin.array())/index_pitch).floor()+1.;
    if((dims>4096.).any()||dims.prod()>2000000.)return; // Exotic domains use original enumeration.
    index_size=dims.cast<int>();spatial_groups.resize(size_t(index_size.x())*index_size.y()*index_size.z());
    // Populate in exactly the original map iteration order, preserving ties.
    for(const auto &entry:groups) {
      const auto &g=*entry.second;
      const Eigen::Vector3i a=((g.lower.array()-expand-index_origin.array())/index_pitch).floor().cast<int>();
      const Eigen::Vector3i b=((g.upper.array()+expand-index_origin.array())/index_pitch).floor().cast<int>();
      for(int x=std::max(0,a.x());x<=std::min(index_size.x()-1,b.x());++x)
       for(int y=std::max(0,a.y());y<=std::min(index_size.y()-1,b.y());++y)
        for(int z=std::max(0,a.z());z<=std::min(index_size.z()-1,b.z());++z)
         spatial_groups[(x*index_size.y()+y)*index_size.z()+z].push_back(&g);
    }
  }
};
StaticSolidField::StaticSolidField(const std::string &path,const std::string &fnv):data_(new Data) {
  std::ifstream raw(path,std::ios::binary);
  if(!raw)throw std::runtime_error("Missing static solid evidence");
  std::string bytes((std::istreambuf_iterator<char>(raw)),{});uint64_t hash=14695981039346656037ULL;
  for(unsigned char c:bytes){hash^=c;hash*=1099511628211ULL;}
  if(fnv.empty()||std::to_string(hash)!=fnv)throw std::runtime_error("Static solid identity mismatch");
  std::istringstream input(bytes);std::string magic;auto &d=*data_;double resolution,ox,oy;
  std::istringstream peek(bytes);std::string format;peek>>format;
  if(format=="SURFACE271B"){
    std::string geometry,geometry_fnv,metadata,metadata_fnv;
    input>>magic>>d.radius>>d.offset>>d.up>>d.down>>d.clearance>>d.target
      >>std::quoted(geometry)>>geometry_fnv>>std::quoted(metadata)>>metadata_fnv;
    std::string extra;
    if(!input||(input>>extra)||d.radius!=.35||d.offset!=.18||d.up!=.55||d.down!=.35||d.clearance!=.3||d.target!=.15)
      throw std::runtime_error("Invalid source-surface profile");
    d.voxel_half=0.;d.source=std::make_shared<source_surface::Field>(geometry,metadata,geometry_fnv,metadata_fnv);return;
  }

  if(!(input>>magic>>resolution>>ox>>oy>>d.radius>>d.offset>>d.up>>d.down>>d.clearance>>d.target>>d.voxel_half)||
      (magic!="ENV224B"&&magic!="SOLID256B")||resolution<=0||d.radius<=0||d.offset<0||d.up<0||d.down<0||d.target<=0||d.voxel_half<0)
    throw std::runtime_error("Invalid static solid geometry");
  for(double x:{resolution,ox,oy,d.radius,d.offset,d.up,d.down,d.clearance,d.target,d.voxel_half})
    if(!std::isfinite(x))throw std::runtime_error("Nonfinite static solid geometry");
  size_t count=0;char type=0;
  if(!(input>>type>>count)||type!='F'||!count||count>10000000)throw std::runtime_error("Invalid floor count");
  for(size_t i=0;i<count;++i) {
    int x,y;double z,edge,terrain;input>>x>>y>>z>>edge>>terrain;
    if(!input||!std::isfinite(z)||!std::isfinite(edge)||edge<0||!std::isfinite(terrain)||terrain<0||terrain>1)
      throw std::runtime_error("Invalid floor record");
  }
  if(!(input>>type>>count)||type!='O'||count>10000000)throw std::runtime_error("Invalid solid count");
  for(size_t i=0;i<count;++i) {
    pcl::PointXYZ p;double ground,upper,up_low=-1e100,up_high=-1e100;input>>p.x>>p.y>>p.z>>ground>>upper;
    if(magic=="SOLID256B")input>>up_low>>up_high;
    if(!input||!std::isfinite(p.x)||!std::isfinite(p.y)||!std::isfinite(p.z)||!std::isfinite(ground)||!std::isfinite(upper)||upper<ground||!std::isfinite(up_low)||!std::isfinite(up_high)||up_high<up_low||
        (up_low>=-1e90&&(std::abs(up_low/.1)>std::numeric_limits<int>::max()-1.||std::abs(up_high/.1)>std::numeric_limits<int>::max()-1.))||
        (ground>=-1e90&&(std::abs(ground/.1)>std::numeric_limits<int>::max()-1.||std::abs(upper/.1)>std::numeric_limits<int>::max()-1.)))
      throw std::runtime_error("Invalid solid point");
    const int bin=ground<-1e90?std::numeric_limits<int>::min():int(std::floor(ground/.1));
    const int upper_bin=ground<-1e90?bin:int(std::floor(upper/.1));
    // Group by the complete association range, so pure same-floor material
    // can be skipped without searching its KD tree. Mixed voxels stay solid.
    const int up_bin=up_low<-1e90?std::numeric_limits<int>::min():int(std::floor(up_low/.1));
    const int up_upper_bin=up_low<-1e90?up_bin:int(std::floor(up_high/.1));
    auto &g=d.groups[{bin,upper_bin,up_bin,up_upper_bin}];if(!g)g.reset(new Data::Group);
    g->cloud->push_back(p);g->floors.push_back({{ground,upper,up_low,up_high}});
    for(int channel=0;channel<2;++channel){const int s=2*channel;
      const auto &f=g->floors.back();if(f[s]<=-1e90)continue;
      // Ordered source bands change exemption only at these two endpoints.
      // Keep even empty-interval endpoints; uncertain numerical cases simply
      // decline a cross-height certificate.
      g->ground_events.push_back(f[s+1]-.26);g->ground_events.push_back(f[s]+.26);
    }
    g->low=std::min(g->low,ground);g->high=std::max(g->high,upper);
    g->up_low=std::min(g->up_low,up_low);g->up_high=std::max(g->up_high,up_high);
    const Eigen::Vector3d q(p.x,p.y,p.z);g->lower=g->lower.cwiseMin(q);g->upper=g->upper.cwiseMax(q);
  }
  std::string extra;if(input>>extra)throw std::runtime_error("Trailing static solid data");
  for(auto &entry:d.groups){auto &g=*entry.second;
    std::sort(g.ground_events.begin(),g.ground_events.end());
    g.ground_events.erase(std::unique(g.ground_events.begin(),g.ground_events.end()),g.ground_events.end());
    g.tree.setInputCloud(g.cloud);
  }
  d.buildSpatialIndex();
  d.buildFreeIndex();
}
StaticSolidField::~StaticSolidField()=default;
#define SOLID_ACCESSOR(name) double StaticSolidField::name() const{return data_->name;}
SOLID_ACCESSOR(radius) SOLID_ACCESSOR(offset) SOLID_ACCESSOR(up) SOLID_ACCESSOR(down)
double StaticSolidField::bodyClearance() const{return data_->clearance;}
#undef SOLID_ACCESSOR
bool StaticSolidField::certifiesFreeRotation(const Eigen::Vector3d &body) const {
  if(!body.allFinite())return false;
  if(data_->source)return data_->source->circleMargin(body.x(),body.y(),body.z()-data_->clearance,data_->radius+data_->offset)>0.;
  if(data_->groups.empty())return true;
  const auto cover=rotationCover(data_->radius,data_->offset);if(!cover)return false;
  bool indexed=true;for(const auto &q:*cover)indexed&=data_->freeCylinder(body+Eigen::Vector3d(q.x(),q.y(),0.));
  if(indexed)return true;
  // The complete rotational union is this larger cylinder. This exact query
  // only proves freedom; a hit preserves ordinary orientation-specific search.
  return !data_->cylinder(body,body.z()-data_->clearance,true,data_->radius+data_->offset).collision();
}
bool StaticSolidField::impossibleAt(const Eigen::Vector3d &body) const {
  if(data_->source)return coreCollision(body); // Do not reuse voxel-SDF angular bounds for a different field.
  // Each finite-cylinder SDF is 1-Lipschitz in its centre. Rotation moves a
  // centre by at most offset*dYaw; min/capping preserves that bound. The body
  // is pi-periodic. This only proves collision at EVERY yaw, never freedom.
  constexpr int n=128;const double angular_bound=data_->offset*M_PI/(2*n);
  for(int i=0;i<n;++i)if(assess(body,i*M_PI/n).margin+angular_bound>=-1e-12)return false;
  return true;
}
bool StaticSolidField::coreCollision(const Eigen::Vector3d &body) const {
  if(!body.allFinite())throw std::runtime_error("Invalid static solid query");
  // The union of two R-cylinders at +/-d contains this central cylinder at
  // every yaw: min(|p-du|^2,|p+du|^2)<=|p|^2+d^2<=R^2.
  // Minkowski voxel padding and equal vertical intervals preserve inclusion.
  const double squared=data_->radius*data_->radius-data_->offset*data_->offset;
  if(data_->source)return squared>0.&&data_->source->circleMargin(body.x(),body.y(),body.z()-data_->clearance,std::sqrt(squared))<=0.;
  if(squared<=0.||data_->freeCylinder(body))return false;
  return data_->cylinder(body,body.z()-data_->clearance,true,std::sqrt(squared)).collision();
}
SolidAssessment StaticSolidField::assess(const Eigen::Vector3d &body,double yaw) const {return query(body,yaw,false);}
bool StaticSolidField::collides(const Eigen::Vector3d &body,double yaw) const {
  if(!body.allFinite()||!std::isfinite(yaw))throw std::runtime_error("Invalid static solid query");
  if(data_->source)return data_->source->assess(body.x(),body.y(),body.z()-data_->clearance,yaw)<=0.;
  const Eigen::Vector3d shift=data_->offset*Eigen::Vector3d(std::cos(yaw),std::sin(yaw),0.);
  for(const Eigen::Vector3d center:{Eigen::Vector3d(body-shift),Eigen::Vector3d(body+shift)}) {
    const pcl::PointXYZ q(center.x(),center.y(),center.z()+.5*(data_->down-data_->up));
    if(!std::isfinite(q.x)||!std::isfinite(q.y)||!std::isfinite(q.z))throw std::runtime_error("Static solid query outside numeric domain");
    if(!data_->freeCylinder(center)&&data_->cylinder(center,body.z()-data_->clearance,true).collision())return true;
  }
  return false;
}
bool StaticSolidField::collides(const Eigen::Vector3d &body,double yaw,StaticSolidQueryCache &cache) const {
  if(!body.allFinite()||!std::isfinite(yaw))throw std::runtime_error("Invalid static solid query");
  if(data_->source){
    if(cache.owner_.get()!=data_.get()){cache.clear();cache.owner_=data_;}
    cache.queries_+=2;return collides(body,yaw);
  }
  if(body.cwiseAbs().maxCoeff()>1e6)return collides(body,yaw);
  if(cache.owner_.get()!=data_.get()){cache.clear();cache.owner_=data_;}
  const Eigen::Vector3d shift=data_->offset*Eigen::Vector3d(std::cos(yaw),std::sin(yaw),0.);
  for(const Eigen::Vector3d center:{Eigen::Vector3d(body-shift),Eigen::Vector3d(body+shift)}){
    const pcl::PointXYZ q(center.x(),center.y(),center.z()+.5*(data_->down-data_->up));
    if(!std::isfinite(q.x)||!std::isfinite(q.y)||!std::isfinite(q.z))throw std::runtime_error("Static solid query outside numeric domain");
    ++cache.queries_;if(data_->freeCylinder(center))continue;
    const uint64_t z=uint64_t(int64_t(std::floor(center.z()/.1)));
    const double ground=body.z()-data_->clearance;
    const auto *groups=data_->spatial_groups.empty()?nullptr:&data_->candidates(Eigen::Vector3d(q.x,q.y,q.z));
    const StaticSolidQueryCache::Key key{int(std::floor(center.x()/.1)),int(std::floor(center.y()/.1)),z};
    auto found=cache.entries_.find(key);bool proven_free=false;
    if(found!=cache.entries_.end())for(unsigned i=0;i<found->second.count;++i){
      const auto &e=found->second.values[i];
      if(center.z()!=e.z&&(!groups||groups!=e.groups||std::abs(ground-e.ground)+1e-9>=e.height_slack))continue;
      const double delta=std::hypot(center.x()-e.x,center.y()-e.y,center.z()-e.z);
      // Identical Z or a proved invariant floor class fixes source exclusions.
      // The capped minimum cylinder SDF is then1-Lipschitz in XYZ. A guard only
      // declines a certificate; the unchanged exact query remains authority.
      if(delta==0.){++cache.hits_;if(e.margin<=0.)return true;proven_free=true;break;}
      if(e.margin+delta<-1e-9){++cache.hits_;return true;}
      if(e.margin-delta>1e-9){++cache.hits_;proven_free=true;break;}
    }
    if(proven_free)continue;
    // Four exact distance anchors suffice for this bucket. When their bounds
    // are inconclusive, ask the existing short-circuit Boolean query rather
    // than recomputing a full nearest distance/gradient just to replace them.
    if(found!=cache.entries_.end()&&found->second.count==4){
      if(data_->cylinder(center,ground,true).collision())return true;
      continue;
    }
    const auto assessment=data_->cylinder(center,ground,false);
    if(cache.entries_.size()>=262144)cache.entries_.clear(); // Performance-only bounded storage.
    auto &bucket=cache.entries_[key];const unsigned slot=bucket.count<4?bucket.count++:bucket.next++%4;
    bucket.values[slot]={center.x(),center.y(),center.z(),ground,assessment.margin,groups?data_->groundClassRadius(*groups,ground):0.,groups};
    if(assessment.collision())return true;
  }
  return false;
}
SolidAssessment StaticSolidField::query(const Eigen::Vector3d &body,double yaw,bool hard_only) const {
  if(!body.allFinite()||!std::isfinite(yaw))throw std::runtime_error("Invalid static solid query");
  SolidAssessment out;out.margin=data_->target;
  if(data_->source){
    source_surface::V witness={{0.,0.,0.}};const double ground=body.z()-data_->clearance;
    out.margin=data_->source->assess(body.x(),body.y(),ground,yaw,&witness);
    out.witness=Eigen::Vector3d(witness[0],witness[1],witness[2]);
    if(!hard_only&&out.margin<data_->target){
      constexpr double h=1e-5;
      for(int k=0;k<4;++k){auto a=body,b=body;double ya=yaw,yb=yaw;
        if(k<3){a(k)+=h;b(k)-=h;}else{ya+=h;yb-=h;}
        out.gradient(k)=(data_->source->assess(a.x(),a.y(),a.z()-data_->clearance,ya)-
          data_->source->assess(b.x(),b.y(),b.z()-data_->clearance,yb))/(2*h);
      }
    }
    if(!std::isfinite(out.margin)||!out.gradient.allFinite()||!out.witness.allFinite())throw std::runtime_error("Nonfinite source solid assessment");
    return out;
  }
  const Eigen::Vector3d heading(std::cos(yaw),std::sin(yaw),0.);
  for(double side:{-1.,1.}) {
    auto value=data_->cylinder(body+side*data_->offset*heading,body.z()-data_->clearance,hard_only);
    if(value.margin>=out.margin)continue;
    value.gradient(3)=side*data_->offset*(-value.gradient(0)*heading.y()+value.gradient(1)*heading.x());
    out=value;if(hard_only&&out.collision())return out;
  }
  return out;
}

SolidAssessment StaticSolidField::Data::cylinder(const Eigen::Vector3d &center,double ground,bool hard_only,double query_radius) const {
  const auto &d=*this;SolidAssessment out;out.margin=d.target;
  const double half_z=.5*(d.up+d.down),mid_z=.5*(d.down-d.up),padding=std::sqrt(3.)*d.voxel_half;
  const double cylinder_radius=query_radius>=0.?query_radius:d.radius;
  const double reach_base=std::hypot(cylinder_radius,half_z)+(hard_only?0.:d.target)+padding;
  std::vector<int> indices;std::vector<float> distances;
  const pcl::PointXYZ query(center.x(),center.y(),center.z()+mid_z);
  if(!std::isfinite(query.x)||!std::isfinite(query.y)||!std::isfinite(query.z))
    throw std::runtime_error("Static solid query outside numeric domain");
  const Eigen::Vector3d q(query.x,query.y,query.z);
  const double reach=reach_base+4.*std::numeric_limits<float>::epsilon()*std::max(1.,q.norm());
  std::vector<const Group*> fallback;
  const bool original_index=d.spatial_groups.size()&&reach_base<=std::hypot(d.radius,half_z)+d.target+padding;
  if(!original_index)for(const auto &entry:d.groups)fallback.push_back(entry.second.get());
  const auto &groups=original_index?d.candidates(q):fallback;
  for(const auto *pointer:groups) {
    const auto &g=*pointer;
    if((g.low>-1e90&&ground-g.low<.26&&g.high-ground<.26)||
        (g.up_low>-1e90&&ground-g.up_low<.26&&g.up_high-ground<.26))continue;
    const auto box_gap=(g.lower-q).cwiseMax(q-g.upper).cwiseMax(0.).eval();
    if(box_gap.squaredNorm()>reach*reach)continue;
    g.tree.radiusSearch(query,reach,indices,distances);
    for(int i:indices) {
      const auto floor=g.floors[i];
      if((floor[0]>-1e90&&std::abs(floor[0]-ground)<.26&&std::abs(floor[1]-ground)<.26)||
          (floor[2]>-1e90&&std::abs(floor[2]-ground)<.26&&std::abs(floor[3]-ground)<.26))continue;
      const auto &p=(*g.cloud)[i];
      const double dx=p.x-center.x(),dy=p.y-center.y(),dz=p.z-center.z()-mid_z;
      const double r=std::hypot(dx,dy),radial=r-cylinder_radius,vertical=std::abs(dz)-half_z;
      const double rp=std::max(radial,0.),vp=std::max(vertical,0.),outside=std::hypot(rp,vp);
      const double margin=outside+std::min(std::max(radial,vertical),0.)-padding;
      if(hard_only){if(margin<=0.){out.margin=margin;return out;}continue;}
      if(margin>=out.margin)continue;
      double dr=0.,dv=0.;
      if(outside>0.){dr=rp/outside;dv=vp/outside;}
      else if(radial>=vertical)dr=1.;else dv=1.;
      out.margin=margin;out.witness<<p.x,p.y,p.z;
      out.gradient<<(r>0.?-dr*dx/r:0.),(r>0.?-dr*dy/r:0.),-dv*(dz>=0.?1.:-1.),0.;
    }
  }
  return out;
}

void StaticSolidField::Data::buildFreeIndex() {
  if(groups.empty())return;
  Eigen::Vector3d lo=Eigen::Vector3d::Constant(1e100),hi=-lo;
  for(const auto &entry:groups){lo=lo.cwiseMin(entry.second->lower);hi=hi.cwiseMax(entry.second->upper);}
  const double padding=std::sqrt(3.)*voxel_half;
  // Both the source point and the query may lie anywhere in their XY cells.
  // This changes only a sufficient-free certificate, never the hard radius.
  const double recall=radius+padding+std::sqrt(2.)*free_xy_pitch;
  free_origin.x()=std::floor((lo.x()-recall)/free_xy_pitch)*free_xy_pitch;
  free_origin.y()=std::floor((lo.y()-recall)/free_xy_pitch)*free_xy_pitch;
  free_origin.z()=(std::floor((lo.z()-clearance-down-padding)/free_z_pitch)-1.)*free_z_pitch;
  const Eigen::Array3d dims((std::floor((hi.x()+recall-free_origin.x())/free_xy_pitch)+1.),
    (std::floor((hi.y()+recall-free_origin.y())/free_xy_pitch)+1.),
    (std::floor((hi.z()-clearance+up+padding-free_origin.z())/free_z_pitch)+2.));
  if(!dims.isFinite().all()||(dims<=0.).any()||(dims>4096.).any()||dims.prod()>64000000.)return;
  free_size=dims.cast<int>();const int nx=free_size.x(),ny=free_size.y();
  const size_t plane=size_t(nx)*ny;free_cells.resize(plane*free_size.z());
  constexpr double inf=1e12;
  std::vector<double> grid(plane),temp(plane),line(std::max(nx,ny)),result(line.size()),breaks(line.size()+1);
  std::vector<int> sites(line.size());
  // Exact squared Euclidean distance transform of occupied cell centres.
  const auto transform=[&](int n) {
    if(*std::min_element(line.begin(),line.begin()+n)>=inf/2){std::fill(result.begin(),result.begin()+n,inf);return;}
    int k=0;sites[0]=0;breaks[0]=-std::numeric_limits<double>::infinity();breaks[1]=-breaks[0];
    for(int q=1;q<n;++q) {
      double cut;
      do {const int at=sites[k];cut=((line[q]+double(q)*q)-(line[at]+double(at)*at))/(2.*(q-at));if(cut<=breaks[k])--k;else break;}while(k>=0);
      ++k;sites[k]=q;breaks[k]=cut;breaks[k+1]=std::numeric_limits<double>::infinity();
    }
    k=0;for(int q=0;q<n;++q){while(breaks[k+1]<q)++k;const double d=q-sites[k];result[q]=d*d+line[sites[k]];}
  };
  const double threshold=std::pow(recall/free_xy_pitch,2);
  const double guard=128.*std::numeric_limits<double>::epsilon()*std::max(1.,threshold);
  for(int z=0;z<free_size.z();++z) {
    std::fill(grid.begin(),grid.end(),inf);
    const double nominal=free_origin.z()+z*free_z_pitch;
    const double roundoff=64.*std::numeric_limits<double>::epsilon()*std::max(1.,std::abs(nominal));
    const double low=nominal-roundoff,high=nominal+free_z_pitch+roundoff;
    const auto covered=[&](double a,double b){return a>-1e90&&low>b-.26&&high<a+.26;};
    const double bottom=low+clearance-up-padding,top=high+clearance+down+padding;
    for(const auto &entry:groups) {
      const auto &g=*entry.second;
      if(g.upper.z()<bottom||g.lower.z()>top||covered(g.low,g.high)||covered(g.up_low,g.up_high))continue;
      for(size_t i=0;i<g.cloud->size();++i) {
        const auto &p=(*g.cloud)[i];const auto &f=g.floors[i];
        if(p.z<bottom||p.z>top||covered(f[0],f[1])||covered(f[2],f[3]))continue;
        const int x=int(std::floor((p.x-free_origin.x())/free_xy_pitch));
        const int y=int(std::floor((p.y-free_origin.y())/free_xy_pitch));
        grid[size_t(x)*ny+y]=0.;
      }
    }
    for(int x=0;x<nx;++x){for(int y=0;y<ny;++y)line[y]=grid[size_t(x)*ny+y];transform(ny);for(int y=0;y<ny;++y)temp[size_t(x)*ny+y]=result[y];}
    for(int y=0;y<ny;++y){for(int x=0;x<nx;++x)line[x]=temp[size_t(x)*ny+y];transform(nx);for(int x=0;x<nx;++x)free_cells[size_t(z)*plane+size_t(x)*ny+y]=result[x]>threshold+guard;}
  }
}
bool StaticSolidField::Data::freeCylinder(const Eigen::Vector3d &center) const {
  if(free_cells.empty())return groups.empty();
  const Eigen::Array3d q((center.x()-free_origin.x())/free_xy_pitch,(center.y()-free_origin.y())/free_xy_pitch,(center.z()-clearance-free_origin.z())/free_z_pitch);
  if((q<0.).any()||(q>=free_size.cast<double>().array()).any())return true;
  const Eigen::Vector3i i=q.floor().cast<int>();
  return free_cells[(size_t(i.z())*free_size.x()+i.x())*free_size.y()+i.y()]!=0;
}
} // namespace reactive_stair
