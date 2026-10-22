#include <gtest/gtest.h>

#include <Eigen/Core>
#include <bspline_opt/uniform_bspline.h>

TEST(UniformBspline, EvaluatesLinearControlPoints)
{
  Eigen::MatrixXd points = Eigen::MatrixXd::Zero(3, 6);
  for (int i = 0; i < points.cols(); ++i) points(0, i) = static_cast<double>(i);

  scan_planner::UniformBspline spline(points, 3, 1.0);
  EXPECT_NEAR(spline.evaluateDeBoorT(0.0).x(), 1.0, 1e-9);
  EXPECT_NEAR(spline.evaluateDeBoorT(2.0).x(), 3.0, 1e-9);
  EXPECT_NEAR(spline.evaluateDeBoorT(2.0).y(), 0.0, 1e-9);
}

TEST(UniformBspline, DerivativeMatchesLinearSlope)
{
  Eigen::MatrixXd points = Eigen::MatrixXd::Zero(3, 6);
  for (int i = 0; i < points.cols(); ++i) points(0, i) = static_cast<double>(i);

  auto derivative = scan_planner::UniformBspline(points, 3, 0.5).getDerivative();
  const Eigen::Vector3d velocity = derivative.evaluateDeBoorT(0.75);
  EXPECT_NEAR(velocity.x(), 2.0, 1e-9);
  EXPECT_NEAR(velocity.y(), 0.0, 1e-9);
  EXPECT_NEAR(velocity.z(), 0.0, 1e-9);
}

#include <bspline_opt/environmental_curve_cost.h>
TEST(EnvironmentalQuadrature, FixedPartitionHasConsistentDirectionalDerivative)
{
  Eigen::MatrixXd q=Eigen::MatrixXd::Zero(3,8);
  for(int i=0;i<8;++i){q(0,i)=i*.1;q(1,i)=.02*std::sin(i);}
  auto score=[](const Eigen::Vector3d&p,double,Eigen::Vector4d &g) {
    g<<0.,4.*p.y()*p.y()*p.y(),0.,0.;return std::pow(p.y(),4);
  };
  auto heading=[](const Eigen::Vector3d&,const Eigen::Vector3d&,const Eigen::Vector3d&){return 0.;};
  Eigen::MatrixXd g,unused;
  const double cost=scan_planner::environmentalCurveCost(q,.2,.8,score,heading,g,0.);
  const double eps=1e-6;q(1,3)+=eps;
  const double plus=scan_planner::environmentalCurveCost(q,.2,.8,score,heading,unused,0.);
  q(1,3)-=2*eps;
  const double minus=scan_planner::environmentalCurveCost(q,.2,.8,score,heading,unused,0.);
  EXPECT_GT(cost,0.);EXPECT_NEAR(g(1,3),(plus-minus)/(2*eps),1e-9);
  // Evaluation count is constant even across a partition ceil threshold.
  int calls=0;auto countScore=[&](const Eigen::Vector3d&p,double,Eigen::Vector4d&g){++calls;return score(p,0.,g);};
  for(double scale : {.999,1.001,2.}) {
    calls=0;Eigen::MatrixXd trial=scale*q;
    scan_planner::environmentalCurveCost(trial,.2,.8,countScore,heading,unused,0.);
    EXPECT_EQ(calls,3*(q.cols()-3));
  }
}

#include <bspline_opt/lbfgs.hpp>
TEST(LbfgsRollback, ErrorRestoresLastAcceptedVariablesAfterRejectedTrials)
{
  struct State {int calls=0;double last=0.;} state;
  auto cost=[](void *data,const double *x,double *g,int) {
    auto &s=*static_cast<State*>(data);++s.calls;s.last=x[0];g[0]=x[0];
    // Two consistent evaluations accept the first step. Subsequent rejected
    // trials emulate a discontinuous environmental objective deterministically.
    return s.calls<=2 ? .5*x[0]*x[0] : 1000.;
  };
  lbfgs::lbfgs_parameter_t param;lbfgs::lbfgs_load_default_parameters(&param);
  param.max_linesearch=20;
  double x=4.,value=0.;const int result=lbfgs::lbfgs_optimize(1,&x,&value,cost,nullptr,nullptr,&state,&param);
  EXPECT_LT(result,0);EXPECT_GT(state.calls,2);EXPECT_DOUBLE_EQ(x,3.);
}
