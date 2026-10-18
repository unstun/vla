"""Verify native bindings and return compact, continuous-clock regression evidence."""
from pathlib import Path
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
TASK = Path('/data/sun/vla_mppi_20261009')
WORK = TASK/'cooperative_search_v240'
AUDIT = HERE.parent.parent/'audits/2026-10-17_v237_terminal_approach'
sys.path.insert(0, str(AUDIT))
from trajectory_coverage import active_gaps
from verify_replay import verify

OUT = HERE/'results'
OUT.mkdir(exist_ok=True)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
receipt = lambda p: dict(path=str(p), sha256=sha(p), bytes=p.stat().st_size)
def write(path, data):
    path.write_text(json.dumps(data, indent=2)+'\n')
def check_inventory(root, inventory):
    for rel, expected in inventory.items():
        assert sha(root/rel) == expected, str(root/rel)

parent = json.loads((TASK/'callback_failure_v232/offline_gate.json').read_text())
for group in ('source_inventory', 'installed_files'):
    check_inventory(TASK/'callback_failure_v232', parent[group])
v238_install = json.loads((HERE.parent/'v238/results/installed_files.json').read_text())
check_inventory(TASK/'terminal_approach_v238', v238_install)
v239_source = json.loads((HERE.parent/'v239/results/source_inventory.json').read_text())
check_inventory(TASK/'cooperative_search_v239', v239_source)
inventory = json.loads((WORK/'source_inventory.json').read_text())
check_inventory(WORK, inventory)
owned = {str(p.relative_to(HERE)): sha(p) for p in (HERE/'src').rglob('*') if p.is_file()}
assert len(owned) == 3 and inventory == dict(v239_source, **owned)
assert len(inventory) == 317
installed = {str(p.relative_to(WORK)): sha(p) for p in (WORK/'install').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
write(OUT/'source_inventory.json', inventory)
write(OUT/'installed_files.json', installed)
shutil.copy2(WORK/'composition.json', OUT/'composition.json')

native = []
regout = OUT/'regressions'
regout.mkdir(exist_ok=True)
for path in sorted((WORK/'regressions').glob('*.xml')):
    cases = ET.parse(path).findall('.//testcase')
    assert cases and all(not any(c.find(tag) is not None for tag in ('failure', 'error', 'skipped')) for c in cases)
    native.append(dict(name=path.stem, cases=len(cases), sha256=sha(path)))
    shutil.copy2(path, regout/path.name)
assert len(native) == 12 and sum(t['cases'] for t in native) == 97
linked = WORK/'regressions/linked_libraries.txt'
assert 'libscan_native_core.so => /work/install/scan_planner/lib/' in linked.read_text()
shutil.copy2(linked, regout/linked.name)
lib = WORK/'install/scan_planner/lib/libscan_native_core.so'
assert b'astar_inputs_changed' in lib.read_bytes()
symbols = subprocess.check_output(['nm', '-D', '-C', str(lib)], text=True)
refresh_symbols = [line for line in symbols.splitlines() if 'GridMap::refreshSensorInputs' in line]
assert any('char const*, int)' in line for line in refresh_symbols)
assert any('char const*, int, bool)' in line for line in refresh_symbols)
(OUT/'refresh_symbols.txt').write_text('\n'.join(refresh_symbols)+'\n')
write(OUT/'native_regressions.json', dict(passed=True, executables=len(native), test_cases=97, tests=native, physics_steps=0))

live = {}
for name in ('candidate_window01', 'candidate_window02', 'candidate_stairs01'):
    folder = WORK/name
    target = OUT/name
    target.mkdir(exist_ok=True)
    for file in ('live_window.json', 'live_events.csv', 'live_splines.csv', 'emergency_context.csv'):
        shutil.copy2(folder/file, target/file)
    result = json.loads((folder/'live_window.json').read_text())
    rows = list(csv.DictReader((folder/'live_splines.csv').open()))
    start = float(rows[0]['publication_s'])
    end = 55.0 if 'stairs' in name else 114.5
    gaps = active_gaps(rows, start, end)
    result.update(window_start_s=start, window_end_s=end, active_curve_gaps=gaps,
                  cumulative_active_gap_s=sum(g['duration_s'] for g in gaps), full_log=receipt(WORK/(name+'.log')))
    log = (WORK/(name+'.log')).read_text()
    # Approach setup first replays 50 fixed-clock stair frames. Exclude that
    # setup from the proof that the live search actually delivered due inputs.
    if 'stairs' not in name:
        marker = re.search(r'^FRAME 49 .*$', log, re.MULTILINE)
        assert marker
        log = log[marker.end():]
    drains = re.findall(r'input_refresh site=astar_search sensor_poses=(\d+) clouds=(\d+) body_poses=(\d+)', log)
    result['ordered_astar_drains_live'] = len(drains)
    result['inputs_delivered_inside_live_astar'] = dict(zip(('sensor_poses', 'clouds', 'body_poses'),
        (sum(int(row[i]) for row in drains) for i in range(3))))
    if 'stairs' not in name:
        assert drains and result['inputs_delivered_inside_live_astar']['clouds'] > 0
    result['zero_emergency_and_gap_gate_passed'] = result['emergency_messages'] == 0 and not gaps
    live[name] = result
assert live['candidate_window01']['initial_digest'] == live['candidate_window02']['initial_digest']
assert all(live[n][key] == value for n in ('candidate_window01', 'candidate_window02') for key, value in dict(body_messages=486, sensor_poses=56, clouds=56, initial_prefix_scans=979).items())
assert live['candidate_stairs01']['successful'] == live['candidate_stairs01']['rounds'] == 298
assert all(r['zero_emergency_and_gap_gate_passed'] for r in live.values()), live
write(OUT/'live_clock_summary.json', live)

recorded = WORK/'candidate_recorded01/frames.csv'
shutil.copy2(recorded, OUT/'recorded_frames.csv')
recorded_result = verify(recorded)
recorded_log = (WORK/'candidate_recorded01.log').read_text()
assert 'BOUNDARY_CONTRACTS passed=4 frame=90' in recorded_log
duration = re.search(r'REFERENCE_DURATION ([0-9.]+)', recorded_log)
assert duration and abs(float(duration[1])-78.5743906257) < 1e-8
recorded_result.update(boundary_contracts=4, original_reference_duration_s=float(duration[1]), full_log=receipt(WORK/'candidate_recorded01.log'))
write(OUT/'recorded_summary.json', recorded_result)
drain = json.loads((WORK/'candidate_drain01/drain_contract.json').read_text())
assert all(drain[key] for key in ('passed', 'held_digest_unchanged', 'stale_held_evidence_rejected', 'default_adoption_passed'))
shutil.copy2(WORK/'candidate_drain01/drain_contract.json', OUT/'drain_contract.json')
publication = json.loads((WORK/'publication_contract01/publication_contract.json').read_text())
assert all(publication[key] for key in ('passed', 'held_curve_clear', 'newest_invalid_support_curve_rejected', 'original_support_restored'))
shutil.copy2(WORK/'publication_contract01/publication_contract.json', OUT/'publication_contract.json')
for name in ('replay_probe.cpp', 'replay.sh', 'CMakeLists.txt'):
    shutil.copy2(AUDIT/name, OUT/('executed_'+name))

# The rejected predecessor remains frozen. Retain its valid runs separately;
# earlier attempts before all static consumers were rebuilt are excluded.
reject = OUT/'rejected_v239'
reject.mkdir(exist_ok=True)
oldwork = TASK/'cooperative_search_v239'
for file in ('live_window.json', 'live_splines.csv', 'live_events.csv', 'emergency_context.csv'):
    shutil.copy2(oldwork/'candidate_window03'/file, reject/file)
oldrows = list(csv.DictReader((reject/'live_splines.csv').open()))
oldgaps = active_gaps(oldrows, float(oldrows[0]['publication_s']), 114.5)
assert len(oldgaps) == 1 and abs(oldgaps[0]['duration_s']-0.18456137063095923) < 1e-7
write(reject/'continuity_rejection.json', dict(accepted=False, active_gaps=oldgaps, valid_live_run='candidate_window03', valid_recorded_run='candidate_recorded02', excluded='Earlier v239 attempts did not rebuild every static consumer.'))
write(reject/'installed_files.json', {str(p.relative_to(oldwork)): sha(p) for p in (oldwork/'install').rglob('*') if p.is_file() and '__pycache__' not in p.parts})
shutil.copy2(oldwork/'candidate_recorded02/frames.csv', reject/'recorded_frames.csv')

bulk = [WORK/'build_candidate.log', WORK/'candidate_drain01.log', WORK/'candidate_recorded01.log']
bulk += sorted((WORK/'regressions').glob('*.log'))
bulk += sorted(WORK.glob('build_candidate_*.log'))
bulk += [oldwork/'candidate_window03.log', oldwork/'candidate_recorded02.log']
bulk += sorted((WORK/'publication_contract01').glob('*.log'))
scope = ('Real-clock native executor, original due DDS input, asynchronous mapper and once-restored initial state. '
         'Recorded body motion does not follow the new commands; initial mapper scheduling history is not exact. '
         'No new physics, measured-motion improvement, new video or baseline promotion.')
gate = dict(passed=True, status='offline_native_continuity_gate_passed', scope=scope,
            physics_steps=0, physical_attempts=0, measured_pause_improvement_validated=False,
            parent_source_files_unchanged=len(parent['source_inventory']), parent_installed_files_unchanged=len(parent['installed_files']),
            v238_installed_files_unchanged=len(v238_install), v239_source_files_unchanged=len(v239_source),
            candidate_source_files_verified=len(inventory), owned_native_files=3, cumulative_native_files_vs_v232=5,
            candidate_installed_files=len(installed), loaded_native_library=receipt(lib), native_test_cases=97,
            boundary_contracts=4, nonadopting_drain_contract=drain, newest_map_publication_negative=publication, live_runs=live,
            recorded=recorded_result, input_identity=dict(path=str(TASK/'terminal_approach_v238/input05'),
            stream=receipt(TASK/'terminal_approach_v238/input05/stream.txt'),
            frames=receipt(TASK/'terminal_approach_v238/input05/frames.txt')),
            source_sha256=sha(AUDIT/'replay_probe.cpp'), replay_script_sha256=sha(AUDIT/'replay.sh'),
            bulk_artifacts=[receipt(p) for p in bulk])
write(OUT/'offline_gate.json', gate)
print(json.dumps(dict(passed=True, native=97, live={n: dict(rounds=r['rounds'], successful=r['successful'], emergency=r['emergency_messages'], gaps=len(r['active_curve_gaps'])) for n, r in live.items()}, recorded=recorded_result['frames'], output=str(OUT))))
