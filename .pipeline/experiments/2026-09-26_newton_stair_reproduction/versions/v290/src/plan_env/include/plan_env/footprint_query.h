#pragma once
#include <array>
#include <cmath>

namespace reactive_stair {
// One body envelope for static planning and live native occupancy queries.
// The caller owns evidence and query policy; this helper cannot grant clearance.
template<class Query>
int twoCylinderQuery(const std::array<double,3> &position, double yaw,
                     double offset, Query query) {
  if (!std::isfinite(yaw) || !std::isfinite(offset)) return 1;
  for (double value:position) if (!std::isfinite(value)) return 1;
  const std::array<double,3> delta{{offset*std::cos(yaw),offset*std::sin(yaw),0.0}};
  const std::array<double,3> front{{position[0]+delta[0],position[1]+delta[1],position[2]}};
  const std::array<double,3> rear{{position[0]-delta[0],position[1]-delta[1],position[2]}};
  if (query(front)!=0) return 1;
  return query(rear)!=0 ? 1 : 0;
}
}
