"""Summarize the frozen v70 observation run without expanding raw archives."""
from collections import Counter, defaultdict
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

BASE = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('round_parser',BASE/'versions/v47/analyze_trial.py')
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--run-root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args = p.parse_args()
    root = args.run_root
    archive = root/'raw_capture.zip'
    members = json.loads((root/'raw_capture_manifest.json').read_text())['members']
    sources = {}
    def read(name):
        path = root/name
        if path.is_file():
            value = path.read_bytes()
        else:
            with zipfile.ZipFile(archive) as z:
                value = z.read(name)
            expected = members[name]
            assert len(value)==expected['bytes'] and hashlib.sha256(value).hexdigest()==expected['sha256']
        sources[name] = {'bytes':len(value),'sha256':hashlib.sha256(value).hexdigest()}
        return value.decode()
    by = defaultdict(list)
    for line in read('backend_timing_trace.jsonl').splitlines():
        r = json.loads(line)
        by[r['stage']].append(r)
    stages = {}
    for stage, rows in by.items():
        if 'entered_ns' not in rows[0]:
            continue
        stages[stage] = {
            'wall_ms':core.distribution((r['finished_ns']-r['entered_ns'])/1e6 for r in rows),
            'thread_cpu_ms':core.distribution(r['cpu_ns']/1e6 for r in rows),
            'top_spans':sorted(rows,key=lambda r:r['finished_ns']-r['entered_ns'],reverse=True)[:4]}
    raw = sorted((r for r in by['raw_callback'] if r.get('identity_matches')),key=lambda r:r['entered_ns'])
    gaps = [{'begin_s':a['entered_ns']/1e9,'end_s':b['entered_ns']/1e9,
             'gap_ms':(b['entered_ns']-a['entered_ns'])/1e6}
            for a,b in zip(raw,raw[1:])]
    text = read('scan.log')
    class Log:
        def read_text(self):
            return text
    starts,rounds = core.parse_rounds(Log())
    lines = text.splitlines()
    maximum = max(rounds,key=lambda r:r['wall_s'])
    section = lines[maximum['start_line']-1:maximum['end_line']]
    maximum['profile'] = json.loads(next(s.split('V50_PROFILE ',1)[1] for s in section if 'V50_PROFILE ' in s))
    maximum['warm_rejections'] = [s.split('V48_WARM_SEED ',1)[1] for s in section if 'V48_WARM_SEED selected=0' in s]
    maximum['final_collision_rejections'] = sum('final_spline_rejected status=1' in s for s in section)
    result = json.loads(read('result.json'))
    proof = {'version':'v70','run':root.name,'kind':'diagnostic_only',
        'original_native_version':'v63','original_backend_version':'v59',
        'physics_end_s':result['physics_duration_s'],'physics_steps':result['physics_steps'],
        'rtf':result['realtime_pacing']['actual_rtf'],'finish_request':result.get('finish_request'),
        'final_gate_reason':result['last_backend']['gate']['closed_reason'],
        'heartbeat_stale_reproduced':any(r.get('gate_after')=='heartbeat_stale' for r in by['watchdog_callback']),
        'matching_raw_callbacks':len(raw),'matching_callback_gap_ms':core.distribution(r['gap_ms'] for r in gaps),
        'largest_matching_callback_gaps':sorted(gaps,key=lambda r:r['gap_ms'],reverse=True)[:8],
        'stages':stages,'trace_complete':bool(by.get('trace_end')),'dropped':by['trace_end'][-1]['dropped'],
        'maximum_planning_round':maximum,'source':sources,
        'source_archive':{'path':str(archive),'bytes':archive.stat().st_size,
            'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()},
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'limits':'Fresh observational Mac trial after Docker restart, not a paired speedup or a reproduction of the historical heartbeat fault. No scheduler-level trace of the earlier gaps; DDS ingress versus dispatch is not directly measured.'}
    args.output.write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps({k:proof[k] for k in ('physics_end_s','rtf','heartbeat_stale_reproduced','matching_callback_gap_ms','trace_complete','dropped')},indent=2))
