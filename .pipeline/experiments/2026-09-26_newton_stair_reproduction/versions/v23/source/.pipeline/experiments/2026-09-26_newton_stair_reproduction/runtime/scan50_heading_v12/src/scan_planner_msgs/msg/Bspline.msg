int32 order
int64 traj_id
builtin_interfaces/Time start_time

float64[] knots
geometry_msgs/Point[] pos_pts

float64[] yaw_pts
float64 yaw_dt

# P2B command identity propagated from route admission to the controller.
string run_id
int64 epoch
string request_id
string goal_id
string route_id
string command_id
int64 generation
string map_epoch
int64 map_revision
