#pragma once
#include <Eigen/Core>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <tuple>
#include <vector>

namespace lite3_nav2 {
// Exact original-PCD cylinder witness, reusing v224's material association,
// source-volume orientation and conservative voxel padding. This is a veto;
// support and live observed-space permission remain native SCAN decisions.
class StaticBodyGeometry {
  struct Point {double x,y,z,low,high;};
  std::map<std::tuple<int,int,int>,std::vector<Point>> cells_;
  double radius_,offset_,up_,down_,clearance_,padding_;
public:
  StaticBodyGeometry(const std::string &path,const std::string &fnv) {
    std::ifstream f(path,std::ios::binary);
    if(!f)throw std::runtime_error("pct_missing_static_body_geometry");
    const std::string bytes((std::istreambuf_iterator<char>(f)),{});
    uint64_t hash=UINT64_C(14695981039346656037);
    for(unsigned char c:bytes){hash^=c;hash*=UINT64_C(1099511628211);}
    if(fnv.empty()||std::to_string(hash)!=fnv)throw std::runtime_error("pct_static_body_identity_mismatch");
    std::istringstream in(bytes);std::string magic;double resolution,ox,oy,target,half;
    if(!(in>>magic>>resolution>>ox>>oy>>radius_>>offset_>>up_>>down_>>clearance_>>target>>half)||magic!="ENV224B")
      throw std::runtime_error("pct_invalid_static_body_geometry");
    // The candidate is bound to the unchanged native shape, not an alternative
    // collision envelope or an approximate trilinear atlas threshold.
    if(std::abs(radius_-.35)>1e-12||std::abs(offset_-.18)>1e-12||
       std::abs(up_-.55)>1e-12||std::abs(down_-.35)>1e-12||
       std::abs(clearance_-.3)>1e-12||!std::isfinite(half)||half<0||half>.1)
      throw std::runtime_error("pct_static_body_shape_mismatch");
    padding_=std::sqrt(3.)*half;
    char type;size_t count;std::string line;
    if(!(in>>type>>count)||type!='F'||count>10000000)throw std::runtime_error("pct_invalid_static_body_floor_count");
    std::getline(in,line);
    for(size_t i=0;i<count;++i)if(!std::getline(in,line))throw std::runtime_error("pct_truncated_static_body_floors");
    if(!(in>>type>>count)||type!='O'||!count||count>10000000)throw std::runtime_error("pct_invalid_static_body_point_count");
    for(size_t i=0;i<count;++i) {
      Point p;if(!(in>>p.x>>p.y>>p.z>>p.low>>p.high)||
          !std::isfinite(p.x)||!std::isfinite(p.y)||!std::isfinite(p.z)||
          !std::isfinite(p.low)||!std::isfinite(p.high)||p.high<p.low||
          std::max({std::abs(p.x),std::abs(p.y),std::abs(p.z)})>10000)
        throw std::runtime_error("pct_invalid_static_body_point");
      cells_[{int(std::floor(p.x/.5)),int(std::floor(p.y/.5)),int(std::floor(p.z/.5))}].push_back(p);
    }
    if(in>>line)throw std::runtime_error("pct_trailing_static_body_geometry");
  }
  bool clear(const Eigen::Vector3d &body,double yaw) const {
    if(!body.allFinite()||!std::isfinite(yaw)||body.cwiseAbs().maxCoeff()>10000)return false;
    const double half_z=.5*(up_+down_),mid=.5*(down_-up_),ground=body.z()-clearance_;
    for(double sign:{-1.,1.}) {
      const Eigen::Vector3d c=body+sign*offset_*Eigen::Vector3d(std::cos(yaw),std::sin(yaw),0.);
      for(int x=int(std::floor((c.x()-radius_-padding_)/.5));x<=int(std::floor((c.x()+radius_+padding_)/.5));++x)
        for(int y=int(std::floor((c.y()-radius_-padding_)/.5));y<=int(std::floor((c.y()+radius_+padding_)/.5));++y)
          for(int z=int(std::floor((c.z()-up_-padding_)/.5));z<=int(std::floor((c.z()+down_+padding_)/.5));++z) {
            const auto found=cells_.find({x,y,z});if(found==cells_.end())continue;
            for(const auto &p:found->second) {
              if(p.low>-1e90&&std::abs(p.low-ground)<.26&&std::abs(p.high-ground)<.26)continue;
              const double radial=std::hypot(p.x-c.x(),p.y-c.y())-radius_;
              const double vertical=std::abs(p.z-c.z()-mid)-half_z;
              const double distance=std::hypot(std::max(radial,0.),std::max(vertical,0.))+
                std::min(std::max(radial,vertical),0.)-padding_;
              if(distance<=0)return false;
            }
          }
    }
    return true;
  }
};
}
