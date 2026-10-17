"""Construct the original Building robot and check policy/factory; integrate zero steps."""
import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

HERE = Path(__file__).resolve().parent
VERSIONS = HERE.parent
BASE = VERSIONS.parent
FACTORY = BASE.parent / '2026-09-27_lite3_factory_runtime_audit'


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--render', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == '', 'CPU-only offline smoke'
    import numpy as np
    import warp as wp
    wp.config.kernel_cache_dir = os.environ['WARP_CACHE_PATH']
    wp.set_device('cpu')
    sys.path[:0] = [str(VERSIONS / 'v40/physics'), str(BASE / 'scripts'), str(FACTORY)]
    reference = module('v234_scenario', VERSIONS / 'v196/run_local_episode.py')
    scenario = reference.building_scenario('historical_full', 1500)
    binding = json.loads((HERE / 'binding.json').read_text())
    assert scenario['spawn_ground_xyz_m'] == binding['start_ground']
    assert scenario['spawn_yaw_rad'] == binding['start_yaw']
    assert scenario['goal_ground_xyz_m'] == binding['goal_ground']
    from scene_assets import verify_inputs
    inputs = verify_inputs()
    module('v234_locomotion', VERSIONS / 'v233/newton_episode.py').activate()
    from robot_scene_v40 import StairRobot
    from lite3_newton_v40 import check_golden_policy
    golden = check_golden_policy()
    robot = StairRobot(startup_mode='factory_pd', stance_hold=True, model_device='cpu',
                       use_solver_graph=True, automatic_contact_capacity=True, scenario=scenario)
    assert robot.steps == 0 and robot.physics_time() == 0 and robot.policy_calls == 0
    assert not robot.navigation_ready
    initial = module('v234_initial', VERSIONS / 'v198/initial_frame_v142.py')
    initial.capture_zero(robot, args.output)
    # Factory initialization and one synthetic protocol call do not advance Newton.
    # No motor command is applied and the return is discarded after validating layout.
    from factory_process import FactoryProcess
    with FactoryProcess(args.output / 'factory', wall_limit=90) as factory:
        request = struct.pack('<47d552s', .002, .002, *([0.] * 45), bytes(552))
        reply = factory.step(request)
        assert len(reply) == 2200
        values = np.frombuffer(reply[:576], dtype='<f8')
        assert np.isfinite(values).all()
        reply_sha = hashlib.sha256(reply).hexdigest()
    assert robot.steps == 0 and robot.physics_time() == 0 and robot.policy_calls == 0
    rendered = None
    if args.render:
        import mujoco
        from PIL import Image
        data = mujoco.MjData(robot.solver.mj_model)
        data.qpos[:] = robot.native_array('qpos')
        data.qvel[:] = robot.native_array('qvel')
        mujoco.mj_forward(robot.solver.mj_model, data)
        with mujoco.Renderer(robot.solver.mj_model, height=128, width=128) as renderer:
            renderer.update_scene(data)
            frame = renderer.render()
        assert frame.shape == (128, 128, 3) and frame.dtype == np.uint8 and frame.std() > 0
        sys.path.insert(0, str(VERSIONS / 'v51'))
        from video_stream import VideoStream
        video = VideoStream(args.output, fps=2, expected_frames=2)
        for _ in range(2):
            video.add(Image.fromarray(frame), {'physics_steps': 0, 'purpose': 'renderer/encoder smoke'})
        video.close()
        rendered = {'passed': True, 'frames': 2, 'physics_steps': 0,
                    'video_sha256': hashlib.sha256(video.final.read_bytes()).hexdigest(),
                    'ffmpeg': subprocess.check_output(['ffmpeg', '-version'], text=True).splitlines()[0],
                    'ffprobe': subprocess.check_output(['ffprobe', '-version'], text=True).splitlines()[0]}
    assert robot.steps == 0 and robot.physics_time() == 0 and robot.policy_calls == 0
    report = dict(passed=True, physics_steps=robot.steps, policy_calls=robot.policy_calls,
                  original_start=scenario['spawn_ground_xyz_m'], original_goal=binding['goal_ground'],
                  scene_inputs=len(inputs['inputs']), golden_policy=golden, render_encoding=rendered,
                  factory_reply_sha256=reply_sha, factory_protocol_bytes=2200,
                  python=sys.version, distributions={name: importlib.metadata.version(name) for name in
                  ('newton', 'warp-lang', 'mujoco', 'mujoco-warp', 'onnxruntime', 'usd-core')})
    (args.output / 'gate.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
