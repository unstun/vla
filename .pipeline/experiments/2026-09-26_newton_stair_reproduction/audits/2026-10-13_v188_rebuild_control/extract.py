"""Stream verified historical captures into compact diagnostic projections."""
import argparse
from collections import Counter, deque
import gzip
import hashlib
import json
from pathlib import Path
import zipfile


def verified_lines(root, name, sources):
    # Same member contract as v177/analyze_remote.py Capture; streaming avoids
    # materializing the full 100MB telemetry string and its parsed object graph.
    manifest = json.loads((root / 'raw_capture_manifest.json').read_text())
    expected = manifest['members'].get(name)
    archive = None
    if (root / name).is_file():
        stream = (root / name).open('rb')
    else:
        archive = zipfile.ZipFile(root / 'raw_capture.zip')
        stream = archive.open(name)
    sha, size = hashlib.sha256(), 0
    try:
        for number, raw in enumerate(stream, 1):
            sha.update(raw); size += len(raw)
            if raw.strip():
                yield number, json.loads(raw)
    finally:
        stream.close()
        if archive is not None:
            archive.close()
    result = dict(sha256=sha.hexdigest(), bytes=size)
    if expected is not None:
        assert result == {k: expected[k] for k in ('sha256', 'bytes')}, name
    sources[name] = dict(**result, archive_manifest_matched=expected is not None)


def extract(root, output):
    output.mkdir(parents=True, exist_ok=False)
    sources = {}
    counts = Counter()
    previous = None
    history = deque(maxlen=10)
    maximum_error = 0.0
    maximum_history_error = 0.0
    previous_time = None
    gaps = []
    differences = []
    with gzip.open(output / 'telemetry.jsonl.gz', 'wt') as target:
        for line, row in verified_lines(root, 'telemetry.jsonl', sources):
            t = row['physics_time_s']
            command = row['effective_command']
            newest = row['policy_input'][87:90]
            assert len(row['policy_input']) == 450 and len(newest) == 3
            error = max(abs(a-b) for group in (row['observation'][6:9], newest) for a,b in zip(group, command))
            maximum_error = max(error, maximum_error)
            assert error < 2e-7, (line, 'effective/input mismatch', error)
            if previous is not None:
                assert row['policy_calls'] == previous + 1, (line, 'policy call gap')
            previous = row['policy_calls']
            history.append(command)
            if len(history) == 10:
                history_error = max(abs(a-b) for a,b in zip(row['policy_input'][60:90], sum(list(history), [])))
                maximum_history_error = max(maximum_history_error, history_error)
                assert history_error < 2e-7, (line, 'command history mismatch')
            if previous_time is not None:
                dt = t-previous_time
                assert dt > 0
                if dt > .025:
                    gaps.append(dict(line=line, from_s=previous_time, to_s=t))
            previous_time = t
            discrepancy = max(abs(a-b) for a,b in zip(row['requested_command'], command))
            if discrepancy > 2e-7:
                differences.append(dict(line=line, time_s=t, requested=row['requested_command'], effective=command))
            compact = {k: row[k] for k in ('physics_time_s','requested_command','effective_command',
                'command_reason','command_sequence','command_stale','stance_mode','stance_reason',
                'policy_owns_joints','navigation_ready','base_up_z','foot_forces_n','state_sequence')}
            compact.update(source_line=line, input_newest_command=newest,
                position=row['body_sensor']['position'], quaternion=row['body_sensor']['quaternion'],
                linear_body=row['body_sensor']['linear_body'], linear_world=row['body_sensor']['linear_world'],
                angular_body=row['body_sensor']['angular_body'])
            target.write(json.dumps(compact, separators=(',', ':'))+'\n')
            counts['telemetry'] += 1
    events = Counter()
    keep = {'raw_command','gated_command','bspline','scan_cancel','route_binding','admission',
            'execution_frozen','route','body_pose','scan_admission','body_pose_observer','pct_route','measured_stop_proof'}
    with gzip.open(output / 'events.jsonl.gz', 'wt') as target:
        for line, row in verified_lines(root, 'artifacts/reactive_observations.jsonl', sources):
            events[row['event']] += 1
            if row['event'] in keep:
                row['source_line'] = line
                target.write(json.dumps(row, separators=(',', ':'))+'\n')
    result = dict(run=root.name, root=str(root), sources=sources, samples=counts['telemetry'],
        events=dict(events), effective_vs_actual_policy_input_max_error=maximum_error,
        complete_history_max_error=maximum_history_error, telemetry_gaps=gaps,
        requested_effective_discrepancies=differences,
        analyzer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    result['outputs'] = {p.name: dict(bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest())
        for p in output.glob('*.gz')}
    (output / 'receipt.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: result[k] for k in ('run','samples','effective_vs_actual_policy_input_max_error',
        'complete_history_max_error','telemetry_gaps')}) , flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--task', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    for attempt in range(1, 6):
        tag = f'v177_full_candidate_attempt{attempt:02d}'
        extract(a.task / 'trials' / tag / 'runs' / tag, a.output / f'attempt{attempt:02d}')
