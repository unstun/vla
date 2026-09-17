// Derived from scan_replan_diagnosis/native_repro/scan_replan_native_repro/src/rebound_replan_repro.cpp
// (sha256 9feceb1cd8607248ab7dc4adf991c8801dd76654eb0dabe1ff828c5ae78ff097). The original options and
// output lines are kept unchanged; the suite adds occupied boxes, follow-up replans with an exact
// simulated clock, and one machine-readable SUITE_* record per planner call.
#include <plan_manage/planner_manager.h>
#include <traj_utils/polynomial_traj.h>

#include <Eigen/Eigen>
#include <rcl/time.h>
#include <rclcpp/rclcpp.hpp>

#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#ifndef SCAN_SUITE_MANAGER_CPP
#define SCAN_SUITE_MANAGER_CPP "unknown"
#endif
#ifndef SCAN_SUITE_MANAGER_SHA256
#define SCAN_SUITE_MANAGER_SHA256 "unknown"
#endif

namespace
{
// Follow-up runs start the simulated ROS clock here, so no stored trajectory has a zero stamp.
constexpr std::int64_t kFollowUpBaseClockNs = 100LL * 1000000000LL;
// scan_replan_fsm.cpp checkCollisionCallback samples the local trajectory every 0.01 s.
constexpr double kCollisionStepS = 0.01;
// Path dump spacing for the top-down report panel.
constexpr double kPathDumpStepS = 0.05;
// instrument_manager.py diagnosticSpline samples 1001 uniform points.
constexpr int kAccelerationSampleIntervals = 1000;

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
  std::string occupied_boxes_file;
  std::vector<double> follow_up_offsets;
  bool dump_samples{false};
  bool print_samples{true};
};

std::string vec_to_string(const Eigen::Vector3d &v)
{
  std::ostringstream os;
  os << std::fixed << std::setprecision(9) << v.x() << "," << v.y() << "," << v.z();
  return os.str();
}

std::string vec_full(const Eigen::Vector3d &v)
{
  char buffer[128];
  std::snprintf(buffer, sizeof(buffer), "%.17g,%.17g,%.17g", v.x(), v.y(), v.z());
  return std::string(buffer);
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

std::vector<double> parse_offsets(const std::string &text)
{
  std::vector<double> offsets;
  std::string item;
  std::istringstream is(text);
  while (std::getline(is, item, ','))
  {
    size_t parsed = 0;
    double value = 0.0;
    try
    {
      value = std::stod(item, &parsed);
    }
    catch (const std::exception &)
    {
      throw std::runtime_error("Invalid --follow-up-offsets entry: " + item);
    }
    if (item.empty() || parsed != item.size() || !std::isfinite(value) || value <= 0.0 || value > 60.0)
      throw std::runtime_error("Invalid --follow-up-offsets entry: " + item + " (expected 0 < s <= 60)");
    if (!offsets.empty() && value <= offsets.back())
      throw std::runtime_error("--follow-up-offsets must be strictly increasing: " + text);
    offsets.push_back(value);
  }
  if (offsets.empty() || offsets.size() > 16 || (!text.empty() && text.back() == ','))
    throw std::runtime_error("Invalid --follow-up-offsets: " + text + " (expected 1..16 comma-separated seconds)");
  return offsets;
}

void usage(std::ostream &os)
{
  os << "Usage: rebound_replan_suite [options] --ros-args --params-file <native_scan.yaml>\n"
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
     << "  --occupied-boxes FILE  JSON axis-aligned boxes marked with GridMap::setOccupied before planning\n"
     << "  --follow-up-offsets L  comma list of increasing seconds since the first plan; at each one the\n"
     << "                         newest accepted trajectory is sampled as the next start and replanned\n"
     << "                         in the same manager (FSM chain: previous, polynomial, random polynomial)\n"
     << "  --dump-samples BOOL    print SUITE_PATH positions of accepted trajectories every 0.05 s (default false)\n"
     << "  --print-samples BOOL   print the legacy SAMPLE lines of the first plan (default true)\n"
     << "  --help                 print this help\n"
     << "\n"
     << "This executable initializes the real SCAN GridMap/BsplineOptimizer/PlanningVisualization,\n"
     << "but does not feed a cloud. Without --occupied-boxes the map condition is dynamics-only\n"
     << "empty-grid isolation.\n";
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
    else if (flag == "--occupied-boxes")
    {
      opt.occupied_boxes_file = need_value(flag);
      if (opt.occupied_boxes_file.empty())
        throw std::runtime_error("Empty --occupied-boxes path");
    }
    else if (flag == "--follow-up-offsets")
    {
      opt.follow_up_offsets = parse_offsets(need_value(flag));
    }
    else if (flag == "--dump-samples")
    {
      opt.dump_samples = parse_bool(need_value(flag), flag);
    }
    else if (flag == "--print-samples")
    {
      opt.print_samples = parse_bool(need_value(flag), flag);
    }
    else
    {
      throw std::runtime_error("Unknown option: " + flag);
    }
  }
  return opt;
}

// ---------------------------------------------------------------------------------------------
// Minimal JSON reader for the occupied-box file (objects, arrays, strings, numbers, literals).

struct JsonValue
{
  enum class Type
  {
    Null,
    Bool,
    Number,
    String,
    Array,
    Object
  };
  Type type{Type::Null};
  bool boolean{false};
  double number{0.0};
  std::string text;
  std::vector<std::string> keys;  // object keys, parallel to items
  std::vector<JsonValue> items;   // array items or object values

  const JsonValue *find(const std::string &key) const
  {
    if (type != Type::Object)
      return nullptr;
    for (size_t i = 0; i < keys.size(); ++i)
    {
      if (keys[i] == key)
        return &items[i];
    }
    return nullptr;
  }
};

class JsonParser
{
public:
  explicit JsonParser(const std::string &text) : s_(text) {}

  JsonValue parse()
  {
    JsonValue value = parse_value(0);
    skip_space();
    if (i_ != s_.size())
      fail("trailing characters");
    return value;
  }

private:
  const std::string &s_;
  size_t i_{0};

  [[noreturn]] void fail(const std::string &message) const
  {
    throw std::runtime_error("occupied-boxes JSON: " + message + " at offset " + std::to_string(i_));
  }

  void skip_space()
  {
    while (i_ < s_.size() && std::isspace(static_cast<unsigned char>(s_[i_])))
      ++i_;
  }

  bool consume(char c)
  {
    skip_space();
    if (i_ < s_.size() && s_[i_] == c)
    {
      ++i_;
      return true;
    }
    return false;
  }

  void expect(char c)
  {
    if (!consume(c))
      fail(std::string("expected '") + c + "'");
  }

  bool literal(const char *word)
  {
    const size_t n = std::strlen(word);
    if (s_.compare(i_, n, word) == 0)
    {
      i_ += n;
      return true;
    }
    return false;
  }

  std::string parse_string()
  {
    skip_space();
    if (i_ >= s_.size() || s_[i_] != '"')
      fail("expected string");
    ++i_;
    std::string out;
    while (i_ < s_.size())
    {
      const char c = s_[i_++];
      if (c == '"')
        return out;
      if (c != '\\')
      {
        out.push_back(c);
        continue;
      }
      if (i_ >= s_.size())
        break;
      const char e = s_[i_++];
      switch (e)
      {
      case '"':
      case '\\':
      case '/':
        out.push_back(e);
        break;
      case 'b':
        out.push_back('\b');
        break;
      case 'f':
        out.push_back('\f');
        break;
      case 'n':
        out.push_back('\n');
        break;
      case 'r':
        out.push_back('\r');
        break;
      case 't':
        out.push_back('\t');
        break;
      case 'u':
        // Box ids are ASCII; keep other code points escaped verbatim.
        if (i_ + 4 > s_.size())
          fail("short unicode escape");
        out += "\\u" + s_.substr(i_, 4);
        i_ += 4;
        break;
      default:
        fail("invalid escape");
      }
    }
    fail("unterminated string");
  }

  double parse_number()
  {
    const size_t start = i_;
    while (i_ < s_.size())
    {
      const char c = s_[i_];
      if (std::isdigit(static_cast<unsigned char>(c)) || c == '-' || c == '+' || c == '.' || c == 'e' || c == 'E')
        ++i_;
      else
        break;
    }
    if (start == i_)
      fail("unexpected character");
    const std::string token = s_.substr(start, i_ - start);
    size_t parsed = 0;
    double value = 0.0;
    try
    {
      value = std::stod(token, &parsed);
    }
    catch (const std::exception &)
    {
      fail("invalid number " + token);
    }
    if (parsed != token.size() || !std::isfinite(value))
      fail("invalid number " + token);
    return value;
  }

  JsonValue parse_value(int depth)
  {
    if (depth > 32)
      fail("nesting too deep");
    skip_space();
    if (i_ >= s_.size())
      fail("unexpected end");
    JsonValue value;
    const char c = s_[i_];
    if (c == '{')
    {
      ++i_;
      value.type = JsonValue::Type::Object;
      if (consume('}'))
        return value;
      do
      {
        value.keys.push_back(parse_string());
        expect(':');
        value.items.push_back(parse_value(depth + 1));
      } while (consume(','));
      expect('}');
    }
    else if (c == '[')
    {
      ++i_;
      value.type = JsonValue::Type::Array;
      if (consume(']'))
        return value;
      do
      {
        value.items.push_back(parse_value(depth + 1));
      } while (consume(','));
      expect(']');
    }
    else if (c == '"')
    {
      value.type = JsonValue::Type::String;
      value.text = parse_string();
    }
    else if (literal("true"))
    {
      value.type = JsonValue::Type::Bool;
      value.boolean = true;
    }
    else if (literal("false"))
    {
      value.type = JsonValue::Type::Bool;
    }
    else if (literal("null"))
    {
      value.type = JsonValue::Type::Null;
    }
    else
    {
      value.type = JsonValue::Type::Number;
      value.number = parse_number();
    }
    return value;
  }
};

struct OccupiedBox
{
  std::string id;
  Eigen::Vector3d min{0.0, 0.0, 0.0};
  Eigen::Vector3d max{0.0, 0.0, 0.0};
};

Eigen::Vector3d json_vec3(const JsonValue *value, const std::string &what)
{
  if (value == nullptr || value->type != JsonValue::Type::Array || value->items.size() != 3)
    throw std::runtime_error("occupied-boxes JSON: " + what + " must be a 3-number array");
  Eigen::Vector3d out;
  for (int k = 0; k < 3; ++k)
  {
    const JsonValue &item = value->items[static_cast<size_t>(k)];
    if (item.type != JsonValue::Type::Number || !std::isfinite(item.number))
      throw std::runtime_error("occupied-boxes JSON: " + what + " has a non-number component");
    out(k) = item.number;
  }
  return out;
}

std::vector<OccupiedBox> load_boxes(const std::string &path)
{
  std::ifstream in(path, std::ios::binary);
  if (!in)
    throw std::runtime_error("Cannot open --occupied-boxes file: " + path);
  std::stringstream buffer;
  buffer << in.rdbuf();
  const std::string text = buffer.str();
  JsonParser parser(text);
  const JsonValue root = parser.parse();
  const JsonValue *list = &root;
  if (root.type == JsonValue::Type::Object)
    list = root.find("boxes");
  if (list == nullptr || list->type != JsonValue::Type::Array || list->items.empty())
    throw std::runtime_error("occupied-boxes JSON: expected a non-empty list or an object with a 'boxes' list");
  std::vector<OccupiedBox> boxes;
  for (size_t i = 0; i < list->items.size(); ++i)
  {
    const JsonValue &item = list->items[i];
    if (item.type != JsonValue::Type::Object)
      throw std::runtime_error("occupied-boxes JSON: box " + std::to_string(i) + " is not an object");
    OccupiedBox box;
    const JsonValue *id = item.find("id");
    box.id = (id != nullptr && id->type == JsonValue::Type::String) ? id->text : ("box_" + std::to_string(i));
    box.min = json_vec3(item.find("min"), "box " + std::to_string(i) + " min");
    box.max = json_vec3(item.find("max"), "box " + std::to_string(i) + " max");
    if ((box.max - box.min).minCoeff() <= 0.0)
      throw std::runtime_error("occupied-boxes JSON: box " + box.id + " requires min < max on every axis");
    boxes.push_back(box);
  }
  return boxes;
}

long mark_boxes(GridMap &map, const std::vector<OccupiedBox> &boxes)
{
  const double res = map.getResolution();
  long total = 0;
  for (size_t b = 0; b < boxes.size(); ++b)
  {
    const OccupiedBox &box = boxes[b];
    Eigen::Vector3i lo, hi;
    for (int k = 0; k < 3; ++k)
    {
      // Mark every voxel whose center lies inside the closed box.
      lo(k) = static_cast<int>(std::ceil(box.min(k) / res - 0.5));
      hi(k) = static_cast<int>(std::floor(box.max(k) / res - 0.5));
      if (hi(k) < lo(k))
        throw std::runtime_error("occupied box " + box.id + " contains no voxel center");
    }
    long marked = 0;
    for (int x = lo(0); x <= hi(0); ++x)
      for (int y = lo(1); y <= hi(1); ++y)
        for (int z = lo(2); z <= hi(2); ++z)
        {
          const Eigen::Vector3i id(x, y, z);
          Eigen::Vector3d pos;
          map.indexToPos(id, pos);
          if (!map.isInMap(pos))
            throw std::runtime_error("occupied box " + box.id + " has a voxel outside the map at " + vec_full(pos));
          map.setOccupied(pos);
          if (map.getOccupancy(pos) != 1)
            throw std::runtime_error("occupied box " + box.id + " voxel not occupied after setOccupied at " + vec_full(pos));
          ++marked;
        }
    const Eigen::Vector3d center = 0.5 * (box.min + box.max);
    std::printf("MAP_BOX index=%zu id=%s min=%s max=%s voxel_index_min=%d,%d,%d voxel_index_max=%d,%d,%d "
                "marked_voxels=%ld center_inflated=%d\n",
                b, box.id.c_str(), vec_full(box.min).c_str(), vec_full(box.max).c_str(),
                lo(0), lo(1), lo(2), hi(0), hi(1), hi(2), marked, map.getInflateOccupancy(center, 0.0));
    total += marked;
  }
  return total;
}

// ---------------------------------------------------------------------------------------------
// Simulated ROS clock control. use_sim_time=true enables the ROS time override on the node clock;
// nothing spins the node, so only these explicit calls move node->now().

bool ros_time_override_enabled(rclcpp::Node &node)
{
  rcl_clock_t *handle = node.get_clock()->get_clock_handle();
  bool enabled = false;
  if (rcl_is_enabled_ros_time_override(handle, &enabled) != RCL_RET_OK)
    throw std::runtime_error("rcl_is_enabled_ros_time_override failed; node clock is not RCL_ROS_TIME");
  return enabled;
}

void set_sim_clock(rclcpp::Node &node, std::int64_t nanoseconds)
{
  if (!ros_time_override_enabled(node))
    throw std::runtime_error("ROS time override is disabled; follow-up timing requires use_sim_time=true");
  rcl_clock_t *handle = node.get_clock()->get_clock_handle();
  if (rcl_set_ros_time_override(handle, nanoseconds) != RCL_RET_OK)
    throw std::runtime_error("rcl_set_ros_time_override failed");
  const std::int64_t now_ns = node.now().nanoseconds();
  if (now_ns != nanoseconds)
    throw std::runtime_error("node clock did not take the override: " + std::to_string(now_ns) +
                             " != " + std::to_string(nanoseconds));
}

std::string use_sim_time_text(rclcpp::Node &node)
{
  try
  {
    return node.get_parameter("use_sim_time").as_bool() ? "true" : "false";
  }
  catch (const std::exception &)
  {
    return "unavailable";
  }
}

// ---------------------------------------------------------------------------------------------

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

void print_success_diagnostics(const scan_planner::LocalTrajData &data, int samples, bool print_samples)
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

    if (!print_samples)
      continue;
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

// ---------------------------------------------------------------------------------------------
// Machine-readable per-call records.

double segment_yaw(const Eigen::Vector3d &from, const Eigen::Vector3d &to, double fallback_yaw)
{
  // Mirrors SCANReplanFSM::estimateYawFromSegment; the odometry-yaw fallback becomes the route yaw.
  const Eigen::Vector2d diff(to(0) - from(0), to(1) - from(1));
  if (diff.squaredNorm() < 1e-8)
    return fallback_yaw;
  return std::atan2(diff(1), diff(0));
}

struct StartState
{
  Eigen::Vector3d pos{0.0, 0.0, 0.0};
  Eigen::Vector3d vel{0.0, 0.0, 0.0};
  Eigen::Vector3d acc{0.0, 0.0, 0.0};
};

void print_call_begin(int call, int attempt, const char *kind, bool poly_init, bool random_poly,
                      rclcpp::Node &node, double requested_offset_s, double measured_offset_s,
                      const StartState &s, const Options &opt)
{
  std::printf("SUITE_CALL_BEGIN call=%d attempt=%d kind=%s poly_init=%s random_poly=%s clock_ns=%lld "
              "requested_offset_s=%.17g measured_offset_s=%.17g start=%s start_vel=%s start_acc=%s "
              "target=%s target_vel=%s\n",
              call, attempt, kind, poly_init ? "true" : "false", random_poly ? "true" : "false",
              static_cast<long long>(node.now().nanoseconds()), requested_offset_s, measured_offset_s,
              vec_full(s.pos).c_str(), vec_full(s.vel).c_str(), vec_full(s.acc).c_str(),
              vec_full(opt.target).c_str(), vec_full(opt.target_vel).c_str());
  std::fflush(stdout);
}

void print_call_end(int call, int attempt, const char *kind, bool success, scan_planner::SCANPlannerManager &manager,
                    rclcpp::Node &node, const StartState &s, const Options &opt, double fallback_yaw)
{
  std::fflush(stdout);
  std::fflush(stderr);
  if (!success)
  {
    std::printf("SUITE_CALL_END call=%d attempt=%d kind=%s success=false clock_ns=%lld\n",
                call, attempt, kind, static_cast<long long>(node.now().nanoseconds()));
    std::fflush(stdout);
    return;
  }

  const scan_planner::LocalTrajData &data = manager.local_data_;
  scan_planner::UniformBspline traj = data.position_traj_;
  scan_planner::UniformBspline vel = traj.getDerivative();
  scan_planner::UniformBspline acc = vel.getDerivative();
  const double duration = traj.getTimeSum();

  // Same sampling as the diagnosis diagnosticSpline (1001 uniform samples of the returned spline).
  double max_acc = 0.0;
  double max_acc_t = 0.0;
  double max_vel = 0.0;
  for (int i = 0; i <= kAccelerationSampleIntervals; ++i)
  {
    const double t = duration * static_cast<double>(i) / static_cast<double>(kAccelerationSampleIntervals);
    const double value = acc.evaluateDeBoorT(t).norm();
    if (value > max_acc)
    {
      max_acc = value;
      max_acc_t = t;
    }
    max_vel = std::max(max_vel, vel.evaluateDeBoorT(t).norm());
  }
  const Eigen::Vector3d end_pos = traj.evaluateDeBoorT(duration);
  const Eigen::Vector3d first_pos = traj.evaluateDeBoorT(0.0);
  const double end_acc = acc.evaluateDeBoorT(duration).norm();
  const double end_vel = vel.evaluateDeBoorT(duration).norm();
  const double endpoint_xy = (end_pos.head<2>() - opt.target.head<2>()).norm();
  const double endpoint_z = std::abs(end_pos.z() - opt.target.z());
  const double endpoint_xyz = (end_pos - opt.target).norm();
  const double start_offset = (first_pos - s.pos).norm();

  // Same loop as SCANReplanFSM::checkCollisionCallback from t_cur = 0 over the whole trajectory.
  GridMap &map = *manager.grid_map_;
  int collision_samples = 0;
  int occupied_samples = 0;
  int out_of_map_samples = 0;
  int checks = 0;
  double first_collision_t = -1.0;
  for (double t = 0.0; t < duration; t += kCollisionStepS)
  {
    const Eigen::Vector3d pos = traj.evaluateDeBoorT(t);
    const Eigen::Vector3d pos_next = traj.evaluateDeBoorT(std::min(t + kCollisionStepS, duration));
    const int occ = map.getInflateOccupancy(pos, segment_yaw(pos, pos_next, fallback_yaw));
    ++checks;
    if (occ == 1)
      ++occupied_samples;
    else if (occ == -1)
      ++out_of_map_samples;
    if (occ != 0)
    {
      ++collision_samples;
      if (first_collision_t < 0.0)
        first_collision_t = t;
    }
  }

  std::printf("SUITE_CALL_END call=%d attempt=%d kind=%s success=true clock_ns=%lld traj_id=%d "
              "duration=%.17g max_acc=%.17g max_acc_t=%.17g max_vel=%.17g end_acc=%.17g end_vel=%.17g "
              "end=%s endpoint_xy_m=%.17g endpoint_z_m=%.17g endpoint_xyz_m=%.17g start_offset_m=%.17g "
              "collision_samples=%d inflated_occupied_samples=%d out_of_map_samples=%d collision_checks=%d "
              "first_collision_t=%.17g\n",
              call, attempt, kind, static_cast<long long>(node.now().nanoseconds()), data.traj_id_,
              duration, max_acc, max_acc_t, max_vel, end_acc, end_vel, vec_full(end_pos).c_str(),
              endpoint_xy, endpoint_z, endpoint_xyz, start_offset, collision_samples, occupied_samples,
              out_of_map_samples, checks, first_collision_t);

  if (opt.dump_samples)
  {
    std::string points;
    const int steps = static_cast<int>(std::floor(duration / kPathDumpStepS + 1e-9));
    char buffer[96];
    for (int k = 0; k <= steps; ++k)
    {
      const Eigen::Vector3d p = traj.evaluateDeBoorT(std::min(k * kPathDumpStepS, duration));
      std::snprintf(buffer, sizeof(buffer), "%s%.9f,%.9f,%.9f", k == 0 ? "" : ";", p.x(), p.y(), p.z());
      points += buffer;
    }
    if (steps * kPathDumpStepS < duration - 1e-9)
    {
      std::snprintf(buffer, sizeof(buffer), ";%.9f,%.9f,%.9f", end_pos.x(), end_pos.y(), end_pos.z());
      points += buffer;
    }
    std::printf("SUITE_PATH call=%d attempt=%d dt=%.17g duration=%.17g points=%s\n",
                call, attempt, kPathDumpStepS, duration, points.c_str());
  }
  std::fflush(stdout);
}
} // namespace

int main(int argc, char **argv)
{
  // Line buffering keeps stdout records ordered with the planner's stderr warnings in one log.
  std::setvbuf(stdout, nullptr, _IOLBF, BUFSIZ);
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
    std::string offsets_text;
    for (size_t k = 0; k < opt.follow_up_offsets.size(); ++k)
    {
      char buffer[40];
      std::snprintf(buffer, sizeof(buffer), "%s%.17g", k == 0 ? "" : ",", opt.follow_up_offsets[k]);
      offsets_text += buffer;
    }
    std::printf("SUITE_INPUT start=%s start_vel=%s start_acc=%s target=%s target_vel=%s poly_init=%s "
                "random_poly=%s seed=%u occupied_boxes=%s follow_up_offsets=%s dump_samples=%s print_samples=%s\n",
                vec_full(opt.start).c_str(), vec_full(opt.start_vel).c_str(), vec_full(opt.start_acc).c_str(),
                vec_full(opt.target).c_str(), vec_full(opt.target_vel).c_str(), opt.poly_init ? "true" : "false",
                opt.random_poly ? "true" : "false", opt.seed,
                opt.occupied_boxes_file.empty() ? "none" : opt.occupied_boxes_file.c_str(),
                offsets_text.empty() ? "none" : offsets_text.c_str(), opt.dump_samples ? "true" : "false",
                opt.print_samples ? "true" : "false");
    std::printf("SUITE_IDENTITY manager_cpp=%s manager_sha256=%s\n", SCAN_SUITE_MANAGER_CPP, SCAN_SUITE_MANAGER_SHA256);

    GridMap &map = *manager.grid_map_;
    if (opt.occupied_boxes_file.empty())
    {
      std::cout << "MAP_CONDITION dynamics_only_empty_grid_no_clouds=true note=GridMap_initialized_from_params_no_point_cloud_fed\n";
    }
    else
    {
      const std::vector<OccupiedBox> boxes = load_boxes(opt.occupied_boxes_file);
      const long voxels = mark_boxes(map, boxes);
      Eigen::Vector3d origin, size;
      map.getRegion(origin, size);
      std::printf("MAP_CONDITION boxes=%zu occupied_voxels=%ld boxes_file=%s map_origin=%s map_size=%s "
                  "resolution=%.17g note=GridMap_initialized_from_params_boxes_marked_with_setOccupied_no_point_cloud_fed\n",
                  boxes.size(), voxels, opt.occupied_boxes_file.c_str(), vec_full(origin).c_str(),
                  vec_full(size).c_str(), map.getResolution());
    }
    print_params(manager.pp_);
    std::cout << "NATIVE_FIRST_CALL_NOTE fresh_process_flag_first_call_forces_polynomial=true"
              << " requested_poly_init=" << (opt.poly_init ? "true" : "false") << "\n";
    std::srand(opt.seed);
    print_poly_init_diagnostics(mirror_first_call_poly_init(opt, manager.pp_));

    const bool follow_ups = !opt.follow_up_offsets.empty();
    if (follow_ups)
    {
      set_sim_clock(*node, kFollowUpBaseClockNs);
      std::printf("CLOCK_CONDITION mode=ros_time_override use_sim_time=%s override_enabled=true base_ns=%lld\n",
                  use_sim_time_text(*node).c_str(), static_cast<long long>(kFollowUpBaseClockNs));
    }
    else
    {
      std::printf("CLOCK_CONDITION mode=unmodified use_sim_time=%s override_enabled=%s now_ns=%lld\n",
                  use_sim_time_text(*node).c_str(), ros_time_override_enabled(*node) ? "true" : "false",
                  static_cast<long long>(node->now().nanoseconds()));
    }
    const double route_yaw = std::atan2(opt.target.y() - opt.start.y(), opt.target.x() - opt.start.x());

    StartState first;
    first.pos = opt.start;
    first.vel = opt.start_vel;
    first.acc = opt.start_acc;
    std::fflush(stdout);

    // Reset the seed so optional random-poly diagnostics do not perturb native reboundReplan.
    std::srand(opt.seed);
    print_call_begin(0, 0, "initial", opt.poly_init, opt.random_poly, *node, 0.0, 0.0, first, opt);
    const bool ok = manager.reboundReplan(
      opt.start, opt.start_vel, opt.start_acc, opt.target, opt.target_vel, opt.poly_init, opt.random_poly);
    print_call_end(0, 0, "initial", ok, manager, *node, first, opt, route_yaw);

    std::cout << "REBOUND_REPLAN_RESULT success=" << (ok ? "true" : "false") << "\n";
    if (ok)
    {
      print_success_diagnostics(manager.local_data_, opt.samples, opt.print_samples);
    }
    if (!ok || !follow_ups)
    {
      std::printf("SUITE_SEQUENCE_END steps_requested=%zu steps_accepted=0 completed=%s stop_reason=%s\n",
                  opt.follow_up_offsets.size(), (ok && !follow_ups) ? "true" : "false",
                  ok ? "no_follow_up_requested" : "initial_rejected");
      std::fflush(stdout);
      rclcpp::shutdown();
      return ok ? 0 : 2;
    }

    // FSM REFERENCE_PATH replan chain (scan_replan_fsm.cpp planFromCurrentTraj).
    const bool chain[3][2] = {{false, false}, {true, false}, {true, true}};
    size_t steps_accepted = 0;
    std::string stop_reason = "completed";
    double previous_offset = 0.0;
    for (size_t k = 0; k < opt.follow_up_offsets.size(); ++k)
    {
      const int call = static_cast<int>(k) + 1;
      const double offset = opt.follow_up_offsets[k];
      const std::int64_t clock_ns = kFollowUpBaseClockNs + static_cast<std::int64_t>(std::llround(offset * 1e9));
      set_sim_clock(*node, clock_ns);
      scan_planner::LocalTrajData &info = manager.local_data_;
      const double raw_t_cur = (node->now() - info.start_time_).seconds();
      const double requested = offset - previous_offset;
      if (raw_t_cur < 0.0 || raw_t_cur > info.duration_ - 1e-3)
      {
        std::printf("SUITE_FOLLOW_UP_SKIPPED call=%d requested_offset_s=%.17g measured_offset_s=%.17g "
                    "trajectory_duration=%.17g reason=offset_beyond_trajectory\n",
                    call, requested, raw_t_cur, info.duration_);
        stop_reason = "offset_beyond_trajectory";
        break;
      }
      const double t_cur = std::min(std::max(raw_t_cur, 0.0), info.duration_);
      StartState state;
      state.pos = info.position_traj_.evaluateDeBoorT(t_cur);
      state.vel = info.velocity_traj_.evaluateDeBoorT(t_cur);
      state.acc = info.acceleration_traj_.evaluateDeBoorT(t_cur);

      bool step_ok = false;
      for (int attempt = 0; attempt < 3 && !step_ok; ++attempt)
      {
        print_call_begin(call, attempt, "follow_up", chain[attempt][0], chain[attempt][1], *node, requested,
                         raw_t_cur, state, opt);
        step_ok = manager.reboundReplan(state.pos, state.vel, state.acc, opt.target, opt.target_vel,
                                        chain[attempt][0], chain[attempt][1]);
        print_call_end(call, attempt, "follow_up", step_ok, manager, *node, state, opt, route_yaw);
      }
      if (!step_ok)
      {
        stop_reason = "follow_up_rejected";
        break;
      }
      ++steps_accepted;
      previous_offset = offset;
    }
    const bool completed = steps_accepted == opt.follow_up_offsets.size();
    std::printf("SUITE_SEQUENCE_END steps_requested=%zu steps_accepted=%zu completed=%s stop_reason=%s\n",
                opt.follow_up_offsets.size(), steps_accepted, completed ? "true" : "false", stop_reason.c_str());
    std::fflush(stdout);
    rclcpp::shutdown();
    return completed ? 0 : 2;
  }
  catch (const std::exception &e)
  {
    std::fflush(stdout);
    std::cerr << "REBOUND_REPLAN_REPRO_ERROR " << e.what() << "\n";
    usage(std::cerr);
    rclcpp::shutdown();
    return 64;
  }
}
