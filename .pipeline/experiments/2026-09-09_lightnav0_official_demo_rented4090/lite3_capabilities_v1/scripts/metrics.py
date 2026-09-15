"""Pure measurements; never imported by model or robot control code."""
import math


def displacement(start, end):
    dx, dy = end[0]-start[0], end[1]-start[1]
    c, s = math.cos(start[2]), math.sin(start[2])
    return {"forward_m": c*dx+s*dy, "lateral_m": -s*dx+c*dy,
            "net_m": math.hypot(dx, dy),
            "yaw_error_rad": math.atan2(math.sin(end[2]-start[2]), math.cos(end[2]-start[2]))}
