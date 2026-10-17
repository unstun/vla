"""Use the installed v232 writer with the original fixture input and default 0.35 m reference."""
from pathlib import Path
import argparse
from lite3_nav2_bridge.profile import write_profile

parser = argparse.ArgumentParser()
parser.add_argument('--component-only', action='store_true')
args = parser.parse_args()
fixtures = Path('/work/fixtures')
profiles = [('component234.yaml', None)]
if not args.component_only:
    profiles.append(('environment_candidate228.yaml', fixtures / 'building/environment225.json'))
for name, environment in profiles:
    path = fixtures / name
    assert not path.exists(), path
    write_profile(path, fixtures / 'building_planner.yaml', name != 'component234.yaml',
                  terrain_manifest=fixtures / 'building/terrain.json', environmental_manifest=environment,
                  base_frame='base' if name == 'component234.yaml' else 'base_link')
