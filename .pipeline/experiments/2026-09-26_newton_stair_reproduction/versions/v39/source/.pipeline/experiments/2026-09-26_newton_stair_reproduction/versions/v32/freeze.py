"""Freeze v32 after K1-K4 (PLAN.md), before any v32 physics."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, shutil

H = Path(__file__).resolve().parent
B = H.parents[1]
R = B.parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
load = lambda p: json.loads(p.read_text())
parent = load(H.parent / 'v31/manifest.json')
prepared = load(H / 'prepared.json')
N = R / prepared['native_build']
A = B / 'audits/2026-09-29_wall_clock_chain'
assert not (H / 'manifest.json').exists()
assert load(H / 'check_change.json')['passed']                                   # K1, K2
assert load(H / 'gc_schedule_check/result.json')['passed']                        # K3
assert load(H / 'independent_review.json')['passed']                             # K4: the first passing round (1-3 failed)
changed = set(prepared['changed_files'])
for name, digest in parent['source_files'].items():
    if name not in changed:
        assert sha(R / name) == digest, name
for name, digest in load(N / 'source_sha256.json').items():
    assert sha(N / name) == digest, name
assert load(N / 'build_result.json')['passed']
preimages = [p for p in (H / 'parent_source').rglob('*') if p.is_file()]
assert len(preimages) == 1 and sha(preimages[0]) == parent['source_files'][next(iter(changed))]
shutil.copyfile(N / 'build_result.json', H / 'build_result.json')
shutil.copyfile(N / 'install_sha256.json', H / 'install_sha256.json')
selected = {R / name for name in parent['source_files']} | {R / name for name in changed}
# Version files, without the snapshot itself and without K3's bulky per-mode replay outputs (clouds, rows,
# factory arrays); each mode's summary.json and gc_events.npy are kept.
for p in H.rglob('*'):
    parts = p.relative_to(H).parts
    if not p.is_file() or '__pycache__' in parts or parts[0] == 'source':
        continue
    if parts[0] == 'gc_schedule_check' and {'none', 'freeze', 'collect_freeze'} & set(parts[:-1]) \
            and parts[-1] not in ('summary.json', 'gc_events.npy'):
        continue
    selected.add(p)
# The diagnosis this version rests on: its record, scripts and results. Of the replay benchmark's per-run
# folders only summary.json is kept (the record cites it); clouds and per-step rows stay local-only.
for p in A.rglob('*'):
    parts = p.relative_to(A).parts
    if p.is_file() and '__pycache__' not in parts and not (parts[0] == 'bench' and len(parts) > 2 and parts[-1] != 'summary.json'):
        selected.add(p)
records = {}
for p in sorted(selected):
    name = str(p.relative_to(R))
    records[name] = sha(p)
    dest = H / 'source' / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(p, dest)
(H / 'manifest.json').write_text(json.dumps({
    'version': 'v32', 'parent': 'v31', 'status': 'frozen_unvalidated', 'frozen_utc': datetime.now(timezone.utc).isoformat(),
    'change': 'The Newton worker (scripts/newton_episode.py) calls gc.collect() and then gc.freeze() once before the '
              'control loop and after every 50th control step: each collection reclaims the garbage created since '
              'the previous freeze, and the survivors move to the permanent generation, so automatic full '
              'collections no longer traverse the retained heap. Second candidate; the first (attempt01/) froze '
              'without collecting and would have leaked. No gate, threshold, computation, native build or planner '
              'configuration changes.',
    'decisions': 'Dr Sun, 2026-09-29: fix the clock fault after the v31 trial (diagnose the wall-clock chain, then '
                 'build v32). Not changed here: mechanism B (host scheduling delays), the superseding of poses '
                 'published during B (location not measured), and the gate time base (Dr Sun to decide).',
    'source_files': records, 'changed_files': sorted(changed), 'native_build': prepared['native_build'],
    'source_snapshot_prefix': 'source/', 'acceptance_plan': 'PLAN.md',
    'freeze_boundary': 'After K1 byte-exact insertions, K2 AST scope, K3 GC-schedule replay (three schedules on '
                       'v31_historical_full01 commands) and K4 independent review (the first passing round, after rounds 1-3 failed; '
                       'independent_review.json); before any v32 '
                       'physics (L1 instrumented diagnostic run, L2 trial).'},
    indent=2) + '\n')
print(json.dumps({'version': 'v32', 'source_files': len(records)}))
