from pathlib import Path
v=Path('.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v288')
p=v/'repair_probe.cpp';s=p.read_text().replace('// Inflated evidence cannot be waived, even if no ray traversed this voxel.','// Cleared inflation is unknown evidence, eligible for full supported-air review.')
s=s.replace('"raw_unknown_provenance_before_inflation",typed==reactive_stair::Verdict::UnknownObstacle','"cleared_inflation_supported_air",typed==reactive_stair::Verdict::Free').replace('"inflated_unknown_refused",map->getInflateOccupancy(Eigen::Vector3d(0,0,.3),0.)!=0','"cleared_inflation_footprint_supported",map->getInflateOccupancy(Eigen::Vector3d(0,0,.3),0.)==0')
# Actual terrain contributor below the queried air (not an invented free label).
needle='  state.reactive_nonterrain_hits_.clear();map->invalidateRawContributorCache();\n  state.md_.occupancy_buffer_[address]=state.mp_.clamp_min_log_-1.;'
replace=needle+'''
  Eigen::Vector3i ground_index=index;ground_index.z()-=2;
  const int ga=map->toAddress(ground_index);
  const double saved=state.md_.occupancy_buffer_[ga];
  state.md_.occupancy_buffer_[ga]=state.mp_.clamp_max_log_;
  state.reactive_terrain_hits_.insert({ground_index.x(),ground_index.y(),ground_index.z()});
  map->invalidateRawContributorCache();
  map->reactiveOccupancy(Eigen::Vector3d(.18,0,.3),nullptr,&typed);
  check("inflated_raw_unknown_terrain_contributor",typed==reactive_stair::Verdict::Free);
  state.reactive_terrain_hits_.clear();state.md_.occupancy_buffer_[ga]=saved;map->invalidateRawContributorCache();
'''
# Check actual member name exists before selecting test provenance.
assert 'reactive_terrain_hits_' in (v/'src/plan_env/include/plan_env/grid_map.h').read_text()
s=s.replace(needle,replace);p.write_text(s)
p=v/'field_probe.cpp';s=p.read_text();s=s.replace('const double expected=std::pow(std::max((.15-margin)/.15,0.),2);','const double expected=std::pow(edge?std::clamp((.15-margin)/.15,0.,1.):std::max((.15-margin)/.15,0.),2);')
s=s.replace('a.gradient.y()<-.1 && std::abs(a.gradient.y()-numerical)<2e-4;','(edge && margin<=1e-8 ? a.gradient.norm()<1e-6 : a.gradient.y()<-.1) &&\n          (edge && std::abs(margin)<1e-8 ? true : std::abs(a.gradient.y()-numerical)<2e-4);');p.write_text(s)
p=v/'src/scan_nav2_controller/test/test_tracking_behavior.cpp';s=p.read_text();s+='''
TEST_F(TrackingBehavior, TerminalYawCentersInWorldCoordinatesWithSlew)
{
  for(double yaw : {-.8, .8, 2.4}) {
    node->clearTrajectory(); replace();
    body.pose.position.x=49.90;body.pose.position.y=.04;
    geometry_msgs::msg::Twist previous;
    for(int i=0;i<60;++i) {
      const auto cmd=tick(yaw);
      EXPECT_TRUE(node->goal_position_latched_);EXPECT_TRUE(node->executionFrozen());
      EXPECT_LE(std::abs(cmd.linear.x-previous.linear.x),.04+1e-8);
      EXPECT_LE(std::abs(cmd.linear.y-previous.linear.y),.04+1e-8);
      EXPECT_LE(std::abs(cmd.angular.z-previous.angular.z),.06+1e-8);
      previous=cmd;
    }
    const auto cmd=node->sampled_command_;
    const Eigen::Vector2d world(std::cos(yaw)*cmd.linear.x-std::sin(yaw)*cmd.linear.y,
        std::sin(yaw)*cmd.linear.x+std::cos(yaw)*cmd.linear.y);
    EXPECT_GT(world.dot(Eigen::Vector2d(.10,-.04)),0.);
    EXPECT_GT(std::hypot(cmd.linear.x,cmd.linear.y),.01);
    EXPECT_LT(cmd.angular.z*yaw,0.);
    EXPECT_DOUBLE_EQ(node->exec_time_,0.);
  }
  body.pose.position.x=50.;body.pose.position.y=0.;
  for(int i=0;i<60;++i)tick(0.);
  EXPECT_EQ(node->sampled_command_,geometry_msgs::msg::Twist());
}
''';p.write_text(s)
p=v/'src/bspline_opt/test/test_uniform_bspline.cpp';s=p.read_text();s+='''
#include <bspline_opt/environmental_curve_cost.h>
TEST(EnvironmentalQuadrature, FixedPartitionHasConsistentDirectionalDerivative)
{
  Eigen::MatrixXd q=Eigen::MatrixXd::Zero(3,8);
  for(int i=0;i<8;++i){q(0,i)=i*.1;q(1,i)=.02*std::sin(i);}
  const auto counts=scan_planner::environmentalCurveSamples(q);
  auto score=[](const Eigen::Vector3d&p,double,Eigen::Vector4d &g) {
    g<<0.,4.*p.y()*p.y()*p.y(),0.,0.;return std::pow(p.y(),4);
  };
  auto heading=[](const Eigen::Vector3d&,const Eigen::Vector3d&,const Eigen::Vector3d&){return 0.;};
  Eigen::MatrixXd g,unused;
  const double cost=scan_planner::environmentalCurveCost(q,.2,.8,score,heading,g,0.,.025,10,&counts);
  const double eps=1e-6;q(1,3)+=eps;
  const double plus=scan_planner::environmentalCurveCost(q,.2,.8,score,heading,unused,0.,.025,10,&counts);
  q(1,3)-=2*eps;
  const double minus=scan_planner::environmentalCurveCost(q,.2,.8,score,heading,unused,0.,.025,10,&counts);
  EXPECT_GT(cost,0.);EXPECT_NEAR(g(1,3),(plus-minus)/(2*eps),1e-9);
  // Evaluation count is constant even across a partition ceil threshold.
  int calls=0;auto countScore=[&](const Eigen::Vector3d&p,double,Eigen::Vector4d&g){++calls;return score(p,0.,g);};
  for(double scale : {.999,1.001,2.}) {
    calls=0;Eigen::MatrixXd trial=scale*q;
    scan_planner::environmentalCurveCost(trial,.2,.8,countScore,heading,unused,0.,.025,10,&counts);
    EXPECT_EQ(calls,std::accumulate(counts.begin(),counts.end(),0));
  }
}
''';s=s.replace('#include <bspline_opt/environmental_curve_cost.h>','#include <bspline_opt/environmental_curve_cost.h>\n#include <numeric>');p.write_text(s)
print('regression sources created')
