# Source sample in the body frame. A repeated ROS timer is not a new sample.
std_msgs/Header header
uint64 simulation_time_ns
uint64 state_sequence
uint64 run_epoch_ns
uint64 command_sequence
uint8 OFF=0
uint8 RL=1
uint8 STAND_SETTLING=2
uint8 STAND_TRANSITION=3
uint8 FIXED_STAND=4
uint8 REJOIN=5
uint8 stance_mode
bool policy_owns_joints
bool navigation_ready
bool command_stale
geometry_msgs/Twist measured_velocity
# Only linear.x, linear.y and angular.z are commanded by this interface.
geometry_msgs/Twist applied_command
