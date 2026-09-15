"""Observation-only metric-stop measurements; never emits control commands."""

import math

INSTRUCTION = "向前直走 3 米，然后停下"
ENGLISH_INSTRUCTION = 'Go straight forward for 3 meters, then stop.'
ALLOWED_INSTRUCTIONS = (INSTRUCTION, ENGLISH_INSTRUCTION)
TARGET_METERS = 3.0
POSITION_TOLERANCE_M = 0.25
SPEED_TOLERANCE_M_S = 0.05
YAW_RATE_TOLERANCE_RAD_S = 0.10
STOP_HOLD_SECONDS = 2.0


class DistanceMeter:
    def __init__(self):
        self.origin = None
        self.previous_position = None
        self.path_length = 0.0
        self.heading = None
        self.start_time = None

    def start(self, position, quaternion, timeline_seconds, frame):
        self.origin = list(position)
        self.previous_position = list(position)
        w, x, y, z = quaternion
        yaw = math.atan2(2 * (w*z + x*y), 1 - 2 * (y*y + z*z))
        self.heading = [math.cos(yaw), math.sin(yaw)]
        self.start_time = float(timeline_seconds)
        self.start_frame = int(frame)
        self.path_length = 0.0

    def sample(self, position, velocity, yaw_speed, desired, applied,
               timeline_seconds, frame, normal_control):
        if self.origin is None:
            return None
        dx, dy = position[0] - self.origin[0], position[1] - self.origin[1]
        forward = dx * self.heading[0] + dy * self.heading[1]
        lateral = -dx * self.heading[1] + dy * self.heading[0]
        self.path_length += math.hypot(position[0] - self.previous_position[0],
                                       position[1] - self.previous_position[1])
        self.previous_position = list(position)
        speed = math.hypot(velocity[0], velocity[1])
        near = abs(forward - TARGET_METERS) <= POSITION_TOLERANCE_M and abs(lateral) <= POSITION_TOLERANCE_M
        stationary = speed < SPEED_TOLERANCE_M_S and abs(yaw_speed) < YAW_RATE_TOLERANCE_RAD_S
        requests_stop = (abs(desired[0]) < SPEED_TOLERANCE_M_S
                         and abs(desired[1]) < YAW_RATE_TOLERANCE_RAD_S
                         and abs(applied[0]) < SPEED_TOLERANCE_M_S
                         and abs(applied[1]) < YAW_RATE_TOLERANCE_RAD_S)
        return {
            'origin': self.origin, 'initial_heading_xy': self.heading,
            'instruction_start_frame': self.start_frame,
            'instruction_start_timeline_seconds': self.start_time,
            'timeline_seconds': float(timeline_seconds),
            'elapsed_timeline_seconds': float(timeline_seconds) - self.start_time,
            'elapsed_frame_derived_seconds': (int(frame) - self.start_frame) / 30.0,
            'target_forward_m': TARGET_METERS, 'forward_m': forward, 'lateral_m': lateral,
            'net_planar_displacement_m': math.hypot(dx, dy),
            'sampled_path_length_m': self.path_length,
            'target_error_m': math.hypot(forward - TARGET_METERS, lateral),
            'actual_planar_speed_m_s': speed, 'actual_yaw_rate_rad_s': float(yaw_speed),
            'desired_v_m_s': float(desired[0]), 'desired_w_rad_s': float(desired[1]),
            'applied_v_m_s': float(applied[0]), 'applied_w_rad_s': float(applied[1]),
            'normal_control': bool(normal_control), 'near_target': bool(near),
            'stationary': bool(stationary), 'requests_stop': bool(requests_stop),
            'qualifying_stop_sample': bool(near and stationary and requests_stop and normal_control),
        }


def sustained_stop_windows(samples):
    """Find two-second timeline intervals; reject reset clocks and sampling gaps."""
    windows = []
    start = None
    previous = None
    for sample in samples:
        time = sample['timeline_seconds']
        if previous is not None and (time <= previous or time - previous > 0.5):
            start = None
        if sample['qualifying_stop_sample']:
            if start is None:
                start = time
            if time - start >= STOP_HOLD_SECONDS:
                if windows and windows[-1]['start_timeline_seconds'] == start:
                    windows[-1]['end_timeline_seconds'] = time
                else:
                    windows.append({'start_timeline_seconds': start,
                                    'end_timeline_seconds': time})
        else:
            start = None
        previous = time
    return windows
