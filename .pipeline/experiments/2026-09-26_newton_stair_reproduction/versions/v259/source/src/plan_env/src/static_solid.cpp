#include <plan_env/static_solid.h>
#include <pcl/kdtree/kdtree_flann.h>
#include <pcl/point_types.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <fstream>
#include <limits>
#include <map>
#include <cstdint>

#include <sstream>
#include <stdexcept>

namespace reactive_stair {
// Reuses v224's source records, floor-specific material classification and KD
// grouping. Only the solid channel is evaluated; ENV225 keeps the soft objective.
struct StaticSolidField::Data {
  SolidAssessment cylinder(const Eigen::Vector3d &center,double ground,bool hard_only) const;
  void buildFreeIndex();
  bool freeCylinder(const Eigen::Vector3d &center) const;
  Eigen::Vector3d free_origin=Eigen::Vector3d::Zero();
  Eigen::Vector3i free_size=Eigen::Vector3i::Zero();
  std::vector<uint8_t> free_cells;
  static constexpr double free_xy_pitch=.05,free_z_pitch=.1;
  double radius,offset,up,down,clearance,target,voxel_half;
  struct Group {
    pcl::PointCloud<pcl::PointXYZ>::Ptr cloud{new pcl::PointCloud<pcl::PointXYZ>};
    pcl::KdTreeFLANN<pcl::PointXYZ> tree{false};
    std::vector<std::array<double,4>> floors;
    double low=1e100,high=-1e100,up_low=1e100,up_high=-1e100;
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
    g->low=std::min(g->low,ground);g->high=std::max(g->high,upper);
    g->up_low=std::min(g->up_low,up_low);g->up_high=std::max(g->up_high,up_high);
    const Eigen::Vector3d q(p.x,p.y,p.z);g->lower=g->lower.cwiseMin(q);g->upper=g->upper.cwiseMax(q);
  }
  std::string extra;if(input>>extra)throw std::runtime_error("Trailing static solid data");
  for(auto &entry:d.groups)entry.second->tree.setInputCloud(entry.second->cloud);
  d.buildSpatialIndex();
  d.buildFreeIndex();
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
  for(const Eigen::Vector3d center:{Eigen::Vector3d(body-shift),Eigen::Vector3d(body+shift)}) {
    const pcl::PointXYZ q(center.x(),center.y(),center.z()+.5*(data_->down-data_->up));
    if(!std::isfinite(q.x)||!std::isfinite(q.y)||!std::isfinite(q.z))throw std::runtime_error("Static solid query outside numeric domain");
    if(!data_->freeCylinder(center)&&data_->cylinder(center,body.z()-data_->clearance,true).collision())return true;
  }
  return false;
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
