#pragma once

#include <memory>

#include "a_star/a_star_search.h"
#include "common/data_types.h"
#include "map_manager/dense_elevation_map.h"
#include "trajectory_optimization/gpmp_optimizer/gpmp_optimizer.h"
#include "trajectory_optimization/gpmp_optimizer/gpmp_optimizer_wnoa.h"

class OfflineElePlanner {
 public:
  OfflineElePlanner(const double max_heading_rate, bool use_quintic)
      : use_quintic_(use_quintic), max_heading_rate_(max_heading_rate) {}
  ~OfflineElePlanner() = default;

  // void InitMap(const double a_start_cost_threshold,
  //              const double safe_cost_margin, const double resolution,
  //              const int num_layers, const double step_cost_weight, const Eigen::MatrixXd& cost_map,
  //              const Eigen::MatrixXd& height_map,
  //              const Eigen::MatrixXd& ceiling, const Eigen::MatrixXd& ele_map,
  //              const Eigen::MatrixXd& grad_x, const Eigen::MatrixXd& grad_y);

  void InitMap(
    const double a_start_cost_threshold,
    const double safe_cost_margin,
    const double resolution,
    const int num_layers,
    const double step_cost_weight,
    const Eigen::Ref<const Eigen::MatrixXd> &cost_map,
    const Eigen::Ref<const Eigen::MatrixXd> &height_map,
    const Eigen::Ref<const Eigen::MatrixXd> &ceiling,
    const Eigen::Ref<const Eigen::MatrixXd> &ele_map,
    const Eigen::Ref<const Eigen::MatrixXd> &grad_x,
    const Eigen::Ref<const Eigen::MatrixXd> &grad_y
  );

  // bool Plan(const Eigen::Vector3i& start, const Eigen::Vector3i& goal,
  //           const bool optimize = true);
  bool Plan(
    Eigen::Ref<const Eigen::Vector3i> &start,
    Eigen::Ref<const Eigen::Vector3i> &goal,
    const bool optimize
  );

  void SetPoseCallbacks(Astar::PoseValidator valid,Astar::PoseCost cost) {path_finder_.SetPoseCallbacks(std::move(valid),std::move(cost));}
  void SetPoseValidity(std::function<bool(const Node&)> valid) {path_finder_.SetPoseValidity(std::move(valid));}
  void SetPoseNecessaryValidity(std::function<bool(const Node&)> valid) {path_finder_.SetPoseNecessaryValidity(std::move(valid));}
  void SetFreeRotation(std::function<bool(const Node&)> certificate) {path_finder_.SetFreeRotation(std::move(certificate));}
  void SetPoseHeadings(double start,double goal) {path_finder_.SetPoseHeadings(start,goal);}
  void SetPoseAngularLowerBound(double weight) {path_finder_.SetPoseAngularLowerBound(weight);}
  void SetPathTransform(std::function<void(std::vector<PathPoint>&)> transform) {path_transform_=std::move(transform);}
  const std::vector<PathPoint> &get_prepared_path() const {return path_;}
  void SetContinuousEndpoints(const Node &start,const Node &goal) { path_finder_.SetContinuousEndpoints(start,goal); }

  void SetReferenceHeight(const double height) {
    trajectory_optimizer_wnoj_.SetReferenceHeight(height);
    trajectory_optimizer_.SetReferenceHeight(height);
  }

  void Debug() {
    path_finder_.Debug();
    trajectory_optimizer_.SetDebug(true);
    trajectory_optimizer_wnoj_.SetDebug(true);
  }

  Eigen::MatrixXd GetDebugPath() const {
    return path_finder_.GetResultMatrix();
  }

  void set_max_iterations(int max_iterations) {
    trajectory_optimizer_.set_max_iterations(max_iterations);
  }

  void SetEnvironmentalCost(std::function<double(const Node &,const Node &)> graph,
      DenseElevationMap::EnvironmentalCost score) {
    path_finder_.SetEnvironmentalCost(std::move(graph));map_->SetEnvironmentalCost(std::move(score));
  }
  void SetPhysicalSupportMode(bool enabled,double height_limit=.26) { path_finder_.SetPhysicalSupportMode(enabled);map_->SetPhysicalSupportMode(enabled,height_limit); }
  void SetPhysicalGapCost(DenseElevationMap::PhysicalGapCost cost) { map_->SetPhysicalGapCost(std::move(cost)); }
  void SetPhysicalSurfaceQuery(DenseElevationMap::PhysicalSurfaceQuery query) { map_->SetPhysicalSurfaceQuery(std::move(query)); }
  void SetTransitionValidator(std::function<bool(const Node &,const Node &)> check) { path_finder_.SetTransitionValidator(std::move(check)); }
  const Astar& get_path_finder() const { return path_finder_; }
  const DenseElevationMap& get_map() const { return *map_; }
  const GPMPOptimizerWnoa& get_trajectory_optimizer() const {
    return trajectory_optimizer_;
  }
  const GPMPOptimizer& get_trajectory_optimizer_wnoj() const {
    return trajectory_optimizer_wnoj_;
  }

 private:
  double max_heading_rate_ = 0.5;
  bool use_quintic_ = false;

  std::shared_ptr<DenseElevationMap> map_;
  Astar path_finder_;
  GPMPOptimizerWnoa trajectory_optimizer_;
  GPMPOptimizer trajectory_optimizer_wnoj_;

  std::function<void(std::vector<PathPoint>&)> path_transform_;
  std::vector<PathPoint> path_;
  std::vector<Eigen::Vector3d> trajectory_;
};
