"""Build a per-stop review page and ordinary scientific plots from audited data."""
import argparse
import csv
import gzip
import hashlib
import html
import json
from pathlib import Path
import shutil
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

HERE=Path(__file__).resolve().parent
LABELS={'bounded_start':'短暂起步／重新起步','bounded_brake':'短暂刹车／转向前减速',
        'brief_adjustment':'短暂轨迹／跟踪调整','endpoint_correction':'包含轨迹尾端小速度纠偏',
        'prolonged_low_review':'较长曲线边界段（单列核查）'}


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--analysis',type=Path,required=True);a=p.parse_args()
    results=HERE/'results';results.mkdir(exist_ok=True)
    figures=HERE/'figures';figures.mkdir(exist_ok=True)
    data=[];plots=[]
    for n in range(1,6):
        path=a.analysis/f'attempt{n:02d}.json';d=json.loads(path.read_text());data.append(d)
        shutil.copyfile(path,results/path.name)
        with gzip.open(a.analysis/f'plot{n:02d}.json.gz','rt') as f:plots.append(json.load(f))
    shutil.copyfile(a.analysis/'index.json',results/'analysis_index.json')
    low=[dict(run=n,**r) for n,d in enumerate(data,1) for r in d['low_intervals']]
    stops=[dict(r) for d in data for r in d['stops']]
    with (HERE/'stops.csv').open('w') as f:
        names=['id','run','time_s','label','pre10_nonzero_below06_s','pre10_zero_s','pre10_at_least06_s',
               'zero_episode_id','zero_duration_s','zero_max_excursion_m','late_after_2s_excursion_m']
        w=csv.DictWriter(f,fieldnames=names);w.writeheader()
        for s in stops:
            z=s['zero_episode'] or {}
            w.writerow(dict(id=s['id'],run=s['run'],time_s=s['time_s'],label=s['label'],
                pre10_nonzero_below06_s=s['pre10']['nonzero_below06_s'],pre10_zero_s=s['pre10']['zero_s'],
                pre10_at_least06_s=s['pre10']['at_least06_s'],zero_episode_id=z.get('id'),
                zero_duration_s=z.get('duration_s'),zero_max_excursion_m=z.get('maximum_excursion_m'),
                late_after_2s_excursion_m=z.get('late_after_2s_excursion_m')))
    with (HERE/'low_intervals.csv').open('w') as f:
        names=['id','run','start_s','end_s','duration_s','classification','command_median_mps','actual_median_mps',
               'endpoint_position_error_median_m','raw_value_match_fraction','estimated_expired_endpoint_s']
        w=csv.DictWriter(f,fieldnames=names,extrasaction='ignore');w.writeheader();w.writerows(low)

    font=Path('/System/Library/Fonts/STHeiti Medium.ttc')
    if font.exists():
        font_manager.fontManager.addfont(str(font))
        plt.rcParams['font.family']=font_manager.FontProperties(fname=str(font)).get_name()
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.unicode_minus':False})
    for stop in stops:
        d=data[stop['run']-1];plot=plots[stop['run']-1]
        t=np.asarray(plot['time_s']);cmd=np.asarray(plot['command']);norm=np.linalg.norm(cmd[:,:2],axis=1)
        actual=np.asarray(plot['actual_speed']);xyz=np.asarray(plot['position'])
        z=stop['zero_episode'];when=stop['time_s']
        left=max(t[0],when-12);right=min(t[-1],max(when+8,(z['end_s']+1) if z else when+8))
        keep=(t>=left)&(t<=right)
        fig,axes=plt.subplots(3,1,figsize=(12,7),sharex=True,gridspec_kw={'height_ratios':[2.1,1,1.3]})
        axes[0].plot(t[keep],norm[keep],color='#1262bd',lw=1.25,label='实际送进 RL 的水平速度')
        axes[0].plot(t[keep],actual[keep],color='#2c8b6f',lw=1.,alpha=.85,label='机身实测水平速度')
        axes[0].axhline(.6,color='#555',ls='--',lw=.9,label='0.6 米/秒巡航参考线')
        axes[0].set_ylim(-.035,max(1.1,float(actual[keep].max())*1.05));axes[0].set_ylabel('m/s');axes[0].legend(loc='upper left',fontsize=8)
        axes[1].plot(t[keep],cmd[keep,2],color='#7559a5',lw=1.);axes[1].set_ylabel('转向指令 (rad/s)')
        for low_row in d['low_intervals']:
            if low_row['end_s']<left or low_row['start_s']>right:continue
            if low_row['classification']=='endpoint_correction':
                for segment in low_row['endpoint_subsegments']:
                    if segment['end_s']>=left and segment['start_s']<=right:
                        axes[0].axvspan(max(left,segment['start_s']),min(right,segment['end_s']),color='#e88861',alpha=.25)
            elif low_row['classification']=='prolonged_low_review':
                axes[0].axvspan(max(left,low_row['start_s']),min(right,low_row['end_s']),color='#f2d47a',alpha=.25)
        if z:
            k=max(0,int(np.searchsorted(t,z['start_s'],side='right'))-1)
            selected=(t>=z['start_s'])&(t<=z['end_s'])&keep
            displacement=np.linalg.norm(xyz[:,:2]-xyz[k,:2],axis=1)*100
            axes[2].plot(t[selected],displacement[selected],color='#bf5d20',lw=1.3)
            for ax in axes:ax.axvspan(max(left,z['start_s']),min(right,z['end_s']),color='#5c6b7a',alpha=.08)
            if z['duration_s']>2:axes[2].axvline(z['start_s']+2,color='#bf5d20',ls=':',lw=.9)
        axes[2].set_ylabel('连续零速期间\n位置变化 (cm)');axes[2].set_xlabel('原始仿真时间（秒）')
        for ax in axes:
            ax.axvline(when,color='#b6313a',ls='--',lw=.85);ax.grid(alpha=.2);ax.set_xlim(left,right)
        axes[0].set_title(f"{stop['id']} | 第 {stop['run']} 轮，{when:.3f} 秒撤销／终点事件")
        fig.tight_layout();fig.savefig(figures/(stop['id']+'.png'),dpi=120);plt.close(fig)
    summary=dict(samples=sum(d['summary']['samples'] for d in data),events=len(stops),runs=5,
        actual_policy_input_error=max(d['receipt']['effective_vs_actual_policy_input_max_error'] for d in data),
        transport_value_match_fraction=[d['summary']['nonzero_raw_value_match_fraction'] for d in data],
        long_low_counts={str(th):sum(r['duration_s']>=th for r in low) for th in (1,2,3)},
        endpoint_intervals=[r for r in low if r['classification']=='endpoint_correction'],
        long_boundary_intervals=[r for r in low if r['classification']=='prolonged_low_review'],
        zeros_are_not_low_walking=True,source_analysis=sha(HERE/'analyze.py'),display_source=sha(Path(__file__)))
    (results/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    options=''.join(f'<option value="{s["id"]}">{s["id"]} · 第{s["run"]}轮 {s["time_s"]:.2f}秒 · {html.escape(s["label"])}</option>' for s in stops)
    table=''.join(f'<tr data-event="{s["id"]}"><td><button onclick="show(\'{s["id"]}\')">{s["id"]}</button></td><td>{s["time_s"]:.2f}</td><td>{s["pre10"]["nonzero_below06_s"]:.2f}</td><td>{s["pre10"]["zero_s"]:.2f}</td><td>{s["pre10"]["at_least06_s"]:.2f}</td><td>{html.escape(s["label"])}</td></tr>' for s in stops)
    long_table=''.join(f'<tr><td>第{r["run"]}轮</td><td>{r["start_s"]:.2f}–{r["end_s"]:.2f}</td><td>{r["duration_s"]:.2f}</td><td>{r["command_median_mps"]:.3f}</td><td>{LABELS[r["classification"]]}</td></tr>' for r in low if r['duration_s']>=2 or r['classification']=='endpoint_correction')
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>原路线停车前后的真实 RL 速度</title>
<style>body{margin:0;background:#f3f5f7;color:#172b42;font:16px/1.65 system-ui,sans-serif}main{max-width:1160px;margin:auto;padding:34px 24px}h1{font-size:30px;line-height:1.3}h2{margin:24px 0 12px;font-size:22px}p{max-width:1000px}.card{background:white;border:1px solid #dfe5ed;border-radius:12px;padding:22px;margin:20px 0}.facts{display:flex;gap:12px;flex-wrap:wrap}.facts span{background:#e5eef9;padding:9px 16px;border-radius:8px}button,select{font:inherit;border:1px solid #bdc9d9;border-radius:6px;background:white;padding:6px 12px;color:#185794;cursor:pointer}select{max-width:100%;width:100%}button:hover{background:#e5eef9}img{width:100%;height:auto}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:9px 10px;border-bottom:1px solid #e5e9f0;text-align:left}th{background:#eaf0f7}.table{overflow:auto}.note{color:#56687b;font-size:14px}.warn{border-left:4px solid #d47937;padding-left:16px}a{color:#185794}</style>
<main><p class="note">v177 五轮原始路线 · 历史记录分析 · 没有改导航或重跑仿真</p><h1>确实有持续小速度纠偏，<br>但零速后漂移不能全部归到它身上。</h1>
<div class="facts"><span>30,741 帧真实模型输入</span><span>35 个停车／撤销事件</span><span>5 段尾端小速度纠偏</span></div>
<div class="card"><p><b>最明确的一段：</b>第一轮 58.82–69.01 秒，非零行走指令持续低于 0.6，约 10.2 秒，中位数仅 0.018 米/秒。末端只差约 2.2 厘米，控制器仍要求继续纠偏，模型一直处于 RL 控制。</p><p><b>必须分开的一段：</b>第一轮约 80.19 秒后，三项指令连续为零约 15.9 秒，身体仍挪约 0.96 米；扣掉前两秒后仍挪约 0.90 米。它不是这 15.9 秒里还有小速度行走指令。</p><p class="warn">低速与原地反复纠偏有直接对应；是否改变停车前速度就能避免后续漂移，还没有同姿态对照证明。正常起步、刹车、原地转向和明确零速均单独统计。</p></div>
<section class="card" id="review"><h2>逐次看：真正送进 RL 的指令与身体运动</h2><select id="selector" onchange="show(this.value,false)">OPTIONS</select><p id="description"></p><a id="figure_link" href="figures/R1-04.png" target="_blank" rel="noopener"><img id="figure" alt="停车前后 RL 速度、转向和零速期间位移图"><span>点击曲线打开完整大图</span></a><p class="note">蓝线：模型收到的水平速度；绿线：身体实际速度。中图单列转向指令。底图只统计关联的连续三项零速段，包含刹车距离；橙色点线标记零速后的第 2 秒。红色虚线是撤销／终点事件，可晚于零速开始。橙色底色是尾端纠偏，黄色是较长边界段，灰色是连续零速。同一个长零速段可能关联多次重试，不能重复当成独立漂移。</p></section>
<section class="card"><h2>全部 35 个事件：停车前 10 秒实际收到什么</h2><p class="note">“低速”仅指非零水平速度小于 0.6；零速与原地转向不算低速行走。表中未列的少量时间是原地转向或记录开始前空窗。</p><div class="table"><table><thead><tr><th>事件</th><th>时间/秒</th><th>非零低速/秒</th><th>三项零速/秒</th><th>≥0.6/秒</th><th>原始停车原因</th></tr></thead><tbody>STOP_TABLE</tbody></table></div></section>
<section class="card"><h2>持续低速与尾端纠偏单列</h2><div class="table"><table><thead><tr><th>轮次</th><th>时间/秒</th><th>持续/秒</th><th>指令中位数 m/s</th><th>分类</th></tr></thead><tbody>LOW_TABLE</tbody></table></div><p class="note">其他 7 段超过 2 秒的低速位于连续局部曲线的边界段：旧规则允许，但不据此保证模型适应。这些单列，不冒充“只是正常起步”。2 秒只是筛选阈值；采用 1/2/3 秒分别为 39/11/3 段。短暂边界段也不等于停车能力合格。</p></section>
<details class="card"><summary>证据边界与原始数据</summary><p>逐帧核对有效指令、45 维观测中的指令，以及 450 维实际模型输入的最新指令和十帧历史，误差均为零。所有非零行走指令都在前 0.3 秒的原控制器输出中找到相同三项值；这是值匹配，不声称唯一消息身份。传给模型前未发现再次降速。</p><p>轨迹相位由曲线起始时间与已观察到的转向暂停估计，不能当成精确原生控制器重放；长尾段额外核对末端误差乘 0.8 与实际命令相符。原始数据的每个读取成员均校验 SHA-256。末端微调与零速漂移在不同姿态上发生，历史相关性不足以确认唯一原因。</p><p><a href="REPORT.zh.md">完整文字报告</a> · <a href="stops.csv">逐次停车 CSV</a> · <a href="low_intervals.csv">全部低速区间 CSV</a> · <a href="results/summary.json">核验数据</a></p></details></main>
<script>const stops=STOP_DATA;function show(id,scroll=true){const s=stops.find(x=>x.id===id);document.getElementById('selector').value=id;document.getElementById('figure').src='figures/'+id+'.png';document.getElementById('figure_link').href='figures/'+id+'.png';const z=s.zero_episode;document.getElementById('description').textContent=s.id+'：'+s.label+'。'+(z?'关联零速段 '+z.start_s.toFixed(2)+'–'+z.end_s.toFixed(2)+' 秒，最大位移 '+(z.maximum_excursion_m*100).toFixed(1)+' 厘米。'+(z.late_after_2s_excursion_m===null?'零速段不足以评估两秒之后的保持。':'两秒之后最大继续挪动 '+(z.late_after_2s_excursion_m*100).toFixed(1)+' 厘米。'):'没有匹配到持续至少 0.1 秒的连续三项零速段。');if(scroll)document.getElementById('review').scrollIntoView({behavior:'smooth'});}show('R1-04',false);</script></html>'''
    page=page.replace('OPTIONS',options).replace('STOP_TABLE',table).replace('LOW_TABLE',long_table).replace('STOP_DATA',json.dumps(stops,ensure_ascii=False).replace('</','<\\/'))
    (HERE/'speeds.html').write_text(page)
    print(json.dumps(dict(stops=len(stops),low_intervals=len(low),figures=len(list(figures.glob('*.png'))),bytes=sum(p.stat().st_size for p in figures.glob('*.png')))))


if __name__=='__main__':main()
