"""Phase C AC7 analysis over collected lockstep episodes.

    python3 phase_c_analyse.py RUN_DIR [RUN_DIR ...] --out-dir ../analysis

For each run: outcome (termination, model STOP, success, closest approach), falls, clamp saturation, watchdog and
contact, decision cadence, and the command-to-body response lag compared with the decision period (AC7's "does the
0.2 s command-history lag matter"). Writes one top-down plot per run and a JSON summary. Standard library + Pillow.
"""

import argparse
import json
import math
import statistics
from pathlib import Path


def s2_count(decision):
    """System 2 calls in one decision. phase_c_red_box_v1 predates the counter and only has s2_called/looked_down, and
    its decision 1 is under-reported there (see RESULT_PHASE_C.md)."""
    if 's2_calls' in decision:
        return decision['s2_calls']
    return 1 if decision.get('s2_called') or decision.get('looked_down') else 0


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def best_lag_ms(command, response, dt_ms, max_lag_steps=40):
    """Lag (ms) maximising the correlation of response(t + lag) with command(t), on de-meaned series."""
    n = len(command)
    if n < max_lag_steps * 3:
        return None, None
    mc, mr = statistics.mean(command), statistics.mean(response)
    c = [v - mc for v in command]
    r = [v - mr for v in response]
    best = (None, -2.0)
    for lag in range(0, max_lag_steps + 1):
        a, b = c[:n - lag], r[lag:]
        num = sum(x * y for x, y in zip(a, b))
        den = math.sqrt(sum(x * x for x in a) * sum(y * y for y in b)) or 1e-12
        corr = num / den
        if corr > best[1]:
            best = (lag, corr)
    return best[0] * dt_ms, best[1]


def plot(run, steps, decisions, episode, path):
    from PIL import Image, ImageDraw
    xs = [s['xyz'][0] for s in steps] + [lm['center'][0] for lm in episode['landmarks']]
    ys = [s['xyz'][1] for s in steps] + [lm['center'][1] for lm in episode['landmarks']]
    x0, x1 = min(xs) - 1.5, max(xs) + 1.5
    y0, y1 = min(ys) - 1.5, max(ys) + 1.5
    scale = min(820 / (x1 - x0), 560 / (y1 - y0))
    width, height = int((x1 - x0) * scale) + 40, int((y1 - y0) * scale) + 60

    def px(x, y):
        return 20 + (x - x0) * scale, 40 + (y1 - y) * scale

    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    for gx in range(math.floor(x0), math.ceil(x1) + 1):
        draw.line([px(gx, y0), px(gx, y1)], fill=(230, 230, 230))
        draw.text(px(gx, y0), '{}m'.format(gx), fill=(130, 130, 130))
    for gy in range(math.floor(y0), math.ceil(y1) + 1):
        draw.line([px(x0, gy), px(x1, gy)], fill=(230, 230, 230))
    colours = {'red_box': (220, 30, 30), 'blue_box': (30, 60, 220), 'green_box': (30, 160, 50)}
    for lm in episode['landmarks']:
        cx, cy = lm['center'][:2]
        hx, hy = lm['size'][0] / 2, lm['size'][1] / 2
        draw.rectangle([px(cx - hx, cy + hy), px(cx + hx, cy - hy)], fill=colours.get(lm['name'], (120, 120, 120)))
        if lm['name'] == episode['target_landmark']:
            r = float(episode['success_radius_m'])
            draw.ellipse([px(cx - r, cy + r), px(cx + r, cy - r)], outline=(0, 0, 0))
    draw.line([px(s['xyz'][0], s['xyz'][1]) for s in steps], fill=(0, 0, 0), width=2)
    for d in decisions:
        ox, oy, _ = d['frame_odom']
        u, v = px(ox, oy)
        s2 = s2_count(d) > 0
        draw.ellipse([u - 3, v - 3, u + 3, v + 3], fill=(230, 120, 0) if s2 else (160, 160, 160))
    end = steps[-1]['xyz']
    draw.text((px(end[0], end[1])[0] + 6, px(end[0], end[1])[1] - 12), 'end', fill=(0, 0, 0))
    draw.text((8, 8), '{}: "{}"  (orange = System 2 cycle; circle = success radius)'.format(
        run, episode['instruction']), fill=(0, 0, 0))
    image.save(path)


def analyse(run_dir, out_dir):
    run_dir = Path(run_dir)
    run = run_dir.name
    isaac = json.loads((run_dir / 'isaac' / 'isaac_episode.json').read_text())
    client = json.loads((run_dir / 'client' / 'client_episode.json').read_text())
    steps = read_jsonl(run_dir / 'isaac' / 'isaac_steps.jsonl')
    decisions = read_jsonl(run_dir / 'client' / 'decisions.jsonl')
    episode = client['episode']
    target = next(lm for lm in episode['landmarks'] if lm['name'] == episode['target_landmark'])
    dt_ms = isaac['policy_dt_ns'] / 1e6

    closest = min(steps, key=lambda s: s['target_distance_m'])
    moving = [s for s in steps if abs(s['applied'][0]) > 0.05 or abs(s['applied'][2]) > 0.05]
    lag_vx_ms, corr_vx = best_lag_ms([s['applied'][0] for s in steps], [s['vel_body'][0] for s in steps], dt_ms)
    lag_wz_ms, corr_wz = best_lag_ms([s['applied'][2] for s in steps], [s['wz_body'] for s in steps], dt_ms)
    s1_periods = [d['ticks'] * 100 for d in decisions if s2_count(d) == 0 and d['discrete_action'] is None]
    s2_periods = [d['ticks'] * 100 for d in decisions if s2_count(d) > 0]
    s2_outputs = [d['llm_output'] for d in decisions if d.get('llm_output')]
    summary = {
        'run': run, 'episode': episode['episode_id'], 'instruction': episode['instruction'],
        'termination_isaac': isaac['termination'], 'termination_client': client['termination'],
        'stopped_by_model': client['stopped_by_model'], 'stop_sim_s': client['stop_sim_s'],
        'success': client['success'], 'sim_seconds': isaac['sim_seconds'],
        'start_distance_m': isaac['landmark_distance_at_start_m'][target['name']],
        'closest_distance_m': closest['target_distance_m'], 'closest_at_sim_s': closest['sim_ns'] / 1e9,
        'final_distance_m': isaac['final_distance_to_target_m'], 'final_pose_source': isaac.get('final_pose_source'),
        'path_length_m': sum(math.hypot(b['xyz'][0] - a['xyz'][0], b['xyz'][1] - a['xyz'][1])
                             for a, b in zip(steps, steps[1:])),
        'fall_or_reset': isaac['termination'] == 'env_done' or any(s['done'] for s in steps),
        'root_height_min_m': min(s['xyz'][2] for s in steps),
        'nonfoot_contact_max_n': isaac['contact_monitor'].get('maximum_nonfoot_force_n'),
        'contact_failure': isaac['contact_monitor'].get('failed'),
        'clamp_policy_steps': isaac.get('clamp_policy_steps', isaac.get('clamp_events')),
        'command_abs_max': client['command_abs_max'],
        'watchdog_events': isaac['watchdog_events'], 'sequence_gaps': isaac['sequence_gaps'],
        'mpc_solve_failures': client.get('mpc_solve_failures'),
        'decisions': client['decisions'], 'system2_cycles': sum(1 for d in decisions if s2_count(d) > 0),
        'look_down_cycles': sum(1 for d in decisions if d['looked_down']),
        'discrete_decisions': client['discrete_decisions'],
        'system2_outputs': s2_outputs,
        'decision_period_ms': {
            's1_median': statistics.median(s1_periods) if s1_periods else None,
            's2_median': statistics.median(s2_periods) if s2_periods else None,
        },
        'latency_s': client['latency_s'],
        'tracking_moving_mean': {
            'applied_vx': statistics.mean(s['applied'][0] for s in moving) if moving else None,
            'body_vx': statistics.mean(s['vel_body'][0] for s in moving) if moving else None,
        },
        'response_lag_ms': {'vx': lag_vx_ms, 'vx_corr': corr_vx, 'wz': lag_wz_ms, 'wz_corr': corr_wz},
        'gpu_device_mib_at_end': isaac.get('gpu_used_mib_at_end'),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    plot(run, steps, decisions, episode, out_dir / '{}_topdown.png'.format(run))
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('runs', nargs='+')
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--summary-name', default='phase_c_summary.json')
    args = parser.parse_args()
    summaries = [analyse(run, args.out_dir) for run in args.runs]
    (args.out_dir / args.summary_name).write_text(json.dumps(summaries, indent=2) + '\n')
    header = '{:22s} {:>7s} {:>5s} {:>6s} {:>6s} {:>6s} {:>6s} {:>5s} {:>4s} {:>5s} {:>4s} {:>8s} {:>8s}'.format(
        'run', 'term', 'stop', 'succ', 'start', 'close', 'final', 'fall', 'clmp', 'wdog', 'S2', 'lag_vx', 'lag_wz')
    print(header)
    for s in summaries:
        print('{:22s} {:>7s} {:>5s} {:>6s} {:6.2f} {:6.2f} {:6.2f} {:>5s} {:4d} {:5d} {:4d} {:>8s} {:>8s}'.format(
            s['run'][-22:], s['termination_isaac'][:7], str(s['stopped_by_model'])[:5], str(s['success'])[:6],
            s['start_distance_m'], s['closest_distance_m'], s['final_distance_m'], str(s['fall_or_reset'])[:5],
            s['clamp_policy_steps'] or 0, s['watchdog_events'], s['system2_cycles'],
            'n/a' if s['response_lag_ms']['vx'] is None else '{:.0f}ms'.format(s['response_lag_ms']['vx']),
            'n/a' if s['response_lag_ms']['wz'] is None else '{:.0f}ms'.format(s['response_lag_ms']['wz'])))


if __name__ == '__main__':
    main()
