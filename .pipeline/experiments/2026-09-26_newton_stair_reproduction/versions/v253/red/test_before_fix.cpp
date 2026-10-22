#include <gtest/gtest.h>
#include <lite3_nav2_plugins/pct_route_planner.hpp>
#include <plan_env/static_support.h>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <unistd.h>

namespace {
struct EndpointFixture {
  const std::string base="/tmp/pct_endpoint_"+std::to_string(getpid());
  std::shared_ptr<reactive_stair::StaticSupportField> support;
  static std::string hash(const std::string &bytes) {
    uint64_t h=14695981039346656037ULL;
    for(unsigned char c:bytes){h^=c;h*=1099511628211ULL;}return std::to_string(h);
  }
  EndpointFixture() {
    constexpr int n=41;
    std::ofstream map(base+".pct",std::ios::binary);map.write("PCTMAP01",8);
    const uint32_t dims[]={1,n,n};map.write(reinterpret_cast<const char*>(dims),sizeof(dims));
    const double meta[]={.1,0.,0.,0.,.5};map.write(reinterpret_cast<const char*>(meta),sizeof(meta));
    for(int channel=0;channel<6;++channel)for(int i=0;i<n*n;++i) {
      const double value=channel==2?10.:0.;map.write(reinterpret_cast<const char*>(&value),sizeof(value));
    }
    for(int i=0;i<n*n;++i)map.put(1);map.close();
    const std::string gap="0 0 0\n";{std::ofstream out(base+".gap");out<<gap;}
    std::ostringstream text;text<<"SUPPORT247 .1 -2.05 -2.05 1 -2.05 -2.05 .3 .12 .35 .18 fixture world 1681 "<<std::quoted(base+".gap")<<' '<<hash(gap)<<'\n';
    for(int x=0;x<n;++x)for(int y=0;y<n;++y)text<<x<<' '<<y<<" 0 1 1\n";
    const auto bytes=text.str();{std::ofstream out(base+".support");out<<bytes;}
    support=std::make_shared<reactive_stair::StaticSupportField>(base+".support",hash(bytes));
  }
  ~EndpointFixture(){for(auto ext:{".pct",".gap",".support"})std::remove((base+ext).c_str());}
};
void exactEnds(const std::vector<Eigen::Vector3d> &path,const Eigen::Vector3d &a,const Eigen::Vector3d &b) {
  ASSERT_GE(path.size(),2u);EXPECT_LT((path.front()-a).norm(),1e-12);EXPECT_LT((path.back()-b).norm(),1e-12);
}
}

TEST(ContinuousEndpoints, TrueSupportedEndpointIsNotReplacedByRoundedGapCentre) {
  EndpointFixture fixture;
  const Eigen::Vector3d a(.449,.449,.34),b(1.173,1.213,.3);
  const double yaw=std::atan2(b.y()-a.y(),b.x()-a.x());
  ASSERT_EQ(fixture.support->assess(a.x(),a.y(),a.z(),yaw),reactive_stair::Verdict::Free);
  ASSERT_EQ(fixture.support->assess(.4,.4,.3,yaw),reactive_stair::Verdict::SupportGap);
  for(bool quintic:{true,false}) {
    lite3_nav2::PCTRoutePlanner planner(fixture.base+".pct",.3,quintic);
    planner.setStaticSupport(fixture.support);
    for(bool smooth:{false,true}) {
      exactEnds(planner.plan(a,b,smooth),a,b);
      exactEnds(planner.plan(b,a,smooth),b,a);
    }
  }
}
TEST(ContinuousEndpoints, UnsupportedTrueEndpointCannotUseSupportedGridCandidate) {
  EndpointFixture fixture;lite3_nav2::PCTRoutePlanner planner(fixture.base+".pct",.3);
  planner.setStaticSupport(fixture.support);
  const Eigen::Vector3d bad(0.,0.,.3),good(1.17,1.21,.3);
  for(bool smooth:{false,true}) {
    EXPECT_THROW(planner.plan(bad,good,smooth),std::runtime_error);
    EXPECT_THROW(planner.plan(good,bad,smooth),std::runtime_error);
  }
  // A failed request must not leak parents or transient endpoints into the next.
  const Eigen::Vector3d a(.449,.449,.3);
  exactEnds(planner.plan(a,good,true),a,good);
}
TEST(ContinuousEndpoints, DistinctRequestsWithinOneCellKeepBothEndpoints) {
  EndpointFixture fixture;
  for(bool quintic:{true,false}) {
    lite3_nav2::PCTRoutePlanner planner(fixture.base+".pct",.3,quintic);
    planner.setStaticSupport(fixture.support);
    const Eigen::Vector3d a(1.011,1.012,.32),b(1.034,1.031,.31);
    for(bool smooth:{false,true}) {
      exactEnds(planner.plan(a,b,smooth),a,b);
      exactEnds(planner.plan(b,a,smooth),b,a);
    }
  }
}
