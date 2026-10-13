"""Causal display of recorded controller-accepted native SCAN splines."""
from pathlib import Path
import csv,json,zipfile
import numpy as np
from scipy.interpolate import BSpline

IDENTITY=('run_id','epoch','request_id','goal_id','route_id','command_id','generation','map_epoch','map_revision')
def owner(data):return tuple(data.get(x) for x in IDENTITY)
def key(data):return owner(data)+(data.get('traj_id'),)
def read_text(root,name):
    p=root/name
    if p.is_file():return p.read_text()
    with zipfile.ZipFile(root/'raw_capture.zip') as archive:return archive.read(name).decode()
def sample_spline(data):
    control=np.array([[p['x'],p['y'],p['z']] for p in data['pos_pts']],dtype=float)
    knots=np.array(data['knots'],dtype=float);degree=int(data['order'])
    if degree!=3 or len(control)<4 or len(knots)!=len(control)+degree+1 or not np.isfinite(control).all() or not np.isfinite(knots).all() or np.any(np.diff(knots)<=0):
        raise ValueError('Malformed recorded native spline')
    values=BSpline(knots,control,degree,extrapolate=False)(np.linspace(knots[degree],knots[-degree-1],150))
    if not np.isfinite(values).all():raise ValueError('Native spline sampling produced nonfinite points')
    return values.astype(np.float32)

class Selection:
    """Controller admission is required; producer-only candidates are never shown."""
    def __init__(self):
        self.curves={};self.desired=None;self.active=None;self.cancelled=set();self.commands={};self.message_count=0
    def consume(self,event):
        data=event['data'];kind=event['event'];identity=owner(data)
        if kind=='bspline':
            self.message_count+=1;self.curves[key(data)]=event
        elif kind=='scan_admission' and data.get('consumer')=='controller':
            if data.get('status')=='accepted':self.desired=key(data)
            elif data.get('status') in ('stopped','rejected'):
                if self.active and owner(self.active['data'])==identity:self.active=None;self.desired=None
        elif kind=='scan_cancel':
            self.cancelled.add(identity)
            if self.active and owner(self.active['data'])==identity:self.active=None;self.desired=None
        elif kind=='raw_command':self.commands[identity]=event
        if self.desired in self.curves:
            curve=self.curves[self.desired]
            if owner(curve['data']) not in self.cancelled and not curve['data'].get('emergency_stop'):
                self.active=curve
    def current(self,simulation_s):
        if self.active is None:return None
        data=self.active['data'];command=self.commands.get(owner(data))
        if command is None:return None
        stamp=command['data']['stamp'];source=stamp['sec']+stamp['nanosec']/1e9
        # The curve is the latest controller-admitted plan, which can replace the
        # command trajectory between control ticks. Require a fresh output from
        # that owner, not a claim that this curve already produced a command.
        if not 0<=simulation_s-source<=.1:return None
        return self.active

class Overlay:
    def __init__(self,root,latency_csv):
        self.root=Path(root)
        sync=[json.loads(x) for x in read_text(self.root,'clock_samples.jsonl').splitlines()]
        sync=[x for x in sync if x.get('accepted') and x.get('samples',0)>=500]
        if not sync or len({x['responder'] for x in sync})!=1:raise ValueError('Converged original clock mapping required')
        self.remote=np.array([x['remote']/1e9 for x in sync]);self.offset=np.array([x['filtered_offset_ns']/1e9 for x in sync])
        rows=[json.loads(x) for x in read_text(self.root,'artifacts/reactive_observations.jsonl').splitlines()]
        self.events=[]
        for event in rows:
            if event['event'] not in ('bspline','scan_admission','scan_cancel','raw_command'):continue
            remote=event['wall_monotonic_ns']/1e9
            event['host_wall_s']=remote+float(np.interp(remote,self.remote,self.offset));self.events.append(event)
        self.events.sort(key=lambda x:x['host_wall_s'])
        self.index=0;self.selection=Selection();self.points={};self.last_wall=-float('inf')
        self.timings=list(csv.DictReader(Path(latency_csv).open()))
        for r in self.timings:r['finish_wall_s']=float(r['wall_s_host'])+float(r['solve_ms'])/1000
        self.timings.sort(key=lambda x:x['finish_wall_s']);self.timing_index=0;self.latest_timing=None
        self.records=[];self.total_splines=sum(x['event']=='bspline' for x in self.events)
        if not self.total_splines:raise ValueError('No final native splines were recorded')
    def frame(self,row):
        wall=row['wall_monotonic_s']
        if wall<self.last_wall:raise ValueError('Noncausal frame order')
        self.last_wall=wall
        while self.index<len(self.events) and self.events[self.index]['host_wall_s']<=wall:
            self.selection.consume(self.events[self.index]);self.index+=1
        while self.timing_index<len(self.timings) and self.timings[self.timing_index]['finish_wall_s']<=wall:
            self.latest_timing=self.timings[self.timing_index];self.timing_index+=1
        event=self.selection.current(row['physics_time_s'])
        timing=self.latest_timing
        record={'source_state_index':row['source_state_index'],'display_time_s':row['display_time_s'],
                'physics_time_s':row['physics_time_s'],'source_wall_s':wall,'trajectory_id':None,
                'curve_event_wall_s':None,'latest_completed_solve_ms':float(timing['solve_ms']) if timing else None,
                'latest_solve_success':bool(int(timing['success'])) if timing else None,'sampled_points':0}
        points=None
        if event:
            k=key(event['data'])
            if k not in self.points:self.points[k]=sample_spline(event['data'])
            points=self.points[k]
            record.update(trajectory_id=event['data']['traj_id'],curve_event_wall_s=event['host_wall_s'],sampled_points=len(points),owner=list(owner(event['data'])))
        self.records.append(record)
        return points,record
