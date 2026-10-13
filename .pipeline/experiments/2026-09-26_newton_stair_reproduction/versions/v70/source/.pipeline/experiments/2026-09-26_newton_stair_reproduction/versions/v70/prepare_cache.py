"""Compile the existing CPU scene/raycast kernels; never step physics."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser()
p.add_argument('--root',type=Path,required=True)
args = p.parse_args()
root = args.root.resolve()
assert root.parent == Path('/private/tmp') and root.name.startswith('vla_newton_v70_')
cache = root/'runtime/warp-cache'
os.environ['WARP_CACHE_PATH'] = str(cache)
import warp as wp
wp.config.kernel_cache_dir = str(cache)
wp.init()
wp.set_device('cpu')
sys.path.insert(0,str(BASE/'scripts'))
sys.path.insert(0,str(BASE/'versions/v40/physics'))
from scene_assets import verify_inputs
from robot_scene_v40 import StairRobot
from geometric_lidar import GeometricLidar
verify_inputs()
robot = StairRobot(startup_mode='factory_pd',stance_hold=True,model_device='cpu',
    use_solver_graph=True,automatic_contact_capacity=True)
lidar = GeometricLidar(robot,None,emitter_self_exclusion=True,visible_human_only=True)
captured = robot.model.state()
captured.body_q.assign(robot.state.body_q)
lidar.scan(0,0.,override_pose=robot.body_and_sensor(),captured_state=captured)
assert robot.steps == 0
files = {str(p.relative_to(cache)):{'bytes':p.stat().st_size,
    'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    for p in cache.rglob('*') if p.is_file()}
(root/'cache_preparation.json').write_text(json.dumps({'scope':'existing CPU model/raycast kernel compilation',
    'physics_steps':0,'model_and_sensor_sources_unchanged':True,'files':files,
    'logical_bytes':sum(v['bytes'] for v in files.values())},indent=2)+'\n')
print(json.dumps({'cache':str(cache),'physics_steps':0,'files':len(files)}))
