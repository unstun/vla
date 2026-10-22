#include "trajectory_optimization/gpmp_optimizer/factors_wnoa/gp_interpolate_obstacle_factor.h"
#include <stdexcept>

gtsam::Vector GPInterpolateObstacleFactorWnoa::evaluateError(
    const gtsam::Vector4& x1, const gtsam::Vector4& x2,
    boost::optional<gtsam::Matrix&> H1,
    boost::optional<gtsam::Matrix&> H2) const {
  if(!x1.allFinite()||!x2.allFinite()||!std::isfinite(height_hint_))throw std::runtime_error("Invalid GPMP interpolation state");
  if (!initialized_) {
    int init_layer = current_layer_;
    gtsam::Vector4 x_tmp = gp_interpolator_.Interpolate(x1, x2);
    current_layer_ = map_->UpdateLayerSafe(current_layer_, x_tmp(0, 0),
                                           x_tmp(2, 0), height_hint_);
    if(!map_->PhysicalSupportMode()) height_hint_ = map_->GetHeightSafe(current_layer_, x_tmp(0, 0), x_tmp(2, 0),
                                       height_hint_);
    // printf("init_layer: %d, current_layer: %d, x_tmp: (%f, %f, %f, %f)\n",
    //        init_layer, current_layer_, x_tmp(0, 0), x_tmp(1, 0), x_tmp(2, 0),
    //        x_tmp(3, 0));
    initialized_ = true;
  }

  double cost;
  Eigen::Vector2d grad;
  gtsam::Matrix44 J_x1, J_x2;
  Eigen::Matrix<double,2,4> H = Eigen::MatrixXd::Zero(2, 4);
  gtsam::Vector4 x_inter = gp_interpolator_.Interpolate(x1, x2, &J_x1, &J_x2);

  int tmp_layer = current_layer_;
  cost = map_->GetValueBilinearSafe(current_layer_, x_inter(0, 0),
                                    x_inter(2, 0), height_hint_, &grad);
  current_layer_ = map_->UpdateLayerSafe(current_layer_, x_inter(0, 0),
                                         x_inter(2, 0), height_hint_);
  if(!map_->PhysicalSupportMode()) height_hint_ = map_->GetHeightSafe(current_layer_, x_inter(0, 0),
                                     x_inter(2, 0), height_hint_);
  // if (tmp_layer != current_layer_) {
  //   printf("--------------------------------------------\n");
  //   map_->SetDebug(true);
  //   map_->UpdateLayerSafe(tmp_layer, x_inter(0, 0), x_inter(2, 0),
  //                         height_hint_);
  //   map_->SetDebug(false);
  //   printf(
  //       "layer changed: %d -> %d, at (%f, %f), x1(%f, %f, %f, %f), x2(%f, "
  //       "%f, %f, %f), tau: %f, height_hint %f\n",
  //       tmp_layer, current_layer_, x_inter(0, 0), x_inter(2, 0), x1(0, 0),
  //       x1(1, 0), x1(2, 0), x1(3, 0), x2(0, 0), x2(1, 0), x2(2, 0), x2(3, 0),
  //       tau_, height_hint_);
  // }
  double error = 0.0;

  if(map_->PhysicalSupportMode()) {
    Eigen::Matrix<double,1,4> physical_gradient;
    error=map_->PhysicalConstraintResidual<4>(x_inter,height_hint_,&physical_gradient);
    H.row(0)=physical_gradient;
  } else if (cost > cost_threshold_) {
    error = (cost - cost_threshold_) * (cost - cost_threshold_);
    H(0, 0) = 2 * (cost - cost_threshold_) * grad(0);
    H(0, 2) = 2 * (cost - cost_threshold_) * grad(1);
  }

  Eigen::Matrix<double,1,4> environment_gradient;
  const double environment=map_->EnvironmentalResidual<4>(x_inter,height_hint_,&environment_gradient);
  H.row(1)=environment_gradient;
  if(H1)*H1=H*J_x1;
  if(H2)*H2=H*J_x2;

  // if (verbose_) {
  // printKeys();
  // printf(
  //     "layer: %d, query pos (%f, %f), cost: %f, threshould: %f,  error: %f, "
  //     "grad: "
  //     "(%f,%f)\n",
  //     current_layer_, x_inter(0, 0), x_inter(2, 0), cost, cost_threshold_,
  //     error, grad(0), grad(1));

  // // }

  return gtsam::Vector2(error,environment);
}