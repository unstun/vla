"""Recompute v45/v47 solve, rate, retry and measured-motion evidence."""
from pathlib import Path
import hashlib
import json
import math
import re

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def distribution(values):
    if not values:
        return None
    values = sorted(values)
    def percentile(q):
        i = (len(values)-1)*q
        lo = int(i)
        return values[lo] + (values[min(lo+1,len(values)-1)]-values[lo])*(i-lo)
    return dict(count=len(values), mean=sum(values)/len(values), median=percentile(.5),
                p95=percentile(.95), p99=percentile(.99), maximum=values[-1])


def rate(times):
    return (len(times)-1)/(times[-1]-times[0]) if len(times)>1 and times[-1]>times[0] else None


def parse_rounds(path):
    starts, rounds, pending = [], [], None
    for line_number, line in enumerate(path.read_text().splitlines(),1):
        match = re.search(r'nominal_replan frequency_hz=.*start_schedule_s=([\d.]+).*ros_s=([\d.]+) state=(\d+) skipped_slots=(\d+)',line)
        if match:
            pending = dict(start_line=line_number, start_wall_s=float(match[1]), ros_s=float(match[2]),
                state=int(match[3]), skipped_slots=int(match[4]), rebound_attempts=0,
                prefix_proposals=0, fixed_height_attempts=0, first_seed_failed=False,
                hints=0, extensions=0, completed=False)
            starts.append(pending)
        if pending is None:
            continue
        if '[rebo replan]:' in line:
            pending['rebound_attempts'] += 1
        if 'reactive_stair_seed_search_failed' in line and pending['rebound_attempts']==1:
            pending['first_seed_failed'] = True
        if 'reference_prefix_proposal' in line:
            pending['prefix_proposals'] += 1
        if 'fixed_height_recovery_attempt' in line:
            pending['fixed_height_attempts'] += 1
        if 'V47_WINDOW_HINT' in line:
            pending['hints'] += 1
            pending['extensions'] += int('growth=1' in line)
        result = re.search(r'nominal_replan_result success=(\d+) wall_s=([\d.]+).*overrun=(\d+)',line)
        if result:
            pending.update(completed=True, end_line=line_number, success=bool(int(result[1])),
                wall_s=float(result[2]), overrun=bool(int(result[3])))
            rounds.append(pending)
            pending = None
    return starts, rounds


def analyze(run):
    directory = BASE/'runs'/run
    starts, rounds = parse_rounds(directory/'scan.log')
    successful = [r['start_wall_s'] for r in rounds if r['success']]
    command_times = {}
    with (directory/'command_frequencies.jsonl').open() as f:
        for line in f:
            row = json.loads(line)
            command_times.setdefault(row['topic'],[]).append(row['wall_monotonic_s'])
    latest = json.loads((directory/'backend_latest.json').read_text())
    history = latest.get('global_refresh',{}).get('history',[])
    result = json.loads((directory/'result.json').read_text())
    pacing = result.get('realtime_pacing',{})
    start_wall = pacing.get('wall_anchor_monotonic_s',starts[0]['start_wall_s'])
    end_wall = start_wall + pacing.get('wall_elapsed_s',starts[-1]['start_wall_s']-start_wall)
    command_times = {topic:[t for t in times if start_wall<=t<=end_wall] for topic,times in command_times.items()}
    history = [r for r in history if r.get('status')=='published']
    points = []
    with (directory/'sensor.jsonl').open() as f:
        for line in f:
            row = json.loads(line)
            body = row['body_sensor']
            points.append((row['sim_time_s'],body['position'],body.get('linear_world',[0,0,0])))
    distance = sum(math.dist(a[1],b[1]) for a,b in zip(points,points[1:]))
    pauses, pause = [], 0.0
    # Measured speed, simulation duration, only while nominal navigation is active.
    for a,b in zip(points,points[1:]):
        if not starts[0]['ros_s'] <= b[0] <= starts[-1]['ros_s']:
            continue
        dt = b[0]-a[0]
        if 0 < dt < .5 and math.hypot(*b[2][:2]) < .05:
            pause += dt
        elif pause:
            pauses.append(pause)
            pause = 0.0
    if pause:
        pauses.append(pause)
    terminal = result.get('finish_request',{})
    sources = {str((directory/n).relative_to(ROOT)):sha(directory/n) for n in
        ('scan.log','result.json','sensor.jsonl','command_frequencies.jsonl','backend_latest.json')}
    metrics = dict(run=run, source_sha256=sources, nominal_attempt_starts=len(starts),
        completed_rounds=len(rounds), incomplete_starts=len(starts)-len(rounds),
        actual_local_attempt_hz=rate([r['start_wall_s'] for r in starts]),
        actual_successful_round_hz=rate(successful), successful_rounds=len(successful),
        local_solve_ms=distribution([r['wall_s']*1000 for r in rounds]),
        local_overruns=sum(r['overrun'] for r in rounds),
        skipped_slots=sum(r['skipped_slots'] for r in starts),
        first_seed_failures=sum(r['first_seed_failed'] for r in rounds),
        first_seed_failure_fraction=sum(r['first_seed_failed'] for r in rounds)/len(rounds),
        prefix_rounds=sum(r['prefix_proposals']>0 for r in rounds),
        fixed_height_rounds=sum(r['fixed_height_attempts']>0 for r in rounds),
        window_hint_rounds=sum(r['hints']>0 for r in rounds),
        window_extension_rounds=sum(r['extensions']>0 for r in rounds),
        rebound_attempt_distribution=distribution([r['rebound_attempts'] for r in rounds]),
        controller_rates={topic:dict(samples=len(times),hz=rate(times)) for topic,times in command_times.items()},
        global_refresh_samples=len(history), global_refresh_hz=rate([r['started_wall_s'] for r in history]),
        realtime_pacing=result.get('realtime_pacing'),
        physical_duration_s=result.get('physics_duration_s'),
        measured_path_length_m=distance, measured_displacement_m=math.dist(points[0][1],points[-1][1]),
        active_nominal_navigation_sim_s=starts[-1]['ros_s']-starts[0]['ros_s'],
        low_speed_fraction=sum(pauses)/(starts[-1]['ros_s']-starts[0]['ros_s']),
        initial_body_xyz_m=points[0][1], final_body_xyz_m=points[-1][1],
        maximum_body_z_m=max(p[1][2] for p in points),
        pauses_over_1s=[p for p in pauses if p>=1], total_low_speed_duration_s=sum(pauses),
        pause_definition='XY measured speed <0.05 m/s; sensor intervals <0.5 s; nominal navigation interval; simulation seconds',
        terminal_status=terminal.get('backend_terminal_status'), terminal_note=terminal.get('note'),
        terminal_results=latest.get('terminal_results'),
        rate_definitions='Local: nominal attempt-start (N-1)/wall span. Controller: native raw commands within navigation pacing window. Global: published refresh starts in the final bounded history (up to 50 entries), which may omit early samples.',
        current_curve_invalid_events=directory.joinpath('scan.log').read_text().count('remaining_spline_invalid'),
        full_route_accepted=terminal.get('backend_terminal_status')=='FINISHED' and any(r.get('status')=='arrived' for r in latest.get('terminal_results',[])), local_30hz_reached=False)
    metrics['hint_groups'] = {}
    for name, group in [('hinted',[r for r in rounds if r['hints']]),('unhinted',[r for r in rounds if not r['hints']])]:
        metrics['hint_groups'][name] = dict(rounds=len(group),successful_rounds=sum(r['success'] for r in group),first_seed_failures=sum(r['first_seed_failed'] for r in group),solve_ms=distribution([r['wall_s']*1000 for r in group]))
    metrics['local_30hz_reached'] = metrics['actual_local_attempt_hz'] >= 29.9 and metrics['local_overruns']==0
    return metrics, rounds


def main():
    output = HERE/'analysis'
    output.mkdir(exist_ok=True)
    results = {}
    for version,run in [('v45','v45_realtime_preview01'),('v47','v47_realtime_trial01')]:
        metrics, rounds = analyze(run)
        results[version] = metrics
        (output/(version+'_rounds.json')).write_text(json.dumps(rounds,indent=2)+'\n')
    (output/'metrics.json').write_text(json.dumps(results,indent=2)+'\n')
    baseline = results['v45']['actual_local_attempt_hz']
    results['comparison'] = dict(local_attempt_frequency_change_percent=100*(results['v47']['actual_local_attempt_hz']/baseline-1),
        limitation='Same configuration, separate live physics trajectories. This is not a paired replay or causal estimate for identical inputs.')
    (output/'comparison.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps({v:{k:r[k] for k in ('actual_local_attempt_hz','local_solve_ms','first_seed_failure_fraction','measured_path_length_m','terminal_status')} for v,r in results.items() if v!='comparison'},indent=2))


if __name__=='__main__':
    main()
