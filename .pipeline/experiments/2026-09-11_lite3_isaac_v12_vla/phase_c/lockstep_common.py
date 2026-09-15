"""Shared by the Isaac lockstep server and the VLA client: episode files, termination codes, pose helpers.

Standard library only, so it imports under Isaac Sim's Python 3.11 and the VLA environment's Python 3.9 alike.
"""

import json
import math
from pathlib import Path

CONTROL_TICK_NS = 100_000_000  # upstream http_internvla_client.py control thread: time.sleep(0.1)

# STATUS_V1.termination_code. 0 means the episode is still running.
TERMINATION_CODES = {
    'running': 0,
    'client_end': 1,
    'env_done': 2,          # V12 termination or auto-reset: treated as a fall
    'nonfoot_contact': 3,   # SubstepContactMonitor latched a non-foot contact at the collision threshold
    'client_timeout': 4,
    'client_lost': 5,
    'max_sim_time': 6,
    'protocol_error': 7,
    'command_rejected': 8,
    'contact_monitor_error': 9,
    'server_error': 10,     # unexpected exception in the Isaac server; the connection is closed, never replied to
}
TERMINATION_NAMES = {code: name for name, code in TERMINATION_CODES.items()}

REQUIRED_EPISODE_KEYS = ('episode_id', 'instruction', 'max_sim_seconds', 'target_landmark', 'success_radius_m',
                         'landmarks', 'camera', 'chase_camera')


def load_episode(path):
    episode = json.loads(Path(path).read_text())
    missing = [key for key in REQUIRED_EPISODE_KEYS if key not in episode]
    if missing:
        raise ValueError('episode {} is missing {}'.format(path, missing))
    names = [landmark['name'] for landmark in episode['landmarks']]
    if len(set(names)) != len(names):
        raise ValueError('landmark names must be unique')
    if episode['target_landmark'] not in names:
        raise ValueError('target_landmark {!r} is not a landmark'.format(episode['target_landmark']))
    if not 0 < float(episode['max_sim_seconds']) <= 600:
        raise ValueError('max_sim_seconds must be in (0, 600]')
    return episode


def landmark(episode, name):
    return next(item for item in episode['landmarks'] if item['name'] == name)


def yaw_from_quaternion_xyzw(q):
    x, y, z, w = q
    return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


def horizontal_distance(a_xy, b_xy):
    return math.hypot(a_xy[0] - b_xy[0], a_xy[1] - b_xy[1])
