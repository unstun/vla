"""Extract the recorded due reference path for the stationary failed turn."""
from pathlib import Path
import hashlib
import json
import sys
HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
TASK = Path('/data/sun/vla_mppi_20261009')
sys.path.insert(0, str(BASE / 'versions/v144'))
from analyze_remote import Capture

out = TASK / 'results/full_route_diagnosis_v146/input'
identity = json.loads((out / 'identity.json').read_text())
capture = Capture(TASK / 'trials/v144_full_candidate_attempt01/runs/v144_full_candidate_attempt01')
routes = [r for r in capture.rows('artifacts/reactive_observations.jsonl')
          if r['event'] == 'pct_route' and r['clock_ns'] <= identity['query_ns']]
route = max(routes, key=lambda r: r['clock_ns'])
poses = route['data']['path']['poses']
text = str(len(poses)) + '\n' + '\n'.join(' '.join(format(float(r['pose']['position'][k]), '.17g')
                                           for k in ('x', 'y', 'z')) for r in poses) + '\n'
(out / 'route.txt').write_text(text)
(out / 'route_identity.json').write_text(json.dumps({'clock_ns': route['clock_ns'],
    'generation': route['data']['generation'], 'poses': len(poses),
    'route_sha256': hashlib.sha256(text.encode()).hexdigest(), 'source': capture.sources}, indent=2) + '\n')
print(json.dumps({'generation': route['data']['generation'], 'poses': len(poses)}))
