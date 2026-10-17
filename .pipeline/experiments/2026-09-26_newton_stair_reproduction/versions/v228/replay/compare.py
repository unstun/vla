"""Compare exact poses and independent occupancy predicates with frozen v223."""
from pathlib import Path
import collections
import csv
import hashlib
import json
import sys

work = Path(sys.argv[1])
old = Path('/data/sun/vla_mppi_20261009/floor_reason_v223/replay_output02')
read = lambda p: list(csv.DictReader(p.open()))
result = {'physics_steps': 0, 'datasets': {}}
for dataset in ('input', 'critical_input'):
    before = read(old / dataset / 'attribution.csv')
    after = read(work / 'replay_output01' / dataset / 'attribution.csv')
    assert len(before) == len(after)
    changes = []
    occupancy_changes = collections.Counter()
    for a, b in zip(before, after):
        assert all(a[k] == b[k] for k in ('frame', 'id', 'kind', 'x', 'y', 'z', 'yaw'))
        for key in ('cylinder_occupied', 'history_101', 'other_occupied', 'history_target', 'torso_occupied', 'unknown'):
            occupancy_changes[key] += a[key] != b[key]
        if bool(int(a['native'])) != bool(int(b['native'])):
            changes.append({'before': a, 'after': b})
    assert not any(occupancy_changes.values()), occupancy_changes
    first = lambda data: dict(collections.Counter(str(int(r['front_reason']) or int(r['rear_reason'])) for r in data if int(r['native'])))
    result['datasets'][dataset] = {
        'queries': len(after), 'before_rejected': sum(bool(int(r['native'])) for r in before),
        'after_rejected': sum(bool(int(r['native'])) for r in after),
        'binary_changes': len(changes), 'rejected_to_free': sum(int(r['before']['native']) != 0 for r in changes),
        'free_to_rejected': sum(int(r['before']['native']) == 0 for r in changes),
        'occupancy_predicate_changes': dict(occupancy_changes),
        'before_first_reason': first(before), 'after_first_reason': first(after),
        'changed_examples': changes[:20],
        'after_by_kind': {str(k): {'queries': sum(int(r['kind']) == k for r in after),
                                 'rejected': sum(int(r['kind']) == k and int(r['native']) != 0 for r in after)}
                          for k in sorted({int(r['kind']) for r in after})},
    }
    if dataset == 'critical_input':
        result['critical_queries'] = after
        assert all(int(r['native']) for r in after)
        assert int(after[0]['edge_guard']) and abs(float(after[0]['floor_z']) - 1.5580306959152221) < 1e-12
result['remote_artifacts'] = {str(p.relative_to(work)): {'bytes': p.stat().st_size,
    'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in (work / 'replay_output01').rglob('*.csv')}
(work / 'replay_comparison.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: v for k, v in result.items() if k != 'remote_artifacts'}, indent=2))
