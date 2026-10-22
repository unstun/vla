#include <gtest/gtest.h>
#include <plan_env/static_support.h>
#include <a_star/a_star_search.h>
#include <lite3_nav2_plugins/pct_route_planner.hpp>
#include <cstdio>
#include <map_manager/support_grid_index.h>
#include <trajectory_optimization/gpmp_optimizer/factors/gp_obstacle_factor.h>
#include <trajectory_optimization/gpmp_optimizer/factors/gp_interpolate_obstacle_factor.h>
#include <trajectory_optimization/gpmp_optimizer/factors_wnoa/gp_obstacle_factor.h>
#include <trajectory_optimization/gpmp_optimizer/factors_wnoa/gp_interpolate_obstacle_factor.h>
#include <unistd.h>

using namespace reactive_stair;

TEST(PhysicalSupport, OrientationAndNearestLayerRemainHard) {
  TerrainSnapshot raw;raw.source_id="fixture";raw.frame="world";raw.stamp_s=1.;
  raw.resolution_m=.1;raw.origin_x_m=raw.origin_y_m=-.05;
  for(int x=-8;x<=8;++x)for(int y=-1;y<=1;++y)raw.cells[{x,y}]={{Support::Flat,0.}};
  auto scored=raw;Parameters parameters;parameters.body_clearance_m=.3;
  parameters.body_height_tolerance_m=.12;parameters.robot_radius_m=.35;
  CollisionDecision decision(parameters);ASSERT_TRUE(decision.acceptTerrain(scored));
  auto cell=[&](double x,double y,Cell2 &out){return staticSupportCell(x,y,raw,true,-.05,-.05,out);};
  const auto query=[&](double yaw){return staticSupportGeometry({{0.,0.,.3}},yaw,raw,scored,decision,parameters,.18,cell,nullptr);};
  EXPECT_EQ(query(0.),Verdict::Free);
  EXPECT_EQ(query(M_PI),Verdict::Free);
  EXPECT_NE(query(M_PI/2.),Verdict::Free);
  // A nearer unsupported floor cannot be skipped for a farther valid level.
  raw.cells[{2,0}]={{Support::Flat,.01},{Support::Flat,.15}};
  scored=raw;scored.cells[{2,0}][0].support=Support::Unsupported;
  ASSERT_TRUE(decision.acceptTerrain(scored));
  EXPECT_EQ(query(0.),Verdict::UnknownSupport);
  EXPECT_EQ(query(std::numeric_limits<double>::quiet_NaN()),Verdict::InvalidQuery);
}

static void checkDirections(bool ramp,int rotation) {
  constexpr int n=25,layers=2;
  Eigen::MatrixXd height(layers*n,n),cost(layers*n,n),gateway(layers*n,n);
  for(int l=0;l<layers;++l)for(int x=0;x<n;++x)for(int y=0;y<n;++y) {
    const int u=rotation%2?y:x;
    // Multiple stored slices contain the same physical surface. Gateway
    // arrows intentionally conflict; physical admission must ignore them.
    height(l*n+x,y)=ramp?.04*u:.2*(u/5);
    cost(l*n+x,y)=25.+((x+y+l)%26);
    gateway(l*n+x,y)=l?-2.:2.;
  }
  Astar search;search.Init(20.,layers,.1,.2,cost,height,gateway);
  search.SetPhysicalSupportMode(true);
  search.SetTransitionValidator([](const Node &a,const Node &b){return std::abs(a.height-b.height)<.26;});
  const Eigen::Vector3i a(0,2,2),b(1,22,22);
  ASSERT_TRUE(search.Search(a,b));const auto forward=search.GetPathPoints();
  ASSERT_TRUE(search.Search(b,a));const auto reverse=search.GetPathPoints();
  EXPECT_EQ(forward.size(),reverse.size());
  for(const auto &path:{forward,reverse})for(size_t i=1;i<path.size();++i)
    EXPECT_LT(std::abs(path[i].height-path[i-1].height),.26);
  // A genuine cliff is rejected in both directions, independent of raw cost.
  for(int l=0;l<layers;++l)for(int x=0;x<n;++x)for(int y=0;y<n;++y)
    height(l*n+x,y)=(rotation%2?y:x)<12?0.:.4;
  search.Init(20.,layers,.1,.2,cost,height,gateway);
  EXPECT_FALSE(search.Search(a,b));EXPECT_FALSE(search.Search(b,a));
}
TEST(PhysicalGraph, StairsAreBidirectionalAcrossSliceGateways) {
  checkDirections(false,0);checkDirections(false,1);
}
TEST(PhysicalGraph, RampsUseTheSameRuleInBothDirections) {
  checkDirections(true,0);checkDirections(true,1);
}

TEST(PhysicalGraph, SliceAliasesUseOneNativeFloorWithoutFalseCeilingGate) {
  const std::string prefix="/tmp/pct_support_alias_"+std::to_string(getpid());
  const auto bundle=prefix+".pct",support_path=prefix+".support";
  {std::ofstream out(bundle,std::ios::binary);out.write("PCTMAP01",8);
   const uint32_t dims[]={2,9,9};out.write(reinterpret_cast<const char*>(dims),sizeof(dims));
   const double meta[]={.1,0.,0.,.5,.5};out.write(reinterpret_cast<const char*>(meta),sizeof(meta));
   for(int channel=0;channel<6;++channel)for(int l=0;l<2;++l)for(int i=0;i<81;++i) {
     const double value=channel==0?50.:channel==1?(l?.075:(i%9>=4?2.:0.)):channel==2?(l?1.:.075):0.;
     out.write(reinterpret_cast<const char*>(&value),sizeof(value));
   }
   for(int i=0;i<162;++i)out.put(1);}
  std::ostringstream text;
  text<<"SUPPORT247 .1 -.45 -.45 1 -.45 -.45 .3 .12 .35 .18 fixture world 81 \"\" none\n";
  for(int x=0;x<9;++x)for(int y=0;y<9;++y)text<<x<<' '<<y<<" 0 1 1\n";
  const auto bytes=text.str();uint64_t fnv=14695981039346656037ULL;
  for(unsigned char c:bytes){fnv^=c;fnv*=1099511628211ULL;}
  {std::ofstream out(support_path);out<<bytes;}
  auto support=std::make_shared<StaticSupportField>(support_path,std::to_string(fnv));
  EXPECT_THROW(StaticSupportField(support_path,"0"),std::runtime_error);
  lite3_nav2::PCTRoutePlanner planner(bundle,.3);planner.setStaticSupport(support);
  const Eigen::Vector3d a(-.2,-.2,.3),b(.2,.2,.3);
  for(const auto &path:{planner.plan(a,b,false),planner.plan(b,a,false)}) {
    ASSERT_GE(path.size(),2u);
    for(const auto &point:path)EXPECT_NEAR(point.z(),.3,1e-12);
  }
  // Final continuous XY may carry a stale slice alias after optimization.
  // Reassociate physical floors without snapping XY or changing endpoints.
  std::vector<Eigen::Vector3d> projected{{-.1,-.1,.3},{.1,.1,.3}};
  Eigen::VectorXd stale=Eigen::VectorXd::Zero(2);
  planner.projectSupportHeights(projected,stale,projected.front(),projected.back());
  ASSERT_GT(projected.size(),2u);
  EXPECT_NEAR(projected.front().x(),-.1,1e-12);
  EXPECT_NEAR(projected.back().x(),.1,1e-12);
  for(const auto &point:projected)EXPECT_NEAR(point.z(),.3,1e-12);
  std::vector<Eigen::Vector3d> wrong_floor{{-.1,-.1,2.3},{.1,.1,2.3}};
  EXPECT_THROW(planner.projectSupportHeights(wrong_floor,stale,wrong_floor.front(),wrong_floor.back()),std::runtime_error);
  std::remove(bundle.c_str());std::remove(support_path.c_str());
}

TEST(PhysicalSupport, OptimizerAndProjectionUseIdenticalHalfOpenCells) {
  EXPECT_EQ(supportGridIndex(4.49),4);
  EXPECT_EQ(supportGridIndex(4.5),5);
  EXPECT_EQ(supportGridIndex(-.5),0);
  EXPECT_EQ(supportGridIndex(-.51),-1);
  constexpr int n=9;Eigen::MatrixXd h(n,n),zero=Eigen::MatrixXd::Zero(n,n);
  for(int y=0;y<n;++y)for(int x=0;x<n;++x)h(y,x)=y*10+x;
  DenseElevationMap map;map.Init(.1,1,zero,zero,h,zero,zero,zero);
  map.SetPhysicalSupportMode(true);
  EXPECT_EQ(map.GetHeight(0,4.51,3.51),45.);
  EXPECT_EQ(map.GetHeight(0,4.49,3.49),34.);
  map.SetPhysicalSupportMode(false);
  EXPECT_EQ(map.GetHeight(0,4.51,3.51),34.);
}

TEST(PhysicalSupport, MissingFloorDistanceHasNoExtraClearanceOrStoreySwitch) {
  constexpr int n=9;Eigen::MatrixXd h=Eigen::MatrixXd::Zero(2*n,n),zero=Eigen::MatrixXd::Zero(2*n,n);
  h.block(n,0,n,n).setConstant(6.);
  h(4,4)=6.;
  DenseElevationMap map;map.Init(.1,2,zero,zero,h,zero,zero,zero);map.SetPhysicalSupportMode(true,.26);
  Eigen::Vector2d gradient;
  EXPECT_NEAR(map.PhysicalSupportResidual(4.1,4.2,0.,&gradient),std::sqrt(.6),1e-12);
  EXPECT_NEAR(gradient(0),0.,1e-12);EXPECT_NEAR(gradient(1),-1./std::sqrt(.6),1e-12);
  constexpr double e=1e-5;
  const double derivative=(map.PhysicalSupportResidual(4.1,4.2+e,0.)-map.PhysicalSupportResidual(4.1,4.2-e,0.))/(2*e);
  EXPECT_NEAR(derivative,gradient(1),1e-8);
  EXPECT_EQ(map.PhysicalSupportResidual(4.6,4.2,0.,&gradient),0.);
  EXPECT_EQ(gradient.squaredNorm(),0.);
  int layer=0;double height=0.;
  EXPECT_FALSE(map.AssociatePhysicalSurface(4.1,4.2,0.,layer,height));
  EXPECT_TRUE(map.AssociatePhysicalSurface(4.1,4.2,6.,layer,height));
  EXPECT_EQ(height,6.);
  EXPECT_THROW(map.PhysicalSupportResidual(4.1,4.2,3.),std::runtime_error);
  EXPECT_THROW(map.PhysicalSupportResidual(std::numeric_limits<double>::quiet_NaN(),0.,0.),std::runtime_error);
  EXPECT_THROW(map.PhysicalSupportResidual(0.,std::numeric_limits<double>::infinity(),0.),std::runtime_error);
  h(0,0)=0.;h(n,0)=.2;map.Init(.1,2,zero,zero,h,zero,zero,zero);
  EXPECT_FALSE(map.AssociatePhysicalSurface(0.,0.,.1,layer,height));
  h(n,0)=0.;map.Init(.1,2,zero,zero,h,zero,zero,zero);
  EXPECT_TRUE(map.AssociatePhysicalSurface(0.,0.,0.,layer,height));
}

TEST(PhysicalSupport, TrialEvaluationCannotMutateReferenceFloor) {
  constexpr int n=9;Eigen::MatrixXd h=Eigen::MatrixXd::Zero(2*n,n),zero=Eigen::MatrixXd::Zero(2*n,n);
  h.block(n,0,n,n).setConstant(6.);h(4,4)=6.;
  auto map=std::make_shared<DenseElevationMap>();map->Init(.1,2,zero,zero,h,zero,zero,zero);map->SetPhysicalSupportMode(true,.26);
  gtsam::Vector6 a6=gtsam::Vector6::Zero(),b6=a6;a6(0)=2.;a6(3)=2.;b6(0)=4.1;b6(3)=4.2;
  gtsam::Vector4 a4=gtsam::Vector4::Zero(),b4=a4;a4(0)=2.;a4(2)=2.;b4(0)=4.1;b4(2)=4.2;
  gtsam::Matrix first,second,other,unused;
  GPObstacleFactor node6(1,map,0,0.,.1,15.);
  const auto n6=node6.evaluateError(a6,first);node6.evaluateError(b6,other);
  EXPECT_TRUE(node6.evaluateError(a6,second).isApprox(n6,1e-12));EXPECT_TRUE(first.isApprox(second,1e-12));EXPECT_EQ(node6.height_hint_,0.);
  GPObstacleFactorWnoa node4(1,map,0,0.,.1,15.);
  const auto n4=node4.evaluateError(a4,first);node4.evaluateError(b4,other);
  EXPECT_TRUE(node4.evaluateError(a4,second).isApprox(n4,1e-12));EXPECT_TRUE(first.isApprox(second,1e-12));EXPECT_EQ(node4.height_hint_,0.);
  GPInterpolateObstacleFactor inter6(1,2,map,0,0.,15.,.1,.01,1.,0.,.5);
  const auto i6=inter6.evaluateError(a6,a6,first,unused);inter6.evaluateError(b6,b6,other,unused);
  EXPECT_TRUE(inter6.evaluateError(a6,a6,second,unused).isApprox(i6,1e-12));EXPECT_TRUE(first.isApprox(second,1e-12));EXPECT_EQ(inter6.height_hint_,0.);
  GPInterpolateObstacleFactorWnoa inter4(1,2,map,0,0.,15.,.1,.01,1.,0.,.5);
  const auto i4=inter4.evaluateError(a4,a4,first,unused);inter4.evaluateError(b4,b4,other,unused);
  EXPECT_TRUE(inter4.evaluateError(a4,a4,second,unused).isApprox(i4,1e-12));EXPECT_TRUE(first.isApprox(second,1e-12));EXPECT_EQ(inter4.height_hint_,0.);
}

TEST(PhysicalSupport, NativeContinuousFloorCannotBeVetoedByMissingTomogramAlias) {
  constexpr int n=9;Eigen::MatrixXd h=Eigen::MatrixXd::Constant(n,n,-100.),zero=Eigen::MatrixXd::Zero(n,n);
  DenseElevationMap map;map.Init(.1,1,zero,zero,h,zero,zero,zero);map.SetPhysicalSupportMode(true,.26);
  map.SetPhysicalSurfaceQuery([](double x,double y,double hint,double &height){
    height=0.;return x>=0.&&x<9.&&y>=0.&&y<9.&&std::abs(hint)<.26;
  });
  int layer=0;double height=0.;Eigen::Vector2d gradient;
  EXPECT_TRUE(map.AssociatePhysicalSurface(4.1,4.2,0.,layer,height));
  EXPECT_EQ(height,0.);EXPECT_EQ(map.PhysicalSupportResidual(4.1,4.2,0.,&gradient),0.);
  EXPECT_EQ(gradient.squaredNorm(),0.);
  EXPECT_FALSE(map.AssociatePhysicalSurface(4.1,4.2,1.,layer,height));
}
