#!/usr/bin/env python3
"""Run every suite case for one build inside the container; keep planner failures as data.

Modelled on scan_replan_diagnosis/container_cases.py: one process per case, a 20-second wall
ceiling per case (return code 124 on timeout) and one raw log per case.
"""

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import time


CASE_CEILING_S = 20
SAMPLES = 101
EXECUTABLE = '/ws/install/scan_fix_native_suite/lib/scan_fix_native_suite/rebound_replan_suite'
RUN_CASES = '/ws/src/scan_fix_native_suite/scripts/run_cases.py'
FIXTURES = '/inputs/fixtures/suite_cases.json'
PARAMS = '/inputs/planner.yaml'


def load_run_cases(path):
    spec = importlib.util.spec_from_file_location('suite_run_cases', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', required=True, choices=['original', 'candidate'])
    parser.add_argument('--fixtures', default=FIXTURES)
    parser.add_argument('--params', default=PARAMS)
    parser.add_argument('--executable', default=EXECUTABLE)
    parser.add_argument('--run-cases', default=RUN_CASES)
    parser.add_argument('--out', default='/out')
    args = parser.parse_args(argv)

    module = load_run_cases(args.run_cases)
    fixtures = Path(args.fixtures)
    runs = json.loads(fixtures.read_text())['runs']
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    result = []
    for run in runs:
        cmd = module.build_command(args.executable, args.params, run, SAMPLES,
                                   fixtures_root=str(fixtures.parent), print_samples=False)
        started = time.monotonic()
        with (out / (run['label'] + '.log')).open('w') as log:
            try:
                completed = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, timeout=CASE_CEILING_S)
                code = completed.returncode
            except subprocess.TimeoutExpired:
                code = 124
        data = {'label': run['label'], 'build': args.build, 'returncode': code,
                'wall_seconds': time.monotonic() - started, 'command': cmd}
        result.append(data)
        print(json.dumps(data), flush=True)
    (out / 'cases_result.json').write_text(json.dumps(result, indent=2) + '\n')
    return 0 if all(r['returncode'] in {0, 2} for r in result) else 1


if __name__ == '__main__':
    raise SystemExit(main())
