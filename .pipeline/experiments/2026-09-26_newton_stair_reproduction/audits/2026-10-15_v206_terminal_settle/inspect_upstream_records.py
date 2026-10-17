"""Read existing machine-dog stop/hold records; never execute its controller."""
from pathlib import Path
import hashlib
import json

UPSTREAM = Path('/Users/sun/tongbu/study/phdproject/machine-dog')
BASE = UPSTREAM / 'artifacts/2026-10-06_v21k_m10000_lite3_deploy/tracked_logs'
CASES = {
    'a5_forced_m12': 'newton_forced_return_5070ti_20261007/runs/m12',
    'a7_quiet_m2': 'newton_no_time_limit_5070ti_20261007/runs/m2',
    'a8_fixed_pose_m2': 'newton_fixed_pose_5070ti_20261013/a8/runs/m2',
    'a8_not_quiet_m12': 'newton_fixed_pose_5070ti_20261013/a8/runs/m12',
}
results = {}
for name, relative in CASES.items():
    root = BASE / relative
    sim = [json.loads(line) for line in (root/'sim/sim_log.jsonl').open()]
    offset = sim[0]['tick']/1000 - sim[0]['sim_s']
    transitions, last_mode, last_row, digest, count = [], None, None, hashlib.sha256(), 0
    trace = root/'runtime_logs/v21k_ticks.jsonl'
    with trace.open('rb') as f:
        for line in f:
            digest.update(line)
            row = json.loads(line)
            state = row.get('robot_state')
            if not state:
                continue
            count += 1
            t = state['timestamp_s']-offset
            mode = (row['hold_state'], row['hold_reason'])
            if t >= 47.8 and mode != last_mode:
                transitions.append(dict(sim_s=t, mode=mode[0], reason=mode[1],
                                        velocity=row.get('velocity'), foot_load_n=row.get('foot_load_n')))
            last_mode, last_row = mode, row
    end = sim[-1]
    results[name] = dict(source_root=str(root), source_trace_sha256=digest.hexdigest(),
                         policy_state_rows=count, timestamp_minus_sim_s=offset,
                         stop_sim_s=48., transitions=transitions,
                         final_hold_state=last_row['hold_state'], final_hold_reason=last_row['hold_reason'],
                         end_sim_s=end['sim_s'], final_xyz=end['pos'], final_rpy_deg=end['rpy_deg'],
                         final_foot_n=end['foot_n'])
sources = [
    '2_experiment/deployment/lite3_rl_deploy_v1a.1/src/stance_hold.zig',
    '2_experiment/deployment/lite3_rl_deploy_v1a.1/src/v21k_runtime.zig',
    '2_experiment/deployment/lite3_rl_deploy_v1a.1/src/controller.zig',
    '2_experiment/deployment/lite3_newton_sim/docker/run_runner.sh',
    '0_trials/2026-08-22/v17a28_mujoco_wasd/run_v17a28_mujoco_wasd.py',
]
report = dict(status='surveyed_existing_records_only', upstream=str(UPSTREAM),
              inspected_head='3fcb41ffb03fd7dffaf092c712417fad51cd78b1',
              source_sha256={p:hashlib.sha256((UPSTREAM/p).read_bytes()).hexdigest() for p in sources},
              cases=results, runtime_edits=False, new_physics_runs=0)
output = Path(__file__).resolve().parent/'results/machine_dog_reference.json'
output.write_text(json.dumps(report, indent=2)+'\n')
for name,result in results.items():
    print(name, json.dumps({k:result[k] for k in ['transitions','final_hold_state','final_xyz','final_rpy_deg','final_foot_n']}))
