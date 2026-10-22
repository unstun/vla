from pathlib import Path
v=Path('.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v288')
def edit(f,old,new,count=1):
 p=v/f;s=p.read_text();assert s.count(old)==count,(f,s.count(old),old[:80]);p.write_text(s.replace(old,new))
g='src/plan_env/include/plan_env/grid_map.h'
edit(g,'class GridMap\n{','class GridMap\n{') if False else None
edit(g,'private:\n','private:\n  mutable std::recursive_mutex work_mutex_;\n',1)
# Accessor is public and each private snapshot view has its own independent mutex.
p=v/g;s=p.read_text();pos=s.index('public:',s.index('class GridMap'));s=s[:pos]+s[pos:].replace('public:','public:\n  std::recursive_mutex &workMutex() const { return work_mutex_; }\n',1);p.write_text(s)
f='src/plan_env/src/grid_map.cpp';p=v/f;s=p.read_text();s=s.replace('{scan_runtime::callbackBoundary(node_->get_logger(),','{std::lock_guard<std::recursive_mutex> lock(workMutex());scan_runtime::callbackBoundary(node_->get_logger(),');assert s.count('lock(workMutex())')==8
s=s.replace('  scan_runtime::callbackBoundary(node_->get_logger(),"depthPoseCallback",','  std::lock_guard<std::recursive_mutex> lock(workMutex());\n  scan_runtime::callbackBoundary(node_->get_logger(),"depthPoseCallback",');p.write_text(s)
edit('src/plan_manage/include/plan_manage/scan_replan_fsm.h','      scan_runtime::callbackBoundary(node_->get_logger(),site,','      std::lock_guard<std::recursive_mutex> lock(planner_manager_->grid_map_->workMutex());\n      scan_runtime::callbackBoundary(node_->get_logger(),site,')
f='src/plan_env/include/plan_env/scan_reactive_grid_methods.inc'
edit(f,'''    if (mapState().md_.occupancy_buffer_[address] < mapState().mp_.clamp_min_log_ - 1e-3) {
      obstacle.occupancy = reactive_stair::Occupancy::Unknown;
    } else if (uninflated_air) {
      obstacle.occupancy = reactive_stair::Occupancy::Free;
    } else {
      obstacle.occupancy = rawContributorOccupancy(query_id);
    }''','''    // Inflation provenance takes precedence over an untraversed air voxel.
    // All-terrain contributors are free; missing contributors remain unknown
    // until the complete support/layer/freshness decision below.
    if (!uninflated_air) {
      obstacle.occupancy = rawContributorOccupancy(query_id);
    } else if (mapState().md_.occupancy_buffer_[address] < mapState().mp_.clamp_min_log_ - 1e-3) {
      obstacle.occupancy = reactive_stair::Occupancy::Unknown;
    } else {
      obstacle.occupancy = reactive_stair::Occupancy::Free;
    }''')
edit(f,'verdict==reactive_stair::Verdict::UnknownObstacle && query.in_map && uninflated_air','verdict==reactive_stair::Verdict::UnknownObstacle && query.in_map')
edit(f,'    // An unobserved air voxel is not an observed obstacle. The complete live','    // Unknown air, including cleared inflation with no obstacle contributor,\n    // is not an observed obstacle. The complete live')
f='src/scan_nav2_controller/include/scan_nav2_controller/tracking_node.hpp'
old='''          publishStop(std::abs(error) <= goal_yaw_tolerance_ ? 0.0 : kp_yaw_ * error);'''
new='''          if (std::abs(error) <= goal_yaw_tolerance_)
            publishStop();
          else {
            // Center on the admitted goal while aligning yaw. A zero-XY pivot
            // at the capture radius sweeps the offset body around the wrong point.
            const Eigen::Vector2d vel_world = clampNorm(
                kp_pos_ * (goal_pos_ - odom_pos_).head<2>(), std::max(max_vx_, max_vy_));
            const double c=std::cos(odom_yaw_), s=std::sin(odom_yaw_);
            geometry_msgs::msg::Twist command;
            command.linear.x=std::clamp(c*vel_world.x()+s*vel_world.y(),-max_vx_,max_vx_);
            command.linear.y=std::clamp(-s*vel_world.x()+c*vel_world.y(),-max_vy_,max_vy_);
            command.angular.z=std::clamp(kp_yaw_*error,-max_vyaw_,max_vyaw_);
            publishVelocity(command);
          }'''
edit(f,old,new)
# Edge cost remains saturated and continuous in value at zero, while only solid
# has an escape derivative through penetration. Do not make negative edge cost zero.
f='src/plan_env/src/environmental_field.cpp'
edit(f,'const double ep=penalty(edge),sp=penalty(solid);','const double ep=std::clamp((d.target-edge)/d.target,0.,1.),sp=penalty(solid);')
edit(f,'out.edge_penalty=penalty(out.edge_margin);out.solid_penalty=penalty(out.solid_margin);','out.edge_penalty=std::clamp((d.target-out.edge_margin)/d.target,0.,1.);out.solid_penalty=penalty(out.solid_margin);')
edit(f,'if(out.edge_margin<d.target)','if(0.0<out.edge_margin && out.edge_margin<d.target)')
f='src/bspline_opt/include/bspline_opt/environmental_curve_cost.h'
edit(f,'#include <stdexcept>','#include <stdexcept>\n#include <vector>')
edit(f,'namespace scan_planner {','''namespace scan_planner {
// Fix the integration partition at optimizer entry. Line searches must compare
// the same objective, rather than changing quadrature when a trial crosses ceil.
inline std::vector<int> environmentalCurveSamples(const Eigen::MatrixXd &q,
    double spatial_step=.025,int minimum_samples=10) {
  if(q.rows()!=3 || !q.allFinite() || !std::isfinite(spatial_step) || spatial_step<=0 || minimum_samples<1)
    throw std::invalid_argument("Invalid environmental sample geometry");
  std::vector<int> counts;
  for(int span=0;span<q.cols()-3;++span) {
    double length=0.;for(int k=0;k<3;++k)length+=(q.col(span+k+1)-q.col(span+k)).norm();
    const Eigen::Vector3d lv=.5*(q.col(span+2)-q.col(span)),rv=.5*(q.col(span+3)-q.col(span+1));
    const double turn=std::abs(std::remainder(std::atan2(rv.y(),rv.x())-std::atan2(lv.y(),lv.x()),2*M_PI));
    const double required=std::max(length/spatial_step,turn/(2*spatial_step));
    if(!std::isfinite(required) || required>std::numeric_limits<int>::max()-1)
      throw std::invalid_argument("Nonfinite environmental sample geometry");
    counts.push_back(std::max(minimum_samples,int(std::ceil(required))));
  }
  return counts;
}''')
edit(f,'double spatial_step=.025,int minimum_samples=10) {\n  gradient','double spatial_step=.025,int minimum_samples=10,\n    const std::vector<int> *fixed_samples=nullptr) {\n  gradient')
p=v/f;s=p.read_text();a=s.index('  double total=0.;');b=s.index('    const double weight=interval/samples;',a)
s=s[:a]+'''  const auto counts=fixed_samples ? *fixed_samples : environmentalCurveSamples(q,spatial_step,minimum_samples);
  if(counts.size()!=size_t(q.cols()-3) || std::any_of(counts.begin(),counts.end(),[](int n){return n<1;}))
    throw std::invalid_argument("Invalid fixed environmental partition");
  double total=0.;
  for(int span=0;span<q.cols()-3;++span) {
    const int samples=counts[span];
'''+s[b:];p.write_text(s)
f='src/bspline_opt/include/bspline_opt/bspline_optimizer.h'
edit(f,'    GridMap::Ptr grid_map_;','    GridMap::Ptr grid_map_;\n    std::vector<int> environmental_samples_;')
f='src/bspline_opt/src/bspline_optimizer.cpp'
edit(f,'      /* ---------- optimize ---------- */','      environmental_samples_=environmentalCurveSamples(cps_.points);\n      /* ---------- optimize ---------- */')
edit(f,'      if(force_stop_type_!=DONT_STOP)result=lbfgs::LBFGSERR_CANCELED;','''      // The solver restores q to its last accepted point on line-search error;
      // objective callbacks leave cps at the final rejected trial otherwise.
      memcpy(cps_.points.data()+3*start_id,q,variable_num_*sizeof(q[0]));
      if(force_stop_type_!=DONT_STOP)result=lbfgs::LBFGSERR_CANCELED;''')
edit(f,'          result == lbfgs::LBFGS_STOP)\n      {','''          result == lbfgs::LBFGS_STOP ||
          (result<0 && result!=lbfgs::LBFGSERR_CANCELED && iter_num_>1 && cps_.points.allFinite()))
      {''',2)
edit(f,'      int result = lbfgs::lbfgs_optimize(variable_num_, q, &final_cost, BsplineOptimizer::costFunctionRefine, NULL, BsplineOptimizer::earlyExit, this, &lbfgs_params);','''      environmental_samples_=environmentalCurveSamples(cps_.points);
      int result = lbfgs::lbfgs_optimize(variable_num_, q, &final_cost, BsplineOptimizer::costFunctionRefine, NULL, BsplineOptimizer::earlyExit, this, &lbfgs_params);
      memcpy(cps_.points.data()+3*start_id,q,variable_num_*sizeof(q[0]));''')
edit(f,'      if(force_stop_type_!=DONT_STOP)return false;','      if(force_stop_type_!=DONT_STOP){lambda4_=origin_lambda4;return false;}')
edit(f,'"Solver error while refining: return=%d, %s", result, lbfgs::lbfgs_strerror(result));','"Solver error while refining: return=%d, %s", result, lbfgs::lbfgs_strerror(result));\n        lambda4_=origin_lambda4;return false;')
edit(f,'      grid_map_->measuredBodyYaw());','      grid_map_->measuredBodyYaw(),.025,10,environmental_samples_.empty()?nullptr:&environmental_samples_);')
print('four source repairs applied')
