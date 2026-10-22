#include <gtest/gtest.h>
#include <plan_env/static_support.h>
#include <a_star/a_star_search.h>
#include <lite3_nav2_plugins/pct_route_planner.hpp>
#include <cstdio>
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
     const double value=channel==0?50.:channel==1?(l?.075:0.):channel==2?(l?1.:.075):0.;
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
  std::remove(bundle.c_str());std::remove(support_path.c_str());
}
