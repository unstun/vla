from pathlib import Path
import json
import yaml
from lite3_nav2_bridge.profile import write_profile
from lite3_nav2_bridge.terrain_bundle import TerrainBundle
work=Path('/work');terrain=work/'fixtures/building/terrain.json';profile=work/'fixtures/environment_candidate228.yaml'
if not profile.exists():
    write_profile(profile,'/task/stair_collision_replay_20261016/input/planner.yaml',True,
        terrain_manifest=terrain,environmental_manifest=work/'fixtures/building/environment225.json')
parameters=TerrainBundle(terrain).native_parameters()
native=yaml.safe_load(profile.with_suffix('.scan.yaml').read_text())['scan_planner_node']['ros__parameters']
assert all(native[k]==v for k,v in parameters.items())
print(json.dumps({'canonical_lattice':{k:v for k,v in parameters.items() if 'support_lattice' in k},'physics_steps':0},indent=2))
