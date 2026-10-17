#include <plan_env/environmental_field.h>
#include <pcl/kdtree/kdtree_flann.h>
#include <pcl/point_types.h>
#include <algorithm>
#include <cmath>
#include <fstream>
#include <map>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <vector>

namespace reactive_stair {
struct EnvironmentalField::Data {
  struct Floor {double z,edge,terrain;};
  double resolution,ox,oy,radius,offset,up,down,clearance,target,voxel_half;
  std::map<std::pair<int,int>,std::vector<Floor>> floors;
  pcl::PointCloud<pcl::PointXYZ>::Ptr points{new pcl::PointCloud<pcl::PointXYZ>};
  std::vector<std::pair<double,double>> supporting_floor;
  struct Group {
    pcl::PointCloud<pcl::PointXYZ>::Ptr cloud{new pcl::PointCloud<pcl::PointXYZ>};
    pcl::KdTreeFLANN<pcl::PointXYZ> tree{false};
    std::vector<int> original;
    double low=1e100,high=-1e100;
    Eigen::Vector3d lower=Eigen::Vector3d::Constant(1e100),upper=Eigen::Vector3d::Constant(-1e100);
  };
  std::map<int,std::unique_ptr<Group>> groups;
  // Bilinear interpolation never mixes distant building floors.
  Floor floor(double x,double y,double z,bool &known) const {
    const double gx=(x-ox)/resolution-.5,gy=(y-oy)/resolution-.5;
    if(gx<std::numeric_limits<int>::min()+1. || gx>std::numeric_limits<int>::max()-1. ||
       gy<std::numeric_limits<int>::min()+1. || gy>std::numeric_limits<int>::max()-1.) {
      known=false;return {z,0.,1.};
    }
    const int ix=int(std::floor(gx)),iy=int(std::floor(gy));
    Floor result{z,0,0};known=true;
    for(int dx=0;dx<2;++dx)for(int dy=0;dy<2;++dy) {
      const double w=(dx?gx-ix:1-gx+ix)*(dy?gy-iy:1-gy+iy);
      if(w<1e-12)continue;
      auto found=floors.find({ix+dx,iy+dy});const Floor *selected=nullptr;double best=.260000001;bool tie=false;
      if(found!=floors.end())for(const auto &f:found->second) {
        const double d=std::abs(f.z-z);
        if(d<best-1e-9){selected=&f;best=d;tie=false;}
        else if(std::abs(d-best)<=1e-9)tie=true;
      }
      if(!selected||tie) {known=false;result.terrain+=w;continue;}
      result.edge+=w*selected->edge;result.terrain+=w*selected->terrain;
    }
    return result;
  }
};
EnvironmentalField::EnvironmentalField(const std::string &path,const std::string &fnv):data_(new Data) {
  std::ifstream raw(path,std::ios::binary);if(!raw)throw std::runtime_error("Missing environmental field");
  std::string bytes((std::istreambuf_iterator<char>(raw)),{});uint64_t hash=14695981039346656037ULL;
  for(unsigned char c:bytes){hash^=c;hash*=1099511628211ULL;}
  if(fnv.empty()||std::to_string(hash)!=fnv)throw std::runtime_error("Environmental field identity mismatch");
  std::istringstream input(bytes);std::string magic;auto &d=*data_;
  if(!(input>>magic>>d.resolution>>d.ox>>d.oy>>d.radius>>d.offset>>d.up>>d.down>>d.clearance>>d.target>>d.voxel_half) ||
      magic!="ENV224B"||d.resolution<=0||d.radius<=0||d.target<=0||d.offset<0||d.up<0||d.down<0||d.voxel_half<0)
    throw std::runtime_error("Invalid environmental geometry");
  for(double x:{d.resolution,d.ox,d.oy,d.radius,d.offset,d.up,d.down,d.clearance,d.target,d.voxel_half})
    if(!std::isfinite(x))throw std::runtime_error("Nonfinite environmental geometry");
  size_t count=0;char type=0;
  if(!(input>>type>>count)||type!='F'||count==0||count>10000000)throw std::runtime_error("Invalid floor count");
  for(size_t i=0;i<count;++i){int x,y;Data::Floor f;input>>x>>y>>f.z>>f.edge>>f.terrain;
    if(!input||!std::isfinite(f.z)||!std::isfinite(f.edge)||f.edge<0||!std::isfinite(f.terrain)||f.terrain<0||f.terrain>1)throw std::runtime_error("Invalid floor record");
    d.floors[{x,y}].push_back(f);}
  if(!(input>>type>>count)||type!='O'||count>10000000)throw std::runtime_error("Invalid solid count");
  for(size_t i=0;i<count;++i){pcl::PointXYZ p;double ground,upper;input>>p.x>>p.y>>p.z>>ground>>upper;
    if(!input||!std::isfinite(p.x)||!std::isfinite(p.y)||!std::isfinite(p.z)||!std::isfinite(ground)||!std::isfinite(upper)||upper<ground)throw std::runtime_error("Invalid solid point");d.points->push_back(p);d.supporting_floor.emplace_back(ground,upper);}
  std::string extra;if(input>>extra)throw std::runtime_error("Trailing environmental data");
  for(size_t i=0;i<d.points->size();++i) {
    const auto range=d.supporting_floor[i];const auto &p=(*d.points)[i];
    const int bin=range.first<-1e90 ? std::numeric_limits<int>::min() : int(std::floor(range.first/.1));
    auto &group=d.groups[bin];if(!group)group.reset(new Data::Group);
    group->cloud->push_back(p);group->original.push_back(int(i));
    group->low=std::min(group->low,range.first);group->high=std::max(group->high,range.second);
    const Eigen::Vector3d position(p.x,p.y,p.z);
    group->lower=group->lower.cwiseMin(position);group->upper=group->upper.cwiseMax(position);
  }
  for(auto &entry:d.groups)entry.second->tree.setInputCloud(entry.second->cloud);
}
EnvironmentalField::~EnvironmentalField()=default;
#define FIELD_ACCESSOR(name) double EnvironmentalField::name() const{return data_->name;}
FIELD_ACCESSOR(radius) FIELD_ACCESSOR(offset) FIELD_ACCESSOR(up) FIELD_ACCESSOR(down) FIELD_ACCESSOR(target)
double EnvironmentalField::bodyClearance() const{return data_->clearance;}
#undef FIELD_ACCESSOR
EnvironmentalAssessment EnvironmentalField::assess(const Eigen::Vector3d &body,double yaw) const {
  if(!body.allFinite()||!std::isfinite(yaw))throw std::runtime_error("Invalid environmental query");
  const auto &d=*data_;EnvironmentalAssessment out;out.floor_known=true;
  out.edge_margin=out.solid_margin=d.target;
  const Eigen::Vector3d heading(std::cos(yaw),std::sin(yaw),0.);
  for(double sign:{-1.,1.}) {
    const Eigen::Vector3d center=body+sign*d.offset*heading;bool known;
    const auto f=d.floor(center.x(),center.y(),body.z()-d.clearance,known);
    out.floor_known &= known;out.terrain=std::max(out.terrain,f.terrain);
    out.edge_margin=std::min(out.edge_margin,f.edge-d.radius);
    if(d.points->empty())continue;
    const double half_z=.5*(d.up+d.down),mid_z=.5*(d.down-d.up);
    pcl::PointXYZ query(center.x(),center.y(),center.z()+mid_z);
    std::vector<int> indices;std::vector<float> distances;
    const double padding=std::sqrt(3.)*d.voxel_half;
    const double search_radius=std::hypot(d.radius,half_z)+d.target+padding;
    const double ground=body.z()-d.clearance;
    for(const auto &entry:d.groups) {
      const auto &group=*entry.second;
      if(group.low>-1e90 && ground-group.low<.26 && group.high-ground<.26)continue;
      const Eigen::Vector3d point(query.x,query.y,query.z);
      const auto gap=(group.lower-point).cwiseMax(point-group.upper).cwiseMax(0.).eval();
      if(gap.squaredNorm()>search_radius*search_radius)continue;
      group.tree.radiusSearch(query,search_radius,indices,distances);
      for(int local:indices){const int i=group.original[local];const auto &p=(*d.points)[i];
      // The static PCD also contains material below its mapped support surface.
      // Exclude it only for that associated level, never for another floor.
      // Mixed voxels retain the no-association sentinel. Live hard occupancy is unchanged.
      if(d.supporting_floor[i].first>-1e90 &&
          std::abs(d.supporting_floor[i].first-(body.z()-d.clearance))<.26 &&
          std::abs(d.supporting_floor[i].second-(body.z()-d.clearance))<.26)continue;
      const double radial=std::hypot(p.x-center.x(),p.y-center.y())-d.radius;
      const double vertical=std::abs(p.z-center.z()-mid_z)-half_z;
      const double distance=std::hypot(std::max(radial,0.),std::max(vertical,0.))+
          std::min(std::max(radial,vertical),0.)-padding;
      out.solid_margin=std::min(out.solid_margin,distance);
      }
    }
  }
  const auto penalty=[&](double margin){return std::clamp((d.target-margin)/d.target,0.,1.);};
  out.edge_penalty=penalty(out.edge_margin);out.solid_penalty=penalty(out.solid_margin);
  return out;
}
} // namespace reactive_stair
