#include <plan_manage/planner_manager.h>
#include <traj_utils/polynomial_traj.h>

#include <Eigen/Eigen>
#include <rclcpp/rclcpp.hpp>

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace
{
struct Options
{
  Eigen::Vector3d start{0.0, 0.0, 0.0};
  Eigen::Vector3d start_vel{0.0, 0.0, 0.0};
  Eigen::Vector3d start_acc{0.0, 0.0, 0.0};
  Eigen::Vector3d target{1.0, 0.0, 0.0};
  Eigen::Vector3d target_vel{0.0, 0.0, 0.0};
  bool poly_init{true};
  bool random_poly{false};
  unsigned int seed{1};
  int samples{41};
  bool show_help{false};
};

std::string vec_to_string(const Eigen::Vector3d &v)
{
  std::ostringstream os;
  os << std::fixed << std::setprecision(9) << v.x() << "," << v.y() << "," << v.z();
  return os.str();
}

double max_abs_component(const Eigen::Vector3d &v)
{
  return std::max(std::abs(v.x()), std::max(std::abs(v.y()), std::abs(v.z())));
}

Eigen::Vector3d parse_vec3(const std::string &text, const std::string &flag)
{
  std::string s = text;
  std::replace(s.begin(), s.end(), ',', ' ');
  std::istringstream is(s);
  Eigen::Vector3d v;
  if (!(is >> v.x() >> v.y() >> v.z()))
  {
    throw std::runtime_error("Invalid " + flag + " vector: " + text + " (expected x,y,z)");
  }
  std::string extra;
  if (is >> extra)
  {
    throw std::runtime_error("Invalid " + flag + " vector: trailing token in " + text);
  }
  if (!std::isfinite(v.x()) || !std::isfinite(v.y()) || !std::isfinite(v.z()))
  {
    throw std::runtime_error("Invalid " + flag + " vector: non-finite component in " + text);
  }
  return v;
}

bool parse_bool(const std::string &text, const std::string &flag)
{
  if (text == "1" || text == "true" || text == "TRUE" || text == "yes" || text == "on")
    return true;
  if (text == "0" || text == "false" || text == "FALSE" || text == "no" || text == "off")
    return false;
  throw std::runtime_error("Invalid " + flag + " bool: " + text);
}

void usage(std::ostream &os)
{
  os << "Usage: rebound_replan_repro [options] --ros-args --params-file <native_scan.yaml>\n"
     << "\n"
     << "Options are parsed after rclcpp removes ROS arguments. Vector format is x,y,z.\n"
     << "  --start x,y,z          start position, meters\n"
     << "  --start-vel x,y,z      start velocity, m/s\n"
     << "  --start-acc x,y,z      start acceleration, m/s^2\n"
     << "  --target x,y,z         target position, meters\n"
     << "  --target-vel x,y,z     target velocity, m/s\n"
     << "  --poly-init BOOL       pass flag_polyInit to reboundReplan (default true)\n"
     << "  --random-poly BOOL     pass flag_randomPolyTraj to reboundReplan (default false)\n"
     << "  --seed N               std::srand seed before reboundReplan (default 1)\n"
     << "  --samples N            trajectory diagnostic sample count on success (default 41)\n"
     << "  --help                 print this help\n"
     << "\n"
     << "This executable initializes the real SCAN GridMap/BsplineOptimizer/PlanningVisualization,\n"
     << "but does not feed a cloud. Map condition is dynamics-only empty-grid isolation.\n";
}

Options parse_options(const std::vector<std::string> &args)
{
  Options opt;
  for (size_t i = 1; i < args.size(); ++i)
  {
    const std::string flag = args[i];
    auto need_value = [&](const std::string &name) -> std::string {
      if (i + 1 >= args.size())
        throw std::runtime_error("Missing value for " + name);
      return args[++i];
    };
    if (flag == "--help" || flag == "-h")
    {
      opt.show_help = true;
    }
    else if (flag == "--start")
    {
      opt.start = parse_vec3(need_value(flag), flag);
    }
    else if (flag == "--start-vel")
    {
      opt.start_vel = parse_vec3(need_value(flag), flag);
    }
    else if (flag == "--start-acc")
    {
      opt.start_acc = parse_vec3(need_value(flag), flag);
    }
    else if (flag == "--target")
    {
      opt.target = parse_vec3(need_value(flag), flag);
    }
    else if (flag == "--target-vel")
    {
      opt.target_vel = parse_vec3(need_value(flag), flag);
    }
    else if (flag == "--poly-init")
    {
      opt.poly_init = parse_bool(need_value(flag), flag);
    }
    else if (flag == "--random-poly")
    {
      opt.random_poly = parse_bool(need_value(flag), flag);
    }
    else if (flag == "--seed")
    {
      const std::string value = need_value(flag);
      size_t parsed = 0;
      unsigned long seed = std::stoul(value, &parsed, 10);
      if (parsed != value.size() || seed > std::numeric_limits<unsigned int>::max())
        throw std::runtime_error("Invalid --seed: " + value);
      opt.seed = static_cast<unsigned int>(seed);
    }
    else if (flag == "--samples")
    {
      const std::string value = need_value(flag);
      size_t parsed = 0;
      int samples = std::stoi(value, &parsed, 10);
      if (parsed != value.size() || samples < 2 || samples > 10001)
        throw std::runtime_error("Invalid --samples: " + value + " (expected 2..10001)");
      opt.samples = samples;
    }
    else
    {
      throw std::runtime_error("Unknown option: " + flag);
    }
  }
  return opt;
}

struct PolyInitDiagnostics
{
  double distance{0.0};
  double total_time{0.0};
  double final_ts{0.0};
  double last_sample_t{0.0};
  int point_count{0};
  Eigen::Vector3d start_vel_eval{0.0, 0.0, 0.0};
  Eigen::Vector3d target_vel_used{0.0, 0.0, 0.0};
  Eigen::Vector3d start_acc_eval{0.0, 0.0, 0.0};
  Eigen::Vector3d last_sample_acc_eval{0.0, 0.0, 0.0};
  Eigen::Vector3d final_acc_eval{0.0, 0.0, 0.0};
  Eigen::Vector3d last_sample_pos{0.0, 0.0, 0.0};
  Eigen::Vector3d final_pos{0.0, 0.0, 0.0};
};

PolyInitDiagnostics mirror_first_call_poly_init(const Options &opt, const scan_planner::PlanParameters &pp)
{
  PolyInitDiagnostics d;
  d.distance = (opt.start - opt.target).norm();
  double ts = d.distance > 0.1 ? pp.ctrl_pt_dist / pp.max_vel_ * 1.2 : pp.ctrl_pt_dist / pp.max_vel_ * 5;
  d.total_time = std::pow(pp.max_vel_, 2) / pp.max_acc_ > d.distance
                   ? std::sqrt(d.distance / pp.max_acc_)
                   : (d.distance - std::pow(pp.max_vel_, 2) / pp.max_acc_) / pp.max_vel_ +
                       2 * pp.max_vel_ / pp.max_acc_;

  PolynomialTraj gl_traj;
  if (!opt.random_poly)
  {
    gl_traj = PolynomialTraj::one_segment_traj_gen(
      opt.start, opt.start_vel, opt.start_acc, opt.target, opt.target_vel, Eigen::Vector3d::Zero(), d.total_time);
  }
  else
  {
    Eigen::Vector3d horizon_dir = ((opt.start - opt.target).cross(Eigen::Vector3d(0, 0, 1))).normalized();
    Eigen::Vector3d vertical_dir = ((opt.start - opt.target).cross(horizon_dir)).normalized();
    // This mirrors the first-call branch of planner_manager.cpp with continuous_failures_count_ == 0.
    Eigen::Vector3d random_inserted_pt = (opt.start + opt.target) / 2 +
                                         (((double)rand()) / RAND_MAX - 0.5) * (opt.start - opt.target).norm() * horizon_dir * 0.8 * (-0.978 / (0 + 0.989) + 0.989) +
                                         (((double)rand()) / RAND_MAX - 0.5) * (opt.start - opt.target).norm() * vertical_dir * 0.4 * (-0.978 / (0 + 0.989) + 0.989);
    Eigen::MatrixXd pos(3, 3);
    pos.col(0) = opt.start;
    pos.col(1) = random_inserted_pt;
    pos.col(2) = opt.target;
    Eigen::VectorXd t(2);
    t(0) = t(1) = d.total_time / 2;
    gl_traj = PolynomialTraj::minSnapTraj(pos, opt.start_vel, opt.target_vel, opt.start_acc, Eigen::Vector3d::Zero(), t);
  }

  double t = 0.0;
  bool flag_too_far = false;
  std::vector<Eigen::Vector3d> point_set;
  ts *= 1.5;
  do
  {
    ts /= 1.5;
    point_set.clear();
    flag_too_far = false;
    Eigen::Vector3d last_pt = gl_traj.evaluate(0);
    for (t = 0; t < d.total_time; t += ts)
    {
      Eigen::Vector3d pt = gl_traj.evaluate(t);
      if ((last_pt - pt).norm() > pp.ctrl_pt_dist * 1.5)
      {
        flag_too_far = true;
        break;
      }
      last_pt = pt;
      point_set.push_back(pt);
    }
  } while (flag_too_far || point_set.size() < 7);
  t -= ts;

  d.final_ts = ts;
  d.last_sample_t = t;
  d.point_count = static_cast<int>(point_set.size());
  d.start_vel_eval = gl_traj.evaluateVel(0);
  d.target_vel_used = opt.target_vel;
  d.start_acc_eval = gl_traj.evaluateAcc(0);
  d.last_sample_acc_eval = gl_traj.evaluateAcc(t);
  d.final_acc_eval = gl_traj.evaluateAcc(d.total_time);
  d.last_sample_pos = gl_traj.evaluate(t);
  d.final_pos = gl_traj.evaluate(d.total_time);
  return d;
}

void print_poly_init_diagnostics(const PolyInitDiagnostics &d)
{
  std::cout << "POLY_INIT_DIAGNOSTICS distance_m=" << d.distance
            << " total_time_s=" << d.total_time
            << " final_ts_s=" << d.final_ts
            << " last_sample_t_s=" << d.last_sample_t
            << " omitted_endpoint_dt_s=" << (d.total_time - d.last_sample_t)
            << " point_count=" << d.point_count << "\n";
  std::cout << "POLY_INIT_END_DERIVATIVES start_vel=" << vec_to_string(d.start_vel_eval)
            << " target_vel=" << vec_to_string(d.target_vel_used)
            << " start_acc=" << vec_to_string(d.start_acc_eval)
            << " last_sample_acc=" << vec_to_string(d.last_sample_acc_eval)
            << " final_acc=" << vec_to_string(d.final_acc_eval)
            << " last_sample_acc_norm=" << d.last_sample_acc_eval.norm()
            << " last_sample_acc_max_abs_component=" << max_abs_component(d.last_sample_acc_eval)
            << " final_acc_norm=" << d.final_acc_eval.norm()
            << "\n";
  std::cout << "POLY_INIT_ENDPOINTS last_sample_pos=" << vec_to_string(d.last_sample_pos)
            << " final_pos=" << vec_to_string(d.final_pos)
            << " target_gap_at_last_sample_m=" << (d.final_pos - d.last_sample_pos).norm()
            << "\n";
}

void print_params(const scan_planner::PlanParameters &pp)
{
  std::cout << "PARAMETERS manager.max_vel=" << pp.max_vel_
            << " manager.max_acc=" << pp.max_acc_
            << " manager.max_jerk=" << pp.max_jerk_
            << " optimization.vel_tolerance=" << pp.vel_tolerance_
            << " optimization.acc_tolerance=" << pp.acc_tolerance_
            << " manager.feasibility_tolerance=" << pp.feasibility_tolerance_
            << " manager.control_points_distance=" << pp.ctrl_pt_dist
            << " manager.planning_horizon=" << pp.planning_horizon_
            << "\n";
}

void print_success_diagnostics(const scan_planner::LocalTrajData &data, int samples)
{
  const double duration = data.duration_;
  scan_planner::UniformBspline acceleration_traj = data.acceleration_traj_;
  scan_planner::UniformBspline jerk_traj = acceleration_traj.getDerivative();

  double max_vel_norm = 0.0;
  double max_acc_norm = 0.0;
  double max_jerk_norm = 0.0;
  double max_vel_abs_component = 0.0;
  double max_acc_abs_component = 0.0;
  double max_jerk_abs_component = 0.0;
  double t_max_vel = 0.0;
  double t_max_acc = 0.0;
  double t_max_jerk = 0.0;

  std::cout << "TRAJECTORY traj_id=" << data.traj_id_
            << " duration_s=" << duration
            << " start_pos=" << vec_to_string(data.start_pos_)
            << " samples=" << samples
            << "\n";
  std::cout << "SAMPLES_BEGIN\n";
  for (int i = 0; i < samples; ++i)
  {
    const double t = duration * static_cast<double>(i) / static_cast<double>(samples - 1);
    const Eigen::Vector3d pos = data.position_traj_.evaluateDeBoorT(t);
    const Eigen::Vector3d vel = data.velocity_traj_.evaluateDeBoorT(t);
    const Eigen::Vector3d acc = data.acceleration_traj_.evaluateDeBoorT(t);
    const Eigen::Vector3d jerk = jerk_traj.evaluateDeBoorT(t);

    if (vel.norm() > max_vel_norm) { max_vel_norm = vel.norm(); t_max_vel = t; }
    if (acc.norm() > max_acc_norm) { max_acc_norm = acc.norm(); t_max_acc = t; }
    if (jerk.norm() > max_jerk_norm) { max_jerk_norm = jerk.norm(); t_max_jerk = t; }
    max_vel_abs_component = std::max(max_vel_abs_component, max_abs_component(vel));
    max_acc_abs_component = std::max(max_acc_abs_component, max_abs_component(acc));
    max_jerk_abs_component = std::max(max_jerk_abs_component, max_abs_component(jerk));

    std::cout << "SAMPLE t=" << t
              << " pos=" << vec_to_string(pos)
              << " vel=" << vec_to_string(vel)
              << " acc=" << vec_to_string(acc)
              << " jerk=" << vec_to_string(jerk)
              << " vel_norm=" << vel.norm()
              << " acc_norm=" << acc.norm()
              << " jerk_norm=" << jerk.norm()
              << "\n";
  }
  std::cout << "SAMPLES_END\n";
  std::cout << "SUMMARY max_vel_norm=" << max_vel_norm
            << " t_max_vel=" << t_max_vel
            << " max_vel_abs_component=" << max_vel_abs_component
            << " max_acc_norm=" << max_acc_norm
            << " t_max_acc=" << t_max_acc
            << " max_acc_abs_component=" << max_acc_abs_component
            << " max_jerk_norm=" << max_jerk_norm
            << " t_max_jerk=" << t_max_jerk
            << " max_jerk_abs_component=" << max_jerk_abs_component
            << "\n";
}
} // namespace

int main(int argc, char **argv)
{
  rclcpp::init(argc, argv);
  try
  {
    std::vector<std::string> user_args = rclcpp::remove_ros_arguments(argc, argv);
    Options opt = parse_options(user_args);
    if (opt.show_help)
    {
      usage(std::cout);
      rclcpp::shutdown();
      return 0;
    }

    std::srand(opt.seed);

    auto node = rclcpp::Node::make_shared("scan_planner_node");
    auto vis = std::make_shared<scan_planner::PlanningVisualization>(node.get());
    scan_planner::SCANPlannerManager manager;
    manager.initPlanModules(node.get(), vis);

    std::cout << std::fixed << std::setprecision(9);
    std::cout << "INPUT start=" << vec_to_string(opt.start)
              << " start_vel=" << vec_to_string(opt.start_vel)
              << " start_acc=" << vec_to_string(opt.start_acc)
              << " target=" << vec_to_string(opt.target)
              << " target_vel=" << vec_to_string(opt.target_vel)
              << " poly_init=" << (opt.poly_init ? "true" : "false")
              << " random_poly=" << (opt.random_poly ? "true" : "false")
              << " seed=" << opt.seed
              << "\n";
    std::cout << "MAP_CONDITION dynamics_only_empty_grid_no_clouds=true note=GridMap_initialized_from_params_no_point_cloud_fed\n";
    print_params(manager.pp_);
    std::cout << "NATIVE_FIRST_CALL_NOTE fresh_process_flag_first_call_forces_polynomial=true"
              << " requested_poly_init=" << (opt.poly_init ? "true" : "false") << "\n";
    std::srand(opt.seed);
    print_poly_init_diagnostics(mirror_first_call_poly_init(opt, manager.pp_));

    // Reset the seed so optional random-poly diagnostics do not perturb native reboundReplan.
    std::srand(opt.seed);
    const bool ok = manager.reboundReplan(
      opt.start, opt.start_vel, opt.start_acc, opt.target, opt.target_vel, opt.poly_init, opt.random_poly);

    std::cout << "REBOUND_REPLAN_RESULT success=" << (ok ? "true" : "false") << "\n";
    if (ok)
    {
      print_success_diagnostics(manager.local_data_, opt.samples);
      rclcpp::shutdown();
      return 0;
    }
    rclcpp::shutdown();
    return 2;
  }
  catch (const std::exception &e)
  {
    std::cerr << "REBOUND_REPLAN_REPRO_ERROR " << e.what() << "\n";
    usage(std::cerr);
    rclcpp::shutdown();
    return 64;
  }
}
