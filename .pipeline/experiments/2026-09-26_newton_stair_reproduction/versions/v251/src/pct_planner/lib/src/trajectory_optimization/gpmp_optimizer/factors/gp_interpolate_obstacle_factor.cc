#include "trajectory_optimization/gpmp_optimizer/factors/gp_interpolate_obstacle_factor.h"
#include <stdexcept>

gtsam::Vector GPInterpolateObstacleFactor::evaluateError(
    const gtsam::Vector6& x1, const gtsam::Vector6& x2,
    boost::optional<gtsam::Matrix&> H1,
    boost::optional<gtsam::Matrix&> H2) const {
  if(!x1.allFinite()||!x2.allFinite()||!std::isfinite(height_hint_))throw std::runtime_error("Invalid GPMP interpolation state");
  if (!initialized_) {
    int init_layer = current_layer_;
    gtsam::Vector6 x_tmp = gp_interpolator_.Interpolate(x1, x2);
    current_layer_ = map_->UpdateLayerSafe(current_layer_, x_tmp(0, 0),
                                           x_tmp(3, 0), height_hint_);
    if(!map_->PhysicalSupportMode()) height_hint_ = map_->GetHeightSafe(current_layer_, x_tmp(0, 0), x_tmp(3, 0),
                                       height_hint_);
    initialized_ = true;
  }

  double cost;
  Eigen::Vector2d grad;
  gtsam::Matrix66 J_x1, J_x2;
  Eigen::Matrix<double,2,6> H = Eigen::MatrixXd::Zero(2, 6);
  gtsam::Vector6 x_inter = gp_interpolator_.Interpolate(x1, x2, &J_x1, &J_x2);

  cost = map_->GetValueBilinearSafe(current_layer_, x_inter(0, 0),
                                    x_inter(3, 0), height_hint_, &grad);
  current_layer_ = map_->UpdateLayerSafe(current_layer_, x_inter(0, 0),
                                         x_inter(3, 0), height_hint_);
  if(!map_->PhysicalSupportMode()) height_hint_ = map_->GetHeightSafe(current_layer_, x_inter(0, 0),
                                     x_inter(3, 0), height_hint_);
  double error = 0.0;

  if(map_->PhysicalSupportMode()) {
    Eigen::Matrix<double,1,6> physical_gradient;
    error=map_->PhysicalConstraintResidual<6>(x_inter,height_hint_,&physical_gradient);
    H.row(0)=physical_gradient;
  } else if (cost > cost_threshold_) {
    error = (cost - cost_threshold_) * (cost - cost_threshold_);
    H(0, 0) = 2 * (cost - cost_threshold_) * grad(0);
    H(0, 3) = 2 * (cost - cost_threshold_) * grad(1);
  }

  Eigen::Matrix<double,1,6> environment_gradient;
  const double environment=map_->EnvironmentalResidual<6>(x_inter,height_hint_,&environment_gradient);
  H.row(1)=environment_gradient;
  if(H1)*H1=H*J_x1;
  if(H2)*H2=H*J_x2;


  return gtsam::Vector2(error,environment);
}