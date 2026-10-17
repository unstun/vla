#include <gtest/gtest.h>
#include <lite3_nav2_plugins/pct_route_planner.hpp>
#include <bspline_opt/bspline_optimizer.h>
#include <bspline_opt/environmental_curve_cost.h>
#include <trajectory_optimization/gpmp_optimizer/factors/gp_obstacle_factor.h>
#include <trajectory_optimization/gpmp_optimizer/factors/gp_interpolate_obstacle_factor.h>
#include <trajectory_optimization/gpmp_optimizer/factors_wnoa/gp_obstacle_factor.h>
#include <trajectory_optimization/gpmp_optimizer/factors_wnoa/gp_interpolate_obstacle_factor.h>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <chrono>
#include <thread>
#include <rcl/time.h>
#include <lite3_nav2_plugins/support_height.hpp>

namespace {
std::shared_ptr<reactive_stair::EnvironmentalField> field(int mode=0,double side=1.) {
  std::ostringstream s;s<<std::setprecision(17)<<"ENV225 0.1 -4 -4 0.35 0.18 0.55 0.35 0.35 0.15 0\nF "<<81*81*2<<'\n';
  for(int x=0;x<81;++x)for(int y=0;y<81;++y)for(double z:{0.,3.}) {
    const double wy=-4+(y+.5)*.1;
    const double edge=z>1 ? 1. : (mode==1 ? (side*wy>0?.40:.8) : .35+.15*std::clamp(wy+.5,0.,2.));
    s<<x<<' '<<y<<' '<<z<<' '<<edge<<" 0\n";
  }
  if(mode==2||mode==3) {
    constexpr int n=161,nz=75;std::vector<float> atlas(n*n*nz);
    for(int x=0;x<n;++x)for(int y=0;y<n;++y)for(int z=0;z<nz;++z) {
      const double px=-4+x*.05,py=-4+y*.05,body_z=-.1+z*.05;
      const double radial=std::hypot(.6-px,py)-.35;
      const double vertical=std::abs((mode==3?-.1:.35)-(body_z-.1))-.45;
      double distance=std::hypot(std::max(radial,0.),std::max(vertical,0.))+std::min(std::max(radial,vertical),0.);
      if(mode==3&&std::abs(body_z-.35)<.26)distance=.15;
      atlas[(x*n+y)*nz+z]=float(std::clamp(distance,-.15,.15));
    }
    s<<"A 0.05 0.05 -4 -4 -0.1 "<<n<<' '<<n<<' '<<nz<<'\n';
    s.write(reinterpret_cast<const char*>(atlas.data()),atlas.size()*sizeof(float));
  }else s<<"A 0 0 0 0 0 0 0 0\n";
  const auto bytes=s.str();uint64_t hash=14695981039346656037ULL;for(unsigned char c:bytes){hash^=c;hash*=1099511628211ULL;}
  const auto path=std::filesystem::temp_directory_path()/("environment_"+std::to_string(mode)+".env");
  {std::ofstream out(path);out<<bytes;}
  auto result=std::make_shared<reactive_stair::EnvironmentalField>(path.string(),std::to_string(hash));
  std::filesystem::remove(path);return result;
}
std::string corridorMap() {
  const auto path=std::filesystem::temp_directory_path()/"environment_corridors.pct";std::ofstream out(path,std::ios::binary);
  out.write("PCTMAP01",8);const uint32_t dimensions[]={1,81,81};out.write(reinterpret_cast<const char*>(dimensions),sizeof(dimensions));
  const double meta[]={.1,0,0,0,1};out.write(reinterpret_cast<const char*>(meta),sizeof(meta));
  for(int channel=0;channel<6;++channel)for(int x=0;x<81;++x)for(int y=0;y<81;++y) {
    double value=channel==2?10.:0.;if(channel==0&&std::abs(x-40)<=8&&std::abs(y-40)<=8)value=30.;
    out.write(reinterpret_cast<const char*>(&value),sizeof(value));
  }
  for(int i=0;i<81*81;++i)out.put(1);return path.string();
}
}

TEST(EnvironmentalField, SaturatesAndKeepsFloorsAndHeadingSeparate) {
  auto f=field();EXPECT_GT(f->cost({0.,0.,.35},0.),0.);EXPECT_DOUBLE_EQ(f->cost({0.,1.,.35},0.),0.);
  EXPECT_DOUBLE_EQ(f->cost({0.,2.,.35},0.),0.);EXPECT_DOUBLE_EQ(f->cost({0.,0.,3.35},0.),0.);
  auto wall=field(2);const auto front=wall->assess({0.,0.,.35},0.),side=wall->assess({0.,0.,.35},M_PI/2.);
  EXPECT_GT(front.solid_penalty,side.solid_penalty);EXPECT_NEAR(front.solid_margin,.07,1e-6);
  EXPECT_DOUBLE_EQ(field(3)->assess({0.,0.,.35},0.).solid_penalty,0.);
  EXPECT_FALSE(f->assess({20.,20.,.35},0.).floor_known);
  // A correctly hashed but truncated export must fail before reading unset geometry.
  const std::string truncated="ENV225 0.1";uint64_t hash=14695981039346656037ULL;
  for(unsigned char c:truncated){hash^=c;hash*=1099511628211ULL;}
  const auto path=std::filesystem::temp_directory_path()/"environment_truncated.env";
  {std::ofstream out(path);out<<truncated;}
  EXPECT_THROW(reactive_stair::EnvironmentalField(path.string(),std::to_string(hash)),std::runtime_error);
  std::filesystem::remove(path);
}

TEST(EnvironmentalHeight, TrueSurfaceAndNativeProxyBandsIntersectWithoutLoweringBelowClearance) {
  const auto stair=lite3_nav2::supportHeightBand(.194552,.194552,.3,.12,.35,10.);
  EXPECT_NEAR(stair.preferred,.544552,1e-12);EXPECT_LT(stair.preferred,.62375);
  const auto depression=lite3_nav2::supportHeightBand(2.9560606,3.0608837,.3,.12,.35,10.);
  EXPECT_GE(depression.preferred,3.0608837+.3);
  EXPECT_LT(std::abs(depression.preferred-2.9560606-.3),.12);
  EXPECT_GT(depression.preferred,2.9560606+.35);
  const auto endpoint=lite3_nav2::supportHeightBand(4.53125,4.5330311966,.3,.12,.35,10.);
  EXPECT_GE(4.831251896035036,endpoint.lower); // Original float16-bound goal must remain admissible.
  EXPECT_THROW(lite3_nav2::supportHeightBand(0.,.3,.3,.12,.35,10.),std::runtime_error);
  EXPECT_THROW(lite3_nav2::supportHeightBand(0.,0.,.3,.12,.35,.4),std::runtime_error);
  const auto low=lite3_nav2::supportHeightBand(0.,0.,.3,.12,.35,10.);
  const auto high=lite3_nav2::supportHeightBand(.18,.18,.3,.12,.35,10.);
  EXPECT_LE(std::max(low.lower,high.lower),std::min(low.upper,high.upper)); // Native bands connect over an 18cm step.
  auto f=field();double z=-1.;ASSERT_TRUE(f->surfaceHeight(.05,.05,0.,z));EXPECT_DOUBLE_EQ(z,0.);
  ASSERT_TRUE(f->surfaceHeight(.05,.05,3.,z));EXPECT_DOUBLE_EQ(z,3.);
  EXPECT_FALSE(f->surfaceHeight(.05,.05,1.5,z));EXPECT_FALSE(f->surfaceHeight(20.,20.,0.,z));
}

TEST(EnvironmentalField, ActualPCTSearchChoosesTheOtherAdmissibleCorridor) {
  const auto path=corridorMap();lite3_nav2::PCTRoutePlanner planner(path,.35);
  const Eigen::Vector3d start(-2.,0.,.35),goal(2.,0.,.35);
  const auto baseline=planner.plan(start,goal,false);
  double original=0.;for(const auto &p:baseline)original+=p.y();ASSERT_GT(std::abs(original),1.);
  const double side=original>0?1.:-1.;planner.setEnvironmentalField(field(1,side));
  const auto changed=planner.plan(start,goal,false);double preference=0.;
  for(const auto &p:changed){preference+=p.y();EXPECT_FALSE(std::abs(p.x())<.85&&std::abs(p.y())<.85);}
  EXPECT_LT(preference*side,-1.);
  const auto optimized=planner.plan(start,goal,true);double optimized_side=0.;for(const auto &p:optimized)optimized_side+=p.y();
  EXPECT_LT(optimized_side*side,-1.);
  std::filesystem::remove(path);
}

TEST(EnvironmentalFactors, BothOrdersAndInterpolantsBypassLegacyDeadZone) {
  auto map=std::make_shared<DenseElevationMap>();auto zeros=Eigen::MatrixXd::Zero(40,40).eval();
  auto costs=Eigen::MatrixXd::Constant(40,40,10.).eval();auto ceiling=Eigen::MatrixXd::Constant(40,40,10.).eval();
  map->Init(.1,1,costs,zeros,zeros,ceiling,zeros,zeros);
  auto f=field();map->SetEnvironmentalCost([f](double x,double y,double height,double yaw,Eigen::Vector4d *gradient){
    const Eigen::Vector3d p(y*.1,x*.1,height+.35);if(!gradient)return f->cost(p,yaw);
    Eigen::Vector4d g;const double value=f->costGradient(p,yaw,g);*gradient<<g.y()*.1,g.x()*.1,g.z(),g(3);return value;
  });
  gtsam::Vector6 x6;x6<<2.,.1,0.,2.,1.,0.;gtsam::Vector4 x4;x4<<2.,.1,2.,1.;
  GPObstacleFactor f6(0,map,0,0.,1.,15.);GPObstacleFactorWnoa f4(0,map,0,0.,1.,15.);
  gtsam::Matrix j6,j4;auto r6=f6.evaluateError(x6,j6);auto r4=f4.evaluateError(x4,j4);
  EXPECT_DOUBLE_EQ(r6(0),0.);EXPECT_GT(r6(1),0.);EXPECT_GT(j6.row(1).norm(),1e-5);
  EXPECT_DOUBLE_EQ(r4(0),0.);EXPECT_NEAR(r4(1),r6(1),1e-12);EXPECT_GT(j4.row(1).norm(),1e-5);
  GPInterpolateObstacleFactor i6(0,1,map,0,0.,15.,1.,.01,1.,0.,.5);
  GPInterpolateObstacleFactorWnoa i4(0,1,map,0,0.,15.,1.,.01,1.,0.,.5);
  gtsam::Matrix a,b;EXPECT_GT(i6.evaluateError(x6,x6,a,b)(1),0.);EXPECT_GT(a.row(1).norm(),1e-6);
  EXPECT_GT(i4.evaluateError(x4,x4,a,b)(1),0.);EXPECT_GT(a.row(1).norm(),1e-6);
  // Supplying just one Jacobian must be valid, too.
  EXPECT_GT(i6.evaluateError(x6,x6,a,boost::none)(1),0.);
  // Whole-factor Jacobians, including velocity/yaw and GP interpolation chains.
  for(int k=0;k<6;++k) {
    auto plus=x6,minus=x6;plus(k)+=1e-5;minus(k)-=1e-5;
    auto fp=f6,fm=f6;EXPECT_NEAR(j6(1,k),(fp.evaluateError(plus)(1)-fm.evaluateError(minus)(1))/2e-5,2e-4);
    i6.evaluateError(x6,x6,a,b);auto ip=i6,im=i6;
    EXPECT_NEAR(a(1,k),(ip.evaluateError(plus,x6)(1)-im.evaluateError(minus,x6)(1))/2e-5,2e-4);
  }
  for(int k=0;k<4;++k) {
    auto plus=x4,minus=x4;plus(k)+=1e-5;minus(k)-=1e-5;
    auto fp=f4,fm=f4;EXPECT_NEAR(j4(1,k),(fp.evaluateError(plus)(1)-fm.evaluateError(minus)(1))/2e-5,2e-4);
    i4.evaluateError(x4,x4,a,b);auto ip=i4,im=i4;
    EXPECT_NEAR(a(1,k),(ip.evaluateError(plus,x4)(1)-im.evaluateError(minus,x4)(1))/2e-5,2e-4);
  }
  map->SetEnvironmentalCost({});EXPECT_DOUBLE_EQ(f6.evaluateError(x6)(1),0.);
  int calls=0;map->SetEnvironmentalCost([&](double,double,double,double,Eigen::Vector4d *g){++calls;if(g)g->setZero();return 0.;});
  Eigen::Matrix<double,1,6> zero_gradient;
  EXPECT_DOUBLE_EQ(map->EnvironmentalResidual<6>(x6,0.,&zero_gradient),0.);
  EXPECT_EQ(calls,1);EXPECT_DOUBLE_EQ(zero_gradient.norm(),0.);
  calls=0;Eigen::MatrixXd curve_gradient;
  EXPECT_DOUBLE_EQ(scan_planner::environmentalCurveCost(Eigen::MatrixXd::Zero(3,4),.2,.1,
    [&](const Eigen::Vector3d &,double,Eigen::Vector4d &g){++calls;g.setZero();return 0.;},
    [](const Eigen::Vector3d &,const Eigen::Vector3d &,const Eigen::Vector3d &){return 0.;},curve_gradient),0.);
  EXPECT_EQ(calls,10);EXPECT_DOUBLE_EQ(curve_gradient.norm(),0.);
}

TEST(EnvironmentalSCAN, NativeObjectiveGradientAndLbfgsMoveAwayFromEdge) {
  int argc=0;rclcpp::init(argc,nullptr);
  {
    auto node=std::make_shared<rclcpp::Node>("environment_scan_test");auto map=std::make_shared<GridMap>();map->node_=node.get();
    auto support=std::const_pointer_cast<GridMapSupportState>(map->owned_state_->support_);support->environmental_field_=field();
    scan_planner::BsplineOptimizer opt;opt.setParam(node.get());opt.setEnvironment(map);
    opt.lambda1_=.05;opt.new_lambda2_=opt.lambda3_=0.;opt.lambda_environment_=1.;opt.max_vel_=opt.max_acc_=10.;
    opt.order_=3;opt.bspline_interval_=.2;opt.iter_num_=0;opt.cps_.resize(9);opt.cps_.clearance=.1;
    for(int i=0;i<9;++i)opt.cps_.points.col(i)=Eigen::Vector3d((i-4)*.2,0.,.35);
    const auto initial=opt.cps_.points;Eigen::MatrixXd gradient;
    const double before=opt.calcEnvironmentalCost(initial,gradient);EXPECT_GT(before,0.);EXPECT_LT(gradient(1,4),0.);
    auto plus=initial,minus=initial;plus(1,4)+=1e-4;minus(1,4)-=1e-4;Eigen::MatrixXd unused;
    EXPECT_NEAR(gradient(1,4),(opt.calcEnvironmentalCost(plus,unused)-opt.calcEnvironmentalCost(minus,unused))/2e-4,1e-4);
    double x[9];std::memcpy(x,initial.data()+9,sizeof(x));double final;
    lbfgs::lbfgs_parameter_t parameters;lbfgs::lbfgs_load_default_parameters(&parameters);parameters.max_iterations=80;parameters.g_epsilon=1e-5;
    const auto objective=[](void *instance,const double *p,double *g,const int n) {
      auto *optimizer=static_cast<scan_planner::BsplineOptimizer*>(instance);double cost;
      optimizer->iter_num_=0; // This component test exercises the objective, not the live collision-refresh loop.
      optimizer->combineCostRebound(p,g,cost,n);return cost;
    };
    lbfgs::lbfgs_optimize(9,x,&final,objective,nullptr,nullptr,&opt,&parameters);
    double g[9];objective(&opt,x,g,9);
    EXPECT_GT(opt.cps_.points(1,4),.1);EXPECT_LT(opt.calcEnvironmentalCost(opt.cps_.points,unused),before);
    // A curved, turning pose near a solid also needs the yaw chain rule.
    support->environmental_field_=field(2);
    Eigen::MatrixXd curve=initial;
    for(int i=0;i<9;++i)curve.col(i)=Eigen::Vector3d(.12*std::sin(i*.35),.1*std::cos(i*.35),.35);
    opt.calcEnvironmentalCost(curve,gradient);
    for(int axis=0;axis<2;++axis) {
      auto a=curve,b=curve;a(axis,4)+=1e-5;b(axis,4)-=1e-5;
      const double numerical=(opt.calcEnvironmentalCost(a,unused)-opt.calcEnvironmentalCost(b,unused))/2e-5;
      EXPECT_NEAR(gradient(axis,4),numerical,2e-3);
    }
    const auto pct_map=corridorMap();lite3_nav2::PCTRoutePlanner pct(pct_map,.35);pct.setEnvironmentalField(support->environmental_field_);
    for(double yaw:{0.,.4,1.2})EXPECT_DOUBLE_EQ(pct.environmentalCost({.2,.1,.35},yaw),map->environmentalCost({.2,.1,.35},yaw));
    std::filesystem::remove(pct_map);
    support->environmental_field_=field();
    std::cout<<"ENVIRONMENT_SCAN before="<<before<<" after="<<opt.calcEnvironmentalCost(opt.cps_.points,unused)<<" center_y="<<opt.cps_.points(1,4)<<std::endl;
  }
  rclcpp::shutdown();
}

TEST(EnvironmentalPCT, IntegerAnchoredLegacyCostIsContinuousInSharedMode) {
  DenseElevationMap map;Eigen::MatrixXd cost=Eigen::MatrixXd::Zero(5,5),zero=cost,ceiling=cost.array()+10.;
  cost.col(2).setConstant(100.);cost.col(3).setConstant(20.);
  map.Init(.1,1,cost,zero,zero,ceiling,zero,zero);
  // Preserve original unconfigured arithmetic, including its measured seam.
  EXPECT_NEAR(map.GetValueBilinearSafe(0,1.5-1e-8,2.,0.),0.,1e-5);
  EXPECT_NEAR(map.GetValueBilinearSafe(0,1.5+1e-8,2.,0.),50.,1e-5);
  map.SetEnvironmentalCost([](double,double,double,double,Eigen::Vector4d *g){if(g)g->setZero();return 0.;});
  for(double x:{0.,1.,1.5-1e-8,1.5+1e-8,1.8,2.,2.3,3.,4.}) {
    Eigen::Vector2d gradient;const double actual=map.GetValueBilinearSafe(0,x,2.,0.,&gradient);
    const int lo=std::min(int(std::floor(x)),3);const double expected=(1-(x-lo))*cost(2,lo)+(x-lo)*cost(2,lo+1);
    EXPECT_NEAR(actual,expected,1e-10);EXPECT_GE(actual,0.);EXPECT_LE(actual,100.);
    if(std::abs(x-std::round(x))>1e-5) {
      const double numerical=(map.GetValueBilinearSafe(0,x+1e-6,2.,0.)-map.GetValueBilinearSafe(0,x-1e-6,2.,0.))/2e-6;
      EXPECT_NEAR(gradient(0),numerical,1e-6);
    }
  }
  Eigen::Vector2d gradient;EXPECT_DOUBLE_EQ(map.GetValueBilinearSafe(0,5.,2.,0.,&gradient),0.);EXPECT_DOUBLE_EQ(gradient(0),0.);
  EXPECT_NEAR(map.GetValueBilinearSafe(0,1.5-1e-8,2.,0.),map.GetValueBilinearSafe(0,1.5+1e-8,2.,0.),2.1e-6);
}

namespace {
void regressionClock(rclcpp::Node &node,int64_t ns) {
  auto clock=node.get_clock()->get_clock_handle();
  ASSERT_EQ(rcl_enable_ros_time_override(clock),RCL_RET_OK);
  ASSERT_EQ(rcl_set_ros_time_override(clock,ns),RCL_RET_OK);
}
void regressionOptimizer(scan_planner::BsplineOptimizer &opt,const GridMap::Ptr &map,rclcpp::Node &node) {
  map->node_=&node;map->query_clock_=node.get_clock();
  map->reactive_body_stamp_s_=1.;map->reactive_body_quaternion_=Eigen::Quaterniond::Identity();
  auto support=std::const_pointer_cast<GridMapSupportState>(map->owned_state_->support_);
  support->environmental_field_=field();
  opt.setParam(&node);opt.setEnvironment(map);opt.lambda_environment_=1.;
  opt.lambda1_=.05;opt.new_lambda2_=opt.lambda3_=0.;opt.max_vel_=opt.max_acc_=10.;
  opt.order_=3;opt.bspline_interval_=.2;opt.iter_num_=0;opt.cps_.resize(9);opt.cps_.clearance=.1;
  for(int i=0;i<9;++i)opt.cps_.points.col(i)=Eigen::Vector3d(std::min(i,5)*.2,0.,.35);
}
}
TEST(EnvironmentalRegression, DelayedLocalSearchStationaryTailKeepsFiniteSoftCost) {
 int argc=0;rclcpp::init(argc,nullptr);
 {
  auto node=std::make_shared<rclcpp::Node>("delayed_search_tail");
  auto map=std::make_shared<GridMap>();scan_planner::BsplineOptimizer opt;
  regressionOptimizer(opt,map,*node);regressionClock(*node,1000000000LL);
  Eigen::MatrixXd gradient;EXPECT_NO_THROW(opt.calcEnvironmentalCost(opt.cps_.points,gradient));
  const auto begin=std::chrono::steady_clock::now();
  // Two failed local-search latency slots; only the independent ROS clock advances.
  std::thread clock([&]{std::this_thread::sleep_for(std::chrono::milliseconds(110));regressionClock(*node,1116800000LL);});
  std::this_thread::sleep_for(std::chrono::microseconds(116800));clock.join();
  EXPECT_GT(std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count(),.1);
  const Eigen::Vector3d end=opt.cps_.points.col(8);
  EXPECT_FALSE(std::isfinite(map->collisionTrajectoryYaw(end,end,Eigen::Vector3d::Zero())));
  double score=-1.;EXPECT_NO_THROW(score=opt.calcEnvironmentalCost(opt.cps_.points,gradient));
  EXPECT_TRUE(std::isfinite(score));EXPECT_GE(score,0.);EXPECT_TRUE(gradient.allFinite());
  // Hard geometry heading is still stale after soft scoring.
  EXPECT_FALSE(std::isfinite(map->collisionTrajectoryYaw(end,end,Eigen::Vector3d::Zero())));
 }
 rclcpp::shutdown();
}
TEST(EnvironmentalRegression, NativeReboundErrorShortCircuitsEnvironmentalAssessment) {
 int argc=0;rclcpp::init(argc,nullptr);
 {
  auto node=std::make_shared<rclcpp::Node>("rebound_stop_short_circuit");
  auto map=std::make_shared<GridMap>();scan_planner::BsplineOptimizer opt;
  regressionOptimizer(opt,map,*node);regressionClock(*node,1116800000LL);
  opt.cps_.points.colwise()=Eigen::Vector3d(0.,0.,.35);opt.iter_num_=4;
  double x[9],g[9],cost=-1.;std::memcpy(x,opt.cps_.points.data()+9,sizeof(x));
  EXPECT_NO_THROW(opt.combineCostRebound(x,g,cost,9));
  EXPECT_EQ(opt.force_stop_type_,scan_planner::BsplineOptimizer::STOP_FOR_ERROR);
  EXPECT_TRUE(std::isfinite(cost));for(double v:g)EXPECT_TRUE(std::isfinite(v));
  EXPECT_NE(scan_planner::BsplineOptimizer::earlyExit(&opt,x,g,cost,0.,0.,0.,9,0,0),0);
 }
 rclcpp::shutdown();
}

TEST(EnvironmentalRegression, MeasuredYawFallbackAndNonfiniteGeometryFailAtOptimizerBoundary) {
 int argc=0;rclcpp::init(argc,nullptr);
 {
  auto node=std::make_shared<rclcpp::Node>("environment_finite_guards");auto map=std::make_shared<GridMap>();
  scan_planner::BsplineOptimizer opt;regressionOptimizer(opt,map,*node);regressionClock(*node,1116800000LL);
  map->reactive_body_quaternion_=Eigen::AngleAxisd(1.2,Eigen::Vector3d::UnitZ());
  Eigen::MatrixXd q=Eigen::MatrixXd::Zero(3,9),gradient;q.row(2).setConstant(.35);
  int assessed=0;
  EXPECT_NO_THROW(scan_planner::environmentalCurveCost(q,.2,.1,
    [&](const Eigen::Vector3d &,double yaw,Eigen::Vector4d &g){++assessed;EXPECT_NEAR(yaw,1.2,1e-12);g.setZero();return 1.;},
    [&](const Eigen::Vector3d &p,const Eigen::Vector3d &a,const Eigen::Vector3d &v){return map->collisionTrajectoryYaw(p,a,v);},gradient,map->measuredBodyYaw()));
  EXPECT_GT(assessed,0);EXPECT_TRUE(gradient.allFinite());
  q(0,4)=std::numeric_limits<double>::quiet_NaN();assessed=0;
  EXPECT_THROW(scan_planner::environmentalCurveCost(q,.2,.1,
    [&](const Eigen::Vector3d &,double,Eigen::Vector4d &g){++assessed;g.setZero();return 0.;},
    [](const Eigen::Vector3d &,const Eigen::Vector3d &,const Eigen::Vector3d &){return 0.;},gradient),std::invalid_argument);
  EXPECT_EQ(assessed,0);
  opt.cps_.points=q;opt.ref_pts_.assign(9,Eigen::Vector3d::Zero());Eigen::MatrixXd output;
  EXPECT_FALSE(opt.BsplineOptimizeTrajRebound(output,.2));
  EXPECT_EQ(opt.force_stop_type_,scan_planner::BsplineOptimizer::STOP_FOR_ERROR);
  EXPECT_FALSE(opt.BsplineOptimizeTrajRefine(q,.2,output));
  for(auto stop:{scan_planner::BsplineOptimizer::STOP_FOR_ERROR,scan_planner::BsplineOptimizer::STOP_FOR_REBOUND}){
    opt.force_stop_type_=stop;double x[9]={},g[9];
    EXPECT_DOUBLE_EQ(scan_planner::BsplineOptimizer::costFunctionRebound(&opt,x,g,9),0.);
    EXPECT_EQ(opt.force_stop_type_,stop);for(double v:g)EXPECT_DOUBLE_EQ(v,0.);
  }
 }
 rclcpp::shutdown();
}
