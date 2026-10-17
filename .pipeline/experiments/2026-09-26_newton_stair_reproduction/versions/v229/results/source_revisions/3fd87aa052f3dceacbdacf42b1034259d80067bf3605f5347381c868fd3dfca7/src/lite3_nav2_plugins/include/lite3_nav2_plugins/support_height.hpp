#pragma once
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace lite3_nav2 {
struct SupportHeightBand {double lower,upper,preferred;};
inline SupportHeightBand supportHeightBand(double proxy,double surface,double clearance,
    double tolerance,double reference,double ceiling) {
  // The bundle quantizes heights to float16 (<=~2 mm here). Retain 5 mm
  // inside the unchanged native threshold rather than comparing at equality.
  constexpr double inset=.005;
  const double lower=std::max(surface+clearance,proxy+clearance-tolerance+inset);
  const double upper=std::min({surface+clearance+tolerance-inset,
      proxy+clearance+tolerance-inset,ceiling-.3});
  if(!std::isfinite(lower)||!std::isfinite(upper)||lower>upper)
    throw std::runtime_error("pct_support_height_empty_band");
  return {lower,upper,std::clamp(surface+reference,lower,upper)};
}
} // namespace lite3_nav2
