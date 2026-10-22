#include <lite3_nav2_plugins/pct_route_planner.hpp>
#include "v232/tools/raw_reference.h"
#include <iostream>
#include <random>
#include <cassert>
#include <filesystem>
#include <fstream>
#include <iomanip>
int main() {
  const char *path="/task/environment_score_v224/fixtures/building/environment03.env",*fnv="4316416882194453309";
  lite3_nav2::StaticBodyGeometry field(path,fnv);
  void *oracle=makePointField(path,fnv,false);
  std::mt19937 rng(244);std::uniform_real_distribution<double> x(-7.5,10.5),y(-9.,8.5),z(.25,6.),angle(-3.141592653589793,3.141592653589793);
  int clear=0,blocked=0;
  for(int i=0;i<2000;++i) {
    const Eigen::Vector3d p(x(rng),y(rng),z(rng));const double yaw=angle(rng);double v[4];
    pointAssessment(oracle,p.x(),p.y(),p.z(),yaw,v);
    const bool ok=field.clear(p,yaw);if(ok!=bool(v[1]>0.))throw std::runtime_error("original PCD cylinder parity mismatch");
    ok?++clear:++blocked;
  }
  // Diagnostic heading sweep keeps support-only endpoint screening distinct
  // from a complete original-PCD body intersection witness.
  std::ofstream sweep("/evaluation/endpoint_geometry.csv");
  sweep<<std::setprecision(17)<<"case,endpoint,yaw,raw_solid_margin,body_clear\n";
  for(const auto &casepath:std::filesystem::directory_iterator("/cases")) {
    std::ifstream ep(casepath.path()/"endpoints.txt");Eigen::Vector3d start,goal;
    ep>>start.x()>>start.y()>>start.z()>>goal.x()>>goal.y()>>goal.z();if(!ep)continue;
    for(int side=0;side<2;++side)for(int k=0;k<72;++k) {
      const auto p=side?goal:start;const double yaw=k*M_PI/72.;double v[4];
      pointAssessment(oracle,p.x(),p.y(),p.z(),yaw,v);
      sweep<<casepath.path().filename().string()<<','<<(side?"goal":"start")<<','<<yaw<<','<<v[1]<<','<<field.clear(p,yaw)<<'\n';
    }
  }
  freePointField(oracle);
  if(field.clear({0,0,0},std::numeric_limits<double>::quiet_NaN()))throw std::runtime_error("NaN admitted");
  bool rejected=false;try{lite3_nav2::StaticBodyGeometry bad(path,"0");}catch(const std::runtime_error&){rejected=true;}
  if(!rejected)throw std::runtime_error("tampered geometry admitted");
  // Real Building high-cost goal reproduces the v242 failure without recovery.
  lite3_nav2::PCTRoutePlanner legacy("/work/fixtures/building/route.pct",.3);
  rejected=false;try{legacy.plan({6.454685211,-4.486811161,4.833031197},{8.054685593,-3.986811161,4.839493294},false);}
  catch(const std::runtime_error&e){rejected=std::string(e.what())=="pct_no_route";}
  if(!rejected)throw std::runtime_error("legacy endpoint failure no longer reproduced");
  // Refusing the real connector must prevent a route, even when geometric
  // endpoint anchors exist. This hits the actual high-cost-start failure seam.
  lite3_nav2::PCTRoutePlanner recovery("/work/fixtures/building/route.pct",.3);
  recovery.setEnvironmentalField(std::make_shared<reactive_stair::EnvironmentalField>(
    "/work/fixtures/building/environment225.env","10040917858432847476"));
  int native_calls=0;
  recovery.enableEndpointRecovery(std::make_shared<lite3_nav2::StaticBodyGeometry>(path,fnv),
    std::make_shared<reactive_stair::SupportGapMask>("/work/fixtures/building/support_gap.txt","10479033888964413526",.35),
    [&](const auto &samples){++native_calls;if(samples.empty())throw std::runtime_error("empty connector query");return false;});
  rejected=false;
  try{recovery.plan({-5.545314789,7.413188934,.358030323},{6.454685211,5.513188839,4.833031197},false,-M_PI/2.);}
  catch(const std::runtime_error &e){rejected=std::string(e.what())=="pct_endpoint_no_safe_anchor:start";}
  if(!rejected||!native_calls)throw std::runtime_error("native connector refusal bypassed");
  std::cout<<"original_pcd_shape_parity=2000 clear="<<clear<<" blocked="<<blocked<<" nonfinite_rejected=1 identity_rejected=1 legacy_high_cost_goal_reproduced=1 native_connector_refusal_preserved=1\n";
}
