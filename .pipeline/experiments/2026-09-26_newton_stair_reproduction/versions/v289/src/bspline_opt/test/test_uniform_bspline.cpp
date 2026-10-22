#include <gtest/gtest.h>
#include <bspline_opt/bspline_optimizer.h>

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

TEST(OptimizerCandidateRecovery, EvaluationCountCannotStandForDescent) {
  scan_planner::BsplineOptimizer opt;double q[]={1,2,3},g[]={1,1,1};
  opt.beginCandidates(q,3);opt.rememberCandidate(q,g,10.,3);
  double trial[]={2,3,4};opt.rememberCandidate(trial,g,11.,3);opt.iter_num_=200;
  EXPECT_FALSE(opt.candidateDescended());EXPECT_DOUBLE_EQ(opt.best_variable_[0],1);
  double better[]={.5,1,1.5};opt.rememberCandidate(better,g,8.,3);
  EXPECT_TRUE(opt.candidateDescended());EXPECT_DOUBLE_EQ(opt.initial_cost_,10.);
  EXPECT_DOUBLE_EQ(opt.min_cost_,8.);EXPECT_DOUBLE_EQ(opt.best_variable_[0],.5);
  opt.beginCandidates(q,3);EXPECT_FALSE(opt.candidateDescended());
}
TEST(OptimizerCandidateRecovery, InvalidOrCanceledTrialCannotBecomeBest) {
  scan_planner::BsplineOptimizer opt;double q[]={1,2,3},g[]={1,1,1};
  opt.beginCandidates(q,3);opt.rememberCandidate(q,g,10.,3);
  double trial[]={0,0,0},bad[]={NAN,0,0};opt.rememberCandidate(trial,bad,1.,3);
  EXPECT_FALSE(opt.candidateDescended());
  opt.force_stop_type_=scan_planner::BsplineOptimizer::STOP_FOR_ERROR;
  opt.rememberCandidate(trial,g,1.,3);EXPECT_FALSE(opt.candidateDescended());
}

TEST(OptimizerCandidateRecovery, InvalidInitialEvaluationCannotInventABaseline) {
  scan_planner::BsplineOptimizer opt;double q[]={1.},g[]={1.},bad[]={NAN};
  opt.beginCandidates(q,1);opt.rememberCandidate(q,bad,10.,1);
  q[0]=.8;opt.rememberCandidate(q,g,8.,1);
  q[0]=.6;opt.rememberCandidate(q,g,6.,1);
  EXPECT_FALSE(opt.candidateDescended());
}
TEST(OptimizerCandidateRecovery, ActualLineSearchFailureRetainsLowerFiniteCandidate) {
  struct State {scan_planner::BsplineOptimizer opt;int calls=0;} state;
  double x=4.,value=0.;state.opt.beginCandidates(&x,1);
  auto cost=[](void *data,const double *q,double *g,int n) {
    auto &s=*static_cast<State*>(data);++s.calls;g[0]=q[0];
    const double f=s.calls<=2 ? .5*q[0]*q[0] : 1000.;
    s.opt.rememberCandidate(q,g,f,n);return f;
  };
  lbfgs::lbfgs_parameter_t p;lbfgs::lbfgs_load_default_parameters(&p);p.max_linesearch=20;
  const int result=lbfgs::lbfgs_optimize(1,&x,&value,cost,nullptr,nullptr,&state,&p);
  ASSERT_LT(result,0);EXPECT_TRUE(state.opt.candidateDescended());
  EXPECT_DOUBLE_EQ(state.opt.initial_cost_,8.);EXPECT_DOUBLE_EQ(state.opt.min_cost_,4.5);
  EXPECT_DOUBLE_EQ(state.opt.best_variable_[0],3.);
}
