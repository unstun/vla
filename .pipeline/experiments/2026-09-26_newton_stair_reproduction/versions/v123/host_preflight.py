"""Check original runtime/input identity on Linux without advancing physics."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import os
import platform
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
TASK = ROOT.parent
os.environ['WARP_CACHE_PATH'] = str(TASK/'cache/preflight-warp')
sys.path[:0] = [str(HERE), str(BASE/'versions/v40/physics'), str(BASE/'scripts'),
                str(BASE/'runtime_sources/bridge'), str(TASK/'host_python')]
import newton
import warp
import numpy
import onnxruntime
import zmq
from scene_assets import verify_inputs
from robot_scene_v40 import StairRobot
from lite3_newton_v40 import verify_inputs as verify_policy
from factory_navigation_startup import FactoryProcess
verify_inputs()
verify_policy()
identity = json.loads((BASE/'setup/runtime_sources.json').read_text())
for row in identity['records']:
    assert hashlib.sha256((BASE/row['path']).read_bytes()).hexdigest() == row['sha256'], row['path']
receipt = {'passed': True, 'platform': platform.platform(), 'python': sys.version,
           'executable': sys.executable, 'physics_advanced': False,
           'packages': {name: importlib.metadata.version(name) for name in
                        ('newton', 'warp-lang', 'mujoco', 'mujoco-warp', 'numpy', 'onnxruntime', 'pyzmq')},
           'source_sync_sha256': hashlib.sha256((HERE/'sync_manifest.json').read_bytes()).hexdigest(),
           'runtime_sync_sha256': hashlib.sha256((HERE/'runtime_sync_manifest.json').read_bytes()).hexdigest()}
(TASK/'results/host_preflight.json').write_text(json.dumps(receipt, indent=2)+'\n')
print(json.dumps(receipt))
