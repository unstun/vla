#pragma once
#include <Eigen/Core>
#include <array>
#include <algorithm>
#include <optional>
#include <cmath>
#include <limits>
namespace reactive_stair {
// Eight unchanged-radius discs cover the complete rotational envelope. This is
// a sufficient FREE certificate only; an uncertain cover never rejects a pose.
inline std::optional<std::array<Eigen::Vector2d,8>> rotationCover(double radius,double offset) {
  if(!std::isfinite(radius)||!std::isfinite(offset)||radius<=0.||offset<0.)return std::nullopt;
  const double outer=radius+offset,angle=M_PI/8;
  const double radicand=radius*radius-std::pow(outer*std::sin(angle),2);
  if(radicand<=0.)return std::nullopt;
  const double low=outer*std::cos(angle)-std::sqrt(radicand);
  const double d=low+64.*std::numeric_limits<double>::epsilon()*std::max(1.,outer);
  if(!std::isfinite(d)||d>=radius||d>outer*std::cos(angle))return std::nullopt;
  std::array<Eigen::Vector2d,8> out;
  for(int i=0;i<8;++i)out[i]=d*Eigen::Vector2d(std::cos(i*M_PI/4),std::sin(i*M_PI/4));
  return out;
}
}
