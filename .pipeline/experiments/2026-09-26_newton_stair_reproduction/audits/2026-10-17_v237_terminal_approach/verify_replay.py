"""A functional regression, not a hardware-specific latency requirement."""
import argparse
import csv
import json
from pathlib import Path

def verify(path):
    rows=list(csv.DictReader(path.open()))
    assert len(rows)==141
    stairs=[r for r in rows if 45<=float(r['time_s'])<=55]
    tail=[r for r in rows if 109<=float(r['time_s'])<=114.5]
    assert len(stairs)==50 and len(tail)==91
    # Exact captured lag is preserved. An already stale snapshot must remain
    # rejected; the repair removes the source of avoidable extra lag.
    fresh=[r for r in rows if r['body_verdict']=='0']
    stale=[r for r in rows if r['body_verdict']=='4']
    assert len(stale)==1 and stale[0]['target_ok']=='0'
    assert all(r['target_ok']=='1' for r in fresh)
    assert all(int(r['goal_search_calls'])==0 for r in rows), 'Avoidable goal-neighborhood search on continuing reference'
    assert all(r['post_spline_status']=='0' for r in rows if r['plan_ok']=='1')
    return dict(frames=len(rows),stairs=len(stairs),approach=len(tail),fresh_targets_passed=len(fresh),
        stale_inputs_still_rejected=len(stale),unnecessary_goal_searches=0,
        target_max_ms=max(float(r['target_ms']) for r in rows),
        optimizer_success=sum(r['plan_ok']=='1' for r in rows),
        optimizer_failures=[dict(frame=r['frame'],time_s=float(r['time_s']),body_verdict=r['body_verdict']) for r in rows if r['target_ok']=='1' and r['plan_ok']=='0'],
        physics_steps=0,measured_pause_improvement_validated=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('frames',type=Path);args=p.parse_args()
    print(json.dumps(verify(args.frames),indent=2))
