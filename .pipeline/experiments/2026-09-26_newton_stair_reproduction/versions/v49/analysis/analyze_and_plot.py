"""Raw-log timing analysis; all outputs stay outside the frozen source manifest."""
from pathlib import Path
import csv, hashlib, json, os, re, tempfile
os.environ.setdefault('MPLCONFIGDIR',str(Path(tempfile.gettempdir())/'v49-mpl'))
os.environ.setdefault('XDG_CACHE_HOME',str(Path(tempfile.gettempdir())/'v49-font-cache'))
Path(os.environ['XDG_CACHE_HOME']).mkdir(exist_ok=True)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
OUT=Path(__file__).resolve().parent
BASE=OUT.parents[2]
FIG=OUT/'time_series'
START=re.compile(r'nominal_replan frequency_hz=([\d.]+) start_schedule_s=([\d.]+) clock=(\w+) ros_s=([\d.]+) state=(\d+) skipped_slots=(\d+)')
END=re.compile(r'nominal_replan_result success=(\d+) wall_s=([\d.]+)')
BUDGET=re.compile(r'V49_BUDGET_RESULT new_plan=(\d+) continued=(\d+) stopped=(\d+) timeout_site=(\S+) wall_ms=([\d.]+) limit_ms=([\d.]+) overrun=(\d+) ros_s=([\d.]+)')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x): p.write_text(json.dumps(x,indent=2)+'\n')
def rows(p):
 with p.open() as f: return [json.loads(s) for s in f if s.strip()]
def stats(a):
 a=np.asarray(a,dtype=float)
 return dict(count=len(a),mean=float(a.mean()),median=float(np.median(a)),p95=float(np.percentile(a,95)),p99=float(np.percentile(a,99)),maximum=float(a.max())) if len(a) else None
def csv_out(p,data):
 if not data: return
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
def analyze(v):
 run=BASE/'runs'/f"{v}_realtime_trial{'02' if v=='v49' else '01'}"
 starts=[]; rounds=[]; budgets=[]; current=None
 for line_no,line in enumerate((run/'scan.log').read_text().splitlines(),1):
  s=START.search(line)
  if s:
   assert s[3]=='wall' and float(s[1])==30
   current=dict(start_line=line_no,start_wall_s=float(s[2]),sim_s=float(s[4]),state=int(s[5]),skipped=int(s[6]),warm_accepts=0,warm_selected=0,warm_fallbacks=0)
   starts.append(current)
  if current is not None:
   current['warm_accepts']+='V48_WARM_RESULT accepted=1' in line
   current['warm_selected']+='V48_WARM_SEED selected=1' in line
   current['warm_fallbacks']+='V48_WARM_RESULT accepted=0 graph_fallback=1' in line
  m=BUDGET.search(line)
  if m:
   event=dict(line=line_no,new_plan=bool(int(m[1])),continued=bool(int(m[2])),stopped=bool(int(m[3])),timeout_site=m[4],wall_ms=float(m[5]),limit_ms=float(m[6]),overrun=bool(int(m[7])),sim_end_s=float(m[8]))
   budgets.append(event)
   if current is not None: current['budget']=event
  m=END.search(line)
  if m:
   assert current is not None,'Unpaired completion'
   r=dict(current,end_line=line_no,success=bool(int(m[1])),solve_ms=float(m[2])*1000)
   r['continued']=r.get('budget',{}).get('continued',False)
   r['stopped']=r.get('budget',{}).get('stopped',False)
   r['timeout_site']=r.get('budget',{}).get('timeout_site','none')
   if v=='v49': assert r['success']==r['budget']['new_plan']
   rounds.append(r);current=None
 assert starts and rounds
 wall=np.array([s['start_wall_s'] for s in starts]);sim=np.array([s['sim_s'] for s in starts])
 assert np.all(np.diff(wall)>0) and np.all(np.diff(sim)>=0)
 exposure=rounds[-1]['start_wall_s']+rounds[-1]['solve_ms']/1000-wall[0]
 frequency=[]
 grid=np.arange(wall[0]+1,wall[-1],.05)
 if wall[-1]-wall[0]>=1: grid=np.append(grid,wall[-1])
 for t in grid:
  item=dict(wall_s=float(t),simulation_s=float(np.interp(t,wall,sim)))
  item['attempt_hz']=int(np.sum((wall>t-1)&(wall<=t)))
  for key in ('success','continued','stopped'):
   selected=[r['start_wall_s'] for r in rounds if r[key]]
   item[key+'_hz']=sum(t-1<x<=t for x in selected)
  frequency.append(item)
 result=json.loads((run/'result.json').read_text());backend=json.loads((run/'backend_latest.json').read_text())
 global_times=[x['started_wall_s'] for x in backend.get('global_refresh',{}).get('history',[]) if x.get('status')=='published']
 sensors=rows(run/'sensor.jsonl');positions=np.array([s['body_sensor']['position'] for s in sensors])
 pace=result.get('realtime_pacing',{})
 commands=rows(run/'command_frequencies.jsonl');rates={}
 for topic in sorted(set(x['topic'] for x in commands)):
  ts=[x['wall_monotonic_s'] for x in commands if x['topic']==topic and wall[0]<=x['wall_monotonic_s']<=rounds[-1]['start_wall_s']+rounds[-1]['solve_ms']/1000]
  rates[topic]=dict(samples=len(ts),hz=(len(ts)-1)/(ts[-1]-ts[0]) if len(ts)>1 else None)
 summary=dict(run=run.name,starts=len(starts),completed_rounds=len(rounds),incomplete_starts=len(starts)-len(rounds),active_wall_exposure_s=exposure,
     attempt_hz=(len(wall)-1)/(wall[-1]-wall[0]) if len(wall)>1 else None,
     new_plan_hz=sum(r['success'] for r in rounds)/exposure,
     continuation_hz=sum(r['continued'] for r in rounds)/exposure,
     new_plans=sum(r['success'] for r in rounds),continued=sum(r['continued'] for r in rounds),stopped=sum(r['stopped'] for r in rounds),
     solve_ms=stats([r['solve_ms'] for r in rounds]),over_25ms=sum(r['solve_ms']>25 for r in rounds),over_33_333ms=sum(r['solve_ms']>1000/30 for r in rounds),over_100ms=sum(r['solve_ms']>=100 for r in rounds),
     all_budget_calls=len(budgets),all_budget_ms=stats([x['wall_ms'] for x in budgets]),all_budget_over_33_333ms=sum(x['wall_ms']>1000/30 for x in budgets),all_budget_over_100ms=sum(x['wall_ms']>=100 for x in budgets),
     skipped_slots=sum(s['skipped'] for s in starts),first_sim_s=float(sim[0]),last_sim_s=float(sim[-1]),
     physical_duration_s=result.get('physics_duration_s'),path_length_xy_m=float(np.linalg.norm(np.diff(positions[:,:2],axis=0),axis=1).sum()),
     final_xyz=positions[-1].tolist(),controller_active_rates=rates,realtime_pacing=pace,terminal_results=backend.get('terminal_results'),stop_flow=backend.get('stop_flow'),
     global_refresh_hz=(len(global_times)-1)/(global_times[-1]-global_times[0]) if len(global_times)>1 else None,
     global_refresh_samples=len(global_times), final_gate=backend.get('gate'),
     full_route_accepted=False,local_30hz_validated=False,
     source_sha256={str(p.relative_to(BASE)):sha(p) for p in (run/'scan.log',run/'result.json',run/'backend_latest.json',run/'sensor.jsonl',run/'command_frequencies.jsonl')})
 dump(OUT/f'{v}_rounds.json',rounds);dump(OUT/f'{v}_budget_events.json',budgets)
 flat=[{k:r[k] for k in ('start_line','end_line','start_wall_s','sim_s','solve_ms','success','continued','stopped','timeout_site','warm_accepts','warm_selected','warm_fallbacks')} for r in rounds]
 csv_out(FIG/f'{v}_round_latency.csv',flat);csv_out(FIG/f'{v}_frequency.csv',frequency)
 return summary,rounds,frequency

def main():
 FIG.mkdir(exist_ok=True)
 data={v:analyze(v) for v in ('v48','v49')}
 metrics={v:d[0] for v,d in data.items()}
 metrics['definitions']={'frequency':'Trailing 1 wall second (t-1,t], sampled every .05 s; plotted at simulation time interpolated from logged start pairs. First partial window omitted. Completion categories attributed to their attempt start. No interpolation beyond last attempt.',
 'attempt_rate':'(N starts - 1)/(last start - first start), wall clock.',
 'new_plan_and_continuation_rate':'Outcome count / (last completed round end - first attempt start), wall clock; continuation is not a new plan.',
 'solve_latency':'Whole nominal replan wall time including timeout handling, at simulation time of attempt start. All V49_BUDGET_RESULT calls also summarized, including independent safety recovery.',
 'comparison':'Same profile, separate physics runs and unequal exposure; no claim of paired live inputs or general hard real-time assurance.'}
 dump(OUT/'metrics.json',metrics)
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none','pdf.fonttype':42})
 fig,axs=plt.subplots(2,2,figsize=(14,8.6),sharex='col',sharey='row',gridspec_kw={'height_ratios':[1,1.5]})
 fig.subplots_adjust(left=.075,right=.98,top=.80,bottom=.20,hspace=.32,wspace=.15)
 fig.text(.075,.95,'Local planning | v48 → v49 solve budget',fontsize=22,weight='bold')
 fig.text(.075,.91,'gpu5070ti · Same Building profile · Rolling rates use wall time; x-axes use simulation time',fontsize=11,color='#526174')
 for col,v in enumerate(('v48','v49')):
  m,rounds,freq=data[v]; rate,lat=axs[:,col]
  rate.set_title(f"{v} · {m['completed_rounds']:,} completed rounds · {m['active_wall_exposure_s']:.1f} s active",loc='left',fontsize=12)
  if freq:
   ts=[x['simulation_s'] for x in freq]
   rate.plot(ts,[x['attempt_hz'] for x in freq],color='#506985',lw=1,label='Attempts')
   rate.plot(ts,[x['success_hz'] for x in freq],color='#167a66',lw=1.5,label='New plans')
   if v=='v49': rate.plot(ts,[x['continued_hz'] for x in freq],color='#dc921b',lw=1,label='Safe continuation')
  else: rate.text(.04,.55,'Less than 1 s of planning exposure;\nno full rolling window.',transform=rate.transAxes)
  rate.axhline(30,color='#343d48',ls='--',lw=1,label='30 Hz target');rate.set_ylim(-1,34)
  groups=[('Fast warm-start <10 ms','#149779','o',lambda r:r['success'] and r['warm_accepts']>0 and r['solve_ms']<10),
          ('Other new plan','#4477aa','o',lambda r:r['success'] and not(r['warm_accepts']>0 and r['solve_ms']<10)),
          ('Safe continuation','#dc921b','D',lambda r:r['continued']),
          ('Stop / failed round','#c34852','x',lambda r:not r['success'] and not r['continued'])]
  for label,color,marker,predicate in groups:
   selected=[r for r in rounds if predicate(r)]
   if selected: lat.scatter([r['sim_s'] for r in selected],[r['solve_ms'] for r in selected],s=12,alpha=.75,color=color,marker=marker,label=label,zorder=3)
  lat.axhspan(.1,10,color='#149779',alpha=.05)
  for value,label,color,style in ((10,'Fast regime: 10 ms','#149779',':'),(25,'v49 total budget: 25 ms','#dc921b','-.'),(1000/30,'30 Hz interval: 33.3 ms','#343d48','--')):
   lat.axhline(value,color=color,ls=style,lw=.9)
  lat.set_yscale('log');lat.set_ylim(.4,1600);lat.set_yticks([1,3,10,25,100,300,1000],labels=['1','3','10','25','100','300','1000'])
  lat.set_xlabel('Simulation time (s)')
  lat.set_title(f"Median {m['solve_ms']['median']:.2f} ms · P99 {m['solve_ms']['p99']:.2f} ms · Max {m['solve_ms']['maximum']:.2f} ms",loc='left',fontsize=11)
  for ax in (rate,lat):
   ax.grid(axis='y',color='#e5e9ee',lw=.6);ax.set_axisbelow(True);ax.set_xlim(10,90)
  if m['stopped']:
   rate.text(.98,.65,f"{m['stopped']} timeout stop commands\n{m['continued']} safe continuations",ha='right',transform=rate.transAxes,fontsize=9,color='#9c3740')
  rate.legend(loc='lower left',fontsize=8,ncol=2,frameon=False)

 handles,labels=axs[1,1].get_legend_handles_labels()
 fig.legend(handles,labels,loc='upper left',bbox_to_anchor=(.075,.873),ncol=4,fontsize=9,frameon=False)
 axs[0,0].set_ylabel('Local planning frequency (Hz)');axs[1,0].set_ylabel('Whole-round solve latency (ms, log scale)')
 fig.text(.075,.125,'Horizontal latency guides: 10 ms fast regime · 25 ms v49 total budget · 33.3 ms at 30 Hz.',fontsize=10)
 fig.text(.075,.09,'Continuation reuses a freshly checked existing curve; it is counted separately from new planning. Stops do not count as planning success.',fontsize=10,color='#526174')
 fig.text(.075,.055,'v49 failed acceptance: 3 rounds exceeded 33.3 ms, and the new timeout notice did not close the backend command gate.',fontsize=10,color='#526174')
 for ext in ('png','svg','pdf'): fig.savefig(FIG/f'v48_v49_planning_time_series.{ext}',dpi=230,facecolor='white')
 plt.close(fig)
 outputs={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='provenance.json' and '__pycache__' not in p.parts}
 dump(FIG/'provenance.json',{'analysis_script_sha256':sha(Path(__file__)),'inputs':{v:data[v][0]['source_sha256'] for v in data},'outputs':outputs,'definitions':metrics['definitions']})
 print(json.dumps({v:{k:x[k] for k in ('starts','completed_rounds','attempt_hz','new_plan_hz','continued','stopped','solve_ms','over_100ms','all_budget_over_100ms','path_length_xy_m','physical_duration_s')} for v,x in metrics.items() if v!='definitions'},indent=2))
if __name__=='__main__':main()
