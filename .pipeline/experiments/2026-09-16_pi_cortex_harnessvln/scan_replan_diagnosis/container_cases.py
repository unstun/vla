#!/usr/bin/env python3
"""Invoke real C++ cases with a per-case deadline; keep planner failures as data."""

import importlib.util
import json
from pathlib import Path
import subprocess
import time


spec = importlib.util.spec_from_file_location('native_cases', '/ws/src/scan_replan_native_repro/scripts/run_cases.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
cases = json.loads(Path('/inputs/cases.json').read_text())['cases']
result = []
for case in cases:
    for repeat in range(3):
        cmd = module.build_command('/ws/install/scan_replan_native_repro/lib/scan_replan_native_repro/rebound_replan_repro',
                                   '/inputs/planner.yaml', case, 101)
        started = time.monotonic()
        label = case['id'] + '_' + str(repeat)
        with Path('/out', label + '.log').open('w') as log:
            try:
                completed = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, timeout=20)
                code = completed.returncode
            except subprocess.TimeoutExpired:
                code = 124
        data = {'id': case['id'], 'repeat': repeat, 'returncode': code,
                'wall_seconds': time.monotonic() - started, 'command': cmd}
        result.append(data)
        print(json.dumps(data), flush=True)
Path('/out/cases_result.json').write_text(json.dumps(result, indent=2) + '\n')
raise SystemExit(0 if all(r['returncode'] in {0, 2} for r in result) else 1)
