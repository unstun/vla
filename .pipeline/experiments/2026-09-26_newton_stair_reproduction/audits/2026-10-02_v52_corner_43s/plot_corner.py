"""Static scientific figure from compact original-run and native-probe evidence."""
from pathlib import Path
import json
import math
import os
os.environ.setdefault('MPLCONFIGDIR', '/tmp/vla-corner-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
e = json.loads((HERE/'corner_evidence.json').read_text())
r = json.loads((HERE/'result.json').read_text())
plt.rcParams.update({'font.size':10, 'axes.spines.top':False, 'axes.spines.right':False})
fig = plt.figure(figsize=(13.8, 9.6), layout='constrained')
grid = fig.add_gridspec(3,2, width_ratios=(1.2,1))
latency = fig.add_subplot(grid[0,0]); command = fig.add_subplot(grid[1,0], sharex=latency)
reserve = fig.add_subplot(grid[2,0], sharex=latency)
geometry = fig.add_subplot(grid[:,1])
rounds=e['focused_rounds']
# Show all focused round starts from the original parser's small CSV.
import csv
all_rounds=list(csv.DictReader((HERE/'rounds.csv').open()))
for success,color,label in (('True','#188469','Accepted round'),('False','#bd3a32','Failed round')):
    rows=[x for x in all_rounds if x['success']==success]
    latency.scatter([float(x['simulation_s']) for x in rows], [float(x['solve_ms']) for x in rows],
                    s=19, color=color, label=label)
latency.axhline(33.333, color='#777777', ls='--', lw=1, label='30 Hz period: 33.3 ms')
latency.set_ylabel('Solve latency (ms)'); latency.set_ylim(-10,770)
latency.legend(loc='upper left', fontsize=9)
raw=e['raw_series']
command.plot([x['sim_s'] for x in raw], [x['speed_mps'] for x in raw], color='#236a9b', lw=1.6)
command.set_ylabel('Raw XY command\n(m/s)'); command.set_ylim(-.03,.92)
curves=e['same_end_curve_streak'];end=e['last_curve']['end_sim_s']
reserve.plot([x['start_sim_s'] for x in reversed(curves)], [x['duration_s'] for x in reversed(curves)],
             'o',color='#188469', markersize=4, label='Accepted curve remaining duration')
t=np.linspace(curves[-1]['start_sim_s'],47,250)
reserve.plot(t,np.maximum(0,end-t),color='#8b6a20',label='Last curve time remaining')
reserve.set_ylabel('Curve reserve (s)');reserve.set_xlabel('Simulation time (s)');reserve.set_ylim(-.08,1.7)
reserve.legend(loc='upper right',fontsize=9)
for ax in (latency,command,reserve):
    ax.axvline(42.353351593,color='#ae4c77',lw=1.2,ls='--')
    ax.axvline(end,color='#7a7a7a',lw=1,ls=':')
    ax.set_xlim(39,47);ax.grid(alpha=.18)
latency.set_title('Recorded v52: route refresh, solve failure, then command stop',loc='left',fontsize=11)
latency.text(42.42,730,'Route refresh\n42.353 s',fontsize=9,color='#ae4c77')
command.text(43.49,.78,'Curve end 43.380 s\nFirst zero command 43.408 s',fontsize=9)

states={x['case']:x for x in r['probes'] if x['kind']=='state'}
targets={x['case']:x for x in r['probes'] if x['kind']=='target'}
p=np.array(states[1]['start']);old=np.array(states[1]['endpoint']);new=np.array(targets[1]['xyz'])
geometry.plot([p[0],old[0]],[p[1],old[1]],color='#188469',lw=3,label='Remaining old curve (endpoint chord)')
geometry.plot([old[0],new[0]],[old[1],new[1]],'--',color='#bd3a32',lw=1.5,label='Rejected warm connector (chord)')
geometry.scatter(*p[:2],marker='o',color='#188469',s=45);geometry.annotate('Start at first failure',p[:2],xytext=(0,-26), ha='center',textcoords='offset points',fontsize=9)
geometry.scatter(*old[:2],marker='s',color='#188469',s=50);geometry.annotate('Old endpoint',old[:2],xytext=(-94,9),textcoords='offset points',fontsize=9)
geometry.scatter(*new[:2],marker='*',color='#bd3a32',s=140);geometry.annotate('New longer target',new[:2],xytext=(0,-23), ha='center',textcoords='offset points',fontsize=9)
prefix=[x for x in r['probes'] if x['case']==1 and x['kind']=='point' and x['label']=='prefix']
for x,time in zip(prefix,(1.75,.875,.4375)):
    q=x['xyz'];geometry.scatter(*q[:2],marker='x',color='#ab7d21',s=50)
    geometry.annotate(f'Prefix {time:g} s',q[:2],xytext=(7,-3),textcoords='offset points',fontsize=9)
samples=e['applied_samples'];xy=np.array([x['measured']['base_xyz'][:2] for x in samples if 41.8<x['sim_s']<46])
geometry.plot(xy[:,0],xy[:,1],color='#236a9b',lw=1,marker='.',label='Measured body samples')
late=next(x for x in r['probes'] if x['case']==2 and x['kind']=='point' and x['label']=='live_collision_planned')
caps=np.array([x['xyz'][:2] for x in late['caps']]);geometry.plot(caps[:,0],caps[:,1],color='#ae4c77',lw=2)
geometry.scatter(*caps[0],marker='X',color='#ae4c77',s=90,label='Front cap: support association fails')
geometry.scatter(*caps[1],marker='o',facecolor='white',edgecolor='#ae4c77',s=45)
geometry.annotate('Front support rejection\nat later 42.2° query yaw',caps[0],xytext=(17,-45),textcoords='offset points',fontsize=9,arrowprops={'arrowstyle':'->','color':'#ae4c77'})
geometry.set_aspect('equal');geometry.set_xlim(6.95,8.95);geometry.set_ylim(-4.65,-.95)
geometry.set_xlabel('World X (m)');geometry.set_ylabel('World Y (m)');geometry.grid(alpha=.18)
geometry.set_title('Corner geometry and native safety probes',loc='left',fontsize=11)
geometry.legend(loc='upper left',fontsize=8)
fig.suptitle('v52 corner diagnosis: failure begins before the safe curve expires',fontsize=15)
fig.savefig(HERE/'corner_diagnosis.png',dpi=160)
fig.savefig(HERE/'corner_diagnosis.pdf')
print(json.dumps({'png_bytes':(HERE/'corner_diagnosis.png').stat().st_size,
                  'pdf_bytes':(HERE/'corner_diagnosis.pdf').stat().st_size}))
