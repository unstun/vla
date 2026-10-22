#include <plan_env/static_solid.h>
#include <pcl/kdtree/kdtree_flann.h>
#include <pcl/point_types.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <fstream>
#include <limits>
#include <map>
#include <sstream>
#include <stdexcept>

namespace reactive_stair {
// Reuses v224's source records, floor-specific material classification and KD
// grouping. Only the solid channel is evaluated; ENV225 keeps the soft objective.
struct StaticSolidField::Data {
  double radius,offset,up,down,clearance,target,voxel_half;
  struct Group {
    pcl::PointCloud<pcl::PointXYZ>::Ptr cloud{new pcl::PointCloud<pcl::PointXYZ>};
    pcl::KdTreeFLANN<pcl::PointXYZ> tree{false};
    std::vector<std::array<double,4>> floors;
    double low=1e100,high=-1e100,up_low=1e100,up_high=-1e100;
    Eigen::Vector3d lower=Eigen::Vector3d::Constant(1e100),upper=Eigen::Vector3d::Constant(-1e100);
  };
  std::map<std::array<int,4>,std::unique_ptr<Group>> groups;
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
bool StaticSolidField::collides(const Eigen::Vector3d &body,double yaw) const {return query(body,yaw,true).collision();}
SolidAssessment StaticSolidField::query(const Eigen::Vector3d &body,double yaw,bool hard_only) const {
  if(!body.allFinite()||!std::isfinite(yaw))throw std::runtime_error("Invalid static solid query");
  const auto &d=*data_;SolidAssessment out;out.margin=d.target;
  const double half_z=.5*(d.up+d.down),mid_z=.5*(d.down-d.up),padding=std::sqrt(3.)*d.voxel_half;
  const double reach_base=std::hypot(d.radius,half_z)+(hard_only?0.:d.target)+padding,ground=body.z()-d.clearance;
  const Eigen::Vector3d heading(std::cos(yaw),std::sin(yaw),0.);
  std::vector<int> indices;std::vector<float> distances;
  for(double side:{-1.,1.}) {
    const Eigen::Vector3d center=body+side*d.offset*heading;
    const pcl::PointXYZ query(center.x(),center.y(),center.z()+mid_z);
    if(!std::isfinite(query.x)||!std::isfinite(query.y)||!std::isfinite(query.z))
      throw std::runtime_error("Static solid query outside numeric domain");
    const Eigen::Vector3d q(query.x,query.y,query.z);
    // This broad-phase allowance only compensates float query-centre rounding.
    // The signed-distance collision threshold stays exactly zero.
    const double reach=reach_base+4.*std::numeric_limits<float>::epsilon()*std::max(1.,q.norm());
    for(const auto &entry:d.groups) {
      const auto &g=*entry.second;
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
        out.gradient(3)=side*d.offset*(-out.gradient(0)*heading.y()+out.gradient(1)*heading.x());
      }
    }
  }
  return out;
}
} // namespace reactive_stair
