"""Plot verified compact diagnostics; raw captures remain on gpu5070ti."""
from pathlib import Path
import csv
import hashlib
import json
import os
import numpy as np

os.environ.setdefault('MPLCONFIGDIR','/tmp/v57-after70-mpl')
os.environ.setdefault('XDG_CACHE_HOME','/tmp/v57-after70-cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent


def rows(name):
    with (HERE/name).open() as f:return list(csv.DictReader(f))


def main():
    native=json.loads((HERE/'attempt01/result.json').read_text())['rows']
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(3,2,figsize=(13,10),sharex=True)
    inputs={}
    for c,n in enumerate([1,2]):
        run=f'v57_realtime_trial{n:02d}'
        summary=json.loads((HERE/(run+'_summary.json')).read_text())
        motion=json.loads((HERE/(run+'_motion.json')).read_text())
        stage=rows(run+'_stages.csv');track=rows(run+'_motion.csv')
        sample=[r for r in stage if r['warm']=='True' and r['success']=='True']
        x=np.array([float(r['sim_s']) for r in sample])
        ax=axes[0,c]
        ax.scatter(x,[float(r['solve_ms']) for r in sample],s=9,color='#8C949E',alpha=.5,label='Complete warm-success round')
        ax.plot(x,[float(r['goal_search_ms']) for r in sample],color='#C16C14',lw=1.3,label='Final-goal search')
        clean=[r for r in sample if float(r['cloud_calls'])==0]
        ax.scatter([float(r['sim_s']) for r in clean],[float(r['warm_seed_ms']) for r in clean],s=6,color='#18825E',alpha=.55,label='Warm seed, no cloud callback')
        ax.axhline(1000/30,color='#333333',ls='--',lw=.8)
        ax.set_yscale('log');ax.set_ylim(.003,250)
        ax.set_ylabel('Measured live time (ms)')
        ax.set_title(f'Trial {n}: goal-search cost grows before warm initialization')
        ax.legend(fontsize=8,loc='lower right')
        probe=[r for r in native[run+'_native'] if r['repeat']==0]
        ax=axes[1,c]
        ax.plot([r['sim_s'] for r in probe],[r['closed'] for r in probe],'-o',color='#C16C14',ms=4)
        ax.set_ylim(0,760);ax.set_ylabel('A* expanded nodes\nOffline recorded-input replay')
        ax.set_title('Every sampled goal search returns an empty path')
        ax=axes[2,c]
        ax.plot([float(r['sim_s']) for r in track],[-float(r['along_error_m']) for r in track],color='#7143A3',lw=1,label='Robot ahead of planned start')
        ax.set_ylabel('Along-path position lead (m)',color='#7143A3');ax.set_ylim(-.25,1.25)
        other=ax.twinx()
        mids=[67.5,72.5,77.5,82.5,87.5]
        speed=[motion['bands'][b]['raw_command_speed_mps']['median'] for b in ['65-70','70-75','75-80','80-85','85-90']]
        other.plot(mids,speed,'o--',color='#136E8D',ms=4,lw=1,label='Median commanded speed (5 s)')
        other.set_ylim(0,1.05);other.set_ylabel('Command speed (m/s)',color='#136E8D')
        ax.set_title('Position feedback increasingly reduces forward command')
        lines=ax.get_lines()+other.get_lines();ax.legend(lines,[p.get_label() for p in lines],fontsize=8,loc='upper left')
        ax.set_xlabel('Simulation time (s)')
        onset=summary['first_expensive_goal_after65']['sim_s']
        for ax in axes[:,c]:
            ax.axvline(onset,color='#666666',ls=':',lw=.9)
            ax.set_xlim(65,90);ax.grid(alpha=.2)
        for suffix in ['_summary.json','_motion.json','_stages.csv','_motion.csv']:
            p=HERE/(run+suffix);inputs[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
    fig.suptitle('v57 post-70-second anomaly: repeated failed goal search and trajectory timing lag',fontsize=15)
    fig.tight_layout(rect=(0,.025,1,.97))
    fig.text(.5,.01,'Dotted line: start–goal pair fits A* pool. Upper panel: original live timings. Middle: unchanged-native offline replay, not new physics.',ha='center',fontsize=8)
    for ext in ['png','pdf']:fig.savefig(HERE/('after70_diagnosis.'+ext),dpi=170)
    plt.close(fig)
    provenance=dict(plot_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),inputs=inputs,
        native_result_sha256=hashlib.sha256((HERE/'attempt01/result.json').read_bytes()).hexdigest(),
        outputs={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in ['after70_diagnosis.png','after70_diagnosis.pdf']})
    (HERE/'plot_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')


if __name__=='__main__':main()
