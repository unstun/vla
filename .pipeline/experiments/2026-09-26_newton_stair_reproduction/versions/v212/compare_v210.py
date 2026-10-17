"""Compare the two closed same-host original-route recordings."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
VERSIONS = HERE.parent
TASK = Path('/data/sun/vla_mppi_20261009')
sys.path.insert(0, str(VERSIONS / 'v196'))
from analyze_remote import Capture


def summarize(version):
    run = f'{version}_linux_full_attempt01'
    capture = Capture(TASK / 'trials' / run / 'runs' / run)
    results = VERSIONS / version / 'results'
    metrics = json.loads((results / 'metrics.json').read_text())
    outcome = json.loads((results / 'outcome.json').read_text())
    route_events = [row for row in capture.rows('artifacts/reactive_observations.jsonl') if row['event'] == 'pct_route']
    bodies = capture.rows('telemetry.jsonl')
    final_hold = outcome['final_hold']
    # Report the existing >=1 s measured slow intervals separately from the
    # final stationary tail. Neither is a count of planner failures.
    pauses = metrics['pauses_over_1s']
    final_pause = pauses[-1] if pauses and pauses[-1]['end_sim_s'] >= metrics['actual_physics_end_s']-.2 else None
    moving_pauses = pauses[:-1] if final_pause else pauses
    paths = [json.dumps([pose['pose'] for pose in row['data']['poses']],sort_keys=True) for row in route_events]
    record = {'run':run, 'full_route_passed':outcome['full_route_gate_passed'],
        'terminal_status':outcome['terminal_status'], 'physics_duration_s':outcome['physics_duration_s'],
        'navigation_wall_s':metrics['navigation_wall_duration_s'], 'actual_rtf':metrics['actual_rtf'],
        'global_route_deliveries':len(route_events), 'distinct_delivered_route_geometries':len(set(paths)),
        'global_route_sim_times_s':[None if row['clock_ns'] is None else row['clock_ns']/1e9 for row in route_events],
        'local_successful_rounds_hz':metrics['planning']['successful_wall_hz'],
        'local_solve_ms':metrics['planning']['solve_ms'],
        'intermediate_slow_intervals_over_1s':moving_pauses, 'final_slow_interval':final_pause,
        'final_hold':final_hold, 'minimum_base_up_z':min(row['base_up_z'] for row in bodies)}
    return record, capture


old, old_capture = summarize('v210')
new, new_capture = summarize('v212')
before = old_capture.json('episode_request.json')
after = new_capture.json('episode_request.json')
ignored = {'run_epoch_ns','integration_version','native_build'}
assert {k:v for k,v in before.items() if k not in ignored} == {k:v for k,v in after.items() if k not in ignored}
assert old_capture.json('inputs/stair_scenario.json') == new_capture.json('inputs/stair_scenario.json')
assert old_capture.json('stance_status.json')['source_sha256'] == new_capture.json('stance_status.json')['source_sha256']
assert old_capture.read('planner.yaml') == new_capture.read('planner.yaml')
old_tree = old_capture.read('nav2_params.bt.xml')
new_tree = new_capture.read('nav2_params.bt.xml')
assert old_tree.replace('<RateController hz="1.0">','<PlanOnGoalChange goal="{goal}">').replace('</RateController>','</PlanOnGoalChange>') == new_tree
def normalized_yaml(capture, version, name):
    return yaml.safe_load(capture.read(name).replace(f'{version}_linux_full_attempt01','SAME_RUN'))
assert normalized_yaml(old_capture,'v210','nav2_params.yaml') == normalized_yaml(new_capture,'v212','nav2_params.yaml')
assert normalized_yaml(old_capture,'v210','nav2_params.scan.yaml') == normalized_yaml(new_capture,'v212','nav2_params.scan.yaml')
report = {'baseline':old,'candidate':new,
    'same_host_original_scenario_request_and_parameters':True,
    'same_locomotion_source':True,'only_behavior_tree_planning_gate_changed':True,
    'global_route_metric':'Observed /pct_path deliveries to LocalMotion; not an instrumented count of internal PCT solver calls.',
    'comparison_scope':'One existing v210 trial versus one new v212 trial; scheduling and physical variation remain possible.',
    'input_sources':{'v210':old_capture.sources,'v212':new_capture.sources}}
(HERE/'results/comparison_v210.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'baseline':old,'candidate':new}),flush=True)
