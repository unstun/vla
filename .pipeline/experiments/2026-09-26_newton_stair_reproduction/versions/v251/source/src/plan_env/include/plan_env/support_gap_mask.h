#pragma once
// Negative-only static map supplement; cannot grant support or sensor freshness.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iterator>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace reactive_stair {
class SupportGapMask {
 public:
  SupportGapMask(const std::string &path, const std::string &expected_fnv,
                 double radius) : radius_squared_(radius*radius) {
    if (!std::isfinite(radius) || radius < 0 || radius > 2)
      throw std::runtime_error("Invalid support gap radius");
    std::ifstream file(path, std::ios::binary);
    if (!file) throw std::runtime_error("Missing support gap mask");
    std::string data((std::istreambuf_iterator<char>(file)), {});
    if (data.empty() || data.size() > 20*1024*1024)
      throw std::runtime_error("Invalid support gap mask size");
    uint64_t fnv=UINT64_C(14695981039346656037);
    for (unsigned char b:data) { fnv^=b; fnv*=UINT64_C(1099511628211); }
    if (std::to_string(fnv)!=expected_fnv)
      throw std::runtime_error("Support gap mask identity mismatch");
    std::istringstream input(data); std::string line; size_t count=0;
    while (std::getline(input,line)) {
      std::istringstream row(line); double x,y,z;std::string extra;
      if (!(row>>x>>y>>z) || row>>extra || !std::isfinite(x) || !std::isfinite(y) ||
          !std::isfinite(z) || std::max({std::abs(x),std::abs(y),std::abs(z)})>10000)
        throw std::runtime_error("Invalid support gap record");
      ++count;
      const auto source=sources_.size();sources_.push_back({{x,y,z}});
      const double reach=2.*radius; // Broad phase also serves the existing soft margin channel.
      // Conservative bins are a broad phase only. Retain source-cell
      // uncertainty, then test the actual continuous cylinder centre below.
      for (int ix=int(std::floor((x-.05-reach)/.1))-1;ix<=int(std::floor((x+.05+reach)/.1))+1;++ix)
        for (int iy=int(std::floor((y-.05-reach)/.1))-1;iy<=int(std::floor((y+.05+reach)/.1))+1;++iy) {
          const double dx=std::max({x-.05-(ix+1)*.1,ix*.1-(x+.05),0.0});
          const double dy=std::max({y-.05-(iy+1)*.1,iy*.1-(y+.05),0.0});
          if (dx*dx+dy*dy<=reach*reach+1e-12) cells_[{ix,iy}].push_back(source);
        }
    }
    if (!count) throw std::runtime_error("Empty support gap mask");
  }
  bool blocks(double x,double y,double ground_z) const {
    if (!std::isfinite(x)||!std::isfinite(y)||!std::isfinite(ground_z)||
        std::max({std::abs(x),std::abs(y),std::abs(ground_z)})>10000) return true;
    auto found=cells_.find({int(std::floor(x/.1)),int(std::floor(y/.1))});
    if (found==cells_.end()) return false;
    return std::any_of(found->second.begin(),found->second.end(),[&](size_t source){
      const auto &gap=sources_[source];
      if(std::abs(gap[2]-ground_z)>=.26)return false;
      const double dx=std::max(std::abs(x-gap[0])-.05,0.);
      const double dy=std::max(std::abs(y-gap[1])-.05,0.);
      return dx*dx+dy*dy<=radius_squared_+1e-12;
    });
  }
  // Signed penetration used by the optimizer only after blocks() refuses.
  // The actual .35 m domain is identical to blocks(); no positive clearance
  // band is introduced. Coordinates and derivatives are world metres.
  double clearanceMargin(double x,double y,double ground_z,double cap,
      std::array<double,2> &gradient) const {
    gradient={{0.,0.}};double margin=cap;
    if(!std::isfinite(x)||!std::isfinite(y)||!std::isfinite(ground_z)||!std::isfinite(cap)||cap<0.||
        std::max({std::abs(x),std::abs(y),std::abs(ground_z)})>10000)
      throw std::runtime_error("Invalid support gap query");
    const auto inspect=[&](size_t source) {
      const auto &gap=sources_[source];if(std::abs(gap[2]-ground_z)>=.26)return;
      const double a=x-gap[0],b=y-gap[1];
      const double dx=std::max(std::abs(a)-.05,0.),dy=std::max(std::abs(b)-.05,0.);
      const double distance=std::hypot(dx,dy);double value=distance-std::sqrt(radius_squared_);
      std::array<double,2> g{{0.,0.}};
      if(distance>0.)g={{std::copysign(dx,a)/distance,std::copysign(dy,b)/distance}};
      else if(std::abs(a)>=std::abs(b)){value-=.05-std::abs(a);g[0]=std::copysign(1.,a);}
      else {value-=.05-std::abs(b);g[1]=std::copysign(1.,b);}
      if(value<margin||(cap==0.&&margin==0.&&dx*dx+dy*dy<=radius_squared_+1e-12)) {
        margin=std::min(value,cap);gradient=g;
      }
    };
    if(cap>std::sqrt(radius_squared_)) {
      // Larger requested soft horizons still use the exact source geometry.
      for(size_t source=0;source<sources_.size();++source)inspect(source);
    } else {
      auto found=cells_.find({int(std::floor(x/.1)),int(std::floor(y/.1))});
      if(found!=cells_.end())for(size_t source:found->second)inspect(source);
    }
    return margin;
  }
  double penetrationMargin(double x,double y,double ground_z,std::array<double,2> &gradient) const {
    return clearanceMargin(x,y,ground_z,0.,gradient);
  }
 private:
  double radius_squared_;
  std::vector<std::array<double,3>> sources_;
  std::map<std::pair<int,int>,std::vector<size_t>> cells_;
};
} // namespace reactive_stair
