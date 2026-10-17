"""Causal display of Option B direct Nav2 SCAN splines and PCT paths.

Direct Twist has no trajectory identity: visibility means the latest recorded
non-emergency spline under a fresh command stream, not P2B admission proof.
"""
from pathlib import Path
import csv
import json
import zipfile
import numpy as np
from scipy.interpolate import BSpline

FRESH_COMMAND_S = .15
EPS = 1e-6


def key(data):
    return data['traj_id']


def stamp_s(stamp):
    return stamp['sec'] + stamp['nanosec'] / 1e9


def read_text(root, name):
    path = root / name
    if path.is_file():
        return path.read_text()
    with zipfile.ZipFile(root / 'raw_capture.zip') as archive:
        return archive.read(name).decode()


def sample_spline(data):
    control = np.array([[p['x'], p['y'], p['z']] for p in data['pos_pts']], dtype=float)
    knots = np.array(data['knots'], dtype=float)
    degree = int(data['order'])
    if (degree != 3 or len(control) < 4 or len(knots) != len(control) + degree + 1
            or not np.isfinite(control).all() or not np.isfinite(knots).all()
            or np.any(np.diff(knots) <= 0)):
        raise ValueError('Malformed recorded native spline')
    values = BSpline(knots, control, degree, extrapolate=False)(
        np.linspace(knots[degree], knots[-degree-1], 150))
    if not np.isfinite(values).all():
        raise ValueError('Native spline sampling produced nonfinite points')
    return values.astype(np.float32)


class Selection:
    """Latest direct spline; emergency stop clears it without identity fields."""
    def __init__(self):
        self.curves = {}
        self.active = None
        self.command = None
        self.route = None
        self.message_count = 0

    def consume(self, event):
        data, kind = event['data'], event['event']
        if kind == 'bspline':
            self.message_count += 1
            self.curves[key(data)] = event
            self.active = None if data.get('emergency_stop', False) else event
        elif kind == 'gated_command':
            self.command = event
        elif kind == 'pct_route':
            self.route = event

    def current(self, simulation_s, wall_s):
        if self.active is None or self.command is None:
            return None
        event, command = self.active, self.command
        data = event['data']
        phase = simulation_s - stamp_s(data['start_time'])
        degree = int(data['order'])
        begin, end = data['knots'][degree], data['knots'][-degree-1]
        curve_age = wall_s - event['host_wall_s']
        command_age = wall_s - command['host_wall_s']
        command_sim_age = simulation_s - command['clock_ns'] / 1e9
        # Both recorded clocks must be causal. Bound stale producer messages
        # by their tracking window, and require a recent direct output stream.
        if not (-EPS <= curve_age <= end - begin + FRESH_COMMAND_S
                and -EPS <= command_age <= FRESH_COMMAND_S
                and -EPS <= command_sim_age <= FRESH_COMMAND_S
                and begin - EPS <= phase <= end + FRESH_COMMAND_S):
            return None
        twist = command['data']
        nonzero = max(abs(twist['linear']['x']), abs(twist['linear']['y']),
                      abs(twist['angular']['z'])) > 1e-6
        tracking = begin - EPS <= phase <= end + EPS
        return event if nonzero or tracking else None

    def current_route(self, simulation_s, wall_s):
        if (self.route is None or self.route['host_wall_s'] > wall_s
                or self.route['clock_ns'] / 1e9 > simulation_s + EPS):
            return None
        return self.route


class Overlay:
    def __init__(self, root, latency_csv):
        self.root = Path(root)
        sync = [json.loads(x) for x in read_text(self.root, 'clock_samples.jsonl').splitlines()]
        sync = [x for x in sync if x.get('accepted') and x.get('samples', 0) >= 500]
        if not sync or len({x['responder'] for x in sync}) != 1:
            raise ValueError('Converged original clock mapping required')
        self.remote = np.array([x['remote']/1e9 for x in sync])
        self.offset = np.array([x['filtered_offset_ns']/1e9 for x in sync])
        self.events = []
        for line in read_text(self.root, 'artifacts/reactive_observations.jsonl').splitlines():
            event = json.loads(line)
            if event['event'] not in ('bspline', 'pct_route', 'gated_command'):
                continue
            remote = event['wall_monotonic_ns']/1e9
            event['host_wall_s'] = remote + float(np.interp(remote, self.remote, self.offset))
            self.events.append(event)
        self.events.sort(key=lambda x: x['host_wall_s'])
        self.index = 0
        self.selection = Selection()
        self.points = {}
        self.route_points = None
        self.last_wall = -float('inf')
        with Path(latency_csv).open() as stream:
            self.timings = list(csv.DictReader(stream))
        for row in self.timings:
            row['finish_wall_s'] = float(row['wall_s_host']) + float(row['solve_ms'])/1000
        self.timings.sort(key=lambda x: x['finish_wall_s'])
        self.timing_index = 0
        self.latest_timing = None
        self.records = []
        self.total_splines = sum(x['event'] == 'bspline' for x in self.events)
        if not self.total_splines:
            raise ValueError('No native splines were recorded')

    def frame(self, row):
        record = dict(source_state_index=row['source_state_index'], display_time_s=row['display_time_s'],
                      physics_time_s=row['physics_time_s'], source_wall_s=None,
                      trajectory_id=None, curve_event_wall_s=None, curve_start_s=None,
                      curve_end_s=None, command_event_wall_s=None, command_clock_s=None,
                      route_event_wall_s=None, route_clock_s=None, route_points=0,
                      latest_completed_solve_ms=None, latest_solve_success=None,
                      solve_finish_wall_s=None, sampled_points=0)
        self.route_points = None
        if row.get('timeline_segment') == 'startup sim':
            self.records.append(record)
            return None, record
        wall, sim = row['wall_monotonic_s'], row['physics_time_s']
        if wall < self.last_wall:
            raise ValueError('Noncausal frame order')
        self.last_wall = wall
        while self.index < len(self.events) and self.events[self.index]['host_wall_s'] <= wall:
            self.selection.consume(self.events[self.index])
            self.index += 1
        while self.timing_index < len(self.timings) and self.timings[self.timing_index]['finish_wall_s'] <= wall:
            self.latest_timing = self.timings[self.timing_index]
            self.timing_index += 1
        timing = self.latest_timing
        record.update(source_wall_s=wall,
                      latest_completed_solve_ms=float(timing['solve_ms']) if timing else None,
                      latest_solve_success=bool(int(timing['success'])) if timing else None,
                      solve_finish_wall_s=timing['finish_wall_s'] if timing else None)
        route = self.selection.current_route(sim, wall)
        if route:
            poses = route['data']['poses']
            if poses:
                self.route_points = np.array([[p['pose']['position'][k] for k in ('x', 'y', 'z')]
                                              for p in poses], dtype=np.float32)
                if not np.isfinite(self.route_points).all():
                    raise ValueError('Nonfinite global PCT path')
            record.update(route_event_wall_s=route['host_wall_s'], route_clock_s=route['clock_ns']/1e9,
                          route_points=len(poses))
        event = self.selection.current(sim, wall)
        points = None
        if event:
            data = event['data']
            cache_key = (key(data), event['host_wall_s'])
            if cache_key not in self.points:
                self.points[cache_key] = sample_spline(data)
            points = self.points[cache_key]
            record.update(trajectory_id=key(data), curve_event_wall_s=event['host_wall_s'],
                          curve_start_s=stamp_s(data['start_time']),
                          curve_end_s=stamp_s(data['start_time']) + data['knots'][-int(data['order'])-1],
                          command_event_wall_s=self.selection.command['host_wall_s'],
                          command_clock_s=self.selection.command['clock_ns']/1e9, sampled_points=len(points))
        self.records.append(record)
        return points, record
