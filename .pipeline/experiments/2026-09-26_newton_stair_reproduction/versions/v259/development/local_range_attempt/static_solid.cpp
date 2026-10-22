#include <plan_env/static_solid.h>
#include <pcl/kdtree/kdtree_flann.h>
#include <pcl/point_types.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <fstream>
#include <limits>
#include <map>
#include <atomic>
#include <cstdint>
#include <unordered_map>
#include <sstream>
#include <stdexcept>

namespace reactive_stair {
// Reuses v224's source records, floor-specific material classification and KD
// grouping. Only the solid channel is evaluated; ENV225 keeps the soft objective.
struct StaticSolidField::Data {
  static uint64_t nextGeneration() {static std::atomic<uint64_t> n{0};return ++n;}
  const uint64_t generation=nextGeneration();
  std::array<double,2> classificationRange(const Eigen::Vector3d &center) const;
  SolidAssessment cylinder(const Eigen::Vector3d &center,double ground,bool hard_only) const;
  bool cylinderCollides(const Eigen::Vector3d &center) const;
  int certificate(const Eigen::Vector3d &center,double radius,double ground_half_span) const;
  double radius,offset,up,down,clearance,target,voxel_half;
  struct Group {
    pcl::PointCloud<pcl::PointXYZ>::Ptr cloud{new pcl::PointCloud<pcl::PointXYZ>};
    pcl::KdTreeFLANN<pcl::PointXYZ> tree{false};
    std::vector<std::array<double,4>> floors;
    double low=1e100,high=-1e100,up_low=1e100,up_high=-1e100;
    std::array<double,4> floor_min{{1e100,1e100,1e100,1e100}},floor_max{{-1e100,-1e100,-1e100,-1e100}};
    Eigen::Vector3d lower=Eigen::Vector3d::Constant(1e100),upper=Eigen::Vector3d::Constant(-1e100);
  };
  std::map<std::array<int,4>,std::unique_ptr<Group>> groups;
  Eigen::Vector3d index_origin=Eigen::Vector3d::Zero();
  Eigen::Vector3i index_size=Eigen::Vector3i::Zero();
  std::vector<std::vector<const Group*>> spatial_groups;
  static constexpr double index_pitch=.5;
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
    const double expand=reach+.2+16.*std::numeric_limits<float>::epsilon()*(std::max(lo.norm(),hi.norm())+reach+1.);
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
    for(int k=0;k<4;++k){g->floor_min[k]=std::min(g->floor_min[k],g->floors.back()[k]);g->floor_max[k]=std::max(g->floor_max[k],g->floors.back()[k]);}
    g->low=std::min(g->low,ground);g->high=std::max(g->high,upper);
    g->up_low=std::min(g->up_low,up_low);g->up_high=std::max(g->up_high,up_high);
    const Eigen::Vector3d q(p.x,p.y,p.z);g->lower=g->lower.cwiseMin(q);g->upper=g->upper.cwiseMax(q);
  }
  std::string extra;if(input>>extra)throw std::runtime_error("Trailing static solid data");
  for(auto &entry:d.groups)entry.second->tree.setInputCloud(entry.second->cloud);
  d.buildSpatialIndex();
}
StaticSolidField::~StaticSolidField()=default;
#define SOLID_ACCESSOR(name) double StaticSolidField::name() const{return data_->name;}
SOLID_ACCESSOR(radius) SOLID_ACCESSOR(offset) SOLID_ACCESSOR(up) SOLID_ACCESSOR(down)
double StaticSolidField::bodyClearance() const{return data_->clearance;}
#undef SOLID_ACCESSOR
bool StaticSolidField::impossibleAt(const Eigen::Vector3d &body) const {
  // Each finite-cylinder SDF is 1-Lipschitz in its centre. Rotation moves a
  // centre by at most offset*dYaw; min/capping preserves that bound. The body
  // is pi-periodic. This only proves collision at EVERY yaw, never freedom.
  constexpr int n=128;const double angular_bound=data_->offset*M_PI/(2*n);
  for(int i=0;i<n;++i)if(assess(body,i*M_PI/n).margin+angular_bound>=-1e-12)return false;
  return true;
}
SolidAssessment StaticSolidField::assess(const Eigen::Vector3d &body,double yaw) const {return query(body,yaw,false);}
bool StaticSolidField::collides(const Eigen::Vector3d &body,double yaw) const {
  if(!body.allFinite()||!std::isfinite(yaw))throw std::runtime_error("Invalid static solid query");
  const Eigen::Vector3d shift=data_->offset*Eigen::Vector3d(std::cos(yaw),std::sin(yaw),0.);
  return data_->cylinderCollides(body-shift)||data_->cylinderCollides(body+shift);
}
SolidAssessment StaticSolidField::query(const Eigen::Vector3d &body,double yaw,bool hard_only) const {
  if(!body.allFinite()||!std::isfinite(yaw))throw std::runtime_error("Invalid static solid query");
  SolidAssessment out;out.margin=data_->target;
  const Eigen::Vector3d heading(std::cos(yaw),std::sin(yaw),0.);
  for(double side:{-1.,1.}) {
    auto value=data_->cylinder(body+side*data_->offset*heading,body.z()-data_->clearance,hard_only);
    if(value.margin>=out.margin)continue;
    value.gradient(3)=side*data_->offset*(-value.gradient(0)*heading.y()+value.gradient(1)*heading.x());
    out=value;if(hard_only&&out.collision())return out;
  }
  return out;
}

SolidAssessment StaticSolidField::Data::cylinder(const Eigen::Vector3d &center,double ground,bool hard_only) const {
  const auto &d=*this;SolidAssessment out;out.margin=d.target;
  const double half_z=.5*(d.up+d.down),mid_z=.5*(d.down-d.up),padding=std::sqrt(3.)*d.voxel_half;
  const double reach_base=std::hypot(d.radius,half_z)+(hard_only?0.:d.target)+padding;
  std::vector<int> indices;std::vector<float> distances;
  const pcl::PointXYZ query(center.x(),center.y(),center.z()+mid_z);
  if(!std::isfinite(query.x)||!std::isfinite(query.y)||!std::isfinite(query.z))
    throw std::runtime_error("Static solid query outside numeric domain");
  const Eigen::Vector3d q(query.x,query.y,query.z);
  const double reach=reach_base+4.*std::numeric_limits<float>::epsilon()*std::max(1.,q.norm());
  std::vector<const Group*> fallback;
  if(d.spatial_groups.empty())for(const auto &entry:d.groups)fallback.push_back(entry.second.get());
  const auto &groups=d.spatial_groups.empty()?fallback:d.candidates(q);
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
      const double r=std::hypot(dx,dy),radial=r-d.radius,vertical=std::abs(dz)-half_z;
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

std::array<double,2> StaticSolidField::Data::classificationRange(const Eigen::Vector3d &center) const {
  const double ground=center.z()-clearance;
  std::array<double,2> range{{-1e100,1e100}};
  const auto boundary=[&](double value){if(value<=ground)range[0]=std::max(range[0],value);if(value>=ground)range[1]=std::min(range[1],value);};
  std::vector<const Group*> fallback;
  if(spatial_groups.empty())for(const auto &entry:groups)fallback.push_back(entry.second.get());
  // The index adds two .1m certificate cells to its recall radius. These
  // groups cover every point relevant anywhere in the same certificate cell.
  const auto &near=spatial_groups.empty()?fallback:candidates(center+Eigen::Vector3d(0.,0.,.5*(down-up)));
  for(const auto *g:near)for(int k:{0,2}) {
    if(g->floor_min[k]<-1e90)continue;
    for(int j:{k,k+1}) {
      const double offset=j==k?.26:-.26,lo=g->floor_min[j]+offset,hi=g->floor_max[j]+offset;
      if(hi<ground){range[0]=std::max(range[0],hi);continue;}
      if(lo>ground){range[1]=std::min(range[1],lo);continue;}
      for(const auto &f:g->floors)boundary(f[j]+offset);
    }
  }
  return range;
}

bool StaticSolidField::Data::cylinderCollides(const Eigen::Vector3d &center) const {
  const int result=certificate(center,0.,0.);
  return result?result<0:cylinder(center,center.z()-clearance,true).collision();
}
bool StaticSolidField::certifiesFreeSegment(const Eigen::Vector3d &a,const Eigen::Vector3d &b,double yaw) const {
  if(!a.allFinite()||!b.allFinite()||!std::isfinite(yaw))throw std::runtime_error("Invalid static solid segment");
  const Eigen::Vector3d middle=(a+b)*.5,shift=data_->offset*Eigen::Vector3d(std::cos(yaw),std::sin(yaw),0.);
  const double radius=(b-a).norm()*.5,half_z=std::abs(b.z()-a.z())*.5;
  return data_->certificate(middle-shift,radius,half_z)>0&&data_->certificate(middle+shift,radius,half_z)>0;
}
int StaticSolidField::Data::certificate(const Eigen::Vector3d &center,double radius,double ground_half_span) const {
  // A finite cylinder is 1-Lipschitz under translation while the material set
  // is fixed. Global classification intervals guarantee that fixed set; the
  // cached number is a certificate only, never an approximate returned margin.
  constexpr double pitch=.1;
  const double ground=center.z()-clearance;
  if((center.array().abs()>1e12).any())return 0;
  const double guard=64.*std::numeric_limits<double>::epsilon()*std::max(1.,std::abs(ground));
  struct Key {
    int64_t x,y,z;
    bool operator==(const Key &b)const{return x==b.x&&y==b.y&&z==b.z;}
  };
  struct Hash {size_t operator()(const Key &k)const {
    size_t h=std::hash<int64_t>{}(k.x);
    for(size_t v:{std::hash<int64_t>{}(k.y),std::hash<int64_t>{}(k.z)})h^=v+0x9e3779b97f4a7c15ULL+(h<<6)+(h>>2);
    return h;
  }};
  struct Value {Eigen::Vector3d sample;double margin;std::array<double,2> range;};
  struct Cache {uint64_t owner=0;std::unordered_map<Key,Value,Hash> values;};
  thread_local Cache cache;
  if(cache.owner!=generation){cache.values.clear();cache.owner=generation;}
  const Key key{int64_t(std::floor(center.x()/pitch)),int64_t(std::floor(center.y()/pitch)),int64_t(std::floor(center.z()/pitch))};
  auto found=cache.values.find(key);
  if(found==cache.values.end()||ground-ground_half_span<=found->second.range[0]+guard||
      ground+ground_half_span>=found->second.range[1]-guard) {
    if(cache.values.size()>=131072)cache.values.clear();
    const Eigen::Vector3d sample((key.x+.5)*pitch,(key.y+.5)*pitch,center.z());
    const auto range=classificationRange(sample);
    if(ground-ground_half_span<=range[0]+guard||ground+ground_half_span>=range[1]-guard)return 0;
    found=cache.values.insert_or_assign(key,Value{sample,cylinder(sample,ground,false).margin,range}).first;
  }
  const auto &v=found->second;
  const double delta=(center-v.sample).norm()+64.*std::numeric_limits<double>::epsilon()*std::max({1.,center.norm(),v.sample.norm(),std::abs(v.margin)});
  if(v.margin-delta-radius>0.)return 1;
  if(v.margin+delta+radius<0.)return -1;
  return 0;
}
} // namespace reactive_stair
