#!/usr/bin/env python3
"""Bounded real GPU window-start qualification, without starting navigation."""

import hashlib
import json
from pathlib import Path
import sys

from observer.session import DisplayProbe


root = Path(__file__).resolve().parent
probe = DisplayProbe(root)
result = {'scope': 'RViz startup and exact run-specific window title only; no Isaac or navigation launch'}
try:
    probe.start()
    result['checks'] = {
        'nvidia_renderer': probe.records.get('nvidia_renderer_verified') is True,
        'run_specific_window_title': probe.records.get('window_matches_run_specific_title') is True,
        'capture_not_started_without_physics': probe.capture is None,
    }
except Exception as error:
    result['error'] = str(error)
finally:
    result['observer'] = probe.stop()
result['passed'] = (bool(result.get('checks')) and all(result['checks'].values())
                    and not result.get('error') and not result['observer']['errors'])
(root / 'artifacts/qualification_result.json').write_text(json.dumps(result, indent=2) + '\n')
hashes = {str(p.relative_to(root / 'artifacts')): hashlib.sha256(p.read_bytes()).hexdigest()
          for p in (root / 'artifacts').rglob('*') if p.is_file() and p.name != 'artifact_hashes.json'}
(root / 'artifacts/artifact_hashes.json').write_text(json.dumps(hashes, indent=2, sort_keys=True) + '\n')
print(json.dumps({'passed': result['passed'], 'checks': result.get('checks'), 'error': result.get('error')}, indent=2))
sys.exit(0 if result['passed'] else 1)
