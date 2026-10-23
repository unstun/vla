"""Frozen Phase A telemetry analysis; standard-library-only, read-only remote execution."""
from bisect import bisect_right
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import socket
import sys
import time
import traceback

EPS = 1e-9
MAIN_BANDS = ('zero', 'below_0p2', 'exact_0p2', 'above_0p2')
FINE_EDGES = (.05, .10, .15, .20, .25, .30, .40)
FINE_BANDS = ('zero',) + tuple('le_' + str(x) for x in FINE_EDGES) + ('above_0.4',)


def main_band(speed):
    if speed == 0:
        return 'zero'
    if speed < .2:
        return 'below_0p2'
    if speed == .2:
        return 'exact_0p2'
    return 'above_0p2'


def fine_band(speed):
    if speed == 0:
        return 'zero'
    return next(('le_' + str(x) for x in FINE_EDGES if speed <= x), 'above_0.4')


def yaw_of(q):
    w, x, y, z = q
    return math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))


def wrap(a):
    return math.atan2(math.sin(a), math.cos(a))


def project(row, number):
    body = row['body_sensor']
    result = dict(t=float(row['physics_time_s']), c=list(row['effective_command']),
                  p=list(body['position'][:2]), v=list(body['linear_world'][:2]),
                  wz=float(body['angular_world'][2]), yaw=yaw_of(body['quaternion']),
                  mode=row['stance_mode'], row=number)
    values = [result['t'], *result['c'], *result['p'], *result['v'], result['wz'], result['yaw']]
    if len(result['c']) != 3 or not all(math.isfinite(x) for x in values):
        raise ValueError('Nonfinite/invalid telemetry at row ' + str(number))
    return result


def pure_sign(row):
    x, y, z = row['c']
    return (1 if z > 0 else -1) if x == y == 0 and abs(z) >= EPS else 0


def empty_band():
    return dict(duration_s=0., weighted_rows=0, command_integral_m=0.,
                body_speed_integral_m=0., axis_integral_m=0., transverse_integral_m=0.)


def add_band(acc, row, dt):
    x, y, _ = row['c']
    speed = math.hypot(x, y)
    body_speed = math.hypot(*row['v'])
    axis = transverse = 0.
    if speed:
        a = row['yaw']
        dx, dy = (math.cos(a) * x - math.sin(a) * y) / speed, (math.sin(a) * x + math.cos(a) * y) / speed
        axis = row['v'][0] * dx + row['v'][1] * dy
        transverse = abs(-row['v'][0] * dy + row['v'][1] * dx)
    acc['duration_s'] += dt
    acc['weighted_rows'] += 1
    acc['command_integral_m'] += speed * dt
    acc['body_speed_integral_m'] += body_speed * dt
    acc['axis_integral_m'] += axis * dt
    acc['transverse_integral_m'] += transverse * dt


def finish_band(acc, total):
    d = acc['duration_s']
    commanded = acc['command_integral_m']
    return dict(acc, share_all=acc['duration_s'] / total if total else None,
                mean_command_mps=commanded / d if d else None,
                mean_body_speed_mps=acc['body_speed_integral_m'] / d if d else None,
                mean_axis_mps=acc['axis_integral_m'] / d if commanded else None,
                mean_transverse_mps=acc['transverse_integral_m'] / d if commanded else None,
                axis_tracking_ratio=acc['axis_integral_m'] / commanded if commanded else None)


def pose_at(rows, times, t):
    i = max(0, min(bisect_right(times, t) - 1, len(rows) - 1))
    r = rows[i]
    if t == r['t'] or i == len(rows) - 1:
        return r['p'], r['yaw'], False
    nxt = rows[i + 1]
    f = (t - r['t']) / (nxt['t'] - r['t'])
    return ([a + f * (b - a) for a, b in zip(r['p'], nxt['p'])],
            r['yaw'] + f * wrap(nxt['yaw'] - r['yaw']), True)


def yaw_intervals(rows, start, end):
    times = [r['t'] for r in rows]
    intervals = []
    i = 0
    while i < len(rows):
        sign = pure_sign(rows[i])
        if not sign:
            i += 1
            continue
        j = i + 1
        while j < len(rows) and pure_sign(rows[j]) == sign:
            j += 1
        a = max(start, rows[i]['t'])
        b = min(end, rows[j]['t'] if j < len(rows) else rows[-1]['t'])
        if b < a or b < start or a > end:
            i = j
            continue
        # A command ending exactly at window start contributed no window exposure.
        if b == a and j < len(rows):
            i = j
            continue
        anchor, angle, interpolated_a = pose_at(rows, times, a)
        endpoint, angle_end, interpolated_b = pose_at(rows, times, b)
        points = [(a, anchor, angle)] + [(r['t'], r['p'], r['yaw']) for r in rows[i:j] if a < r['t'] < b]
        points.append((b, endpoint, angle_end))
        terms = [(r, min(b, rows[k + 1]['t']) - max(a, r['t']))
                 for k in range(i, min(j, len(rows) - 1))
                 for r in [rows[k]] if min(b, rows[k + 1]['t']) > max(a, r['t'])]
        duration = b - a
        mean_cmd = sum(r['c'][2] * dt for r, dt in terms) / duration if duration else None
        cmds = [r['c'][2] for r, _ in terms] or [rows[i]['c'][2]]
        intervals.append(dict(index=len(intervals) + 1, start_s=a, end_s=b, duration_s=duration,
            command_start_row=rows[i]['row'], command_end_row=rows[j - 1]['row'],
            window_start_bracket_row=rows[max(0, bisect_right(times, a) - 1)]['row'],
            displacement_endpoint_row=rows[min(j, len(rows) - 1)]['row'],
            left_censored=rows[i]['t'] < start, right_censored=j == len(rows),
            interpolated_boundary=interpolated_a or interpolated_b,
            mean_command_yaw_radps=mean_cmd, min_command_yaw_radps=min(cmds), max_command_yaw_radps=max(cmds),
            mean_world_z_radps=sum(r['wz'] * dt for r, dt in terms) / duration if duration else None,
            heading_change_rad=sum(wrap(q[2] - p[2]) for p, q in zip(points, points[1:])),
            max_xy_displacement_cm=100 * max(math.dist(p[1], anchor) for p in points),
            net_xy_displacement_cm=100 * math.dist(endpoint, anchor),
            stance_modes=sorted({r['mode'] for r, _ in terms} or {rows[i]['mode']})))
        i = j
    return intervals


def analyze(rows, goal_xy, nav_start):
    if not rows:
        return dict(status='unavailable', reason='no_telemetry')
    times = [r['t'] for r in rows]
    if any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError('Telemetry timestamps are not strictly increasing')
    if nav_start is None or not math.isfinite(nav_start):
        return dict(status='unavailable', reason='no_navigation_start')
    after = next((i for i, r in enumerate(rows) if r['t'] >= nav_start), None)
    if after is None:
        return dict(status='unavailable', reason='no_post_goal_telemetry')
    entry = next((r for r in rows[after:] if math.dist(r['p'], goal_xy) <= .25), None)
    first_zero = next((r for r in rows[after:] if max(map(abs, r['c'])) < EPS), None)
    if entry:
        start, kind = entry['t'], 'goal_circle'
    elif first_zero:
        start, kind = max(rows[after]['t'], first_zero['t'] - 10.), 'fallback_before_first_zero'
    else:
        return dict(status='unavailable', reason='no_circle_entry_or_post_goal_zero')
    end = rows[-1]['t']
    total = end - start
    main = {k: empty_band() for k in MAIN_BANDS}
    fine = {k: empty_band() for k in FINE_BANDS}
    dt_values = []
    for row, nxt in zip(rows, rows[1:]):
        dt = min(end, nxt['t']) - max(start, row['t'])
        if dt <= 0:
            continue
        speed = math.hypot(*row['c'][:2])
        add_band(main[main_band(speed)], row, dt)
        add_band(fine[fine_band(speed)], row, dt)
        dt_values.append(nxt['t'] - row['t'])
    main = {k: finish_band(v, total) for k, v in main.items()}
    fine = {k: finish_band(v, total) for k, v in fine.items()}
    nz = total - main['zero']['duration_s']
    low = main['below_0p2']['duration_s'] + main['exact_0p2']['duration_s']
    high = main['above_0p2']['duration_s'] + main['exact_0p2']['duration_s']
    intervals = yaw_intervals(rows, start, end)
    return dict(status='ok' if total > 0 else 'zero_duration', window_kind=kind, start_s=start, end_s=end,
        duration_s=total, goal_circle_entered=entry is not None, first_post_goal_zero_s=first_zero['t'] if first_zero else None,
        first_circle_entry_row=entry['row'] if entry else None, nav_start_s=nav_start,
        terminal_weighted_rows=len(dt_values), max_sample_dt_s=max(dt_values, default=None),
        sample_gaps_over_0p04_s=sum(dt > .04 for dt in dt_values),
        bands=main, fine_bands=fine, low_inclusive_share=low / total if total else None,
        high_inclusive_share=high / total if total else None,
        nonzero_time_s=nz, low_share_nonzero=low / nz if nz > 0 else None,
        pure_yaw_intervals=intervals, pure_yaw_total_s=sum(x['duration_s'] for x in intervals),
        pure_yaw_longest_s=max((x['duration_s'] for x in intervals), default=0.),
        pure_yaw_max_displacement_cm=max((x['max_xy_displacement_cm'] for x in intervals), default=None))


class Reader:
    def __init__(self, root, expected):
        self.root, self.expected, self.sources = Path(root), expected, {}

    def consume(self, name, telemetry=False):
        p = self.root / name
        before = p.stat()
        digest = hashlib.sha256()
        size = 0
        rows = []
        with p.open('rb') as f:
            if telemetry:
                for n, line in enumerate(f, 1):
                    digest.update(line)
                    size += len(line)
                    rows.append(project(json.loads(line), n))
                value = rows
            else:
                data = f.read()
                digest.update(data)
                size = len(data)
                value = json.loads(data)
        after = p.stat()
        entry = dict(path=str(p), bytes=size, sha256=digest.hexdigest(), stable_read=(
            before.st_ino, before.st_size, before.st_mtime_ns) == (after.st_ino, after.st_size, after.st_mtime_ns))
        expected = self.expected.get(name)
        entry['matches_historical'] = bool(expected and all(entry[k] == expected[k] for k in ('bytes', 'sha256')))
        self.sources[name] = entry
        if not entry['stable_read'] or not entry['matches_historical']:
            raise ValueError('Source identity mismatch: ' + name)
        return value

    def optional(self, name):
        if name not in self.expected:
            return None
        return self.consume(name)


def process_run(slot):
    reader = Reader(slot['root'], slot['expected_sources'])
    started = time.monotonic()
    try:
        scenario = reader.consume('inputs/stair_scenario.json')
        driver = reader.optional('artifacts/stair_driver_result.json')
        goal_event = next((r for r in (driver or {}).get('journal', []) if r.get('event') == 'goal_request'), None)
        nav = goal_event.get('initial_snapshot', {}).get('sim_time_s') if goal_event else None
        nav_source = 'driver_goal_request'
        if nav is None:
            video = reader.optional('video_states.json')
            nav = next((r['physics_time_s'] for r in (video or []) if r.get('goal_sent')), None)
            nav_source = 'video_goal_sent' if nav is not None else 'unavailable'
        rows = reader.consume('telemetry.jsonl', telemetry=True)
        result = dict(analysis=analyze(rows, scenario['goal_ground_xyz_m'][:2], nav),
                      telemetry_rows=len(rows), navigation_start_source=nav_source)
    except Exception as error:
        result = dict(analysis=dict(status='error', reason=repr(error)), traceback=traceback.format_exc())
    return dict(type='run', run=slot['run'], cohort=slot['cohort'], variant=slot['variant'], case_id=slot['case_id'],
                repeat=slot['repeat'], historical_outcome=slot['historical_outcome'], sources=reader.sources,
                wall_seconds=time.monotonic() - started, **result)


def emit(value):
    print(json.dumps(value, separators=(',', ':'), allow_nan=False), flush=True)


def main(request, source_hash, freeze_hash):
    start = time.monotonic()
    emit(dict(type='header', source_sha256=source_hash, frozen_sha256=freeze_hash, host=socket.gethostname(),
              python=platform.python_version(), nice=os.nice(0), loadavg=os.getloadavg(),
              run_count=len(request['runs']), new_physics_steps=0, epoch_s=time.time()))
    statuses = Counter()
    for slot in request['runs']:
        result = process_run(slot)
        statuses[result['analysis']['status']] += 1
        emit(result)
    emit(dict(type='complete', count=sum(statuses.values()), statuses=dict(statuses),
              wall_seconds=time.monotonic() - start, loadavg=os.getloadavg(), new_physics_steps=0))


if __name__ == '__main__':
    main(REQUEST, SOURCE_SHA256, FROZEN_SHA256)
