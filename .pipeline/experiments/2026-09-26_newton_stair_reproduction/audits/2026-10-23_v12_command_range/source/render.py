"""Local scientific figures from verified compact results; no metric recomputation."""
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir())/'v12-command-range-mpl'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
BLUE='#326B9D'; GOLD='#D79B31'; GREY='#D6DBE0'; DARK='#263746'; ORANGE='#BB6039'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                     'axes.labelcolor':DARK,'text.color':DARK,'xtick.color':DARK,'ytick.color':DARK,
                     'axes.edgecolor':'#AAB3BA','grid.color':'#E2E6E9','svg.fonttype':'none'})
records=[json.loads(s) for s in (ROOT/'results/extract01.jsonl').read_text().splitlines()]
runs=[r for r in records if r['type']=='run']
intervals=json.loads((ROOT/'results/pure_yaw_intervals.json').read_text())


def label(r):
    prefix='old10' if r['cohort']=='original10' else 'pair'
    suffix='' if prefix=='old10' else f" r{r['repeat']}"
    return f"{prefix} {r['variant']} {r['case_id']}{suffix}" + (' *' if r['analysis']['window_kind']!='goal_circle' else '')


def save(fig,name):
    fig.savefig(ROOT/'figures'/f'{name}.png',dpi=160,bbox_inches='tight',facecolor='white')
    fig.savefig(ROOT/'figures'/f'{name}.svg',bbox_inches='tight',facecolor='white')
    svg = ROOT/'figures'/f'{name}.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    plt.close(fig)


fig,ax=plt.subplots(figsize=(12.8,13.5));y=np.arange(len(runs));left=np.zeros(len(runs))
for key,title,color,hatch in [('zero','Zero translation',GREY,''),('below_0p2','0 < speed < 0.2 m/s',BLUE,''),
                              ('exact_0p2','Exactly 0.2 m/s',ORANGE,'//'),('above_0p2','Speed > 0.2 m/s',GOLD,'')]:
    values=np.array([r['analysis']['bands'][key]['share_all']*100 for r in runs])
    if not np.any(values):continue
    ax.barh(y,values,left=left,height=.70,color=color,label=title,hatch=hatch)
    left+=values
ax.set_yticks(y,[label(r) for r in runs]);ax.invert_yaxis();ax.set_xlim(0,100)
ax.set_xlabel('Share of the declared window (%) — includes stops')
ax.set_xticks([0,25,50,75,100]);ax.xaxis.grid(True);ax.set_axisbelow(True)
ax.axhline(9.5,color=DARK,linewidth=.8)
ax.legend(loc='lower left',bbox_to_anchor=(0,1.015),ncol=3,frameon=False)
for i,r in enumerate(runs):ax.text(101.5,i,f"{r['analysis']['duration_s']:.1f} s",va='center',fontsize=9)
ax.text(101.5,-1,'Window',fontsize=9)
fig.suptitle('Terminal command exposure — all 34 retained recordings',x=.04,y=.985,ha='left',fontsize=17,weight='bold')
fig.text(.04,.025,'* Never entered the 25 cm circle: declared fallback window; kept separate in group comparisons.\nExact 0.2 m/s duration = 0. Shares use applied commands and recorded simulation time. No new physics.',fontsize=10)
fig.subplots_adjust(left=.24,right=.89,top=.92,bottom=.09)
save(fig,'command_exposure')

fig,axes=plt.subplots(1,2,figsize=(11,4.5),sharey=True)
for ax,run in zip(axes,['pair24_v291_CD12_r1','pair24_v291_S04_r1']):
    r=next(r for r in runs if r['run']==run);b=[r['analysis']['fine_bands'][k] for k in ['le_0.05','le_0.1']];x=np.arange(2)
    command=[q['mean_command_mps']*100 for q in b];measured=[q['mean_axis_mps']*100 for q in b]
    ax.bar(x-.17,command,.32,color=BLUE,label='Commanded speed')
    ax.bar(x+.17,measured,.32,color=GOLD,label='Measured along command')
    for i,(c,m,q) in enumerate(zip(command,measured,b)):
        ax.text(i-.17,c+.12,f'{c:.2f}',ha='center',fontsize=10)
        ax.text(i+.17,max(m,0)+.12,f'{m:.2f}',ha='center',fontsize=10)
        ax.text(i,6.35,f"{q['duration_s']:.2f} s observed",ha='center',fontsize=9)
    ax.set_xticks(x,['(0, 0.05] m/s','(0.05, 0.10] m/s']);ax.axhline(0,color=DARK,linewidth=.8)
    ax.set_ylim(-.35,6.8);ax.set_title(run.replace('pair24_','').replace('_',' '));ax.yaxis.grid(True);ax.set_axisbelow(True)
axes[0].set_ylabel('Speed (cm/s)');axes[0].legend(frameon=False,loc='upper left',bbox_to_anchor=(0,1.30),ncol=2)
fig.suptitle('Previously reported low-speed stall cases',x=.04,y=.99,ha='left',fontsize=16,weight='bold')
fig.text(.04,.015,'Time-weighted terminal observations on terrain, including transitions. These averages do not select a flat-ground speed floor.',fontsize=9)
fig.subplots_adjust(left=.08,right=.98,top=.74,bottom=.18,wspace=.16)
save(fig,'low_speed_stalls')

fig,ax=plt.subplots(figsize=(10,5.3))
for variant,color,marker in [('v290',BLUE,'o'),('v291',GOLD,'s')]:
    selected=[q for q in intervals if ('_'+variant+'_') in q['run']]
    ax.scatter([q['duration_s'] for q in selected],[q['max_xy_displacement_cm'] for q in selected],
               s=45,color=color,marker=marker,label=variant,alpha=.8,edgecolor='white',linewidth=.4)
for q in sorted(intervals,key=lambda x:x['duration_s'],reverse=True)[:2]:
    txt=q['run'].replace('pair24_','').replace('_',' ')+'\n'+f"{math.degrees(abs(q['heading_change_rad'])):.1f}° observed turn"
    offset=(-145,-39) if q['duration_s']>1.2 else (15,4)
    ax.annotate(txt,(q['duration_s'],q['max_xy_displacement_cm']),xytext=offset,textcoords='offset points',
                fontsize=10,arrowprops=dict(arrowstyle='-',color=DARK,lw=.7))
ax.set_xlim(0,1.7);ax.set_ylim(0,4.3);ax.set_xlabel('Pure-yaw interval duration (s)');ax.set_ylabel('Maximum sampled XY displacement (cm)')
ax.grid(True);ax.set_axisbelow(True);ax.legend(frameon=False,loc='upper left')
ax.set_title('39 terminal pure-yaw intervals',loc='left',pad=16,fontsize=16,weight='bold')
fig.text(.08,.035,'33 intervals lasted ≤0.22 s. Largest observed turn: 50.4°. None establishes 90°/180° turn clearance.',fontsize=10)
fig.subplots_adjust(left=.09,right=.97,top=.86,bottom=.19)
save(fig,'pure_yaw_drift')
inputs=['results/extract01.jsonl','results/pure_yaw_intervals.json']
files={str(p.relative_to(ROOT)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in (ROOT/'figures').glob('*')}
(ROOT/'results/plot_provenance.json').write_text(json.dumps(dict(renderer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    matplotlib_version=matplotlib.__version__,inputs={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in inputs},files=files),indent=2)+'\n')
print('Rendered three scientific figures as PNG/SVG.')
