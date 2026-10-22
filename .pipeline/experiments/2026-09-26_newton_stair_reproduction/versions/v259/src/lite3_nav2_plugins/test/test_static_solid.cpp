#include <gtest/gtest.h>
#include <plan_env/static_solid.h>
#include <lite3_nav2_plugins/pct_route_planner.hpp>
#include <trajectory_optimization/gpmp_optimizer/factors/gp_obstacle_factor.h>
#include <trajectory_optimization/gpmp_optimizer/factors/gp_interpolate_obstacle_factor.h>
#include <trajectory_optimization/gpmp_optimizer/factors_wnoa/gp_obstacle_factor.h>
#include <trajectory_optimization/gpmp_optimizer/factors_wnoa/gp_interpolate_obstacle_factor.h>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <unistd.h>
using reactive_stair::StaticSolidField;
namespace {
std::string hash(const std::string &s){uint64_t h=14695981039346656037ULL;for(unsigned char c:s){h^=c;h*=1099511628211ULL;}return std::to_string(h);}
struct Fixture {
  const std::string path="/tmp/static_solid_"+std::to_string(getpid())+".env";
  std::shared_ptr<StaticSolidField> field;
  Fixture(const std::string &points="",size_t n=0,double voxel=0.) {
    std::ostringstream s;s<<std::setprecision(17)<<"ENV224B .1 0 0 .35 .18 .55 .35 .3 .15 "<<voxel<<"\nF 1\n0 0 0 1 0\nO "<<n<<'\n'<<points;
    const auto bytes=s.str();{std::ofstream f(path);f<<bytes;}field=std::make_shared<StaticSolidField>(path,hash(bytes));
  }
  ~Fixture(){std::remove(path.c_str());}
};
}
TEST(StaticSolid, EmptyEvidenceAndInvalidQueries) {
  Fixture f;EXPECT_DOUBLE_EQ(f.field->assess({0,0,.3},0.).margin,.15);
  EXPECT_THROW(f.field->assess({NAN,0,.3},0.),std::runtime_error);
  EXPECT_THROW(f.field->assess({0,0,.3},NAN),std::runtime_error);
  EXPECT_THROW(f.field->assess({1e300,0,.3},0.),std::runtime_error);
  EXPECT_THROW(StaticSolidField(f.path,"wrong"),std::runtime_error);
}
TEST(StaticSolid, BothOrientedCylindersEnforceRealRadius) {
  Fixture f(".50 0 .3 -1e100 -1e100\n",1);
  EXPECT_NEAR(f.field->assess({0,0,.3},0.).margin,-.03,1e-7);
  EXPECT_TRUE(f.field->assess({0,0,.3},0.).collision());
  EXPECT_FALSE(f.field->assess({0,0,.3},M_PI/2).collision());
  EXPECT_NEAR(f.field->assess({0,0,.3},M_PI).margin,-.03,1e-7);
}
TEST(StaticSolid, SameFloorMaterialOnlyIsExcluded) {
  Fixture f(".30 0 0 0 0\n",1);
  EXPECT_FALSE(f.field->assess({0,0,.3},0.).collision());
  // Same XYZ material, but querying the other physical floor must retain it.
  EXPECT_TRUE(f.field->assess({0,0,.03},0.).collision());
}
TEST(StaticSolid, MixedWallOrRailingCannotBeWaivedAsFloor) {
  Fixture f(".30 0 0 0 .565\n",1);
  EXPECT_TRUE(f.field->assess({0,0,.3},0.).collision());
}
TEST(StaticSolid, VerticalExtentAndVoxelUncertaintyMatchOriginalGeometry) {
  Fixture f(".53 0 .3 -1e100 -1e100\n",1,.025);
  EXPECT_NEAR(f.field->assess({0,0,.3},0.).margin,-std::sqrt(3.)*.025,1e-7);
  EXPECT_FALSE(f.field->assess({0,0,-.5},0.).collision());
  EXPECT_FALSE(f.field->assess({0,0,1.},0.).collision());
}
TEST(StaticSolid, WorldAndYawGradientMatchesFiniteDifference) {
  Fixture f(".48 .10 .3 -1e100 -1e100\n",1);
  Eigen::Vector3d p(0.,.02,.3);const double yaw=.4;const auto a=f.field->assess(p,yaw);
  ASSERT_TRUE(a.collision());
  for(int j=0;j<4;++j){auto lo=p,hi=p;double yl=yaw,yh=yaw;const double h=1e-5;
    if(j<3){lo(j)-=h;hi(j)+=h;}else {yl-=h;yh+=h;}
    const double fd=(f.field->assess(hi,yh).margin-f.field->assess(lo,yl).margin)/(2*h);
    EXPECT_NEAR(a.gradient(j),fd,1e-5)<<j;
  }
}
TEST(StaticSolid, BuildingB08WitnessIsOccupiedWithoutCoordinateRule) {
  // Actual vertical original PCD surface, independent of floor association.
  Fixture f("-6.434781074523926 -3.2528491020202637 4.931616306304932 -1e100 -1e100\n",1,.025);
  const auto a=f.field->assess({-6.045314788818359,-3.1868112087249756,4.833031196594238},-2.872806690561133);
  EXPECT_NEAR(a.margin,-.13330188246820845-std::sqrt(3.)*.025,1e-7);EXPECT_TRUE(a.collision());
}
TEST(StaticSolid, OriginalPureUpwardB08FloorMaterialIsNotAHardWall) {
  Fixture f("-6.425 -3.225 4.525 4.533030986785889 4.533030986785889\n",1,.025);
  EXPECT_FALSE(f.field->assess({-6.045314788818359,-3.1868112087249756,4.833031196594238},-2.872806690561133).collision());
}

TEST(StaticSolid, GlobalTransitionUsesContinuousSolidGeometry) {
  Fixture f("0 0 .3 -1e100 -1e100\n",1);
  const char *map=std::getenv("PCT_TEST_MAP");ASSERT_NE(map,nullptr);
  lite3_nav2::PCTRoutePlanner planner(map,.3);planner.setStaticSolid(f.field);
  Node a,b;a.continuous=b.continuous=true;
  // Recover continuous grid coordinates from the fixture-independent wrapper.
  const auto node=[&](double x,double y){Node n;n.continuous=true;
    n.position<< (x-planner.cx_)/planner.resolution_+planner.nx_/2,
                 (y-planner.cy_)/planner.resolution_+planner.ny_/2;
    n.height=0.;return n;};
  a=node(-1,0);b=node(1,0);EXPECT_FALSE(planner.transitionAllowed(a,b));
  a=node(-1,1);b=node(1,1);EXPECT_TRUE(planner.transitionAllowed(a,b));
  EXPECT_THROW(planner.validateSolidPath({{-1,0,.3},{1,0,.3}},true),lite3_nav2::PCTOptimizationFailure);
  EXPECT_NO_THROW(planner.validateSolidPath({{-1,1,.3},{1,1,.3}},true));
}

TEST(StaticSolid, AllHeadingCertificateNeverRejectsAUsableOrientation) {
  Fixture single(".50 0 .3 -1e100 -1e100\n",1);
  EXPECT_FALSE(single.field->impossibleAt({0,0,.3}));
  // A vertical pillar through the body centre blocks every orientation.
  Fixture pillar("0 0 .3 -1e100 -1e100\n",1);
  EXPECT_TRUE(pillar.field->impossibleAt({0,0,.3}));
}

TEST(StaticSolid, InstalledPCTPhysicalCallbackAndAllGPMPJacobiansShareSolidDomain) {
  Fixture f(".48 .10 .3 -1e100 -1e100\n",1);
  const std::string base=f.path+".physical",bundle=base+".pct",support_path=base+".support";
  constexpr int n=21;
  {std::ofstream out(bundle,std::ios::binary);out.write("PCTMAP01",8);const uint32_t dims[]={1,n,n};
   out.write(reinterpret_cast<const char*>(dims),sizeof(dims));const double meta[]={.1,0.,0.,0.,.5};out.write(reinterpret_cast<const char*>(meta),sizeof(meta));
   for(int c=0;c<6;++c)for(int i=0;i<n*n;++i){const double value=c==2?10.:0.;out.write(reinterpret_cast<const char*>(&value),sizeof(value));}
   for(int i=0;i<n*n;++i)out.put(1);}
  std::ostringstream text;text<<"SUPPORT247 .1 -1.05 -1.05 1 -1.05 -1.05 .3 .12 .35 .18 fixture world 441 \"\" none\n";
  for(int x=0;x<n;++x)for(int y=0;y<n;++y)text<<x<<' '<<y<<" 0 1 1\n";
  const auto bytes=text.str();{std::ofstream out(support_path);out<<bytes;}
  lite3_nav2::PCTRoutePlanner planner(bundle,.3);
  planner.setStaticSupport(std::make_shared<reactive_stair::StaticSupportField>(support_path,hash(bytes)));
  planner.setStaticSolid(f.field);auto map=planner.planner_.map_;
  const auto check=[&](auto &node,auto &inter,auto state){
    gtsam::Matrix j1,j2;const auto residual=node.evaluateError(state,j1);ASSERT_GT(residual(0),0.);
    constexpr double e=1e-6;
    for(int j=0;j<state.size();++j){auto a=state,b=state;a(j)+=e;b(j)-=e;
      EXPECT_NEAR((node.evaluateError(a)(0)-node.evaluateError(b)(0))/(2*e),j1(0,j),1e-5);}
    inter.evaluateError(state,state,j1,j2);
    for(int j=0;j<state.size();++j){auto a=state,b=state;a(j)+=e;b(j)-=e;
      EXPECT_NEAR((inter.evaluateError(a,state)(0)-inter.evaluateError(b,state)(0))/(2*e),j1(0,j),1e-5);
      EXPECT_NEAR((inter.evaluateError(state,a)(0)-inter.evaluateError(state,b)(0))/(2*e),j2(0,j),1e-5);}
  };
  gtsam::Vector6 v6=gtsam::Vector6::Zero();v6(0)=10.2;v6(3)=10.;v6(1)=std::sin(.4);v6(4)=std::cos(.4);
  gtsam::Vector4 v4;v4<<10.2,std::sin(.4),10.,std::cos(.4);
  GPObstacleFactor n6(1,map,0,0.,.1,15.);GPInterpolateObstacleFactor i6(1,2,map,0,0.,15.,.1,.01,1.,0.,.3);
  GPObstacleFactorWnoa n4(1,map,0,0.,.1,15.);GPInterpolateObstacleFactorWnoa i4(1,2,map,0,0.,15.,.1,.01,1.,0.,.3);
  check(n6,i6,v6);check(n4,i4,v4);
  std::remove(bundle.c_str());std::remove(support_path.c_str());
}

TEST(StaticSolid, TrueFloorAndOriginalBelowFloorVolumeExemptionsAreBothPreserved) {
  Fixture legacy(".30 0 .325 .6 .6\n",1,.025);
  const std::string bytes="SOLID256B .1 0 0 .35 .18 .55 .35 .3 .15 .025\nF 1\n0 0 0 1 0\nO 1\n.30 0 .325 .6 .6 .33 .33\n";
  {std::ofstream out(legacy.path);out<<bytes;}
  StaticSolidField both(legacy.path,hash(bytes));
  EXPECT_FALSE(both.assess({0,0,.9},0.).collision()); // Original floor volume.
  EXPECT_FALSE(both.assess({0,0,.63},0.).collision()); // Actual upward surface.
  EXPECT_TRUE(both.assess({0,0,.1},0.).collision()); // Another level remains solid.
}

TEST(StaticSolid, BinaryHardQueryMatchesSignedDomainAtContactAndBothHeadings) {
  Fixture f(".53 0 .3 -1e100 -1e100\n",1);
  for(double x:{-1e-5,0.,1e-5})for(double yaw:{0.,M_PI/2.,M_PI}) {
    const Eigen::Vector3d p(x,0.,.3);
    EXPECT_EQ(f.field->collides(p,yaw),f.field->assess(p,yaw).collision());
  }
  EXPECT_THROW(f.field->collides({NAN,0.,.3},0.),std::runtime_error);
}

TEST(StaticSolid, FreeCellIndexRetainsEveryContactAndFloorBoundary) {
  Fixture f(".53 0 .3 0 0\n.1 .4 .6 -1e100 -1e100\n",2,.025);
  for(double boundary:{-.26,0.,.1,.26,.4})for(double eps:{-1e-12,0.,1e-12})
    for(double x:{-.1,0.,.05,.1,.3})for(double yaw:{0.,.7,1.57,3.14}) {
      const Eigen::Vector3d p(x,.05,boundary+eps+.3);
      EXPECT_EQ(f.field->collides(p,yaw),f.field->assess(p,yaw).collision());
    }
  EXPECT_THROW(f.field->collides({1e300,0.,.3},0.),std::runtime_error);
}
