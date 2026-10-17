"""Record only actually executed Mac host unit tests; no ROS skips count as passes."""
from pathlib import Path
import argparse
import json
import platform
import unittest

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    modules = ['test_applied_transport', 'test_initial_frame', 'test_full_route',
               'test_native_gate', 'test_mac_supervisor']
    suite = unittest.defaultTestLoader.loadTestsFromNames(modules)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    record = dict(passed=result.wasSuccessful() and not result.skipped,
                  host=platform.system() + '/' + platform.machine(), modules=modules,
                  tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                  skipped=len(result.skipped))
    args.output.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record))
    if not record['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
