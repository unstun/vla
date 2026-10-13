"""Build an offline Chinese video + Matplotlib timing report from one recording."""
from pathlib import Path
import argparse,base64,csv,hashlib,html,io,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from curve_overlay import Overlay,owner

def svg_plot(rows,duration,log=False,stops=()):
    x=np.array([r['t'] for r in rows]);y=np.array([r['ms'] for r in rows]);ok=np.array([r['success'] for r in rows])
    fig=plt.figure(figsize=(12,3.5),facecolor='#ffffff');ax=fig.add_axes([.075,.18,.905,.76])
    # Break across inactive periods; never imply computations during a stop.
    px=[];py=[]
    for i,(a,b) in enumerate(zip(x,y)):
        if i and a-x[i-1]>.5:px.append(np.nan);py.append(np.nan)
        px.append(a);py.append(b)
    ax.plot(px,py,color='#147d91',lw=.95,alpha=.8,zorder=2)
    ax.scatter(x[ok],y[ok],s=5,color='#147d91',zorder=3)
    ax.scatter(x[~ok],y[~ok],s=34,marker='x',color='#c34646',lw=1.6,zorder=4)
    ax.axhline(1000/30,color='#c18726',lw=1.3,ls=(0,(5,4)),zorder=1)
    for stop in stops:ax.axvline(stop['t'],color='#c34646',alpha=.25,lw=1)
    ax.set_xlim(0,duration)
    if log:ax.set_yscale('log');ax.set_ylim(max(.01,y[y>0].min()*.7),max(y.max()*1.25,40))
    else:ax.set_ylim(0,max(40,y.max()*1.13))
    ax.set_xlabel('Video time (s)',fontsize=10,color='#59616b');ax.set_ylabel('Complete planning round (ms)',fontsize=10,color='#59616b')
    ax.grid(axis='y',color='#e5e8eb',lw=.8);ax.set_axisbelow(True)
    for side in ('top','right'):ax.spines[side].set_visible(False)
    for side in ('left','bottom'):ax.spines[side].set_color('#ccd2d6')
    ax.tick_params(colors='#59616b',labelsize=9)
    stream=io.StringIO();fig.savefig(stream,format='svg',metadata={'Date':None});plt.close(fig)
    text=stream.getvalue();return text[text.index('<svg'):]

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--analysis',type=Path,required=True);p.add_argument('--render',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    frames=json.loads((a.render/'curve_frames.json').read_text());origin=frames[0]['source_wall_s'];duration=len(frames)/30
    raw=list(csv.DictReader((a.analysis/'latency.csv').open()))
    rows=[dict(t=float(r['wall_s_mac'])-origin,ms=float(r['solve_ms']),success=bool(int(r['success'])),simulation_s=float(r['simulation_s'])) for r in raw]
    assert rows and len(rows)==json.loads((a.analysis/'metrics.json').read_text())['planning']['completed']
    assert all(0<=r['t']<=duration and r['ms']>=0 for r in rows)
    overlay=Overlay(a.source,a.analysis/'latency.csv');stops=[];seen=set()
    for event in overlay.events:
        if event['event']!='scan_cancel' or owner(event['data']) in seen:continue
        seen.add(owner(event['data']));stops.append(dict(t=event['host_wall_s']-origin,reason=event['data'].get('reason','')))
    video=a.render/'newton_stair_recorded.mp4';video_bytes=video.read_bytes();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    values=np.array([r['ms'] for r in rows]);metrics=json.loads((a.analysis/'metrics.json').read_text());status=metrics['terminal']['backend_terminal_status']
    meta=dict(run=a.source.name,physical_version='v116',native_version='v114',display_version='v117',terminal=status,rounds=len(rows),successes=sum(r['success'] for r in rows),median_ms=float(np.median(values)),p95_ms=float(np.percentile(values,95)),maximum_ms=float(values.max()),budget_ms=1000/30,over_budget=int((values>1000/30).sum()),source_splines=overlay.total_splines,visible_curve_frames=sum(r['trajectory_id'] is not None for r in frames),video_seconds=duration,video_sha256=sha(video),latency_csv_sha256=sha(a.analysis/'latency.csv'),source_states_sha256=sha(a.source/'video_states.json'),clock_mapping=metrics['clock_mapping'],prior_attempt='attempt01 transport timeout; preserved, not included in these curves/timings')
    data=dict(meta=meta,rounds=rows,frames=[dict(t=r['display_time_s'],id=r['trajectory_id'],ms=r['latest_completed_solve_ms']) for r in frames],stops=stops)
    (a.output/'timing_data.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n')
    (a.output/'latency.csv').write_bytes((a.analysis/'latency.csv').read_bytes())
    plots=[svg_plot(rows,duration,log,stops) for log in (False,True)]
    for name,svg in zip(['latency_linear.svg','latency_log.svg'],plots):(a.output/name).write_text(svg)
    template=Path(__file__).with_name('report_template.html').read_text()
    replacements={'__DATA__':json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/'),
      '__VIDEO__':base64.b64encode(video_bytes).decode(),'__LINEAR__':plots[0],'__LOG__':plots[1],
      '__MEDIAN__':f"{meta['median_ms']:.2f}",'__P95__':f"{meta['p95_ms']:.2f}",'__MAX__':f"{meta['maximum_ms']:.2f}",
      '__ROUNDS__':str(meta['rounds']),'__FAILURES__':str(meta['rounds']-meta['successes']),'__OVER__':str(meta['over_budget']),
      '__SPLINES__':str(meta['source_splines']),'__RUN__':html.escape(a.source.name),
      '__STATUS__':'到达终点' if status=='FINISHED' else '本轮未到达终点'}
    for old,new in replacements.items():template=template.replace(old,new)
    output=a.output/'local_planning.html';output.write_text(template)
    meta.update(html=str(output.resolve()),html_sha256=sha(output),offline_self_contained=True,matplotlib_version=matplotlib.__version__)
    (a.output/'provenance.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'html':str(output.resolve()),'bytes':output.stat().st_size,'rounds':len(rows),'splines':overlay.total_splines,'status':status},ensure_ascii=False))
if __name__=='__main__':main()
