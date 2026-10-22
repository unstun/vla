from pathlib import Path
import json,hashlib
b=Path('.pipeline/experiments/2026-09-26_newton_stair_reproduction');v=b/'versions/v288'
# Single named entry lock; no internal A-star or per-cache locks.
for f in ['src/plan_env/include/plan_env/grid_map.h','src/plan_env/src/grid_map.cpp','src/plan_manage/include/plan_manage/scan_replan_fsm.h','work_probe.cpp']:
 p=v/f;p.write_text(p.read_text().replace('workMutex()','lockMutex()'))
# Constant quadrature removes all per-optimizer partition state and setup.
p=v/'src/bspline_opt/include/bspline_opt/environmental_curve_cost.h';s=p.read_text();a=s.index('// Fix the integration partition');z=s.index('// Cubic B-spline samples',a);s=s[:a]+s[z:];s=s.replace('#include <vector>\n','')
s=s.replace('    double measured_yaw=std::numeric_limits<double>::quiet_NaN(),\n    double spatial_step=.025,int minimum_samples=10,\n    const std::vector<int> *fixed_samples=nullptr) {','    double measured_yaw=std::numeric_limits<double>::quiet_NaN()) {')
s=s.replace('!std::isfinite(lookahead) || lookahead<0 || !std::isfinite(spatial_step) || spatial_step<=0 || minimum_samples<1)','!std::isfinite(lookahead) || lookahead<0)')
a=s.index('  const auto dynamic_samples=');z=s.index('  double total=0.;',a);s=s[:a]+s[z:];s=s.replace('    const int samples=counts[span];','    constexpr int samples=3; // Same objective partition throughout every line search.');p.write_text(s)
p=v/'src/bspline_opt/include/bspline_opt/bspline_optimizer.h';p.write_text(p.read_text().replace('    std::vector<int> environmental_samples_;\n',''))
p=v/'src/bspline_opt/src/bspline_optimizer.cpp';s=p.read_text().replace('      environmental_samples_=environmentalCurveSamples(cps_.points);\n','').replace('lbfgs_params.delta = 1e-6;','lbfgs_params.delta = 1e-4;').replace('grid_map_->measuredBodyYaw(),.025,10,environmental_samples_.empty()?nullptr:&environmental_samples_);','grid_map_->measuredBodyYaw());')
# Keep actual negative solver returns countable even when a safe restored
# candidate is retained. A reduced warning count is not solver convergence.
needle='      if(force_stop_type_!=DONT_STOP)result=lbfgs::LBFGSERR_CANCELED;'
s=s.replace(needle,needle+'''\n      if(result<0 && result!=lbfgs::LBFGSERR_CANCELED && result!=lbfgs::LBFGSERR_MAXIMUMITERATION && iter_num_>1)
        RCLCPP_INFO(rclcpp::get_logger("bspline_opt"),"LBFGS_RESTORED stage=rebound return=%d; hard validation pending",result);''')
needle='      if(force_stop_type_!=DONT_STOP){lambda4_=origin_lambda4;return false;}'
s=s.replace(needle,needle+'''\n      if(result<0 && result!=lbfgs::LBFGSERR_MAXIMUMITERATION && iter_num_>1)
        RCLCPP_INFO(rclcpp::get_logger("bspline_opt"),"LBFGS_RESTORED stage=refine return=%d; hard validation pending",result);''');p.write_text(s)
p=v/'src/bspline_opt/test/test_uniform_bspline.cpp';s=p.read_text().replace('  const auto counts=scan_planner::environmentalCurveSamples(q);\n','').replace(',0.,.025,10,&counts',',0.').replace('std::accumulate(counts.begin(),counts.end(),0)','3*(q.cols()-3)').replace('#include <numeric>\n','');p.write_text(s)
# Keep the same smooth body-frame proportional controller; the shared center
# tolerance prevents Controller from starting PD before tracker centering ends.
p=v/'src/scan_nav2_controller/include/scan_nav2_controller/tracking_node.hpp';s=p.read_text().replace('public:\n  explicit TrackingNode','public:\n  static constexpr double kGoalCenterTolerance=0.02;\n  explicit TrackingNode',1)
a=s.index('        if (std::abs(error) <= goal_yaw_tolerance_)',s.index('// Final capture'));z=s.index('        last_update_time_ = current_time;',a)
s=s[:a]+'''        const Eigen::Vector2d position_error=(goal_pos_-odom_pos_).head<2>();
        const bool centered=position_error.norm()<=kGoalCenterTolerance;
        if (centered && std::abs(error) <= goal_yaw_tolerance_)
          publishStop();
        else {
          const Eigen::Vector2d vel_world=centered ? Eigen::Vector2d::Zero() :
              clampNorm(kp_pos_*position_error,std::min(0.15,std::max(max_vx_,max_vy_)));
          const double c=std::cos(odom_yaw_), s=std::sin(odom_yaw_);
          geometry_msgs::msg::Twist command;
          command.linear.x=std::clamp(c*vel_world.x()+s*vel_world.y(),-max_vx_,max_vx_);
          command.linear.y=std::clamp(-s*vel_world.x()+c*vel_world.y(),-max_vy_,max_vy_);
          command.angular.z=std::abs(error)<=goal_yaw_tolerance_ ? 0. : std::clamp(kp_yaw_*error,-max_vyaw_,max_vyaw_);
          publishVelocity(command);
        }
'''+s[z:];p.write_text(s)
p=v/'src/scan_nav2_controller/src/controller.cpp';s=p.read_text().replace('pose.position.y-g.y)<=state_->xy_tolerance &&\n    std::abs(pose.position.z-g.z)<=state_->z_tolerance;','pose.position.y-g.y)<=std::min(state_->xy_tolerance,scan_planner::TrackingNode::kGoalCenterTolerance) &&\n    std::abs(pose.position.z-g.z)<=state_->z_tolerance;');p.write_text(s)
p=v/'src/scan_nav2_controller/test/test_controller.cpp';s=p.read_text();s+='''
TEST_F(RouteHeadingTest, AlignedOffCenterCaptureKeepsTranslatingBeforePdHold)
{
  expiredCornerStub();
  auto body=pose();body.pose=route.poses.back().pose;body.pose.position.x-=.1;
  const auto cmd=settledCommand(body,{}).twist;
  EXPECT_GT(std::hypot(cmd.linear.x,cmd.linear.y),.01);
  EXPECT_LE(std::hypot(cmd.linear.x,cmd.linear.y),.15+1e-9);
  EXPECT_FALSE(actual->state_->goal_reached);EXPECT_FALSE(actual->terminalPhase());
  body.pose=route.poses.back().pose;
  EXPECT_EQ(settledCommand(body,{}).twist,geometry_msgs::msg::Twist());
  EXPECT_TRUE(actual->state_->goal_reached);
}
''';p.write_text(s)
(v/'source_inventory.json').write_text(json.dumps({str(p.relative_to(v)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((v/'src').rglob('*')) if p.is_file()},indent=2)+'\n')
p=v/'README.md';p.write_text('''# v288 candidate

Parent: frozen v287. User-authorized lightweight changes: one recursive map/FSM entry lock; one live obstacle classification plus support decision; support-projection/chord-plane A-star proposals; constant3 environmental quadrature, clipped edge gradient, past3/delta1e-4 and restored accepted variables; bounded terminal XY/yaw centering before PD. Hard0.35m, scanner0.1s, original cohort/geometry/factory policy unchanged. No scene/coordinate branches. Outcomes are recorded in the independent v288 audit; the version label is not acceptance.
''')
print('Final constant quadrature / past-delta / center-before-PD design applied')
