"""v198 physics/rays and v216 locomotion; repair only captured-scan scheduling."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
VERSIONS = HERE.parent


def recorder_source():
    frozen = VERSIONS / 'v198/newton_episode.py'
    source = frozen.read_text()
    changes = {
        'future = scanner.submit(lidar.scan, scan_index, actor_time, override_pose=pose, captured_state=captured_state)':
            'future = SCAN_DEADLINE.submit(scanner, lidar.scan, scan_index, actor_time, override_pose=pose, captured_state=captured_state)',
        'publish_scan(future.result(), index, captured_pose, captured_time)':
            'publish_scan(SCAN_DEADLINE.result(future), index, captured_pose, captured_time)',
        'publish_scan(future.result(timeout=2.), index, captured_pose, captured_time)':
            'publish_scan(SCAN_DEADLINE.result(future), index, captured_pose, captured_time)',
        '                        if pending_scan is not None:\n                            raise RuntimeError("Captured scan did not finish before the next sensor period")':
            '                        if pending_scan is not None:\n                            future, index, captured_pose, captured_time = pending_scan\n                            publish_scan(SCAN_DEADLINE.result(future), index, captured_pose, captured_time)\n                            pending_scan = None',
    }
    for before, after in changes.items():
        assert source.count(before) == 1, before
        source = source.replace(before, after)
    return frozen, source, changes


def main():
    from scan_deadline import ScanDeadline, PERIOD_S
    spec = importlib.util.spec_from_file_location('v237_locomotion', VERSIONS / 'v216/activate.py')
    locomotion = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(locomotion)
    adapter = locomotion.install()
    out = Path(os.environ['NEWTON_RUN_DIR'])
    sources = [HERE / 'scan_deadline.py', Path(__file__), VERSIONS / 'v216/activate.py',
               Path(adapter.__file__), adapter.SOURCE, VERSIONS / 'v198/newton_episode.py']
    (out / 'locomotion_activation.json').write_text(json.dumps(dict(integration='v237', navigation='v232',
        locomotion='v216', adapter_loaded_before_robot_construction=True,
        files={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}), indent=2)+'\n')
    frozen, source, changes = recorder_source()
    executed = out / 'executed_v237_recorder.py'
    executed.write_text(source)
    (out / 'v237_recorder_binding.json').write_text(json.dumps(dict(period_s=PERIOD_S,
        parent_source_sha256=hashlib.sha256(frozen.read_bytes()).hexdigest(),
        executed_source_sha256=hashlib.sha256(source.encode()).hexdigest(), changes=changes,
        raycast_or_capture_timestamps_changed=False), indent=2)+'\n')
    deadline = ScanDeadline()
    namespace = dict(__file__=str(frozen), __name__='v237_original_physical_recorder', SCAN_DEADLINE=deadline)
    try:
        exec(compile(source, str(executed), 'exec'), namespace)
        namespace['main']()
    finally:
        deadline.save(out / 'scan_timing.jsonl')


if __name__ == '__main__':
    main()
