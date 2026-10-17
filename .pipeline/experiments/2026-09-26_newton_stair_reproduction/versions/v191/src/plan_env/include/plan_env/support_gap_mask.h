#pragma once
// Negative-only static map supplement; cannot grant support or sensor freshness.
#include <algorithm>
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
                 double radius) {
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
      // Conservative square-to-square distance, retaining subcell uncertainty.
      for (int ix=std::floor((x-.05-radius)/.1);ix<=int(std::floor((x+.05+radius)/.1));++ix)
        for (int iy=std::floor((y-.05-radius)/.1);iy<=int(std::floor((y+.05+radius)/.1));++iy) {
          const double dx=std::max({x-.05-(ix+1)*.1,ix*.1-(x+.05),0.0});
          const double dy=std::max({y-.05-(iy+1)*.1,iy*.1-(y+.05),0.0});
          if (dx*dx+dy*dy<=radius*radius+1e-12) cells_[{ix,iy}].push_back(z);
        }
    }
    if (!count) throw std::runtime_error("Empty support gap mask");
    for (auto &cell:cells_) {
      auto &zs=cell.second;std::sort(zs.begin(),zs.end());
      zs.erase(std::unique(zs.begin(),zs.end()),zs.end());
    }
  }
  bool blocks(double x,double y,double ground_z) const {
    if (!std::isfinite(x)||!std::isfinite(y)||!std::isfinite(ground_z)||
        std::max({std::abs(x),std::abs(y),std::abs(ground_z)})>10000) return true;
    auto found=cells_.find({int(std::floor(x/.1)),int(std::floor(y/.1))});
    if (found==cells_.end()) return false;
    return std::any_of(found->second.begin(),found->second.end(),[&](double z){
      return std::abs(z-ground_z)<.26;
    });
  }
 private:
  std::map<std::pair<int,int>,std::vector<double>> cells_;
};
} // namespace reactive_stair
