"""Extract verified original evidence, clocks and motion for a precise diagnosis."""
from pathlib import Path
import collections
import hashlib
import json
import math
import sys
import numpy as np

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
RAW=Path('/data/sun/vla_mppi_20261009/trials/v237_linux_full_attempt01/runs/v237_linux_full_attempt01')
OUT=HERE/'results'
sys.path.insert(0,str(BASE/'versions/v196'))
from analyze_remote import Capture,core
from pause_metrics import low_speed_intervals, summarize

def save(name,value):
    (OUT/name).write_text(json.dumps(value,indent=2)+'\n')

def main():
    OUT.mkdir(exist_ok=True)
    expected=json.loads((BASE/'audits/2026-10-17_v237_gpu5070ti_physical/results/outcome.json').read_text())['archive_sha256']
    archive=RAW/'raw_capture.zip';h=hashlib.sha256()
    with archive.open('rb') as stream:
        for block in iter(lambda:stream.read(4*2**20),b''):h.update(block)
    assert h.hexdigest()==expected
    c=Capture(RAW)
    telemetry=c.rows('telemetry.jsonl');sensor=c.rows('sensor.jsonl');clock=c.rows('clock_samples.jsonl')
    nav=c.read('nav2.log');lines=nav.splitlines()
    class Log:
        def read_text(self):return nav
    starts,rounds=core.parse_rounds(Log())
    sync=[r for r in clock if r.get('accepted') and r.get('samples',0)>=500]
    assert sync and len({r['responder'] for r in sync})==1
    remote=np.array([r['remote']/1e9 for r in sync]);offset=np.array([r['filtered_offset_ns']/1e9 for r in sync])
    host=np.array([r['realtime_pacing']['wall_anchor_monotonic_s']+r['realtime_pacing']['wall_elapsed_s'] for r in telemetry])
    native=np.array([r['physics_time_s'] for r in telemetry])
    assert np.all(np.diff(host)>0) and np.all(np.diff(native)>0)
    def native_at_remote(t):
        mapped=t+float(np.interp(t,remote,offset))
        return float(np.interp(mapped,host,native))
    chosen=[]
    for r in rounds:
        if 108.5<=r.get('ros_s',-1)<=115:
            chosen.append(dict(r,estimated_finish_native_s=native_at_remote(r['start_wall_s']+r['wall_s']),
                completion_time_limit='schedule-start plus solver timer, mapped through original clock/pacer; excludes small pre-timer overhead'))
    save('nominal_rounds.json',chosen)
    begin=min(r['start_line'] for r in chosen)-8;end=max(r['end_line'] for r in chosen)+8
    (OUT/'native_window.log').write_text('\n'.join(lines[max(0,begin-1):end])+'\n')
    save('log_window_identity.json',dict(original_start_line=begin,original_end_line=end,clock_mapping='Original accepted clock samples and telemetry pacer; no direct ROS+wall addition'))
    rows=[]
    previous=None;transitions=[]
    for r in telemetry:
        t=r['physics_time_s'];mode=r.get('stance_mode')
        if previous and mode!=previous.get('stance_mode'):
            transitions.append(dict(first_row_s=t,previous_row_s=previous['physics_time_s'],from_mode=previous.get('stance_mode'),to_mode=mode,
                command=r.get('command'),requested_command=r.get('requested_command'),command_reason=r.get('command_reason'),stale=r.get('command_stale')))
        if 109<=t<=114.5:
            rows.append(dict(time_s=t,mode=mode,stance_reason=r.get('stance_reason'),
                speed_mps=math.hypot(*r['body_sensor']['linear_world'][:2]),position=r['body_sensor']['position'],
                command=r.get('command'),requested_command=r.get('requested_command'),reason=r.get('command_reason'),
                command_stale=r.get('command_stale'),sequence=r.get('command_sequence'),
                policy_owns_joints=r.get('policy_owns_joints')))
        previous=r
    save('motion_window.json',rows)
    save('stance_transitions.json',[r for r in transitions if 108.5<=r['first_row_s']<=120])
    all_intervals=low_speed_intervals((r['physics_time_s'],math.hypot(*r['body_sensor']['linear_world'][:2])) for r in telemetry)
    driver=c.json('artifacts/stair_driver_result.json')
    observations=[r for r in driver['journal'] if r.get('event')=='observation']
    save('driver_window.json',[r for r in observations if 109<=r['sim_time_s']<=114.5])
    arrival=next((r['sim_time_s'] for r in observations if r.get('arrived')),None)
    save('measured_pauses.json',dict(definition='20ms recorded measured horizontal speed<.05m/s; sample gaps<.1s. Each interval extent includes preceding sample; raw durations independent of stance.',
        approach=summarize(all_intervals,109,114.5),stairs=summarize(all_intervals,45,55),first_driver_arrived_s=arrival))
    reactive=c.rows('artifacts/reactive_observations.jsonl')
    event_samples={}
    for r in reactive:event_samples.setdefault(r.get('event','unknown'),r)
    save('observer_schema.json',dict(counts=dict(collections.Counter(r.get('event') for r in reactive)),examples=event_samples))
    save('emergency_publications.json',[r for r in reactive if r.get('event')=='bspline' and r['data'].get('emergency_stop')])
    # Save compact backend snapshots only for the selected original host/native span.
    backend=c.rows('backend_states.jsonl')
    save('backend_schema.json',dict(count=len(backend),first=backend[0],last=backend[-1],telemetry_fields=list(telemetry[0])))
    save('stance_status.json',c.json('stance_status.json'))
    save('input_provenance.json',dict(raw=str(RAW),archive_sha256=expected,files=c.sources,physics_steps=0))
    print(json.dumps(dict(rounds=len(chosen),motion_rows=len(rows),pauses=summarize(all_intervals,109,114.5),first_arrived_s=arrival),indent=2),flush=True)

if __name__=='__main__':main()
