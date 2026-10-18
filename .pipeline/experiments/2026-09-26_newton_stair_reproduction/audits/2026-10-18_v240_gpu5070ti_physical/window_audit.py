"""Audit original fixed windows and route-relative approach from measured telemetry."""
from pathlib import Path
import csv
import json
import math
import sys

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
PREFIX=Path('/data/sun/vla_mppi_20261009')
PREVIOUS=PREFIX/'trials/v237_linux_full_attempt01/runs/v237_linux_full_attempt01'
CURRENT=PREFIX/'trials/v241_linux_full_attempt01/runs/v241_linux_full_attempt01'
sys.path[:0]=[str(BASE/'versions/v196'),str(BASE/'audits/2026-10-17_v237_terminal_approach')]
from analyze_remote import Capture, core
from pause_metrics import low_speed_intervals, summarize
from trajectory_coverage import active_gaps

def audit(root):
    c=Capture(root)
    rows=c.rows('telemetry.jsonl')
    samples=[(r['physics_time_s'],math.hypot(*r['body_sensor']['linear_world'][:2])) for r in rows]
    intervals=low_speed_intervals(samples)
    events=c.rows('artifacts/reactive_observations.jsonl')
    emergency=[e['clock_ns']*1e-9 for e in events if e.get('event')=='bspline' and e['data'].get('emergency_stop')]
    curves=[]
    for e in events:
        if e.get('event')!='bspline':continue
        data=e['data'];stamp=data['start_time']
        curves.append(dict(publication_s=e['clock_ns']*1e-9,start_s=stamp['sec']+stamp['nanosec']*1e-9,
            duration_s=data['knots'][len(data['pos_pts'])]-data['knots'][data['order']],emergency=int(data['emergency_stop'])))
    class Log:
        def read_text(self):return c.read('nav2.log')
    starts,rounds=core.parse_rounds(Log())
    scenario=c.json('inputs/stair_scenario.json');goal=scenario['goal_ground_xyz_m']
    pilot=c.json('inputs/pilot.json')
    distance=lambda r:math.dist(r['body_sensor']['position'][:2],goal[:2])
    approach=[r for r in rows if r['physics_time_s']>=55 and distance(r)<=4.5 and r['body_sensor']['position'][2]>=goal[2]-.5]
    approach_start=approach[0]['physics_time_s'] if approach else None
    near_goal=[r for r in approach if distance(r)<=pilot['goal_xy_tolerance_m'] and r.get('stance_mode') in ('STAND_SETTLING','STAND_TRANSITION','FIXED_STAND')]
    terminal_begin=near_goal[0]['physics_time_s'] if near_goal else None
    windows={'stairs_45_55':(45.,55.),'terminal_109_115':(109.,115.)}
    if approach_start is not None:
        windows['route_relative_approach']=(approach_start,terminal_begin if terminal_begin is not None else samples[-1][0])
    result={}
    for name,(lo,hi) in windows.items():
        if hi<=lo:continue
        part=[r for r in rounds if lo<=r.get('ros_s',-1)<hi]
        actual=[r for r in rows if lo<=r['physics_time_s']<hi]
        low=summarize(intervals,lo,hi)
        # Keep raw fixed-window stops visible even if the run arrives earlier.
        # Terminal stance is separately labelled rather than silently excluded.
        coverage_end=min(hi,terminal_begin) if terminal_begin is not None else hi
        gaps=active_gaps(curves,lo,coverage_end) if coverage_end>lo and samples[-1][0]>=coverage_end else None
        result[name]=dict(measured=low,recording_covers_window=samples[-1][0]>=hi,
            emergency_times_s=[t for t in emergency if lo<=t<hi],
            completed_rounds=len(part),successful_rounds=sum(bool(r['success']) for r in part),
            failed_rounds=[dict(start_ros_s=r['ros_s'],solve_ms=r['wall_s']*1000) for r in part if not r['success']],
            rounds_over_100ms=sum(r['wall_s']>.1 for r in part),
            incomplete_round_starts=[r.get('ros_s') for r in starts if not r.get('completed') and lo<=r.get('ros_s',-1)<hi],
            active_curve_check_window_s=[lo,coverage_end] if coverage_end>lo else None,
            active_curve_gaps=gaps,stance_samples={mode:sum(r.get('stance_mode')==mode for r in actual) for mode in sorted({r.get('stance_mode','unknown') for r in actual})},
            distance_range_m=[min(map(distance,actual)),max(map(distance,actual))] if actual else None)
    transitions=[]
    for a,b in zip(rows,rows[1:]):
        if a.get('stance_mode')!=b.get('stance_mode') and b['physics_time_s']>=45:
            transitions.append(dict(time_s=b['physics_time_s'],from_mode=a.get('stance_mode'),to_mode=b.get('stance_mode'),distance_m=distance(b),reason=b.get('stance_reason')))
    return dict(run=root.name,windows=result,total_emergency_publications=len(emergency),all_emergency_times_s=emergency,
        all_measured_low_intervals=intervals,approach_distance_threshold_m=4.5,approach_start_s=approach_start,
        first_near_goal_stance_s=terminal_begin,near_goal_xy_radius_m=pilot['goal_xy_tolerance_m'],
        stance_transitions=transitions,source=c.sources)

def main():
    result={'v237':audit(PREVIOUS),'v241':audit(CURRENT)}
    result['definition']=dict(speed_limit_mps=.05,source='Original20ms measured horizontal telemetry',
        integration='Right-sample intervals; gaps >=.1s break pauses; moving gaps excluded from stopped time',
        fixed_windows='Raw45–55s and109–115s always retained, including any terminal hold',
        relative_window='First distance<=4.5m at upper-floor height after55s through first near-goal non-RL stance; separate from full terminal gate',
        curve_coverage='Actual Bspline publications with replacement ownership; checked only before near-goal terminal stance',
        full_route_and_pd='Independently verified by unchanged original route/terminal gates')
    (HERE/'results/window_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({v:{k:dict(success=f"{w['successful_rounds']}/{w['completed_rounds']}",stops_ge_05s=w['measured']['count_ge_05s'],emergencies=len(w['emergency_times_s'])) for k,w in result[v]['windows'].items()} for v in ('v237','v241')},indent=2))

if __name__=='__main__':main()
