#!/usr/bin/env python3
"""Deterministic fixtures for the native SCAN terminal-acceleration A/B suite.

Modes:
  extract        read the display-off and RViz failed-run journals (large, local-only) and write
                 fixtures/recorded_requests.json with verified journal hashes
  generate       write fixtures/suite_cases.json and fixtures/boxes/*.json from the recorded
                 diagnosis cases, recorded_requests.json and planner.yaml (default mode)
  from-journals  turn resubmitted goal requests in any pilot journal into a replay fixture file,
                 derived exactly like the diagnosis failed-resume case (implement.md item C5); the
                 four recorded diagnosis cases are always added as the AC0 validity control

Start derivation (same as scan_replan_diagnosis/inputs/cases.json): the PCT request ground start
plus the run's frozen nominal body height, zero start velocity and acceleration, and the last PCT
route waypoint (already a body-reference point) as the SCAN target.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import sys


HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parent
REPO = EXPERIMENT.parents[2]
FIXTURES = HERE / 'fixtures'
DIAGNOSIS_CASES = EXPERIMENT / 'scan_replan_diagnosis/inputs/cases.json'
DIAGNOSIS_CASES_SHA256 = '16b912dece55cd48f0a57976556ae2edb0794424a3bd2fd58652099604e32dda'
PLANNER_YAML = EXPERIMENT / 'scan_replan_diagnosis/inputs/planner.yaml'
PLANNER_YAML_SHA256 = '851a6eb51b3175365fd5b7e58eeb8beb170259178dcbf1407da422075226d47b'

SUITE_SCHEMA = 'scan_fix_suite_cases_v1'
BOXES_SCHEMA = 'scan_fix_occupied_boxes_v1'
RECORDED_SCHEMA = 'scan_fix_recorded_requests_v1'

FAILED_DISPLAY_RUNS = (
    ('failed_off_resume', 'pointcloud_display/runs/pointcloud_20260916T171400Z_off/returned_artifacts'),
    ('failed_rviz_resume', 'pointcloud_display/runs/pointcloud_20260916T172100Z_rviz/returned_artifacts'),
)
SWEEP_BASE_CASE = 'failed_run_resume'
SWEEP_X_CENTIMETERS = tuple(range(-120, -105))  # -1.20 m .. -1.06 m, 0.01 m steps, 15 poses
FOLLOW_UP_OFFSETS_S = (0.3, 0.6)
MAPS = (
    {'id': 'empty', 'lateral_center_offset_m': None},
    {'id': 'far_box', 'lateral_center_offset_m': 1.0},
    {'id': 'near_box', 'lateral_center_offset_m': 0.3},
)
BOX_HALF_XY_M = 0.15
BOX_Z_RANGE_M = (1.0, 3.0)
DUMP_RUN_LABELS = (
    'failed_run_resume__empty__poly_s0_r0',
    'failed_run_resume__near_box__poly_s0_r0',
    'sweep_x_m1p14__empty__followup_poly_s0_r0',
)
POSITION_SOURCE = 'PCT-request ground pose + frozen nominal body height; not exact SCAN argument capture'
VELOCITY_SOURCE = 'Zeroed stop-to-goal simplification; first resubmit native log also shows zero'
ATTEMPT = re.compile(r'-attempt-(\d+)$')


class FixtureError(RuntimeError):
    pass


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    return sha256_bytes(Path(path).read_bytes())


def rel(path):
    path = Path(path).resolve()
    try:
        return path.relative_to(REPO).as_posix()
    except ValueError:
        return str(path)


def dumps(value):
    return json.dumps(value, indent=2, sort_keys=True) + '\n'


def inits():
    rows = [{'id': 'poly_s0_r%d' % r, 'poly_init': True, 'random_poly': False, 'seed': 0, 'repeat': r}
            for r in range(3)]
    rows += [{'id': 'rand_s%d_r0' % s, 'poly_init': True, 'random_poly': True, 'seed': s, 'repeat': 0}
             for s in range(10)]
    return rows


def sweep_id(centimeters):
    return 'sweep_x_m%dp%02d' % (abs(centimeters) // 100, abs(centimeters) % 100)


def load_planner_geometry(path=PLANNER_YAML, expected_sha256=PLANNER_YAML_SHA256):
    digest = sha256_file(path)
    if expected_sha256 is not None and digest != expected_sha256:
        raise FixtureError('planner.yaml hash mismatch: %s' % digest)
    values = {}
    for line in Path(path).read_text().splitlines():
        match = re.match(r'\s+([A-Za-z_.]+):\s*([^#\s]+)\s*$', line)
        if match:
            values[match.group(1)] = match.group(2)
    try:
        size = [float(values['grid_map.sliding_map_size_' + axis]) for axis in 'xyz']
        ground = float(values['grid_map.ground_height'])
        geometry = {
            'source': rel(path), 'sha256': digest,
            'resolution_m': float(values['grid_map.resolution']),
            'map_origin_m': [-size[0] / 2.0, -size[1] / 2.0, ground],
            'map_size_m': size,
            'double_cylinder_radius_m': float(values['grid_map.double_cylinder_radius']),
            'double_cylinder_offset_m': float(values['grid_map.double_cylinder_offset']),
            'obstacles_inflation_z_up_m': float(values['grid_map.obstacles_inflation_z_up']),
            'obstacles_inflation_z_down_m': float(values['grid_map.obstacles_inflation_z_down']),
            'use_sim_time': values['use_sim_time'] == 'true',
            'map_sliding_en': values['grid_map.map_sliding_en'] == 'true',
            'origin_rule': 'grid_map.cpp:88 origin (-size_x/2, -size_y/2, ground_height); no odometry is fed, so the map never slides',
        }
    except KeyError as error:
        raise FixtureError('planner.yaml lacks ' + str(error))
    return geometry


def load_diagnosis_cases(path=DIAGNOSIS_CASES, expected_sha256=DIAGNOSIS_CASES_SHA256):
    digest = sha256_file(path)
    if expected_sha256 is not None and digest != expected_sha256:
        raise FixtureError('diagnosis cases.json hash mismatch: %s' % digest)
    doc = json.loads(Path(path).read_text())
    if doc.get('schema') != 'scan_minimized_repro_cases_v1' or len(doc.get('cases', [])) != 4:
        raise FixtureError('unexpected diagnosis cases.json content')
    return doc, digest


# ---------------------------------------------------------------------------------------------
# Journal extraction and the stop-pose to case conversion (shared by generate and from-journals).

def extract_plan_requests(journal_path):
    """Return the PCT plan history of a pilot journal, keyed by request id (latest entry wins)."""
    journal_path = Path(journal_path)
    doc = json.loads(journal_path.read_bytes())
    history = {}
    for event in doc.get('events', []):
        state = event.get('state')
        if not isinstance(state, dict) or not isinstance(state.get('pct'), dict):
            continue
        for entry in state['pct'].get('plan_history') or []:
            history[entry['request_id']] = entry
    del doc
    return history


def verified_run_inputs(returned_dir):
    """Hash-check a returned run's pilot journal and read its nominal body height."""
    returned_dir = Path(returned_dir)
    journal = returned_dir / 'pilot_journal.json'
    hashes_path = returned_dir / 'artifact_hashes.json'
    config_path = returned_dir / 'resolved_backend_config.json'
    for path in (journal, hashes_path, config_path):
        if not path.is_file():
            raise FixtureError('missing run input: ' + str(path))
    recorded = json.loads(hashes_path.read_text()).get('pilot_journal.json')
    actual = sha256_file(journal)
    if recorded != actual:
        raise FixtureError('pilot journal hash mismatch for %s: %s != %s' % (journal, actual, recorded))
    config = json.loads(config_path.read_text())
    height = config['resolved_config']['map']['nominal_body_height_m']
    if not isinstance(height, (int, float)) or not math.isfinite(height):
        raise FixtureError('invalid nominal_body_height_m in ' + str(config_path))
    return {
        'journal': journal, 'journal_sha256': actual,
        'artifact_hashes': hashes_path, 'artifact_hashes_sha256': sha256_file(hashes_path),
        'config': config_path, 'config_sha256': sha256_file(config_path),
        'nominal_body_height_m': float(height),
    }


def request_record(entry, inputs, run_id):
    request = entry['request']
    waypoints = entry.get('waypoints_m') or []
    if not entry.get('ok') or not waypoints:
        raise FixtureError('plan %s has no accepted route' % entry.get('request_id'))
    if entry.get('z_semantics') != 'lite3_body_reference_no_display_offset':
        raise FixtureError('unexpected waypoint z semantics for %s' % entry.get('request_id'))
    match = ATTEMPT.search(entry['request_id'])
    return {
        'source_run': run_id,
        'source_request_id': entry['request_id'],
        'goal_id': entry.get('goal_id'),
        'attempt': int(match.group(1)) if match else None,
        'route_id': entry.get('route_id'),
        'start_ground_xyz_m': [float(v) for v in request['start_xyz_m']],
        'requested_target_ground_xyz_m': [float(v) for v in request['target_xyz_m']],
        'route_last_waypoint_m': [float(v) for v in waypoints[-1]],
        'route_waypoint_count': len(waypoints),
        'z_semantics': entry['z_semantics'],
        'nominal_body_height_m': inputs['nominal_body_height_m'],
        'source_artifacts': [
            {'path': rel(inputs['journal']), 'sha256': inputs['journal_sha256'],
             'verified_against': rel(inputs['artifact_hashes'])},
            {'path': rel(inputs['config']), 'sha256': inputs['config_sha256'],
             'field': 'resolved_config.map.nominal_body_height_m'},
        ],
    }


def resume_records_from_run(returned_dir, run_id=None, request_kind='resume'):
    """Resubmitted-goal plan requests (attempt >= 2) of one returned pilot run."""
    inputs = verified_run_inputs(returned_dir)
    run_id = run_id or Path(returned_dir).resolve().parent.name
    records = []
    for request_id, entry in sorted(extract_plan_requests(inputs['journal']).items()):
        match = ATTEMPT.search(request_id)
        is_resume = bool(match) and int(match.group(1)) >= 2
        if request_kind == 'resume' and not is_resume:
            continue
        records.append(request_record(entry, inputs, run_id))
    return records


def case_from_stop_record(record, case_id, group):
    """Convert a recorded stop/resubmission request into a replay start (diagnosis derivation)."""
    ground = record['start_ground_xyz_m']
    height = record['nominal_body_height_m']
    values = list(ground) + list(record['route_last_waypoint_m']) + [height]
    if len(ground) != 3 or len(record['route_last_waypoint_m']) != 3 or not all(
            isinstance(v, (int, float)) and math.isfinite(v) for v in values):
        raise FixtureError('invalid stop record for ' + case_id)
    return {
        'id': case_id,
        'group': group,
        'start': [float(ground[0]), float(ground[1]), float(ground[2]) + float(height)],
        'start_velocity': [0.0, 0.0, 0.0],
        'start_acceleration': [0.0, 0.0, 0.0],
        'target': [float(v) for v in record['route_last_waypoint_m']],
        'target_velocity': [0.0, 0.0, 0.0],
        'provenance': {
            'source_run': record['source_run'],
            'source_request_id': record['source_request_id'],
            'position_source': POSITION_SOURCE,
            'velocity_source': VELOCITY_SOURCE,
            'derivation': 'start = request.start_xyz_m + [0, 0, nominal_body_height_m]; target = last PCT waypoint',
            'nominal_body_height_m': float(height),
            'source_artifacts': record.get('source_artifacts', []),
        },
    }


def case_from_diagnosis(case, cases_path, cases_sha256, source_artifacts):
    return {
        'id': case['id'],
        'group': 'recorded_diagnosis',
        'start': list(case['start']),
        'start_velocity': list(case['start_velocity']),
        'start_acceleration': list(case['start_acceleration']),
        'target': list(case['target']),
        'target_velocity': list(case['target_velocity']),
        'provenance': {
            'source_run': case['source_run'],
            'source_request_id': case['source_request_id'],
            'position_source': case['position_source'],
            'velocity_source': case['velocity_source'],
            'derivation': 'copied from the recorded diagnosis fixture',
            'fixture': rel(cases_path), 'fixture_sha256': cases_sha256,
            'diagnosis_original_outcome': case['original_outcome'],
            'source_artifacts': [a for a in source_artifacts if case['source_run'] in a['path']],
        },
    }


# ---------------------------------------------------------------------------------------------
# Box geometry.

def point_segment_distance(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    t = 0.0 if length2 == 0.0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / length2))
    return math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy))


def segments_intersect(p1, p2, q1, q2):
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    d1, d2 = cross(q1, q2, p1), cross(q1, q2, p2)
    d3, d4 = cross(p1, p2, q1), cross(p1, p2, q2)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


def segment_rectangle_distance(a, b, lo, hi):
    """Minimum XY distance between segment a-b and the axis-aligned rectangle [lo, hi]."""
    def inside(p):
        return lo[0] <= p[0] <= hi[0] and lo[1] <= p[1] <= hi[1]
    corners = [(lo[0], lo[1]), (hi[0], lo[1]), (hi[0], hi[1]), (lo[0], hi[1])]
    edges = list(zip(corners, corners[1:] + corners[:1]))
    if inside(a) or inside(b) or any(segments_intersect(a, b, c, d) for c, d in edges):
        return 0.0
    distances = [point_segment_distance(c, a, b) for c in corners]
    distances += [point_segment_distance(p, c, d) for p in (a, b) for c, d in edges]
    return min(distances)


def box_for_route(start_case, map_spec, geometry):
    sx, sy = start_case['start'][:2]
    tx, ty = start_case['target'][:2]
    length = math.hypot(tx - sx, ty - sy)
    if length < 1e-6:
        raise FixtureError('degenerate route for ' + start_case['id'])
    ux, uy = (tx - sx) / length, (ty - sy) / length
    nx, ny = -uy, ux  # left of the travel direction; +y for these routes, toward the map interior
    offset = map_spec['lateral_center_offset_m']
    cx = (sx + tx) / 2.0 + nx * offset
    cy = (sy + ty) / 2.0 + ny * offset
    lo = [round(cx - BOX_HALF_XY_M, 6), round(cy - BOX_HALF_XY_M, 6), BOX_Z_RANGE_M[0]]
    hi = [round(cx + BOX_HALF_XY_M, 6), round(cy + BOX_HALF_XY_M, 6), BOX_Z_RANGE_M[1]]
    res = geometry['resolution_m']
    origin = geometry['map_origin_m']
    size = geometry['map_size_m']
    for k in range(3):
        if lo[k] < origin[k] + res or hi[k] > origin[k] + size[k] - res:
            raise FixtureError('box for %s/%s leaves the map on axis %d' % (start_case['id'], map_spec['id'], k))
    clearance = segment_rectangle_distance((sx, sy), (tx, ty), lo[:2], hi[:2])
    if clearance <= 0.0:
        raise FixtureError('box for %s/%s intersects the straight route' % (start_case['id'], map_spec['id']))
    box_id = '%s__%s' % (start_case['id'], map_spec['id'])
    derivation = {
        'rule': 'axis-aligned box centred at the start-target midpoint, offset along the left normal of the route',
        'side': 'left of travel (+y for these routes; the -y map edge is about 0.5 m from the route)',
        'lateral_center_offset_m': offset,
        'half_extent_xy_m': BOX_HALF_XY_M,
        'z_range_m': list(BOX_Z_RANGE_M),
        'straight_route_to_box_xy_m': round(clearance, 9),
        'inflation_radius_m': geometry['double_cylinder_radius_m'],
        'straight_route_within_inflation_reach': clearance < geometry['double_cylinder_radius_m'],
        'route_to_map_min_y_edge_m': round(min(sy, ty) - origin[1], 9),
    }
    return box_id, {'schema': BOXES_SCHEMA, 'boxes': [{'id': box_id, 'min': lo, 'max': hi}], 'derivation': derivation}


# ---------------------------------------------------------------------------------------------
# Suite assembly.

def run_entry(start_case, map_id, init, boxes_rel, kind, offsets, dump_labels):
    label = '%s__%s__%s' % (start_case['id'], map_id, init['id'] if kind == 'single' else 'followup_' + init['id'])
    return {
        'label': label,
        'kind': kind,
        'start_id': start_case['id'],
        'start_group': start_case['group'],
        'map_id': map_id,
        'init_id': init['id'],
        'repeat': init['repeat'],
        'start': start_case['start'],
        'start_velocity': start_case['start_velocity'],
        'start_acceleration': start_case['start_acceleration'],
        'target': start_case['target'],
        'target_velocity': start_case['target_velocity'],
        'poly_init': init['poly_init'],
        'random_poly': init['random_poly'],
        'seed': init['seed'],
        'occupied_boxes': boxes_rel,
        'follow_up_offsets_s': list(offsets),
        'dump_samples': label in dump_labels,
    }


def build_suite(starts, geometry, init_rows, maps, follow_up_start_ids, sources, dump_labels, purpose):
    boxes = {}
    runs = []
    for start_case in starts:
        for map_spec in maps:
            boxes_rel = None
            if map_spec['lateral_center_offset_m'] is not None:
                box_id, box_doc = box_for_route(start_case, map_spec, geometry)
                boxes_rel = 'boxes/%s.json' % box_id
                boxes[boxes_rel] = box_doc
            for init in init_rows:
                runs.append(run_entry(start_case, map_spec['id'], init, boxes_rel, 'single', (), dump_labels))
    base_init = init_rows[0]
    for start_case in starts:
        if start_case['id'] in follow_up_start_ids:
            runs.append(run_entry(start_case, 'empty', base_init, None, 'follow_up', FOLLOW_UP_OFFSETS_S, dump_labels))
    labels = [r['label'] for r in runs]
    if len(set(labels)) != len(labels):
        raise FixtureError('duplicate run labels')
    missing = sorted(set(dump_labels) - set(labels))
    if missing:
        raise FixtureError('dump-sample runs are missing: %s' % missing)
    single = [r for r in runs if r['kind'] == 'single']
    follow = [r for r in runs if r['kind'] == 'follow_up']
    suite = {
        'schema': SUITE_SCHEMA,
        'purpose': purpose,
        'generator': {'script': rel(Path(__file__)), 'script_sha256': sha256_file(__file__)},
        'planner_params': geometry,
        'sources': sources,
        'samples': 101,
        'follow_up': {
            'offsets_s': list(FOLLOW_UP_OFFSETS_S),
            'semantics': ('offsets are simulated seconds since the first plan; each follow-up samples the newest '
                          'accepted trajectory at that clock time and replans in the same manager with the FSM '
                          'REFERENCE_PATH chain (previous trajectory, polynomial, random polynomial)'),
            'init_id': base_init['id'],
        },
        'starts': starts,
        'inits': init_rows,
        'maps': [dict(m) for m in maps],
        'boxes': {path: {'sha256': sha256_bytes(dumps(doc).encode()), 'derivation': doc['derivation'],
                         'box': doc['boxes'][0]} for path, doc in sorted(boxes.items())},
        'runs': runs,
        'counts': {
            'starts': len(starts), 'inits': len(init_rows), 'maps': len(maps),
            'single_runs_per_build': len(single), 'follow_up_runs_per_build': len(follow),
            'process_runs_per_build': len(runs), 'process_runs_total_two_builds': 2 * len(runs),
            'first_calls_per_build': len(runs),
            'follow_up_steps_per_build': len(follow) * len(FOLLOW_UP_OFFSETS_S),
            'box_files': len(boxes), 'dump_sample_runs': sum(1 for r in runs if r['dump_samples']),
        },
    }
    return suite, boxes


def recorded_requests_doc(experiment=EXPERIMENT):
    records = {}
    for case_id, returned in FAILED_DISPLAY_RUNS:
        found = resume_records_from_run(experiment / returned)
        if len(found) != 1:
            raise FixtureError('expected one resubmission request in %s, found %d' % (returned, len(found)))
        records[case_id] = found[0]
    return {
        'schema': RECORDED_SCHEMA,
        'extractor': {'script': rel(Path(__file__)), 'function': 'resume_records_from_run'},
        'records': records,
    }


def generate(recorded_path=None, cases_path=DIAGNOSIS_CASES, planner_path=PLANNER_YAML,
             cases_sha256=DIAGNOSIS_CASES_SHA256, planner_sha256=PLANNER_YAML_SHA256):
    recorded_path = Path(recorded_path or FIXTURES / 'recorded_requests.json')
    diagnosis, diagnosis_sha = load_diagnosis_cases(cases_path, cases_sha256)
    geometry = load_planner_geometry(planner_path, planner_sha256)
    recorded = json.loads(recorded_path.read_text())
    if recorded.get('schema') != RECORDED_SCHEMA:
        raise FixtureError('unexpected recorded requests schema')
    starts = [case_from_diagnosis(c, cases_path, diagnosis_sha, diagnosis['source_artifacts'])
              for c in diagnosis['cases']]
    for case_id, _ in FAILED_DISPLAY_RUNS:
        starts.append(case_from_stop_record(recorded['records'][case_id], case_id, 'recorded_failed_stop'))
    base = next(s for s in starts if s['id'] == SWEEP_BASE_CASE)
    for centimeters in SWEEP_X_CENTIMETERS:
        case = copy.deepcopy(base)
        case['id'] = sweep_id(centimeters)
        case['group'] = 'stop_position_sweep'
        case['start'] = [centimeters / 100.0, base['start'][1], base['start'][2]]
        case['provenance'] = {
            'derivation': 'start x replaced by %.2f m; all other fields copied from %s' % (centimeters / 100.0, SWEEP_BASE_CASE),
            'base_case': SWEEP_BASE_CASE,
            'base_source_run': base['provenance']['source_run'],
            'base_source_request_id': base['provenance']['source_request_id'],
            'position_source': 'synthetic stop-position sweep around the failed resume pose',
            'velocity_source': VELOCITY_SOURCE,
        }
        starts.append(case)
    sources = {
        'diagnosis_cases': {'path': rel(cases_path), 'sha256': diagnosis_sha},
        'recorded_requests': {'path': rel(recorded_path), 'sha256': sha256_file(recorded_path)},
        'planner_yaml': {'path': rel(planner_path), 'sha256': geometry['sha256']},
    }
    follow_ids = {sweep_id(c) for c in SWEEP_X_CENTIMETERS}
    return build_suite(starts, geometry, inits(), MAPS, follow_ids, sources, set(DUMP_RUN_LABELS),
                       'Native A/B suite for PRD R2 (fixtures, sweep, random init, occupancy boxes, follow-ups)')


def from_journals(returned_dirs, request_kind='resume', full_matrix=False):
    diagnosis, diagnosis_sha = load_diagnosis_cases()
    starts = [case_from_diagnosis(c, DIAGNOSIS_CASES, diagnosis_sha, diagnosis['source_artifacts'])
              for c in diagnosis['cases']]
    sources = {'planner_yaml': {'path': rel(PLANNER_YAML), 'sha256': PLANNER_YAML_SHA256},
               'diagnosis_cases': {'path': rel(DIAGNOSIS_CASES), 'sha256': diagnosis_sha,
                                   'use': 'AC0 validity control starts'},
               'runs': []}
    for returned in returned_dirs:
        records = resume_records_from_run(returned, request_kind=request_kind)
        run_id = Path(returned).resolve().parent.name
        sources['runs'].append({'returned_artifacts': rel(returned), 'requests': len(records)})
        for record in records:
            suffix = record['source_request_id'][len(record['source_run']) + 1:] \
                if record['source_request_id'].startswith(record['source_run'] + '-') else record['source_request_id']
            case_id = re.sub(r'[^A-Za-z0-9_]+', '_', '%s__%s' % (run_id, suffix))
            starts.append(case_from_stop_record(record, case_id, 'recorded_isaac_stop'))
    if len(starts) == len(diagnosis['cases']):
        raise FixtureError('no matching requests in the given runs')
    geometry = load_planner_geometry()
    init_rows = inits() if full_matrix else inits()[:3]
    maps = MAPS if full_matrix else MAPS[:1]
    return build_suite(starts, geometry, init_rows, maps, set(), sources, set(),
                       'Native replay of recorded Isaac stop poses with both builds (item C5)')


def write_outputs(output_dir, suite, boxes, force=False, suite_name='suite_cases.json'):
    output_dir = Path(output_dir)
    files = {suite_name: dumps(suite)}
    files.update({path: dumps(doc) for path, doc in boxes.items()})
    conflicts = [name for name, text in files.items()
                 if (output_dir / name).exists() and (output_dir / name).read_text() != text]
    if conflicts and not force:
        raise FixtureError('refusing to overwrite differing frozen fixtures: %s' % conflicts[:5])
    for name, text in files.items():
        path = output_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return {name: sha256_bytes(text.encode()) for name, text in files.items()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='mode')
    extract = sub.add_parser('extract')
    extract.add_argument('--output', type=Path, default=FIXTURES / 'recorded_requests.json')
    extract.add_argument('--force', action='store_true')
    gen = sub.add_parser('generate')
    gen.add_argument('--output-dir', type=Path, default=FIXTURES)
    gen.add_argument('--recorded', type=Path, default=FIXTURES / 'recorded_requests.json')
    gen.add_argument('--force', action='store_true')
    journals = sub.add_parser('from-journals')
    journals.add_argument('--returned-artifacts', type=Path, action='append', required=True,
                          help='returned_artifacts directory of a pilot run; repeatable')
    journals.add_argument('--output-dir', type=Path, required=True)
    journals.add_argument('--request-kind', choices=['resume', 'all'], default='resume')
    journals.add_argument('--full-matrix', action='store_true', help='13 initializations x 3 maps instead of polynomial seed 0 x3 on the empty map')
    journals.add_argument('--force', action='store_true')
    args = parser.parse_args(argv)
    mode = args.mode or 'generate'
    if mode == 'extract':
        text = dumps(recorded_requests_doc())
        if args.output.exists() and args.output.read_text() != text and not args.force:
            raise FixtureError('refusing to overwrite differing ' + str(args.output))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
        print(json.dumps({'output': str(args.output), 'sha256': sha256_bytes(text.encode())}, indent=2))
        return 0
    if mode == 'generate':
        output_dir = getattr(args, 'output_dir', FIXTURES)
        suite, boxes = generate(getattr(args, 'recorded', None))
        hashes = write_outputs(output_dir, suite, boxes, force=getattr(args, 'force', False))
    else:
        output_dir = args.output_dir
        suite, boxes = from_journals(args.returned_artifacts, args.request_kind, args.full_matrix)
        hashes = write_outputs(output_dir, suite, boxes, force=args.force)
    print(json.dumps({'output_dir': str(output_dir), 'counts': suite['counts'],
                      'suite_sha256': hashes['suite_cases.json']}, indent=2))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except FixtureError as error:
        print('make_fixtures: ' + str(error), file=sys.stderr)
        raise SystemExit(2)
