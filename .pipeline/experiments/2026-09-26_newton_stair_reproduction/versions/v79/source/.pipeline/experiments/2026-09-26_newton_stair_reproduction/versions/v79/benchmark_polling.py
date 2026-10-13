"""Same-input encoder comparison; component evidence, not a heartbeat repair claim."""
from pathlib import Path
import argparse
import hashlib
import json
import statistics
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'backend_ros'))
from p2b_backend_ros.plan_history import PlanHistory

parser = argparse.ArgumentParser()
parser.add_argument('--result', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
original = json.loads(args.result.read_text())['last_backend']
history = PlanHistory()
for row in original['pct']['plan_history']:
    history.append(row)
compact = dict(original)
compact['pct'] = dict(history.snapshot(), configured_pct_layer=original['pct']['configured_pct_layer'])
assert all(compact[key] == value for key, value in original.items() if key != 'pct')
measurements = {}
for name, data in [('original_full', original), ('compact', compact)]:
    samples = []
    for unused in range(100):
        started = time.perf_counter_ns()
        encoded = json.dumps(data, sort_keys=True).encode()
        samples.append((time.perf_counter_ns() - started) / 1e6)
    measurements[name] = {'bytes': len(encoded), 'mean_ms': statistics.mean(samples),
                          'p95_ms': sorted(samples)[94], 'maximum_ms': max(samples)}
result = {'source': str(args.result), 'source_sha256': hashlib.sha256(args.result.read_bytes()).hexdigest(),
          'python': sys.version, 'samples_per_condition': 100, 'measurements': measurements,
          'non_pct_state_identical': True, 'route_count': history.sequence,
          'claim': 'Encoder benchmark of the original retained post-fault snapshot; not the missing pre-fault payload or end-to-end heartbeat validation.'}
args.output.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(measurements))
