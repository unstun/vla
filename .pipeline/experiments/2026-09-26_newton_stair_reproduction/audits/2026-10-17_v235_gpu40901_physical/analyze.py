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
PREFIX = Path('/home/ubuntu/sun/vla_v234_20261017')
RUN = 'v235_linux_full_attempt01'
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
    """Report missing completion evidence without inventing a recorder result."""
    rows = capture.json('video_states.json')
    telemetry = capture.rows('telemetry.jsonl')
    sensor = capture.rows('sensor.jsonl')
    log = capture.read('run.log')
    assert 'Captured scan did not finish before the next sensor period' in log
    process = capture.json('process.json')
    assert process['exit_code'] != 0 and not any(r.get('goal_sent') for r in rows)
    end = rows[-1]['physics_time_s']
    pace = capture.json('realtime_pacing.json')
    outcome = dict(run=RUN, host='gpu40901', navigation_source='v232', execution_package='v235',
        migration='v234', locomotion='v216', overall_result='FAILED', full_route_gate_passed=False,
        terminal_status='RECORDER_EXCEPTION_BEFORE_NAVIGATION_GOAL', recorded_backend_terminal_status=None,
        fallen=None, physics_duration_s=end, physics_steps=None, raw_root=str(RAW),
        result_json_present=False, finish_request_present=False, goal_sent=False,
        critical_failure_receipt=None, process_failure=dict(present=False, display_marker_physics_s=None),
        failure_reason='Captured scan did not finish before the next sensor period',
        process_exit_code=process['exit_code'], process_wall_s=process['wall_seconds'],
        recorded_states=len(rows), sensor_frames=len(sensor), analysis_returncode=analyzed.returncode,
        archive_sha256=None, archive_bytes=None, archive_members_verified=0,
        claim='One physical attempt stopped during startup/early sensing; no navigation goal, no stair/full-route/terminal-PD acceptance. Original result and finish remain absent.')
    save('outcome.json', outcome)
    # Display scalars describe this pre-navigation recording, with no solve-rate claim.
    metrics = dict(diagnostic_only=True, full_qualification=False,
        actual_rtf=pace['actual_rtf'], terminal=None,
        frequency_definition='No navigation goal or planning rounds; zero completed solves, not a measured planner throughput.',
        planning=dict(attempts=0, completed=0, successful=0, successful_wall_hz=0., solve_ms=dict(maximum=0.)),
        actual_physics_end_s=end, failure_reason=outcome['failure_reason'])
    save('metrics.json', metrics)
    (OUT / 'latency.csv').write_text('wall_s_host,solve_ms\n')
    comparison = json.loads((HERE / 'baseline_comparison.json').read_text())
    old = load(BASE / 'audits/2026-10-17_v232_physical_comparison/postprocess.py', 'v235_partial_summary')
    old.HERE = HERE
    comparison['v235'] = old.summarize(RAW)
    save('comparison.json', comparison)
    times = [r['sensor']['wall_s'] for r in sensor]
    save('sensor_failure_context.json', dict(passed=False, warmup=capture.json('sensor_warmup.json'),
        completed_scan_wall_s=dict(minimum=min(times), maximum=max(times), mean=sum(times)/len(times)),
        pending_failed_scan_wall_s=None,
        last_recorded_physics_s=end, navigation_goal_sent=False,
        configured_physics_cpu_set=[22, 23], original_sensor_period_s=.1,
        conclusion='Original scanner deadline guard fired. Exact pending-scan latency was not recorded; CPU load/affinity causality requires separate profiling.'))
    receipts = OUT / 'execution_receipts'
    for name in ('process.json', 'shared_state.json', 'episode_request.json', 'initial_state.json',
                 'realtime_pacing.json', 'sensor_warmup.json', 'factory_handoff.json', 'stance_status.json',
                 'v232_runtime_binding.json', 'locomotion_activation.json', 'backend_latest.json', 'retention_result.json'):
        (receipts / name).write_text(capture.read(name))
    for name in ('execution.json', 'execution_request.json', 'graph_preflight.json', 'native_preflight.json',
                 'resource_admission.json', 'source_gate_before.json'):
        shutil.copyfile(VERSIONS / 'v235' / name, receipts / name)
    save('actual_profile_equivalence.json', load(VERSIONS / 'v234/verify_profile.py', 'v235_partial_profile').verify(RAW))
    save('post_run_source_parity.json', load(VERSIONS / 'v235/launch.py', 'v235_partial_source').verify_sources())
    host = load(VERSIONS / 'v234/host_inventory.py', 'v235_partial_host').snapshot(PREFIX)
    before = json.loads((VERSIONS / 'v235/resource_admission.json').read_text())
    host['prior_peer_continuity'] = {pid: ('same_process' if host['peers'].get(pid, {}).get('start_ticks') == row['start_ticks'] else 'exited_or_replaced') for pid, row in before['peers'].items()}
    host['peer_mutations_by_this_task'] = []
    save('host_after.json', host)
    print(json.dumps(outcome, indent=2), flush=True)


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
        gate = subprocess.run([sys.executable, str(VERSIONS / 'v235/verify_full_route.py'),
            '--run-root', str(RAW)], env=env, stdout=log, stderr=subprocess.STDOUT)
    route = json.loads((RAW / 'full_route_verification.json').read_text())
    save('full_route_verification.json', route)
    capture = Capture(RAW)
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
    outcome = dict(run=RUN, host='gpu40901', navigation_source='v232', execution_package='v235',
        migration='v234', locomotion='v216', overall_result='PASSED' if route['passed'] else 'FAILED',
        full_route_gate_passed=route['passed'], terminal_status=terminal or ('PHYSICAL_FALL' if actual.get('fallen') else 'BOUNDED_END'),
        recorded_backend_terminal_status=terminal, fallen=actual.get('fallen', False),
        physics_duration_s=actual['physics_duration_s'], physics_steps=actual['physics_steps'],
        raw_root=str(RAW), archive_sha256=sha(archive_path) if archive_path.exists() else None,
        archive_bytes=archive_path.stat().st_size if archive_path.exists() else None,
        archive_members_verified=verified, gate_returncode=gate.returncode, analysis_returncode=analyzed.returncode,
        critical_failure_receipt=failure,
        process_failure=dict(present=bool(failure), display_marker_physics_s=None),
        claim='One original-route physical attempt on40901. No repeated reliability or cross-host algorithm speedup claim.')
    save('outcome.json', outcome)
    old = load(BASE / 'audits/2026-10-17_v232_physical_comparison/postprocess.py', 'v235_original_summarizer')
    old.HERE = HERE
    comparisons = json.loads((HERE / 'baseline_comparison.json').read_text())
    comparisons['v235'] = old.summarize(RAW)
    save('comparison.json', comparisons)
    for name in ('execution.json', 'execution_request.json', 'graph_preflight.json',
                 'native_preflight.json', 'resource_admission.json', 'source_gate_before.json'):
        shutil.copyfile(VERSIONS / 'v235' / name, receipts / name)
    for name in ('shared_state.json', 'source_gate.json', 'episode_request.json', 'result.json',
                 'initial_state.json', 'nav2_params.yaml', 'nav2_params.scan.yaml', 'planner.yaml',
                 'v232_runtime_binding.json', 'locomotion_activation.json', 'native_commands.json',
                 'backend_latest.json', 'artifacts/stair_driver_result.json',
                 'artifacts/external_episode/finish_request.json', 'native_process_failure.json'):
        try:
            (receipts / name.replace('/', '__')).write_text(capture.read(name))
        except (FileNotFoundError, KeyError):
            pass
    profile = load(VERSIONS / 'v234/verify_profile.py', 'v235_actual_profile').verify(RAW)
    save('actual_profile_equivalence.json', profile)
    parity = load(VERSIONS / 'v235/launch.py', 'v235_postrun_source').verify_sources()
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
    host = load(VERSIONS / 'v234/host_inventory.py', 'v235_after_inventory').snapshot(PREFIX)
    before = json.loads((VERSIONS / 'v235/resource_admission.json').read_text())
    host['prior_peer_continuity'] = {pid: ('same_process' if host['peers'].get(pid, {}).get('start_ticks') == row['start_ticks'] else 'exited_or_replaced') for pid, row in before['peers'].items()}
    host['peer_mutations_by_this_task'] = []
    save('host_after.json', host)
    print(json.dumps(outcome, indent=2), flush=True)


if __name__ == '__main__':
    main()
