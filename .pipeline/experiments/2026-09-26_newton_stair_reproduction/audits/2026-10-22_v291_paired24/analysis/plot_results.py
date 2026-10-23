"""Standalone scientific figures; fixed full-recorded values, shared zero scales."""
from pathlib import Path
import os,json,math
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/v291-paired24-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import MaxNLocator
HERE=Path(__file__).resolve().parents[1]
summary=json.loads((HERE/'results/summary.json').read_text());assert summary['full_geometry'] and len(summary['runs'])==24
rows=summary['runs'];out=HERE/'figures';out.mkdir(exist_ok=True)
font=Path('/System/Library/Fonts/STHeiti Medium.ttc')
font_manager.fontManager.addfont(str(font));font_name=font_manager.FontProperties(fname=str(font)).get_name()
plt.rcParams.update({'font.size':13,'font.family':font_name,'svg.fonttype':'path','axes.spines.top':False,'axes.spines.right':False,'axes.spines.left':False,'axes.edgecolor':'#c5cec1','xtick.color':'#65756f','ytick.color':'#233b37','axes.labelcolor':'#233b37','text.color':'#233b37','savefig.facecolor':'#fffefa'})
colors={'v290':'#426e91','v291':'#23694c'}
all_values=[r['stop']['worst_episode_cm'] for r in rows if r['stop'].get('worst_episode_cm') is not None]
limit=max(5.,math.ceil(max(all_values,default=0)/5)*5)*1.22
for case in ('D07','CD12','S04','A04'):
 fig,axes=plt.subplots(1,2,figsize=(8.6,3.5),sharey=True);fig.subplots_adjust(left=.09,right=.98,top=.84,bottom=.22,wspace=.22)
 for ax,metric,title in zip(axes,('first','worst'),('第一次喊停后的位移 · cm','这一趟最差停步位移 · cm')):
  ax.set_facecolor('#fffefa');ax.set_title(title,loc='left',fontsize=13,pad=13)
  ax.set_xlim(0,limit);ax.set_ylim(3.55,.45);ax.set_yticks([1,2,3],['1','2','3']);ax.tick_params(axis='y',length=0);ax.xaxis.set_major_locator(MaxNLocator(nbins=4));ax.grid(axis='x',color='#e5e8df',linewidth=.7);ax.set_axisbelow(True)
  for repeat in (1,2,3):
   for version,dy in [('v290',-.16),('v291',.16)]:
    r=next(r for r in rows if r['case_id']==case and r['repeat']==repeat and r['variant']==version);first=r['stop'].get('first');episode=first if metric=='first' else max(r['stop']['episodes'],key=lambda e:e['max_displacement_cm'],default=None);value=episode['max_displacement_cm'] if episode else None;censored=bool(episode and episode['pd_entry_censored']);y=repeat+dy
    if value is None:ax.text(limit*.025,y,'缺测',va='center',color=colors[version],fontsize=11);continue
    ax.barh(y,value,height=.27,facecolor='none' if censored else colors[version],edgecolor=colors[version],hatch='////' if censored else None,linewidth=1)
    ax.text(value+limit*.025,y,f'{value:.1f}'+(' *' if censored else ''),va='center',fontsize=11,color=colors[version])
 axes[0].set_ylabel('第几次',labelpad=8)
 fig.text(.09,.07,'旧版 v290',color=colors['v290'],fontsize=13);fig.text(.29,.07,'新版 v291',color=colors['v291'],fontsize=13);fig.text(.50,.07,'* 这次停步未开始 PD 接管',fontsize=10,color='#65756f')
 fig.savefig(out/f'{case}_stop_comparison.svg',bbox_inches='tight');fig.savefig(out/f'{case}_stop_comparison.png',dpi=160,bbox_inches='tight');plt.close(fig)
print('Wrote four source-backed SVG/PNG figures with identical axis limits:',limit)

# Explicit diagnostic examples, in addition to (not instead of) all24 values.
phase_colors={'RL':'#dca988','STAND_SETTLING':'#f1dbaa','STAND_TRANSITION':'#b6d1bc','FIXED_STAND':'#6b9f85','REJOIN':'#a5bbc9'}
fig,axes=plt.subplots(2,2,figsize=(9,5.6),sharex=True,sharey=True)
fig.subplots_adjust(left=.09,right=.98,top=.9,bottom=.2,hspace=.38,wspace=.18)
for col,case in enumerate(('S04','A04')):
 for row,version in enumerate(('v290','v291')):
  ax=axes[row,col];r=next(r for r in rows if r['case_id']==case and r['variant']==version and r['repeat']==1);e=r['stop']['first'];points=e['plot'];start=e['start_s']
  ax.set_title(f'{case} 第 1 次 · '+('旧版' if version=='v290' else '新版'),loc='left',fontsize=12)
  ax.set_facecolor('#fffefa');ax.plot([p['t']-start for p in points],[p['cm'] for p in points],color=colors[version],linewidth=2)
  for a,b in zip(points,points[1:]):ax.axvspan(a['t']-start,b['t']-start,ymin=0,ymax=.06,color=phase_colors[a['mode']],linewidth=0)
  if e['pd_entry_s'] is not None:
   t=e['pd_entry_s']-start;ax.axvline(t,color='#6b9f85',linestyle=':',linewidth=1);ax.text(t+.12,31,'开始 PD',fontsize=9,color='#567b63',rotation=90,va='top')
  ax.set_ylim(0,34);ax.set_xlim(0,12);ax.grid(axis='y',color='#e5e8df',linewidth=.7);ax.set_axisbelow(True)
  if col==0:ax.set_ylabel('位移 · cm')
  if row==1:ax.set_xlabel('全零命令生效后 · 秒')
fig.text(.09,.08,'底部阶段条：',fontsize=10)
for x,mode,label in [(.29,'STAND_SETTLING','等待接管'),(.48,'STAND_TRANSITION','PD 交接'),(.66,'RL','退回走路控制'),(.87,'FIXED_STAND','站立')]:
 fig.text(x,.08,label,color='#163a30',fontsize=11,bbox=dict(facecolor=phase_colors[mode],edgecolor=phase_colors[mode],boxstyle='round,pad=.25'))
fig.savefig(out/'handoff_first_repeat.svg',bbox_inches='tight');fig.savefig(out/'handoff_first_repeat.png',dpi=160,bbox_inches='tight');plt.close(fig)
for path in out.glob('*.svg'):
 path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')
