#include "map_manager/dense_elevation_map.h"

#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

void DenseElevationMap::Init(const double resolution, const int num_layers,
                             const Eigen::MatrixXd& cost_map,
                             const Eigen::MatrixXd& ele_mask,
                             const Eigen::MatrixXd& height,
                             const Eigen::MatrixXd& ceiling,
                             const Eigen::MatrixXd& grad_x,
                             const Eigen::MatrixXd& grad_y) {
  resolution_ = resolution;
  resolution_inv_ = 1.0 / resolution;
  max_layers_ = num_layers;
  max_x_ = cost_map.cols();
  max_y_ = cost_map.rows() / num_layers;
  xy_size_ = max_x_ * max_y_;
  cost_ = cost_map;
  ele_mask_ = ele_mask;
  height_ = height;
  ceiling_ = ceiling;
  grad_x_ = grad_x;
  grad_y_ = grad_y;

  printf("max layers: %d, max_x: %d, max_y: %d\n", max_layers_, max_x_, max_y_);
}

double DenseElevationMap::GetRealCost(int layer, double x, double y,
                                      Eigen::Vector2d* grad, int* new_layer) {
  const int col = index(x);
  int row = index(y) + layer * max_y_;
  double cost = cost_(row, col);

  // * grid that is unlikely to be the border between different layers
  if (cost < safe_cost_threshold_) {
    if (grad != nullptr) {
      *grad = Eigen::Vector2d(grad_x_(row, col), grad_y_(row, col));
    }
    return cost;
  }

  // double ele_value = ele_mask_(row, col);
  double this_height = height_(row, col);
  int real_row = row;
  int real_layer = layer;

  if (layer > 0) {
    int lower_row = row - max_y_;
    double lower_height = height_(lower_row, col);
    if (abs(this_height - lower_height) < resolution_) {
      double lower_cost = cost_(lower_row, col);
      if (lower_cost < cost) {
        cost = lower_cost;
        real_row = lower_row;
        real_layer = layer - 1;
      }
    }
  }

  if (layer < max_layers_ - 1) {
    int upper_row = row + max_y_;
    double upper_height = height_(upper_row, col);
    if (abs(this_height - upper_height) < resolution_) {
      double upper_cost = cost_(upper_row, col);
      if (upper_cost < cost) {
        cost = upper_cost;
        real_row = upper_row;
        real_layer = layer + 1;
      }
    }
  }

  if (grad != nullptr) {
    *grad = Eigen::Vector2d(grad_x_(real_row, col), grad_y_(real_row, col));
  }
  if (new_layer != nullptr) {
    *new_layer = real_layer;
  }

  return cost;
}

double DenseElevationMap::GetRealCostSafe(int layer, double x, double y,
                                          const double height_hint) {
  int real_layer = UpdateLayerSafe(layer, x, y, height_hint);
  return cost_(index_y_safe(y) + real_layer * max_y_, index_x_safe(x));
}

int DenseElevationMap::UpdateLayer(const int layer, const double x,
                                   const double y) {
  const int col = index(x);
  int row = index(y) + layer * max_y_;
  double cost = cost_(row, col);
  int real_layer = layer;
  double lower_cost = 99;
  double upper_cost = 99;
  double lower_height = -99;
  double upper_height = -99;

  // * grid that is unlikely to be the border between different layers
  if (cost < safe_cost_threshold_) {
    if (debug_) {
      printf("cost < safe_cost_threshold_!, cost: %f\n", cost);
    }
    return layer;
  }

  // double ele_value = ele_mask_(row, col);
  double this_height = height_(row, col);

  if (layer > 0) {
    int lower_row = row - max_y_;
    lower_height = height_(lower_row, col);
    if (abs(this_height - lower_height) < resolution_ || this_height < -50) {
      lower_cost = cost_(row - max_y_, col);
      if (lower_cost + offset_ < cost) {
        real_layer = layer - 1;
        cost = lower_cost;
      }
    }
  }

  if (layer < max_layers_ - 1) {
    int upper_row = row + max_y_;
    upper_height = height_(upper_row, col);
    if (abs(this_height - upper_height) < resolution_ || this_height < -50) {
      upper_cost = cost_(row + max_y_, col);
      if (upper_cost + offset_ < cost) {
        real_layer = layer + 1;
      }
    }
  }

  if (debug_) {
    // std::cout << ele_mask_ << std::endl;
    printf(
        "layer: %d, x: %f, y: %f, row: %d, col: %d, cost: %f, lower_cost: %f, "
        "upper_cost: %f, height: %f\n, lower_height: %f, upper_height: %f\n",
        layer, x, y, index(y), col, cost_(row, col), lower_cost, upper_cost,
        height_(row, col), lower_height, upper_height);
  }

  return real_layer;
}

// int DenseElevationMap::UpdateLayerSafe(const int layer, const double x,
//                                        const double y,
//                                        const double height_hint) {
//   const int col = index(x);
//   int row = index(y) + layer * max_y_;
//   double cost = cost_(row, col);
//   int real_layer = layer;
//   double lower_cost = 99;
//   double upper_cost = 99;
//   double lower_height = -1e6;
//   double upper_height = -1e6;

//   // * grid that is unlikely to be the border between different layers
//   if (cost < safe_cost_threshold_) {
//     if (debug_) {
//       printf("cost < safe_cost_threshold_!, cost: %f\n", cost);
//     }
//     return layer;
//   }

//   double this_height = height_(row, col);

//   // * judge height difference

//   if (abs(height_hint - this_height) > 5 * resolution_) {
//     // * means this grid is not valid in this layer, search up and down
//     if (layer > 0) {
//       lower_height = height_(row - max_y_, col);
//     }
//     if (layer < max_layers_ - 1) {
//       upper_height = height_(row + max_y_, col);
//     }

//     if (abs(lower_height - height_hint) < abs(upper_height - height_hint)) {
//       if (abs(height_hint - lower_height) < 2 * resolution_) {
//         real_layer = layer - 1;
//       }
//     } else {
//       if (abs(height_hint - upper_height) < 2 * resolution_) {
//         real_layer = layer + 1;
//       }
//     }

//     if (debug_) {
//       // std::cout << ele_mask_ << std::endl;
//       printf(
//           "layer: %d, x: %f, y: %f, row: %d, col: %d, cost: %f, lower_cost: "
//           "%f, "
//           "upper_cost: %f, height: %f\n, lower_height: %f, upper_height:
//           %f\n", layer, x, y, index(y), col, cost_(row, col), lower_cost,
//           upper_cost, height_(row, col), lower_height, upper_height);
//     }
//     return real_layer;
//   }

//   // * valid grid
//   if (layer > 0) {
//     int lower_row = row - max_y_;
//     lower_height = height_(lower_row, col);
//     if (abs(this_height - lower_height) < 1.5 * resolution_ ||
//         this_height < -50) {
//       lower_cost = cost_(row - max_y_, col);
//       if (lower_cost + offset_ < cost) {
//         real_layer = layer - 1;
//         cost = lower_cost;
//       }
//     }
//   }

//   if (layer < max_layers_ - 1) {
//     int upper_row = row + max_y_;
//     upper_height = height_(upper_row, col);
//     if (abs(this_height - upper_height) < 1.5 * resolution_ ||
//         this_height < -50) {
//       upper_cost = cost_(row + max_y_, col);
//       if (upper_cost + offset_ < cost) {
//         real_layer = layer + 1;
//       }
//     }
//   }

//   if (debug_) {
//     // std::cout << ele_mask_ << std::endl;
//     printf(
//         "layer: %d, x: %f, y: %f, row: %d, col: %d, cost: %f, lower_cost: %f,
//         " "upper_cost: %f, height: %f\n, lower_height: %f, upper_height:
//         %f\n", layer, x, y, index(y), col, cost_(row, col), lower_cost,
//         upper_cost, height_(row, col), lower_height, upper_height);
//   }

//   return real_layer;
// }

int DenseElevationMap::UpdateLayerSafe(const int layer, const double x,
                                       const double y,
                                       const double height_hint) {
  if(physical_support_mode_) {
    const int xcell=index_x_safe(x),ycell=index_y_safe(y);
    int selected=layer;double best=physical_height_limit_;
    for(int k=0;k<max_layers_;++k) {
      const double h=height_(k*max_y_+ycell,xcell);
      if(h<=-50.)continue;
      const double d=std::abs(h-height_hint);
      if(d<best){best=d;selected=k;}
    }
    return selected;
  }
  const int col = index_x_safe(x);
  int row = index_y_safe(y) + layer * max_y_;
  double cost = cost_(row, col);
  int real_layer = layer;
  double this_height = GetHeight(layer, x, y);
  bool unsafe_grid =
      (this_height < -50) || (abs(this_height - height_hint) > 5 * resolution_);

  // * grid that is unlikely to be the border between different layers
  if ((!unsafe_grid) && (cost < safe_cost_threshold_)) {
    if (debug_) {
      printf("cost < safe_cost_threshold_!, cost: %f, height: %f\n", cost,
             height_(row, col));
    }
    return layer;
  }

  // * for unsafe grid, both cost and height are not reliable

  double upper_height = -200;
  double lower_height = -200;
  double lower_cost = 1000;
  double upper_cost = 1000;

  double min_cost = unsafe_grid ? 1000 : cost;

  if (layer > 0) {
    lower_height = height_(row - max_y_, col);
    lower_cost = cost_(row - max_y_, col);
    // * filter out jump down scenario
    if (abs(height_hint - lower_height) < 5 * resolution_) {
      if ((abs(this_height - lower_height) < 1.5 * resolution_ &&
           lower_cost < cost) ||
          (unsafe_grid && lower_cost < 2 * safe_cost_threshold_)) {
        real_layer = layer - 1;
        min_cost = lower_cost;
      }
    }
  }

  if (layer < max_layers_ - 1) {
    upper_height = height_(row + max_y_, col);
    upper_cost = cost_(row + max_y_, col);
    if (abs(height_hint - upper_height) < 5 * resolution_) {
      if ((abs(this_height - upper_height) < 1.5 * resolution_ &&
           upper_cost < cost) ||
          (unsafe_grid && upper_cost < 2 * safe_cost_threshold_)) {
        if (upper_cost < min_cost) {
          real_layer = layer + 1;
          min_cost = upper_cost;
        }
      }
    }
  }

  if (debug_) {
    // std::cout << ele_mask_ << std::endl;
    printf(
        "layer: %d -> %d, x: %f, y: %f, row: %d, col: %d, cost: %f, "
        "lower_cost: %f, "
        "upper_cost: %f, height: %f\n, hint: %f, lower_height: %f, "
        "upper_height: %f\n",
        layer, real_layer, x, y, index(y), col, cost_(row, col), lower_cost,
        upper_cost, height_(row, col), height_hint, lower_height, upper_height);
  }

  return real_layer;
}

double DenseElevationMap::GetHeight(const int layer, const double x,
                                    const double y) {
  return height_(index_y_safe(y) + layer * max_y_, index_x_safe(x));
}

double DenseElevationMap::GetHeightSafe(const int layer, const double x,
                                        const double y,
                                        const double height_hint) {
  double new_height =
      height_(index_y_safe(y) + layer * max_y_, index_x_safe(x));

  if (abs(new_height - height_hint) > 6 * resolution_) {
    return height_hint;
  }

  return new_height;
}

double DenseElevationMap::GetCeiling(const int layer, const double x,
                                     const double y) {
  return ceiling_(index_y_safe(y) + layer * max_y_, index_x_safe(x));
}

double DenseElevationMap::GetValueBilinear(const int layer, const double x,
                                           const double y,
                                           Eigen::Vector2d* grad) {
  double x_lb = std::max(std::floor(x - 0.5), 0.0);
  double y_lb = std::max(std::floor(y - 0.5), 0.0);

  double value[2][2];
  for (int x = 0; x < 2; ++x) {
    for (int y = 0; y < 2; ++y) {
      value[x][y] = GetRealCost(layer, x_lb + x, y_lb + y, grad);
    }
  }

  Eigen::Vector2d diff(x - x_lb, y - y_lb);

  double y0 = (1 - diff(0)) * value[0][0] + diff(0) * value[1][0];
  double y1 = (1 - diff(0)) * value[0][1] + diff(0) * value[1][1];
  double x0 = (1 - diff(1)) * value[0][0] + diff(1) * value[0][1];
  double x1 = (1 - diff(1)) * value[1][0] + diff(1) * value[1][1];

  if (grad) {
    (*grad)(0) = x1 - x0;
    (*grad)(1) = y1 - y0;
  }

  return (1 - diff(1)) * y0 + diff(1) * y1;
}

double DenseElevationMap::GetValueBilinearSafe(const int layer, const double x,
                                               const double y,
                                               const double height_hint,
                                               Eigen::Vector2d* grad) {
  if(physical_support_mode_){if(grad)grad->setZero();return 0.;}

  // A* and PathPointToNode anchor cells at integer coordinates. The legacy
  // half-cell patch with integer weights extrapolates and jumps at n+0.5.
  // Enable the consistent integer-anchored view with shared scoring only;
  // the unconfigured upstream objective retains its original arithmetic.
  const bool continuous = bool(environmental_cost_);
  const double qx = continuous ? std::min(std::max(x, 0.0), double(max_x_ - 1)) : x;
  const double qy = continuous ? std::min(std::max(y, 0.0), double(max_y_ - 1)) : y;
  double x_lb = std::max(std::floor(qx - (continuous ? 0.0 : 0.5)), 0.0);
  double y_lb = std::max(std::floor(qy - (continuous ? 0.0 : 0.5)), 0.0);

  double value[2][2];
  for (int x = 0; x < 2; ++x) {
    for (int y = 0; y < 2; ++y) {
      value[x][y] = GetRealCostSafe(layer, x_lb + x, y_lb + y, height_hint);
    }
  }

  Eigen::Vector2d diff(qx - x_lb, qy - y_lb);

  double y0 = (1 - diff(0)) * value[0][0] + diff(0) * value[1][0];
  double y1 = (1 - diff(0)) * value[0][1] + diff(0) * value[1][1];
  double x0 = (1 - diff(1)) * value[0][0] + diff(1) * value[0][1];
  double x1 = (1 - diff(1)) * value[1][0] + diff(1) * value[1][1];

  if (grad) {
    (*grad)(0) = x1 - x0;
    (*grad)(1) = y1 - y0;
    if (continuous && qx != x) (*grad)(0) = 0.0;
    if (continuous && qy != y) (*grad)(1) = 0.0;
  }

  return (1 - diff(1)) * y0 + diff(1) * y1;
}
// The optimizer retains its graph reference floor. A missing association has a
// distance residual to that same floor's cell union, not to a remote storey.
// This is zero throughout the feasible domain: no clearance band is added.
bool DenseElevationMap::AssociatePhysicalSurface(double x,double y,double hint,
    int &layer,double &height) const {
  if(!std::isfinite(x)||!std::isfinite(y)||!std::isfinite(hint))return false;
  if(physical_surface_query_) {
    if(!physical_surface_query_(x,y,hint,height))return false;
    // The slice cache is only a display/ceiling hint. Actual continuous native
    // support remains authoritative even when that PCT cell has no floor alias.
    if(x>=-.5&&x<max_x_-.5&&y>=-.5&&y<max_y_-.5) {
      const int col=supportGridIndex(x),row=supportGridIndex(y);double best=physical_height_limit_;
      for(int k=0;k<max_layers_;++k){const double h=height_(k*max_y_+row,col),d=std::abs(h-height);if(h>-50.&&d<best){best=d;layer=k;}}
    }
    return true;
  }
  if(x<-.5||x>=max_x_-.5||y<-.5||y>=max_y_-.5)return false;
  const int col=supportGridIndex(x),row=supportGridIndex(y);
  if(col<0||col>=max_x_||row<0||row>=max_y_)return false;
  double best=std::numeric_limits<double>::infinity();int selected=-1;bool ambiguous=false;
  for(int k=0;k<max_layers_;++k) {
    const double h=height_(k*max_y_+row,col),d=std::abs(h-hint);
    if(h<=-50.||d>=physical_height_limit_)continue;
    if(d+1e-9<best){best=d;selected=k;height=h;ambiguous=false;}
    else if(std::abs(d-best)<=1e-9&&std::abs(h-height)>1e-9)ambiguous=true;
  }
  if(selected<0||ambiguous)return false;
  layer=selected;return true;
}

double DenseElevationMap::PhysicalSupportResidual(double x,double y,double hint,
    Eigen::Vector2d *gradient) const {
  if(gradient)gradient->setZero();
  if(!std::isfinite(x)||!std::isfinite(y)||!std::isfinite(hint))
    throw std::runtime_error("Invalid physical support query");
  int layer=0;double height=0.;
  if(AssociatePhysicalSurface(x,y,hint,layer,height))return 0.;
  const int cx=x<-.5?0:x>=max_x_-.5?max_x_-1:supportGridIndex(x);
  const int cy=y<-.5?0:y>=max_y_-.5?max_y_-1:supportGridIndex(y);
  const int extent=std::max({std::abs(cx),std::abs(cy),std::abs(cx-max_x_+1),std::abs(cy-max_y_+1)});
  double best=std::numeric_limits<double>::infinity();Eigen::Vector2d delta=Eigen::Vector2d::Zero();
  for(int radius=0;radius<=extent;++radius) {
    for(int row=std::max(0,cy-radius);row<=std::min(max_y_-1,cy+radius);++row)
      for(int col=std::max(0,cx-radius);col<=std::min(max_x_-1,cx+radius);++col) {
        if(std::max(std::abs(col-cx),std::abs(row-cy))!=radius)continue;
        int candidate=0;double floor=0.;if(!AssociatePhysicalSurface(col,row,hint,candidate,floor))continue;
        const Eigen::Vector2d d(x-std::min(std::max(x,col-.5),col+.5),y-std::min(std::max(y,row-.5),row+.5));
        const double squared=d.squaredNorm();if(squared<best){best=squared;delta=d;}
      }
    // Any as-yet unvisited cell is at least radius cells from the query.
    if(std::isfinite(best)&&best<=double(radius)*radius)break;
  }
  if(!std::isfinite(best))throw std::runtime_error("No physical support near GPMP reference floor");
  const double distance=std::sqrt(best);
  // In the existing least-squares factor, .5*r*r is distance to the
  // violated feasible set. A quadratic distance penalty leaves a small
  // unsupported penetration at its optimum; this linear violation penalty
  // has no added margin anywhere inside the legal set.
  const double residual=std::sqrt(2.*distance);
  if(gradient&&distance>0.)*gradient=delta/(distance*residual);
  return residual;
}
