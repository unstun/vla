"""Verified original-capture diagnosis; output compact evidence and external fixtures."""
import argparse
import collections
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import zipfile

BASE = Path(__file__).resolve().parents[2]


def load_module(name, source):
    spec = importlib.util.spec_from_file_location(name, source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


core = load_module('actual_v47_round_parser', BASE / 'versions/v47/analyze_trial.py')


class Capture:
    def __init__(self, root):
        self.root = root
        self.archive = zipfile.ZipFile(root / 'raw_capture.zip')
        self.manifest = json.loads((root / 'raw_capture_manifest.json').read_text())
        self.sources = {}

    def read(self, name):
        path = self.root / name
        value = path.read_bytes() if path.is_file() else self.archive.read(name)
        self.verify(name, len(value), hashlib.sha256(value).hexdigest())
        return value.decode()

    def rows(self, name):
        path = self.root / name
        stream = path.open('rb') if path.is_file() else self.archive.open(name)
        sha = hashlib.sha256()
        size = 0
        with stream:
            for line in stream:
                sha.update(line)
                size += len(line)
                if line.strip():
                    yield json.loads(line), len(line)
        self.verify(name, size, sha.hexdigest())

    def verify(self, name, size, sha):
        expected = self.manifest['members'].get(name)
        if expected and (size != expected['bytes'] or sha != expected['sha256']):
            raise ValueError('Original archived member changed: ' + name)
        self.sources[name] = {'bytes': size, 'sha256': sha}


def distribution(values):
    return core.distribution(list(values))


IDENTITY = ('run_id', 'epoch', 'request_id', 'goal_id', 'route_id',
            'command_id', 'generation', 'map_epoch', 'map_revision')


def analyze(name, root, output, fixtures):
    cap = Capture(root)
    scan = cap.read('scan.log')
    lines = scan.splitlines()
    class OriginalLog:
        def read_text(self):
            return scan
    starts, rounds = core.parse_rounds(OriginalLog())
    for r in rounds:
        section = lines[r['start_line']-1:r['end_line']]
        r['warm_accepts'] = sum('V48_WARM_RESULT accepted=1' in x for x in section)
        profiles = [json.loads(x.split('V50_PROFILE ', 1)[1]) for x in section if 'V50_PROFILE ' in x]
        if len(profiles) != 1:
            raise ValueError('Expected exactly one profile per complete round')
        r['profile'] = profiles[0]
        r['warm_reasons'] = dict(collections.Counter(re.search(r'reason=(\S+)', x)[1]
            for x in section if 'V48_WARM_SEED selected=0' in x))

    snapshots = []
    chosen = {}
    prior = None
    fault = None
    fixture_targets = {'early': 12., 'middle': 23., 'late': 29.3 if name == 'trial01' else 44.}
    for row, size in cap.rows('backend_states.jsonl'):
        data = row['data']
        flow = data.get('stop_flow')
        if fault is None and flow and flow.get('reason') == 'heartbeat_stale':
            fault = {'sim_s': row['sim_time_s'], 'flow': flow,
                     'owner': data['gate']['owner'], 'previous': prior}
        summary = {'sim_s': row['sim_time_s'], 'bytes': size,
            'heartbeat_s': data['gate'].get('last_heartbeat_s'),
            'raw_callback_s': data['scan_port'].get('last_raw_command_s'),
            'measurement_s': (data['gate'].get('last_measurement') or {}).get('monotonic_s'),
            'gate_reason': data['gate']['closed_reason'],
            'stop_flow': flow,
            'pct_history_count': len(data['pct'].get('plan_history', [])),
            'global_history_count': len(data['global_refresh'].get('history', []))}
        snapshots.append(summary)
        prior = summary
        for label, target in fixture_targets.items():
            if label not in chosen or abs(row['sim_time_s']-target) < abs(chosen[label]['sim_time_s']-target):
                chosen[label] = row
    if fault is None:
        raise ValueError('Recorded heartbeat failure missing')
    flow = fault['flow']
    fault_time = flow['started_monotonic_s']
    last_heartbeat = fault['previous']['heartbeat_s']
    owner = fault['owner']
    raw = []
    for row, unused_size in cap.rows('artifacts/reactive_observations.jsonl'):
        wall = row.get('wall_monotonic_ns', 0) / 1e9
        if row['event'] == 'raw_command' and fault_time-1. <= wall <= fault_time+1.:
            message = row['data']
            identity = {k: message[k] for k in IDENTITY}
            raw.append({'receipt_s': wall, 'identity_matches': identity == owner,
                'identity': identity, 'stamp': message['stamp'],
                'traj_id': message['traj_id'], 'twist': message['twist']})
    matching = [r for r in raw if r['identity_matches']]
    inside = [r for r in matching if last_heartbeat < r['receipt_s'] < fault_time]
    body = [row for row, size in cap.rows('backend_body_callbacks.jsonl')]
    gaps = [{'begin_s': a['entered_ns']/1e9, 'end_s': b['entered_ns']/1e9,
             'gap_s': (b['entered_ns']-a['entered_ns'])/1e9,
             'previous_duration_s': (a['finished_ns']-a['entered_ns'])/1e9,
             'stamp_delta_s': (b['stamp_ns']-a['stamp_ns'])/1e9}
             for a, b in zip(body, body[1:])]
    fault_gaps = [g for g in gaps if g['begin_s'] <= fault_time and g['end_s'] >= last_heartbeat]
    recent = [r for r in rounds if last_heartbeat-1. <= r['start_wall_s'] <= fault_time+1.]
    clock = [row for row, size in cap.rows('clock_samples.jsonl')
             if row.get('accepted') and row.get('samples', 0) >= 500]
    offsets = sorted(r['filtered_offset_ns']/1e9 for r in clock)
    offset = offsets[len(offsets)//2]
    pace = json.loads(cap.read('result.json'))['realtime_pacing']
    begin = pace['wall_anchor_monotonic_s']-offset
    end = begin+pace['wall_elapsed_s']
    navigation = [r for r in rounds if begin <= r['start_wall_s']+r['wall_s'] <= end]
    active = [r for r in navigation if r['start_wall_s'] <= fault_time]
    solve_total = sum(min(r['start_wall_s']+r['wall_s'],fault_time)-r['start_wall_s'] for r in active)
    completed_active = [r for r in active if r['start_wall_s']+r['wall_s'] <= fault_time]
    groups = {}
    for label, group in [('all', active), ('warm_accepted', [r for r in active if r['warm_accepts']]),
                         ('cold_or_failed', [r for r in active if not r['warm_accepts']]),
                         ('over_100ms', [r for r in active if r['wall_s'] >= .1])]:
        groups[label] = {'count': len(group), 'solve_ms': distribution(r['wall_s']*1000 for r in group),
            'sum_solve_s': sum(r['wall_s'] for r in group),
            'inclusive_stage_wall_ms': {stage: distribution(r['profile'][stage]['wall_ms'] for r in group)
                for stage in ('target','goal_search','inputs','cloud','sliding_map','seed','warm_seed','optimizer','refine','final_check')},
            'warm_rejection_reasons': dict(sum((collections.Counter(r['warm_reasons']) for r in group), collections.Counter()))}
    active_span = fault_time-active[0]['start_wall_s']
    gap_rows = [{'next_start_s': b['start_wall_s'], 'previous_solve_ms': a['wall_s']*1000,
        'non_solve_gap_ms': (b['start_wall_s']-a['start_wall_s']-a['wall_s'])*1000,
        'start_interval_ms': (b['start_wall_s']-a['start_wall_s'])*1000,
        'next_skipped_slots': b['skipped_slots']}
        for a,b in zip(active,active[1:])]
    fixtures.mkdir(parents=True, exist_ok=True)
    fixture_records = {}
    for label, row in chosen.items():
        data = row['data']
        p = fixtures / (name+'_'+label+'.json')
        p.write_text(json.dumps(data, sort_keys=True))
        fields = {k: len(json.dumps(v, sort_keys=True).encode()) for k,v in data.items()}
        fixture_records[label] = {'path': str(p), 'bytes': p.stat().st_size,
            'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
            'sim_s': row['sim_time_s'], 'field_bytes': fields,
            'pct_history_count': len(data['pct']['plan_history']),
            'route_waypoint_counts': [len(x.get('waypoints_m', [])) for x in data['pct']['plan_history']]}
    max_round = max(active, key=lambda r:r['wall_s'])
    proof = {'run': root.name, 'capture_root': str(root), 'fault': fault,
        'last_matching_heartbeat_before_stop_s': last_heartbeat,
        'fault_flow_minus_last_heartbeat_s': fault_time-last_heartbeat,
        'raw_window_messages': raw,
        'matching_raw_between_last_backend_heartbeat_and_fault': inside,
        'matching_raw_max_receipt_gap_s': max((b['receipt_s']-a['receipt_s'] for a,b in zip(matching,matching[1:])),default=None),
        'backend_body_callback_fault_gaps': fault_gaps,
        'maximum_body_callback_gap': max(gaps,key=lambda r:r['gap_s']),
        'maximum_body_callback_duration_s': max((r['finished_ns']-r['entered_ns'])/1e9 for r in body),
        'recent_planning_rounds': recent, 'active_planning_window_s': active_span,
        'active_attempt_hz': len(active)/active_span,
        'active_successful_hz': sum(r['success'] for r in completed_active)/active_span,
        'active_completed_before_fault':len(completed_active),
        'active_rounds_started_before_fault':len(active),
        'rate_definition':'Completions before original fault-flow start / wall window from first plan start; solve occupancy clipped at fault boundary. Group latency summaries include complete rounds whose starts precede the fault.',
        'active_solver_seconds': solve_total, 'active_solver_fraction': solve_total/active_span,
        'active_skipped_slots': sum(r['skipped_slots'] for r in active),
        'start_intervals_ms': distribution(r['start_interval_ms'] for r in gap_rows),
        'non_solve_gaps_ms': distribution(r['non_solve_gap_ms'] for r in gap_rows),
        'largest_non_solve_gaps': sorted(gap_rows,key=lambda r:r['non_solve_gap_ms'],reverse=True)[:10],
        'groups': groups, 'maximum_round': max_round,
        'backend_snapshot_sizes': {'count':len(snapshots),'first':snapshots[0],'last':snapshots[-1]},
        'backend_snapshots_near_fault': [r for r in snapshots if fault['sim_s']-.6 <= r['sim_s'] <= fault['sim_s']+.4],
        'fixtures': fixture_records, 'source': cap.sources,
        'profile_scope_warning': 'Inclusive scopes overlap: input refresh runs inside seed and optimizer; cloud/sliding_map run within inputs. Do not sum stage wall times.'}
    output.mkdir(parents=True,exist_ok=True)
    (output/(name+'.json')).write_text(json.dumps(proof,indent=2)+'\n')
    (output/(name+'_snapshot_sizes.csv')).write_text('sim_s,bytes,pct_history_count\n'+''.join(
        f"{r['sim_s']},{r['bytes']},{r['pct_history_count']}\n" for r in snapshots))
    print(json.dumps({'trial':name,'raw_matching_inside_fault_gap':len(inside),
        'backend_fault_callback_gaps':fault_gaps,'recent_solve_max_ms':max(r['wall_s']*1000 for r in recent),
        'active_hz':proof['active_successful_hz'],'solver_fraction':proof['active_solver_fraction'],
        'skipped_slots':proof['active_skipped_slots'],'max_round_s':max_round['wall_s'],
        'fixtures': {k:{f:v[f] for f in ('sim_s','bytes','pct_history_count')} for k,v in fixture_records.items()}},indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--fixtures', type=Path, required=True)
    args = p.parse_args()
    for name, root in [('trial01','/private/tmp/vla_newton_v67__xr5p654/runs/v67_mac_trial01_attempt01'),
                       ('trial02','/private/tmp/vla_newton_v68_ooqtmr__/runs/v68_mac_trial01_attempt02')]:
        analyze(name, Path(root), args.output, args.fixtures)
