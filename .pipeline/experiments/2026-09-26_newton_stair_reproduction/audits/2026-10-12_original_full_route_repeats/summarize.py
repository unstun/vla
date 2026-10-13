"""Audit closed captures remotely, preserving interrupted-cohort boundaries."""
from pathlib import Path
import csv
import argparse
import importlib.util
import json
import math
import os
import shutil
import socket
import sys
import time

from run_repeats import ATTEMPTS, BASE, HERE, OUTPUT, TASK, VERSION, identities, save, sha

sys.path.insert(0, str(VERSION))
from analyze_remote import Capture


def load_source(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    global OUTPUT
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch-root', type=Path, default=OUTPUT)
    parser.add_argument('--observed-only', action='store_true')
    args = parser.parse_args()
    OUTPUT = args.batch_root
    assert OUTPUT.parent == TASK / 'results' and OUTPUT.name in (
        'full_route_repeats_20261012', 'full_route_repeats_post_reboot_20261012')
    request = json.loads((OUTPUT / 'request.json').read_text())
    tags = request['tags']
    assert len(tags) == 6 and len(set(tags)) == 6
    progress = json.loads((OUTPUT / 'progress.json').read_text())
    if args.observed_only:
        if OUTPUT.name == 'full_route_repeats_20261012':
            reboot = json.loads((OUTPUT / 'environment_after_reboot.json').read_text())
            assert reboot['old_batch_cmdline'] is None
            assert request['started_unix_s'] < reboot['unix_s'] - float(reboot['uptime'].split()[0])
        else:
            assert progress['state'] == 'interrupted' and progress['active'] is None
            assert progress['error'] == "AssertionError('Other GPU compute tasks active; retain results and inspect')"
            command = Path(f"/proc/{request['pid']}/cmdline")
            assert not command.exists() or b'run_post_reboot.py' not in command.read_bytes()
        tags = [r['tag'] for r in progress['completed']]
        assert tags == request['tags'][:len(tags)] and 0 < len(tags) < 6
    else:
        assert progress['state'] == 'completed' and len(progress['completed']) == 6
    before = json.loads((OUTPUT / 'identities_before.json').read_text())
    actual = identities()
    assert all(before[k] == v for k, v in actual.items())
    if args.observed_only:
        save(OUTPUT / 'identities_at_observed_audit.json', actual)
    else:
        assert before == json.loads((OUTPUT / 'identities_after.json').read_text())
    if 'boot_id' in before:
        assert before['boot_id'] == Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        assert before['execution_runner_sha256'] == sha(HERE / 'run_post_reboot.py')
        assert before['execution_protocol_sha256'] == sha(HERE / 'POST_REBOOT_PLAN.md')
    retention = load_source('original_retention', BASE / 'versions/v51/artifacts.py')
    proof_parser = load_source('original_stop_proofs', BASE / 'audits/2026-10-10_nav2_recovery/analyze_recovery_proofs.py')
    os.environ['PATH'] = str(VERSION) + ':' + os.environ['PATH']
    expected = json.loads((BASE / 'inputs/historical_full_building.json').read_text())
    rows, epochs, latencies, provenance = [], [], [], {}
    returned = OUTPUT / 'return'
    returned.mkdir(exist_ok=False)
    for index, tag in enumerate(tags, 1):
        assert tag.startswith('v147_full_candidate_attempt') and tag[-2:].isdigit()
        trial = TASK / 'trials' / tag
        root = trial / 'runs' / tag
        analysis = TASK / 'results/recording_v147' / tag
        local = returned / tag
        local.mkdir()
        retention.BASE = trial
        retention.AUDIT = trial / 'artifact_audit'
        retention.closed_run(root)
        inventory_path = analysis / 'remote_artifacts.json'
        inventory = json.loads(inventory_path.read_text())
        actual = {str(p.relative_to(trial)) for p in trial.rglob('*') if p.is_file() and not p.is_symlink()}
        assert actual == set(inventory['files']), f'{tag}: file set changed'
        for name, entry in inventory['files'].items():
            path = trial / name
            assert path.stat().st_size == entry['bytes'] and sha(path) == entry['sha256'], path
        assert not (root / '.artifact-active').exists()
        archive = retention.archive_members(root)
        retention.closed_run(root)
        assert archive['status'] == 'completed'
        assert json.loads((root / 'retention_result.json').read_text())['status'] == 'completed'
        capture = Capture(root)
        request = capture.json('episode_request.json')
        scenario = capture.json('inputs/stair_scenario.json')
        for key in ('spawn_ground_xyz_m', 'spawn_yaw_rad', 'goal_ground_xyz_m'):
            assert scenario[key] == expected[key], (tag, key)
        assert request['building_route_profile'] == 'historical_full'
        assert request['integration_version'] == 'v147' and request['scene'] == 'building_full'
        initial = capture.json('initial_state.json')
        states = capture.json('video_states.json')
        assert initial['passed'] and initial['physics_steps'] == 0 and initial['physics_time_s'] == 0
        assert initial['state_sha256_before'] == initial['state_sha256_after']
        assert states[0] == initial['frame'] and states[0]['physics_time_s'] == 0
        assert all(math.isfinite(x) for r in states for x in r['joint_q'][:3])
        initial_xyz = states[0]['joint_q'][:3]
        target_xyz = [a + b for a, b in zip(expected['spawn_ground_xyz_m'], (0, 0, 0.14))]
        assert math.dist(initial_xyz, target_xyz) < 1e-5
        x, y, z, w = states[0]['joint_q'][3:7]
        yaw = math.atan2(2 * (w * z + x * y), 1 - 2 * (y*y + z*z))
        assert abs(math.atan2(math.sin(yaw - expected['spawn_yaw_rad']), math.cos(yaw - expected['spawn_yaw_rad']))) < 1e-5
        max_step = max(math.dist(a['joint_q'][:3], b['joint_q'][:3]) for a, b in zip(states, states[1:]))
        assert all(a['physics_time_s'] < b['physics_time_s'] for a, b in zip(states, states[1:]))
        assert max_step < 0.2, f'{tag}: discontinuous body state'
        driver = capture.json('artifacts/stair_driver_result.json')
        goal = next(r for r in driver['journal'] if r['event'] == 'goal_request')
        assert goal['payload']['target_ground_xyz'] == expected['goal_ground_xyz_m']
        assert math.dist(goal['initial_snapshot']['measured']['base_xyz'][:2], expected['spawn_ground_xyz_m'][:2]) < 0.30
        actual_receipt = trial / 'evidence/build_receipt.json'
        assert sha(actual_receipt) == before['candidate_receipt_sha256']
        metric = json.loads((analysis / 'metrics.json').read_text())
        terminal = metric['terminal']
        assert terminal['run_id'] == tag and metric['state_copyback_verified']
        epochs.append(terminal['observed_run_epoch_ns'])
        route = json.loads((root / 'full_route_verification.json').read_text())
        proof = proof_parser.analyze(tag)
        save(local / 'recovery_proofs.json', proof)
        native_log = capture.read('nav2.log')
        symptoms = {'failed_to_make_progress': native_log.count('Failed to make progress'),
                    'fixed_height_recovery_attempts': native_log.count('fixed_height_recovery_attempt;'),
                    'fixed_height_recovery_rejected': native_log.count('fixed_height_recovery_result accepted=0'),
                    'fixed_height_recovery_accepted': native_log.count('fixed_height_recovery_result accepted=1'),
                    'claim': 'Recorded symptom counts; no replay-based root-cause or server-load attribution.'}
        if terminal['backend_terminal_status'] != 'FINISHED':
            selected = [line for line in native_log.splitlines()
                        if any(marker in line for marker in ('Failed to make progress', 'Aborting handle.',
                                                             'fixed_height_recovery_result', 'native_replan_exhausted'))]
            save(local / 'failure_excerpt.json', {'run': tag, 'symptoms': symptoms,
                                                'terminal_excerpt': selected[-18:],
                                                'source': capture.sources['nav2.log']})
        sample_rows = list(csv.DictReader((analysis / 'latency.csv').open()))
        latency = [float(r['solve_ms']) for r in sample_rows]
        assert len(latency) == metric['planning']['completed']
        assert sum(int(r['success']) for r in sample_rows) == metric['planning']['successful']
        assert sum(t > 60 for t in latency) == metric['planning']['over_60ms']['rounds']
        latencies.extend(latency)
        qualification = (terminal['backend_terminal_status'] == 'FINISHED' and route['passed']
                         and metric['fallen'] is False and metric['state_copyback_verified']
                         and proof['all_replacements_have_recorded_proof'])
        row = {'index': index, 'run': tag, 'terminal': terminal['backend_terminal_status'],
               'terminal_note': terminal['note'], 'original_full_route_gate': route['passed'],
               'accepted': qualification, 'fallen': metric['fallen'],
               'measured_path_m': metric['measured_path_m'], 'native_end_s': metric['actual_physics_end_s'],
               'navigation_wall_s': metric['navigation_wall_duration_s'], 'actual_rtf': metric['actual_rtf'],
               'dropped_physics_steps': metric['dropped_physics_steps'],
               'replacement_owners': proof['replacement_owners'],
               'all_replacement_proofs_passed': proof['all_replacements_have_recorded_proof'],
               'planning': metric['planning'], 'longest_pause_sim_s': metric['longest_pause_sim_s'],
               'native_symptoms': symptoms,
               'pauses_over_1s': metric['pauses_over_1s'], 'mapping': metric['mapping'],
               'final_body_xyz_m': metric['final_body_xyz_m'],
               'final_xy_error_m': math.dist(states[-1]['joint_q'][:2], expected['goal_ground_xyz_m'][:2]),
               'final_height_error_m': abs(states[-1]['joint_q'][2] - expected['goal_ground_xyz_m'][2] - expected['locomotion_reference_height_m']),
               'run_epoch_ns': terminal['observed_run_epoch_ns'],
               'original_initial_body_xyz_m': initial_xyz, 'first_physics_time_s': 0,
               'initial_state_sha256': initial['state_sha256_before'],
               'video_states': len(states), 'max_position_step_m': max_step,
               'remote_file_count': len(inventory['files']),
               'remote_bytes': sum(r['bytes'] for r in inventory['files'].values()),
               'archive_members_verified': len(archive['members']),
               'archive_sha256': archive['archive_sha256'], 'copyback_verified': True, 'retention': 'completed'}
        rows.append(row)
        save(local / 'capture_audit.json', {'passed': True, 'row': row, 'sources': capture.sources,
                                          'inventory_sha256': sha(inventory_path),
                                          'native_receipt_sha256': sha(actual_receipt)})
        for name in ('metrics.json', 'outcome.json', 'remote_artifacts.json', 'latency.csv', 'max_round.json'):
            shutil.copyfile(analysis / name, local / name)
        for name in ('full_route_verification.json', 'raw_capture_manifest.json', 'retention_result.json'):
            shutil.copyfile(root / name, local / name)
        provenance[tag] = {'trial_root': str(trial), 'capture_root': str(root), 'analysis_root': str(analysis),
                           'inventory_sha256': sha(inventory_path), 'archive_sha256': archive['archive_sha256']}
        print(json.dumps({'event': 'verified_capture', 'run': tag, 'accepted': qualification,
                          'files': row['remote_file_count'], 'archive_members': row['archive_members_verified']}), flush=True)
    assert len(set(epochs)) == len(tags), 'Run epochs are not distinct'
    for port in (46200, 46201, 46202, 46203, 8785):
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', port))
    # Reuse the frozen round distribution definition for a pooled descriptive view.
    from analyze_remote import core
    accepted = sum(r['accepted'] for r in rows)
    resource_summary = None
    if (OUTPUT / 'memory_samples.csv').exists():
        with (OUTPUT / 'memory_samples.csv').open() as stream:
            memory_rows = list(csv.DictReader(stream))
        assert memory_rows
        resource_summary = {
            'samples': len(memory_rows),
            'first_unix_s': float(memory_rows[0]['unix_s']),
            'last_unix_s': float(memory_rows[-1]['unix_s']),
            'minimum_available_bytes': min(int(r['available_bytes']) for r in memory_rows),
            'maximum_swap_used_bytes': max(int(r['swap_used_bytes']) for r in memory_rows),
            'maximum_load_1min': max(float(r['load_1min']) for r in memory_rows),
            'claim': 'One-second samples of the post-reboot interval, not evidence about the earlier outage. Other GPU work appeared before the next admission check.'}
    result = {'stage': 'experiment + analysis', 'host': 'gpu5070ti', 'version': 'v147',
              'requested_trials': 6, 'completed_trials': len(rows), 'accepted_trials': accepted,
              'arrived_trials': sum(r['original_full_route_gate'] for r in rows),
              'navigation_failed_trials': sum(r['terminal'] == 'FAILED' for r in rows),
              'passed': len(rows) == 6 and accepted == 6, 'falls': sum(r['fallen'] for r in rows),
              'interrupted_batch_observed_only': args.observed_only,
              'original_progress_state': progress['state'],
              'original_active_tag': progress['active'],
              'requested_tags': json.loads((OUTPUT / 'request.json').read_text())['tags'],
              'resources': resource_summary,
              'unique_run_epochs': len(set(epochs)), 'excluded_pilot': 'v147_full_candidate_attempt01',
              'batch_root': str(OUTPUT), 'request_sha256': sha(OUTPUT / 'request.json'),
              'pre_reboot_attempts_reported_separately': 'boot_id' in before,
              'original_profile_sha256': before['original_profile_sha256'],
              'original_spawn_ground_xyz_m': expected['spawn_ground_xyz_m'],
              'original_goal_ground_xyz_m': expected['goal_ground_xyz_m'],
              'all_capture_integrity_checks_passed': True,
              'all_replacement_proofs_passed': all(r['all_replacement_proofs_passed'] for r in rows),
              'replacement_owners': sum(r['replacement_owners'] for r in rows),
              'pooled_planning': {'completed': len(latencies), 'solve_ms': core.distribution(latencies),
                                  'over_60ms': sum(t > 60 for t in latencies)},
              'rows': rows, 'identities': before, 'remote_provenance': provenance,
              'summarizer_sha256': sha(Path(__file__)), 'verification_unix_s': time.time(),
              'claim': ('Closed outcomes verified from an incomplete six-trial cohort. Preserve all outcomes, original progress and unstarted or partial attempts separately; no completed-cohort claim.' if args.observed_only else
                        'Six newly initialized episodes in one fixed original Building scene. All six outcomes counted; pilot excluded. No population reliability, random-seed coverage,30Hz or Jetson claim.')}
    save(OUTPUT / 'RESULT.json', result)
    save(returned / 'RESULT.json', result)
    for name in ('request.json', 'progress.json', 'identities_before.json', 'identities_after.json', 'resources_after.json'):
        if (OUTPUT / name).exists():
            shutil.copyfile(OUTPUT / name, returned / name)
    for name in ('environment_after_reboot.json', 'previous_boot_memory_inspection.json',
                 'earlier_boot_memory_inspection.json', 'partial_attempt05_inventory.json',
                 'identities_at_observed_audit.json'):
        if args.observed_only and (OUTPUT / name).exists():
            shutil.copyfile(OUTPUT / name, returned / name)
    for tag in tags:
        name = f'{tag}_preflight.json'
        shutil.copyfile(OUTPUT / name, returned / name)
    if (OUTPUT / 'memory_samples.csv').exists():
        shutil.copyfile(OUTPUT / 'memory_samples.csv', returned / 'memory_samples.csv')
    manifests = {str(p.relative_to(returned)): {'bytes': p.stat().st_size, 'sha256': sha(p)}
                 for p in sorted(returned.rglob('*')) if p.is_file()}
    byte_count = sum(row['bytes'] for row in manifests.values())
    assert byte_count < 5 * 1024**2, f'Local return budget exceeded: {byte_count}'
    save(OUTPUT / 'return_manifest.json', {'root': str(returned), 'files': manifests,
                                         'total_bytes': byte_count, 'file_count': len(manifests)})
    print(json.dumps({'event': 'complete', 'passed': result['passed'], 'accepted': accepted,
                      'trials': len(rows), 'return_bytes': byte_count, 'return_files': len(manifests)}), flush=True)


if __name__ == '__main__':
    main()
