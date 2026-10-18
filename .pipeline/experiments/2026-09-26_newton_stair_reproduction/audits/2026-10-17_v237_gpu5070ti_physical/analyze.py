"""Evaluate one closed 40901 capture with original route and measured-PD gates."""
from pathlib import Path
import hashlib
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
VERSIONS = BASE / 'versions'
PREFIX = Path('/data/sun/vla_mppi_20261009')
RUN = 'v237_linux_full_attempt01'
TASK = PREFIX / 'trials' / RUN
RAW = TASK / 'runs' / RUN
OUT = HERE / 'results'
sys.path.insert(0, str(VERSIONS / 'v196'))
from analyze_remote import Capture


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 2**20), b''):
            digest.update(block)
    return digest.hexdigest()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def partial(capture, route, analyzed):
    """Derive diagnostic timing from recorded events; preserve missing terminal files."""
    import csv
    import numpy as np
    from analyze_remote import core
    rows = capture.json('video_states.json')
    telemetry = capture.rows('telemetry.jsonl')
    sensor = capture.rows('sensor.jsonl')
    log = capture.read('run.log')
    reason = next((line for line in reversed(log.splitlines()) if line.startswith(('RuntimeError:', 'TimeoutError:', 'ValueError:'))), 'Physical recorder failed; inspect original run.log')
    process = capture.json('process.json')
    assert process['exit_code'] != 0
    end = rows[-1]['physics_time_s']
    goal_sent = any(r.get('goal_sent') for r in rows)
    pace = capture.json('realtime_pacing.json')
    finish_path = RAW / 'artifacts/external_episode/finish_request.json'
    finish = json.loads(finish_path.read_text()) if finish_path.exists() else None
    outcome = dict(run=RUN, host='gpu5070ti', navigation_source='v232', execution_package='v237',
        host_binding='v233', locomotion='v216', overall_result='FAILED', full_route_gate_passed=False,
        terminal_status='RECORDER_FAILED', recorded_backend_terminal_status=finish.get('backend_terminal_status') if finish else None,
        fallen=None, physics_duration_s=end, physics_steps=None, raw_root=str(RAW),
        result_json_present=False, finish_request_present=bool(finish), goal_sent=goal_sent,
        critical_failure_receipt=None, process_failure=dict(present=False, display_marker_physics_s=None),
        failure_reason=reason, process_exit_code=process['exit_code'], process_wall_s=process['wall_seconds'],
        recorded_states=len(rows), sensor_frames=len(sensor), analysis_returncode=analyzed.returncode,
        claim='One physical attempt failed before final recorder result. Report any original finish request; no route/terminal acceptance.')
    save('outcome.json', outcome)
    class Log:
        def read_text(self):return capture.read('nav2.log')
    _, rounds = core.parse_rounds(Log())
    sync = [r for r in capture.rows('clock_samples.jsonl') if r.get('accepted') and r.get('samples',0)>=500]
    assert sync and len({r['responder'] for r in sync}) == 1
    remote = np.array([r['remote']/1e9 for r in sync])
    offset = np.array([r['filtered_offset_ns']/1e9 for r in sync])
    begin = pace['wall_anchor_monotonic_s']
    selected = []
    for row in rounds:
        host = row['start_wall_s'] + float(np.interp(row['start_wall_s'],remote,offset))
        if begin <= host <= begin+pace['wall_elapsed_s']:
            selected.append(dict(wall_s_host=host,solve_ms=row['wall_s']*1000,success=int(row['success']),ros_s=row['ros_s']))
    assert selected
    metrics = dict(diagnostic_only=True, full_qualification=False, actual_rtf=pace['actual_rtf'], terminal=None,
        frequency_definition='Completed original nominal_replan rounds in recorded navigation wall interval. Diagnostic prefix only; absent completion/result is not synthesized.',
        planning=dict(completed=len(selected),successful=sum(r['success'] for r in selected),
            successful_wall_hz=sum(r['success'] for r in selected)/pace['wall_elapsed_s'],
            solve_ms=core.distribution([r['solve_ms'] for r in selected])),
        actual_physics_end_s=end, failure_reason=reason)
    save('metrics.json', metrics)
    with (OUT/'latency.csv').open('w') as stream:
        writer=csv.DictWriter(stream,fieldnames=['wall_s_host','solve_ms','success','ros_s']);writer.writeheader();writer.writerows(selected)
    comparison=json.loads((HERE/'baseline_comparison.json').read_text())
    old=load(BASE/'audits/2026-10-17_v232_physical_comparison/postprocess.py','v237_partial_summary');old.HERE=HERE
    comparison['v237']=old.summarize(RAW);save('comparison.json',comparison)
    receipts=OUT/'execution_receipts'
    for name in ('process.json','shared_state.json','episode_request.json','initial_state.json','realtime_pacing.json',
                 'sensor_warmup.json','factory_handoff.json','stance_status.json','v232_runtime_binding.json',
                 'locomotion_activation.json','backend_latest.json','retention_result.json'):
        (receipts/name).write_text(capture.read(name))
    if finish:
        (receipts/'artifacts__external_episode__finish_request.json').write_text(finish_path.read_text())
    for name in ('execution.json','execution_request.json','graph_preflight.json','native_preflight.json','resource_admission.json','source_gate_before.json'):
        shutil.copyfile(VERSIONS/'v237'/name,receipts/name)
    save('actual_profile_equivalence.json',load(VERSIONS/'v233/verify_profile.py','v237_partial_profile').verify(RAW))
    save('post_run_source_parity.json',load(VERSIONS/'v237/launch.py','v237_partial_source').verify_sources())
    host=load(HERE/'host_inventory.py','v237_partial_host').snapshot(PREFIX)
    before=json.loads((PREFIX/'evidence/v237_host_before.json').read_text())
    host['prior_peer_continuity']={pid:('same_process' if host['peers'].get(pid,{}).get('start_ticks')==row['start_ticks'] else 'exited_or_replaced') for pid,row in before['peers'].items()}
    host['peer_mutations_by_this_task']=[];save('host_after.json',host)
    print(json.dumps(outcome,indent=2),flush=True)


def main():
    OUT.mkdir(exist_ok=True)
    receipts = OUT / 'execution_receipts'
    receipts.mkdir(exist_ok=True)
    env = dict(os.environ, PYTHONPATH=str(VERSIONS / 'v196') + ':' + os.environ.get('PYTHONPATH', ''))
    with (OUT / 'analysis.log').open('w') as log:
        analyzed = subprocess.run([sys.executable, str(VERSIONS / 'v196/analyze_remote.py'),
            '--run-root', str(RAW), '--output', str(OUT), '--metrics-only'],
            env=env, stdout=log, stderr=subprocess.STDOUT)
    save('analysis_status.json', dict(returncode=analyzed.returncode,
        analyzer_sha256=sha(VERSIONS / 'v196/analyze_remote.py')))
    with (OUT / 'full_route_gate.log').open('w') as log:
        gate = subprocess.run([sys.executable, str(HERE / 'verify_full_route.py'),
            '--run-root', str(RAW)], env=env, stdout=log, stderr=subprocess.STDOUT)
    route = json.loads((RAW / 'full_route_verification.json').read_text())
    save('full_route_verification.json', route)
    capture = Capture(RAW)
    scan_rows = capture.rows('scan_timing.jsonl')
    assert scan_rows and all(r['period_s'] == .1 for r in scan_rows)
    finished = [r for r in scan_rows if 'total_s' in r]
    save('scanner_timing_summary.json', dict(jobs=len(scan_rows), completed=len(finished),
        period_s=.1, maximum_total_ms=max(r['total_s'] for r in finished)*1000,
        mean_total_ms=sum(r['total_s'] for r in finished)/len(finished)*1000,
        deadline_failures=sum(r.get('deadline_failed',False) for r in scan_rows),
        early_checks_resolved=sum(r.get('wall_at_check_s',1)<.1 and r.get('waited_wall_s',0)>.001 for r in scan_rows),
        maximum_runnable_wait_ms=max(r.get('runnable_wait_s',0) for r in finished)*1000,
        worst_jobs=sorted(finished,key=lambda r:r['total_s'],reverse=True)[:10]))
    if not (RAW / 'result.json').exists():
        partial(capture, route, analyzed)
        return
    actual = capture.json('result.json')
    terminal = (actual.get('finish_request') or {}).get('backend_terminal_status')
    try:
        failure = capture.json('native_process_failure.json')
    except (FileNotFoundError, KeyError):
        failure = None
    verified = 0
    manifest_path = RAW / 'raw_capture_manifest.json'
    archive_path = RAW / 'raw_capture.zip'
    if manifest_path.exists() and archive_path.exists():
        manifest = json.loads(manifest_path.read_text())
        with zipfile.ZipFile(archive_path) as archive:
            for name, record in manifest['members'].items():
                data = archive.read(name)
                assert len(data) == record['bytes'] and hashlib.sha256(data).hexdigest() == record['sha256'], name
                verified += 1
    outcome = dict(run=RUN, host='gpu5070ti', navigation_source='v232', execution_package='v237',
        host_binding='v233', locomotion='v216', overall_result='PASSED' if route['passed'] else 'FAILED',
        full_route_gate_passed=route['passed'], terminal_status=terminal or ('PHYSICAL_FALL' if actual.get('fallen') else 'BOUNDED_END'),
        recorded_backend_terminal_status=terminal, fallen=actual.get('fallen', False),
        physics_duration_s=actual['physics_duration_s'], physics_steps=actual['physics_steps'],
        raw_root=str(RAW), archive_sha256=sha(archive_path) if archive_path.exists() else None,
        archive_bytes=archive_path.stat().st_size if archive_path.exists() else None,
        archive_members_verified=verified, gate_returncode=gate.returncode, analysis_returncode=analyzed.returncode,
        critical_failure_receipt=failure,
        process_failure=dict(present=bool(failure), display_marker_physics_s=None),
        claim='One original-route physical attempt on gpu5070ti. No repeated reliability or cross-host algorithm speedup claim.')
    save('outcome.json', outcome)
    old = load(BASE / 'audits/2026-10-17_v232_physical_comparison/postprocess.py', 'v237_original_summarizer')
    old.HERE = HERE
    comparisons = json.loads((HERE / 'baseline_comparison.json').read_text())
    comparisons['v237'] = old.summarize(RAW)
    save('comparison.json', comparisons)
    for name in ('execution.json', 'execution_request.json', 'graph_preflight.json',
                 'native_preflight.json', 'resource_admission.json', 'source_gate_before.json'):
        shutil.copyfile(VERSIONS / 'v237' / name, receipts / name)
    for name in ('shared_state.json', 'source_gate.json', 'episode_request.json', 'result.json',
                 'initial_state.json', 'nav2_params.yaml', 'nav2_params.scan.yaml', 'planner.yaml',
                 'v232_runtime_binding.json', 'locomotion_activation.json', 'native_commands.json',
                 'backend_latest.json', 'artifacts/stair_driver_result.json',
                 'artifacts/external_episode/finish_request.json', 'native_process_failure.json'):
        try:
            (receipts / name.replace('/', '__')).write_text(capture.read(name))
        except (FileNotFoundError, KeyError):
            pass
    profile = load(VERSIONS / 'v233/verify_profile.py', 'v237_actual_profile').verify(RAW)
    save('actual_profile_equivalence.json', profile)
    parity = load(VERSIONS / 'v237/launch.py', 'v237_postrun_source').verify_sources()
    for name in ('native_graph.py', 'long_route_driver.py'):
        assert hashlib.sha256(capture.read('frozen_v232_' + name).encode()).hexdigest() == sha(VERSIONS / 'v232' / name)
    assert hashlib.sha256(capture.read('executed_long_route_driver_v232.py').encode()).hexdigest() == sha(VERSIONS / 'v232/long_route_driver.py')
    save('post_run_source_parity.json', parity)
    telemetry = capture.rows('telemetry.jsonl')
    end = actual['physics_duration_s']
    tail = [r for r in telemetry if r.get('physics_time_s', r.get('time_s', -1)) >= end - 10]
    save('terminal_pd_samples.json', dict(window_s=[end - 10, end], samples=len(tail),
        stance_modes=sorted({r.get('stance_mode', 'unknown') for r in tail}),
        original_route_gate_passed=route['passed'], claim='Measured terminal acceptance is evaluated by the unchanged original route gate and analyzer.'))
    suffix = []
    for row in reversed(telemetry):
        if row.get('stance_mode') != 'FIXED_STAND':
            break
        suffix.append(row)
    suffix.reverse()
    t = lambda row: row.get('physics_time_s', row.get('time_s'))
    driver = capture.json('artifacts/stair_driver_result.json')
    save('terminal_pd_hold.json', dict(passed=bool(route['passed'] and suffix),
        definition='Consecutive final measured telemetry suffix with stance_mode FIXED_STAND; physics times, no reset.',
        start_s=t(suffix[0]) if suffix else None, end_s=t(suffix[-1]) if suffix else None,
        duration_s=t(suffix[-1]) - t(suffix[0]) if suffix else 0,
        samples=len(suffix), final_stance=telemetry[-1].get('stance_mode'),
        final_command=telemetry[-1].get('command'), driver_final=driver.get('final_snapshot')))
    host = load(HERE / 'host_inventory.py', 'v237_after_inventory').snapshot(PREFIX)
    before = json.loads((PREFIX / 'evidence/v237_host_before.json').read_text())
    host['prior_peer_continuity'] = {pid: ('same_process' if host['peers'].get(pid, {}).get('start_ticks') == row['start_ticks'] else 'exited_or_replaced') for pid, row in before['peers'].items()}
    host['peer_mutations_by_this_task'] = []
    save('host_after.json', host)
    print(json.dumps(outcome, indent=2), flush=True)


if __name__ == '__main__':
    main()
