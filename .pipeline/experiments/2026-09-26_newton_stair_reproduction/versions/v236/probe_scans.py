"""Original Building ray replay and native-clock catch-up; zero physics steps."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import sys
import threading
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
PREFIX = Path('/home/ubuntu/sun/vla_v234_20261017')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--scans', type=int, default=50)
    parser.add_argument('--fixed', action='store_true')
    parser.add_argument('--flexible', action='store_true')
    args = parser.parse_args()
    assert not args.output.exists()
    import numpy as np
    import warp as wp
    wp.config.kernel_cache_dir = os.environ['WARP_CACHE_PATH']
    wp.init()
    wp.set_device('cpu')
    sys.path[:0] = [str(HERE.parent / 'v40/physics'), str(BASE / 'scripts'), str(HERE.parent / 'v198')]
    spec = importlib.util.spec_from_file_location('v236_locomotion', HERE.parent / 'v216/activate.py')
    locomotion = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(locomotion)
    locomotion.install()
    from robot_scene_v40 import StairRobot
    from lite3_newton_v40 import check_golden_policy
    from geometric_lidar import GeometricLidar
    from realtime_pacer import NativeClockPacer
    raw = PREFIX / 'trials/v235_linux_full_attempt01/runs/v235_linux_full_attempt01'
    robot = StairRobot(startup_mode='factory_pd', stance_hold=True, model_device='cpu',
        use_solver_graph=True, automatic_contact_capacity=True,
        scenario=json.loads((raw / 'inputs/stair_scenario.json').read_text()))
    recorded = json.loads((raw / 'video_states.json').read_text())[-1]
    robot.state.body_q.assign(np.asarray(recorded['body_q'], dtype=np.float32))
    robot.state.joint_q.assign(np.asarray(recorded['joint_q'], dtype=np.float32))
    captured = robot.model.state()
    captured.body_q.assign(robot.state.body_q)
    pose = json.loads((raw / 'sensor.jsonl').read_text().splitlines()[-1])['body_sensor']
    lidar = GeometricLidar(robot, None, emitter_self_exclusion=True, visible_human_only=True)
    before = robot.state.body_q.numpy().copy()
    lidar.scan(0, 0., override_pose=pose, captured_state=captured)
    def run(index, submitted):
        started = time.monotonic()
        cpu = time.thread_time()
        sched = Path(f'/proc/self/task/{threading.get_native_id()}/schedstat')
        old = list(map(int, sched.read_text().split()))
        result = lidar.scan(index, 0., override_pose=pose, captured_state=captured)
        new = list(map(int, sched.read_text().split()))
        finished = time.monotonic()
        return dict(index=index, queue_s=started-submitted, wall_s=finished-started,
            total_s=finished-submitted, thread_cpu_s=time.thread_time()-cpu,
            runnable_wait_s=(new[1]-old[1])/1e9,
            data_sha256=hashlib.sha256(result[0].tobytes()+result[1].tobytes()).hexdigest())
    original_affinity = os.sched_getaffinity(0)
    golden = check_golden_policy()
    batches = []
    with ThreadPoolExecutor(max_workers=1) as pool:
        cpu_sets = [original_affinity] * 3 if args.flexible else [{22, 23}, {20, 21, 22, 23}, {22, 23}]
        for cpus in cpu_sets:
            os.sched_setaffinity(0, cpus)
            # Existing worker threads retain affinity; set the worker itself.
            pool.submit(os.sched_setaffinity, 0, cpus).result()
            rows = [pool.submit(run, i, time.monotonic()).result(timeout=5) for i in range(args.scans)]
            batches.append(dict(cpus=sorted(cpus), rows=rows,
                maximum_s=max(r['total_s'] for r in rows),
                mean_s=sum(r['total_s'] for r in rows)/len(rows),
                over_100ms=sum(r['total_s'] > .1 for r in rows)))
            print(json.dumps({k: v for k, v in batches[-1].items() if k != 'rows'}), flush=True)
        # A recorded wall lag makes actual native .1s arrive before .1s wall.
        # No physics integration is executed by this scheduling reproduction.
        pacer = NativeClockPacer(0.)
        pacer.wall_start_s -= .2
        submitted = time.monotonic()
        future = pool.submit(run, 16, submitted)
        for i in range(1, 6):
            pacer.wait(i*.02)
        checked = time.monotonic()
        old_guard_rejects = not future.done()
        replay = future.result(timeout=5)
        early = dict(old_guard_rejects=old_guard_rejects,
            wall_at_native_next_scan_s=checked-submitted, native_period_s=.1,
            worker=replay, genuine_wall_overrun=replay['total_s'] > .1)
        if args.fixed:
            from scan_deadline import ScanDeadline
            deadline = ScanDeadline()
            pacer = NativeClockPacer(0.)
            pacer.wall_start_s -= .2
            native = 0.
            for i in range(100):
                submitted = time.monotonic()
                future = deadline.submit(pool, run, i % args.scans, submitted)
                for _ in range(5):
                    native += .02
                    pacer.wait(native)
                value = deadline.result(future)
                assert value['data_sha256'] == batches[0]['rows'][i % args.scans]['data_sha256']
            early['fixed_scans'] = len(deadline.records)
            early['fixed_rejects'] = sum(r.get('deadline_failed', False) for r in deadline.records)
            early['early_checks_resolved'] = sum(r['wall_at_check_s'] < .1 and r['waited_wall_s'] > .001 for r in deadline.records)
            early['fixed_maximum_s'] = max(r['total_s'] for r in deadline.records)
            early['fixed_records'] = deadline.records
    os.sched_setaffinity(0, original_affinity)
    assert robot.steps == 0 and np.array_equal(before, robot.state.body_q.numpy())
    for batch in batches[1:]:
        assert [r['data_sha256'] for r in batch['rows']] == [r['data_sha256'] for r in batches[0]['rows']]
    cgroup = Path('/sys/fs/cgroup') / Path('/proc/self/cgroup').read_text().strip().split('::', 1)[1].lstrip('/')
    report = dict(physics_steps=0, original_ray_data_equal_across_affinities=True,
        golden_policy=golden,
        cpu_cgroup=str(cgroup), cpu_max=(cgroup/'cpu.max').read_text().strip(),
        cpu_stat=(cgroup/'cpu.stat').read_text(),
        cpu_limit_batches=batches, catchup_reproduction=early,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    if args.flexible:
        original = json.loads((PREFIX / 'evidence/v236_scan_probe02.json').read_text())
        assert [r['data_sha256'] for r in batches[0]['rows']] == [r['data_sha256'] for r in original['cpu_limit_batches'][0]['rows']]
        report['original_host_ray_bytes_equal'] = True
        assert report['cpu_max'] == '400000 100000'
        assert all(b['over_100ms'] == 0 for b in batches)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(early), flush=True)
    assert old_guard_rejects, 'The original early-rejection symptom did not reproduce'


if __name__ == '__main__':
    main()
