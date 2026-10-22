#pragma once
#include <algorithm>
#include <cmath>
#include <limits>

// Grid coordinates name cell centres. All physical queries share the same
// half-open partition, including interpolated optimizer samples.
inline int supportGridIndex(double q) {
  const double edge=q+.5,nearest=std::round(edge);
  return int(std::floor(std::abs(edge-nearest)<=32.*std::numeric_limits<double>::epsilon()*
      std::max(1.,std::abs(edge)) ? nearest : edge));
}
