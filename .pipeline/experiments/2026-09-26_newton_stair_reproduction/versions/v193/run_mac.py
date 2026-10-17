"""Render v192_mac_full_attempt01 on Mac ARM64 Cocoa and verify all outputs."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
TASK = Path('/private/tmp/vla_stop_audit_20261012')


def main():
    subprocess.run([sys.executable, str(HERE / 'prepare_mac.py')], check=True, timeout=120)
    root = TASK / 'video_v193'
    out = root / 'runs/full01'
    out.mkdir(exist_ok=False)
    env = dict(
        os.environ,
        NEWTON_RUN_DIR=str(out),
        V193_RENDER_ROOT=str(root),
        V193_DISPLAY_CONTRACT=str(root / 'display_contract.json'),
        WARP_CACHE_PATH=str(root / 'cache'),
        OPENBLAS_NUM_THREADS='1',
        OMP_NUM_THREADS='1',
        PYOPENGL_PLATFORM='darwin',
        PYTHONDONTWRITEBYTECODE='1',
        PYTHONPATH=str(TASK / 'host_python') + ':' + str(HERE) + ':' + str(BASE / 'runtime_sources/bridge'),
    )
    env.pop('PYGLET_HEADLESS', None)
    command = [sys.executable, str(HERE / 'render_capture.py')]
    (root / 'render_request.json').write_text(json.dumps({
        'command': command,
        'env': {k: env[k] for k in ('NEWTON_RUN_DIR', 'V193_RENDER_ROOT', 'V193_DISPLAY_CONTRACT',
                                    'WARP_CACHE_PATH', 'PYTHONPATH', 'PYOPENGL_PLATFORM')},
        'physics_steps_requested': 0,
    }, indent=2) + '\n')
    with (root / 'render.log').open('w') as log:
        subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=1800)
    subprocess.run([sys.executable, str(HERE / 'verify_video.py')], env=env, check=True, timeout=180)
    delivered = HERE / 'delivered'
    delivered.mkdir(exist_ok=True)
    shutil.copyfile(out / 'newton_stair_recorded.mp4', delivered / 'v192_mac_full_attempt01.mp4')
    returned = HERE / 'returned'
    returned.mkdir(exist_ok=True)
    for name in ('display_contract.json', 'render_request.json'):
        shutil.copyfile(root / name, returned / name)
    for name in ('result.json', 'video_verification.json', 'host_port_verification.json', 'delivery_verification.json', 'frames.json', 'curve_frames.json', 'heading_camera.json',
                 'executed_render_episode_host.py', 'executed_render_heading_host.py', 'appearance.json'):
        shutil.copyfile(out / name, returned / name)


if __name__ == '__main__':
    main()
