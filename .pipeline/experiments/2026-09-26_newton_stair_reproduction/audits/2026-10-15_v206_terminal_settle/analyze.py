"""Read captured control states and replay stance decisions; never step physics."""
from pathlib import Path
import argparse
import collections
import csv
import hashlib
import io
import json
import math
import tarfile
import types
import zipfile

import numpy as np


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Capture:
    def __init__(self, path):
        self.path = Path(path)
        self.receipts = {}
        self.tar = tarfile.open(path) if self.path.suffix == '.tar' else None
        self.prefix = self.tar.getnames()[0].split('/')[0] if self.tar else ''
        self.archive = None
        self.manifest = json.loads(self.direct('raw_capture_manifest.json'))

    def direct(self, name):
        if self.tar:
            return self.tar.extractfile(self.prefix + '/' + name).read()
        return (self.path / name).read_bytes()

    def read(self, name):
        try:
            data = self.direct(name)
        except (KeyError, FileNotFoundError):
            if self.archive is None:
                self.archive = zipfile.ZipFile(io.BytesIO(self.direct('raw_capture.zip')))
            data = self.archive.read(name)
            item = self.manifest['members'][name]
            assert len(data) == item['bytes'] and sha(data) == item['sha256'], name
        self.receipts[name] = {'bytes': len(data), 'sha256': sha(data)}
        return data

    def json(self, name):
        return json.loads(self.read(name))

    def rows(self, name):
        return [json.loads(line) for line in self.read(name).splitlines() if line]


def module(source):
    result = types.ModuleType('captured_hold')
    exec(compile(source, 'executed_stance_hold.py', 'exec'), result.__dict__)
    return result


def inputs(mod, previous, current):
    # Newton's state arrays are float32. Preserve its norm rounding.
    qd = np.array(previous['joint_qd'], dtype=np.float32)
    obs = current['observation']
    q0 = np.tile([0., -.8, 1.6], 4)
    return mod.HoldInput(
        now_s=previous['physics_time_s'], command=current['effective_command'],
        joint_pos=np.array(obs[9:21]) + q0,
        joint_vel=np.array(obs[21:33]) / .05,
        policy_target=current['target'], applied_target=previous['target'],
        applied_kp=previous['motor_kp'], applied_kd=previous['motor_kd'],
        linear_speed=float(np.linalg.norm(qd[:3])),
        angular_speed=float(np.linalg.norm(qd[3:6])),
        tilt_deg=float(np.degrees(np.arccos(np.clip(previous['base_up_z'], -1, 1)))),
        foot_forces=current['foot_forces_n'])


def basic_failure(mod, x):
    if max(abs(v) for v in x.command) > mod.COMMAND_DEADBAND:
        return 'new_command'
    if x.linear_speed > mod.SETTLE_LINEAR_SPEED_MAX:
        return 'linear_speed'
    if x.angular_speed > mod.SETTLE_ANGULAR_SPEED_MAX:
        return 'angular_speed'
    if x.tilt_deg > mod.TILT_MAX_DEG:
        return 'tilt'
    if min(x.foot_forces) < mod.ENTRY_FOOT_FORCE_N:
        return 'four_contact'
    return 'pass'


def run_replay(source, pairs, bypass_balance=False):
    mod = module(source)
    if bypass_balance:
        mod.BALANCE_LOW, mod.BALANCE_HIGH = 0., 1.
    hold = mod.StanceHold('auto', entry_kd='xfade1s')
    trace, windows, mismatches = [], [], []
    first_transition = None
    for previous, current in pairs:
        x = inputs(mod, previous, current)
        before_blocks = hold.counters['support_balance_blocks']
        window_start = hold._settle_started
        out = hold.update(x)
        if out.mode == 'STAND_TRANSITION' and first_transition is None:
            first_transition = x.now_s
        forces = np.array(x.foot_forces)
        shares = (forces[0] + forces[[1, 2, 3]]) / forces.sum()
        blocked = hold.counters['support_balance_blocks'] > before_blocks
        if blocked:
            means = hold._settle_split_sum / hold._settle_split_count
            windows.append(dict(start_s=window_start, end_s=x.now_s,
                                samples=hold._settle_split_count,
                                shares=means.tolist(),
                                rejected=[name for name, value in zip(['front', 'left', 'diagonal'], means)
                                          if value < mod.BALANCE_LOW or value > mod.BALANCE_HIGH]))
        row = dict(input_s=x.now_s, telemetry_s=current['physics_time_s'],
                   command=list(x.command), requested=current['requested_command'],
                   stale=current['command_stale'], transport_reason=current['command_reason'],
                   linear_speed=x.linear_speed, angular_speed=x.angular_speed,
                   tilt_deg=x.tilt_deg, foot_forces=forces.tolist(), shares=shares.tolist(),
                   basic_gate=basic_failure(mod, x), block=blocked,
                   mode=out.mode, reason=out.reason, progress=out.progress,
                   recorded_mode=current['stance_mode'])
        trace.append(row)
        if not bypass_balance and (out.mode != current['stance_mode'] or
                                   out.reason != current['stance_reason'] or
                                   abs(out.progress-current['stance_progress']) > 1e-9):
            mismatches.append(dict(input_s=x.now_s, actual=[out.mode, out.reason, out.progress],
                                   recorded=[current['stance_mode'], current['stance_reason'], current['stance_progress']]))
        # Counterfactual validity ends at the first altered control ownership.
        if bypass_balance and first_transition is not None:
            break
    return dict(trace=trace, windows=windows, mismatches=mismatches,
                counters=hold.counters, first_transition_s=first_transition,
                final_mode=hold.mode, final_reason=hold.reason)


def stats(trace):
    result = dict(samples=len(trace), start_s=trace[0]['input_s'], end_s=trace[-1]['input_s'])
    for key in ['linear_speed', 'angular_speed', 'tilt_deg', 'foot_forces', 'shares']:
        data = np.array([row[key] for row in trace])
        result[key] = dict(min=np.min(data, axis=0).tolist(), mean=np.mean(data, axis=0).tolist(),
                           max=np.max(data, axis=0).tolist())
    result['basic_gate_counts'] = dict(collections.Counter(row['basic_gate'] for row in trace))
    result['transport_reason_counts'] = dict(collections.Counter(row['transport_reason'] for row in trace))
    result['nonzero_command_samples'] = sum(max(abs(v) for v in r['command']) > 1e-3 for r in trace)
    result['stale_samples'] = sum(r['stale'] for r in trace)
    return result


def analyze(capture, name, output):
    source = capture.read('executed_stance_hold.py')
    stance = capture.json('stance_status.json')
    rows = capture.rows('telemetry.jsonl')
    assert all(b['physics_steps']-a['physics_steps'] == 20 for a,b in zip(rows, rows[1:]))
    start = [r['t_s'] for r in stance['hold']['transitions']
             if r['from'] == 'RL' and r['to'] == 'STAND_SETTLING'][-1]
    pairs = [(a,b) for a,b in zip(rows, rows[1:]) if a['physics_time_s'] >= start-1e-9]
    assert abs(pairs[0][0]['physics_time_s']-start) < 1e-9
    replays = [run_replay(source, pairs), run_replay(source, pairs)]
    assert replays[0] == replays[1], 'Nondeterministic decision replay'
    replay = replays[0]
    assert not replay['mismatches'], replay['mismatches'][:3]
    probe = run_replay(source, pairs, bypass_balance=True)
    active = [r for r in replay['trace'] if r['transport_reason']=='active']
    clock = [r for r in capture.rows('clock_samples.jsonl')
             if r.get('accepted') and r.get('samples', 0) >= 500]
    remote_s = [r['remote']/1e9 for r in clock]
    offsets_s = [r['filtered_offset_ns']/1e9 for r in clock]
    host_s = [r['realtime_pacing']['wall_anchor_monotonic_s'] +
              r['realtime_pacing']['wall_elapsed_s'] for r in rows]
    physical_s = [r['physics_time_s'] for r in rows]
    def remote_to_sim(t):
        host_t = t + float(np.interp(t, remote_s, offsets_s))
        return float(np.interp(host_t, host_s, physical_s))
    backend = capture.rows('backend_states.jsonl')[-1]['data']
    terminal_event = backend['terminal_results'][-1]
    terminal_event_s = remote_to_sim(terminal_event['monotonic_ns']/1e9)
    before_terminal = [r for r in active if r['input_s'] < terminal_event_s]
    windows_before_terminal = [r for r in replay['windows'] if r['end_s'] < terminal_event_s]
    late = [r for r in before_terminal if r['input_s'] >= before_terminal[-1]['input_s']-5]
    summary = dict(run=name, capture_path=str(capture.path), total_control_rows=len(rows),
                   terminal_replay_samples=len(pairs), replay_repeats=2,
                   mode_reason_progress_mismatches=0, terminal_start_s=start,
                   counters=replay['counters'], first_transition_s=replay['first_transition_s'],
                   final_mode=replay['final_mode'], final_reason=replay['final_reason'],
                   support_windows=replay['windows'], active_terminal=stats(active), final_five_seconds=stats(late),
                   terminal_event=terminal_event, terminal_event_sim_s=terminal_event_s,
                   pre_terminal_event=stats(before_terminal),
                   support_blocks_before_terminal_event=len(windows_before_terminal),
                   zero_to_terminal_event_s=terminal_event_s-start,
                   first_basic_gate_pass_s=next(r['input_s'] for r in active if r['basic_gate']=='pass'),
                   underloaded_foot_samples={leg:sum(r['foot_forces'][i]<10. for r in before_terminal)
                                             for i,leg in enumerate(['FL','FR','HL','HR'])},
                   balance_only_bypass_first_transition_s=probe['first_transition_s'],
                   counterfactual_boundary='Decision probe only; stops at first changed ownership. No physics or PD stability claim.',
                   original_stance_status=stance,
                   source_hashes={n:sha(capture.read(n)) for n in ['executed_stance_hold.py','executed_newton_stance.py','executed_lite3_newton.py']})
    summary['near_terminal_commands'] = [
        {k:r[k] for k in ['physics_time_s','effective_command','command_stale','command_reason','stance_mode','stance_reason']}
        for r in rows if start-1 <= r['physics_time_s'] <= start+.3]
    commands = capture.rows('command_frequencies.jsonl')
    summary['terminal_ros_commands'] = [dict(r, mapped_sim_s=remote_to_sim(r['wall_monotonic_s']))
        for r in commands if r['topic']=='/quad_0/cmd_vel' and
        start-1 <= remote_to_sim(r['wall_monotonic_s']) <= start+.3]
    log = capture.read('nav2.log').decode(errors='replace')
    summary['terminal_log_lines'] = [l for l in log.splitlines() if any(k in l.lower() for k in
                                        ['terminal_settle_timeout','goal succeeded','goal reached','nav2_failed'])][-30:]
    summary['sources'] = capture.receipts
    (output/(name+'.json')).write_text(json.dumps(summary, indent=2)+'\n')
    with (output/(name+'.csv')).open('w') as f:
        writer = csv.DictWriter(f, fieldnames=list(replay['trace'][0]))
        writer.writeheader(); writer.writerows(replay['trace'])
    print(json.dumps({k:summary[k] for k in ['run','terminal_start_s','terminal_replay_samples','mode_reason_progress_mismatches',
                                           'counters','first_transition_s','balance_only_bypass_first_transition_s','final_five_seconds','source_hashes','terminal_log_lines',
                                           'terminal_event_sim_s','zero_to_terminal_event_s','support_blocks_before_terminal_event']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--capture', required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    analyze(Capture(args.capture), args.name, args.output)
