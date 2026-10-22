#pragma once

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <geometry_msgs/msg/twist.hpp>

namespace scan_nav2_controller
{
// One output history, independent of spline timestamps. Exact target capture
// avoids an exponential tail that would prevent the locomotion stand latch.
class CommandSlew
{
public:
  double linear_acceleration{1.0}, linear_deceleration{2.0};
  double angular_acceleration{2.0}, angular_deceleration{3.0};

  void reset() { command_={}; initialized_=false; }
  geometry_msgs::msg::Twist update(const geometry_msgs::msg::Twist &target, int64_t now)
  {
    if (!initialized_) { stamp_=now; initialized_=true; return command_; }
    const double dt=(now-stamp_)*1e-9;
    stamp_=now;
    if (dt<0.0 || dt>0.2) { command_={}; return command_; }
    command_.linear.x=axis(command_.linear.x,target.linear.x,dt,linear_acceleration,linear_deceleration);
    command_.linear.y=axis(command_.linear.y,target.linear.y,dt,linear_acceleration,linear_deceleration);
    command_.angular.z=axis(command_.angular.z,target.angular.z,dt,angular_acceleration,angular_deceleration);
    return command_;
  }
  static double axis(double current,double target,double dt,double acceleration,double deceleration)
  {
    if (current*target<0.0) {
      const double braking=std::abs(current)/deceleration;
      if (dt<=braking) return approach(current,0.0,deceleration*dt);
      return approach(0.0,target,acceleration*(dt-braking));
    }
    const double rate=std::abs(target)>std::abs(current) ? acceleration : deceleration;
    return approach(current,target,rate*dt);
  }
private:
  static double approach(double current,double target,double step)
  {
    return current+std::clamp(target-current,-step,step);
  }
  geometry_msgs::msg::Twist command_;
  int64_t stamp_{0};
  bool initialized_{false};
};
}  // namespace scan_nav2_controller
