"""Generate component fixtures only. Does not launch any ROS node or goal."""
import argparse
from pathlib import Path
from lite3_nav2_bridge.profile import write_profile

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fixtures', type=Path, required=True)
    args = parser.parse_args()
    root = args.fixtures.resolve()
    print(write_profile(root/'component.yaml',root/'building_planner.yaml',False,
                        terrain_manifest=root/'building/terrain.json',base_frame='base'))
