"""Source-bound corner spawn with the unchanged historical final goal."""
from pathlib import Path
import hashlib
import json
import math

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
SCENARIO_SHA256='d2bd7294f45f3819c2d4155711ae3639e1ee812feed6631abf87883a4d22d5d0'


def load_corner(path=None):
    path=HERE/'corner_scenario.json' if path is None else Path(path)
    if hashlib.sha256(path.read_bytes()).hexdigest()!=SCENARIO_SHA256:
        raise ValueError('Corner scenario differs from the recorded/geometric preflight')
    scenario=json.loads(path.read_text())
    historical=json.loads((BASE/'inputs/historical_full_building.json').read_text())
    if scenario['goal_ground_xyz_m']!=historical['goal_ground_xyz_m']:
        raise ValueError('Corner test changed the historical final goal')
    xyz=scenario['spawn_ground_xyz_m'];yaw=scenario['spawn_yaw_rad']
    if len(xyz)!=3 or not all(math.isfinite(x) for x in [*xyz,yaw]):
        raise ValueError('Invalid corner spawn coordinates')
    if scenario['route_profile']!='corner_start' or scenario['frame_id']!='world':
        raise ValueError('Corner scene/profile/frame mismatch')
    return scenario
