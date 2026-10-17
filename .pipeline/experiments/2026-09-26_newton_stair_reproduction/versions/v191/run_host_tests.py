"""Record the actual Mac host test suite separately from ROS/container tests."""
from pathlib import Path
import argparse
import json
import platform
import unittest
from run_mac_full import validate_task

MODULES = ['test_applied_transport', 'test_initial_frame', 'test_full_route',
           'test_native_gate', 'test_mac_supervisor', 'test_source_inventory']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task-root', type=Path, required=True)
    args = parser.parse_args()
    task = validate_task(args.task_root)
    assert (platform.system(), platform.machine()) == ('Darwin', 'arm64')
    suite = unittest.defaultTestLoader.loadTestsFromNames(MODULES)
    with (task / 'evidence/v191_host_tests.log').open('w') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    summary = dict(passed=result.wasSuccessful() and not result.skipped,
                   host='Darwin/arm64', modules=MODULES, tests=result.testsRun,
                   failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped))
    (task / 'evidence/v191_host_tests.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary))
    if not summary['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
