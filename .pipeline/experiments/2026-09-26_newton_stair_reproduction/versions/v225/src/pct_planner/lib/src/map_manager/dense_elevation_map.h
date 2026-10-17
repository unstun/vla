#pragma once

#include <Eigen/Dense>
#include <functional>
#include <cmath>

class DenseElevationMap {
 public:
  DenseElevationMap() = default;
  ~DenseElevationMap() = default;

  void Init(const double resolution, const int num_layers,
            const Eigen::MatrixXd& cost_map, const Eigen::MatrixXd& ele_mask,
            const Eigen::MatrixXd& height, const Eigen::MatrixXd& ceiling,
            const Eigen::MatrixXd& grad_x, const Eigen::MatrixXd& grad_y);

  double GetValueBilinear(const int layer, const double x, const double y,
                          Eigen::Vector2d* grad = nullptr);

  double GetValueBilinearSafe(const int layer, const double x, const double y,
                              const double height_hint,
                              Eigen::Vector2d* grad = nullptr);

  int UpdateLayer(const int layer, const double x, const double y);

  int UpdateLayerSafe(const int layer, const double x, const double y,
                      const double height_hint);

  double GetHeight(const int layer, const double x, const double y);

  double GetHeightSafe(const int layer, const double x, const double y,
                       const double height_hint);

  double GetCeiling(const int layer, const double x, const double y);

  double inline GetNominalCost(int layer, double x, double y) {
    auto idx = CoordsToIndex(layer, x, y);
    return cost_(idx[0], idx[1]);
  };

  std::array<int, 2> inline CoordsToIndex(int layer, double x, double y) {
    int col = index(x);
    int row = index(y) + layer * max_y_;
    return {row, col};
  }

  using EnvironmentalCost=std::function<double(double,double,double,double,Eigen::Vector4d *)>;
  void SetEnvironmentalCost(EnvironmentalCost cost) { environmental_cost_=std::move(cost); }
  template<int N> double EnvironmentalResidual(const Eigen::Matrix<double,N,1> &x,double height,
      Eigen::Matrix<double,1,N> *gradient=nullptr) const {
    if(gradient)gradient->setZero();
    if(!environmental_cost_)return 0.;
    // Local axes are grid Y, grid X, height in metres, world yaw.
    const double yaw=std::atan2(x(1),x(N/2+1));Eigen::Vector4d g;
    const double residual=std::sqrt(2.*environmental_cost_(x(0),x(N/2),height,yaw,gradient?&g:nullptr));
    if(gradient&&residual>0.) {
      (*gradient)(0)=g(0)/residual;(*gradient)(N/2)=g(1)/residual;
      const double speed2=x(1)*x(1)+x(N/2+1)*x(N/2+1);
      if(speed2>0.) {
        (*gradient)(1)=g(3)*x(N/2+1)/(speed2*residual);
        (*gradient)(N/2+1)=-g(3)*x(1)/(speed2*residual);
      }
    }
    return residual;
  }
  void SetDebug(const bool flag) { debug_ = flag; }

 private:
  int inline index(double coord) { return static_cast<int>(coord); }

  int inline index_x_safe(double coord) {
    return std::min(std::max(index(coord), 0), max_x_ - 1);
  }

  int inline index_y_safe(double coord) {
    return std::min(std::max(index(coord), 0), max_y_ - 1);
  }

  double GetRealCost(int layer, double x, double y,
                     Eigen::Vector2d* grad = nullptr,
                     int* real_layer = nullptr);

  double GetRealCostSafe(int layer, double x, double y,
                         const double height_hint);

 private:
  EnvironmentalCost environmental_cost_;
  bool debug_ = false;
  double resolution_ = 0.0;
  double resolution_inv_ = 0.0;
  int max_layers_ = 0;
  int max_x_ = 0;
  int max_y_ = 0;
  int xy_size_ = 0;
  double offset_ = 0;

  double safe_cost_threshold_ = 10;

  Eigen::MatrixXd cost_;
  Eigen::MatrixXd ele_mask_;
  Eigen::MatrixXd height_;
  Eigen::MatrixXd ceiling_;
  Eigen::MatrixXd grad_x_;
  Eigen::MatrixXd grad_y_;
};
