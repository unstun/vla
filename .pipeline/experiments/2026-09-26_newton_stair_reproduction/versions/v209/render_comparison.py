"""Render completed short physics probes, without advancing their physics."""
import argparse
import bisect
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import zipfile

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
TASK = Path('/data/sun/vla_mppi_20261009')
RAW = TASK / 'stance_v208'
FPS = 30
CASES = ('zero_boundary', 'quiet_blocked')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def prepare(out):
    manifest = json.loads((HERE / 'manifest.json').read_text())
    for rel, expected in manifest['files'].items():
        assert sha(ROOT / rel) == expected, rel
    for rel, expected in json.loads((HERE.parent / 'v208/manifest.json').read_text())['source_files'].items():
        assert sha(HERE.parent / 'v208' / rel) == expected, rel
    inputs = {}
    for case in CASES:
        for variant in ('old', 'candidate'):
            folder = RAW / f'{variant}_{case}_01'
            for path in sorted(folder.iterdir()):
                if path.is_file():
                    inputs[str(path.relative_to(RAW))] = sha(path)
        assert sha(RAW / f'old_{case}_01/initial_state.json') == sha(RAW / f'candidate_{case}_01/initial_state.json')
    archive = RAW / 'v208_completed_probes.zip'
    if not archive.exists():
        with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as handle:
            for rel in inputs:
                handle.write(RAW / rel, rel)
    with zipfile.ZipFile(archive) as handle:
        assert handle.testzip() is None
        for rel, expected in inputs.items():
            assert hashlib.sha256(handle.read(rel)).hexdigest() == expected, rel
    write(out / 'inputs.json', {'physical_root': str(RAW), 'files': inputs,
          'archive': str(archive), 'archive_sha256': sha(archive),
          'archive_members_verified': True, 'manifest_sha256': sha(HERE / 'manifest.json')})
    return inputs


def rows_for(case, variant):
    folder = RAW / f'{variant}_{case}_01'
    initial = json.loads((folder / 'initial_state.json').read_text())
    initial['elapsed_s'] = 0.0
    rows = [initial] + [json.loads(line) for line in (folder / 'telemetry.jsonl').read_text().splitlines()]
    times = [row['elapsed_s'] for row in rows]
    assert all(a < b for a, b in zip(times, times[1:]))
    return rows, times


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=False)
    inputs = prepare(out)
    os.environ['PYGLET_HEADLESS'] = '1'
    os.environ['PYOPENGL_PLATFORM'] = 'egl'
    sys.path[:0] = [str(BASE / 'versions/v51'), str(BASE / 'scripts')]
    import numpy as np
    import warp as wp
    import newton
    from PIL import Image, ImageDraw, ImageFont
    from scipy.spatial.transform import Rotation
    from robot_scene import StairRobot
    from render_episode_v51 import prepare_appearance
    from video_stream import VideoStream

    robot = StairRobot(stance_hold=False, startup_mode='policy', automatic_contact_capacity=True)
    prepare_appearance(robot, None, out)
    # No simulation or policy evaluation is permitted in a display process.
    def forbidden(*unused, **unused_kwargs):
        raise RuntimeError('Physics/policy execution is forbidden during replay')
    robot.step = forbidden
    robot.solver.step = forbidden
    start_steps, start_policy = robot.steps, robot.policy_calls
    torso_index = next(i for i, name in enumerate(robot.model.body_label) if name.rsplit('/', 1)[-1] == 'TORSO')
    viewer = newton.viewer.ViewerGL(width=640, height=440, vsync=False, headless=True)
    viewer.set_model(robot.model)
    viewer.camera.fov = 48.0
    viewer.renderer.sky_upper = viewer.renderer.sky_lower = (.9, .9, .9)
    viewer.renderer.ambient_sky = (.8, .8, .8)
    viewer.renderer.ambient_ground = (.3, .3, .3)
    viewer.renderer.spotlight_enabled = False
    font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    title = ImageFont.truetype(font_path, 27)
    normal = ImageFont.truetype(font_path, 21)
    small = ImageFont.truetype(font_path, 18)
    cases = {case: {variant: rows_for(case, variant) for variant in ('old', 'candidate')} for case in CASES}
    counts = {case: math.ceil(max(values[1][-1] for values in cases[case].values()) * FPS) + 1 for case in CASES}
    stream = None if args.preview else VideoStream(out, FPS, sum(counts.values()))
    max_position_error = 0.0
    max_orientation_error = 0.0
    success = False
    try:
        for chapter, case in enumerate(CASES, 1):
            initial = cases[case]['old'][0][0]
            base = np.array(initial['body_sensor']['position'])
            quat = initial['body_sensor']['quaternion']
            yaw = Rotation.from_quat([*quat[1:], quat[0]]).as_euler('xyz')[2]
            forward = np.array([math.cos(yaw), math.sin(yaw), 0.])
            right = np.array([math.sin(yaw), -math.cos(yaw), 0.])
            camera = base - .85 * forward + .8 * right + np.array([0., 0., .48])
            target = base + np.array([0., 0., -.12])
            indices = [75] if args.preview else range(counts[case])
            for frame_index in indices:
                frame = Image.new('RGB', (1280, 720), (17, 25, 38))
                draw = ImageDraw.Draw(frame)
                label = '1 / 2   Zero-command boundary' if chapter == 1 else '2 / 2   Already quiet, waiting for hold'
                draw.text((24, 14), label, font=title, fill='white')
                draw.text((24, 51), 'Recorded physics | 1x simulation time | two separate initialized-state tests', font=small, fill=(177, 191, 209))
                records = {}
                for column, variant in enumerate(('old', 'candidate')):
                    rows, times = cases[case][variant]
                    sample_time = min(frame_index / FPS, times[-1])
                    index = max(0, bisect.bisect_right(times, sample_time) - 1)
                    row = rows[index]
                    robot.state.joint_q.assign(np.asarray(row['joint_q'], dtype=np.float32))
                    robot.state.joint_qd.assign(np.asarray(row['joint_qd'], dtype=np.float32))
                    newton.eval_fk(robot.model, robot.state.joint_q, robot.state.joint_qd, robot.state)
                    torso = robot.state.body_q.numpy()[torso_index]
                    sensor = row['body_sensor']
                    position_error = float(np.linalg.norm(torso[:3] - np.asarray(sensor['position'])))
                    wxyz = sensor['quaternion']
                    expected_quat = np.array([*wxyz[1:], wxyz[0]])
                    orientation_error = float(min(np.linalg.norm(torso[3:] - expected_quat), np.linalg.norm(torso[3:] + expected_quat)))
                    assert position_error < 1e-4 and orientation_error < 1e-4
                    max_position_error = max(max_position_error, position_error)
                    max_orientation_error = max(max_orientation_error, orientation_error)
                    viewer.set_camera(tuple(camera), pitch=-20, yaw=0)
                    viewer.camera.look_at(tuple(target))
                    viewer.begin_frame(row['physics_time_s'])
                    viewer.log_state(robot.state)
                    viewer.end_frame()
                    frame.paste(Image.fromarray(viewer.get_frame(render_ui=False).numpy()).convert('RGB'), (column * 640, 121))
                    x = column * 640 + 24
                    color = (255, 194, 98) if variant == 'old' else (99, 228, 183)
                    draw.text((x, 88), 'V206 HOLD / OLD' if variant == 'old' else 'V208 HOLD / CANDIDATE', font=normal, fill=color)
                    mode = row['stance_mode']
                    owner = 'RL controls joints' if row['policy_owns_joints'] else 'PD controls joints'
                    draw.rectangle((column * 640, 561, column * 640 + 639, 719), fill=(17, 25, 38))
                    draw.text((x, 573), f'{mode}  |  {owner}', font=small, fill=color)
                    draw.text((x, 602), f"t = {row['elapsed_s']:.2f} s   speed = {np.linalg.norm(sensor['linear_body']):.3f} m/s", font=small, fill='white')
                    drift = np.linalg.norm(np.array(sensor['position'][:2]) - base[:2]) * 100
                    draw.text((x, 629), f"XY drift: {drift:.2f} cm   |   {row['stance_reason']}", font=small, fill=(177, 191, 209))
                    command = row['effective_command']
                    draw.text((x, 656), 'Initial recorded state' if index == 0 else f'Command: {command[0]:.2f}, {command[1]:.2f}, {command[2]:.2f}', font=small, fill=(177, 191, 209))
                    records[variant] = {'source': f'{variant}_{case}_01', 'source_index': index,
                                        'elapsed_s': row['elapsed_s'], 'sample_time_s': sample_time,
                                        'physics_time_s': row['physics_time_s'], 'stance_mode': mode}
                draw.line((640, 80, 640, 685), fill=(79, 94, 112), width=2)
                draw.text((24, 692), 'Short stop tests only; this is not a full-route result. No physics executed for this video.', font=small, fill=(150, 166, 188))
                metadata = {'chapter': chapter, 'case': case, 'records': records,
                            'camera_position': camera.tolist(), 'camera_target': target.tolist()}
                if args.preview:
                    frame.save(out / f'preview_{case}.jpg')
                else:
                    stream.add(frame, metadata)
                if frame_index % 90 == 0:
                    print(f'chapter {chapter} frame {frame_index}/{counts[case]}', flush=True)
        success = True
    finally:
        if stream:
            stream.close(success=success)
        viewer.close()
    assert robot.steps == start_steps and robot.policy_calls == start_policy == 0
    for rel, expected in inputs.items():
        assert sha(RAW / rel) == expected
    write(out / 'result.json', {'version': 'v209', 'source': 'v208 four physical probes',
          'render_only_no_physics_steps': True, 'policy_calls': 0,
          'input_hashes_unchanged': True, 'frames': 2 if args.preview else sum(counts.values()),
          'fps': FPS, 'max_fk_position_error_m': max_position_error,
          'max_fk_quaternion_error': max_orientation_error,
          'timeline': 'Causal recorded states; 1x simulation time; terminal frame held up to one frame.',
          'full_route_acceptance': False})


if __name__ == '__main__':
    main()
