#include <cmath>
using std::pow;
class MotionExample { public:
void CubicSpline(double init_position, double init_velocity,
                                double goal_position, double goal_velocity,
                                double run_time, double cycle_time,
                                double total_time, double &sub_goal_position,
                                double &sub_goal_position_next,
                                double &sub_goal_position_next2);
};
void MotionExample::CubicSpline(double init_position, double init_velocity,
                                double goal_position, double goal_velocity,
                                double run_time, double cycle_time,
                                double total_time, double &sub_goal_position,
                                double &sub_goal_position_next,
                                double &sub_goal_position_next2) {
  double a, b, c, d;
  d = init_position;
  c = init_velocity;
  a = (goal_velocity * total_time - 2 * goal_position + init_velocity * total_time +
       2 * init_position) /
      pow(total_time, 3);
  b = (3 * goal_position - goal_velocity * total_time - 2 * init_velocity * total_time -
       3 * init_position) /
      pow(total_time, 2);

  if (run_time > total_time)
    run_time = total_time;
  sub_goal_position = a * pow(run_time, 3) + b * pow(run_time, 2) + c * run_time + d;

  if (run_time + cycle_time > total_time)
    run_time = total_time - cycle_time;
  sub_goal_position_next = a * pow(run_time + cycle_time, 3) +
                      b * pow(run_time + cycle_time, 2) +
                      c * (run_time + cycle_time) + d;

  if (run_time + cycle_time * 2 > total_time)
    run_time = total_time - cycle_time * 2;
  sub_goal_position_next2 = a * pow(run_time + cycle_time * 2, 3) +
                       b * pow(run_time + cycle_time * 2, 2) +
                       c * (run_time + cycle_time * 2) + d;
}
extern "C" void lite3_spline(double initial, double goal, double elapsed,
                              double dt, double duration, double *out) {
  MotionExample example;
  example.CubicSpline(initial, 0., goal, 0., elapsed, dt, duration,
                      out[0], out[1], out[2]);
}
