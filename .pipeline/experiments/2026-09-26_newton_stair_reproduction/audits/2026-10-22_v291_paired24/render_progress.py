"""Refresh the existing standalone HTML using compact local campaign results."""
from pathlib import Path
import json,re,html
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
PAGE=ROOT/'docs/research/plans/2026-10-22-convergence/index.html'
request=json.loads((HERE/'source/request.json').read_text());p=HERE/'results/batch_status.json';status=json.loads(p.read_text()) if p.exists() else []
finished=sum(r.get('state')=='closed' for r in status);byrun={r['run']:r for r in status};cards=[]
for case in ('D07','CD12','S04','A04'):
 cells=[]
 for variant in ('v290','v291'):
  values=[]
  for repeat in (1,2,3):
   run=f'pair24_{variant}_{case}_r{repeat}';r=byrun.get(run,{});state=r.get('state');text='已录制·待审' if state=='closed' else '启动失败' if state=='startup_failure' else '运行中' if state else '待跑';cls='recorded' if state=='closed' else 'running' if state else ''
   if state=='closed' and not r.get('result_present'):text='运行中断';cls='running'
   elif state=='closed' and r.get('terminal')=='FAILED':text='任务未完成';cls='running'
   values.append(f'<span class="trial-cell {cls}" title="{run}">第 {repeat} 次<br><b>{text}</b></span>')
  cells.append('<div class="trial-row"><strong>'+('旧版 v290' if variant=='v290' else '新版 v291')+'</strong>'+''.join(values)+'</div>')
 cards.append('<article class="panel"><div class="panel-inner"><h3>'+case+'</h3>'+''.join(cells)+'</div></article>')
section='''<!-- PAIRED24:START -->
<style>.trial-row{display:grid;grid-template-columns:85px repeat(3,1fr);gap:8px;margin-top:14px;align-items:center}.trial-row>strong{font-size:13px}.trial-cell{padding:10px 5px;border-radius:9px;background:#eff0e8;text-align:center;font-size:11px;color:#65756f}.trial-cell b{font-weight:500}.trial-cell.running{background:#f7e7cf;color:#895224}.trial-cell.recorded{background:#dfebdf;color:#23694c}.campaign-total{font-size:40px;line-height:1.2;font-weight:650;color:#23694c}.holdout-strip{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:15px}.holdout-strip>div{padding:12px 15px;background:#edf1e6;border-radius:12px}.holdout-strip strong{display:block}.holdout-strip span{font-size:12px;color:#65756f}@media(max-width:650px){.trial-row{grid-template-columns:72px repeat(3,1fr);gap:5px}.holdout-strip{grid-template-columns:1fr 1fr}}</style>
<section class="section" id="paired24"><div class="section-head"><div><div class="section-label">本轮新旧物理对照 / 条件已冻结</div><h2>这次直接看：停下后，真的少滑了吗？</h2><p>同一台 ultra9，4 条路线，新旧版本各 3 次。相邻配对，平衡先后顺序。</p></div><div><div class="campaign-total">FINISHED <span style="font-size:20px;color:#65756f">/ 24</span></div><span class="small muted">已完成物理录制</span></div></div>
<div class="explain-grid">CARDS</div><p class="note">“已录制”不等于成功。整条路线的几何检查和最后站稳 ≥2 秒都通过，才算成功。没到终点的漂移记为“缺测”，不会填成零；喊停后又启动的过程单独保留。</p>
<div class="holdout-strip"><div><strong>CU04</strong><span>新物理路线 · 上楼</span></div><div><strong>CD09</strong><span>新物理路线 · 下楼</span></div><div><strong>CM04</strong><span>新物理路线 · 中间平台出发</span></div><div><strong>CE04</strong><span>新物理路线 · 靠近边界停站</span></div></div><p class="note">这四条已有离线合法性检查，此前未进入已核对的物理选择列表。现在提前选定，本轮 24 次不运行它们；第一批通过后才决定后续验证。</p>
<div class="analysis-links"><a href="../../../../.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-22_v291_paired24/PLAN.md">查看固定条件与判定标准</a><a href="../../../../.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-22_v291_paired24/source/request.json">查看 24 次固定顺序</a><a href="#checklist">查看已完成任务 ↗</a></div></section>
<!-- PAIRED24:END -->'''.replace('FINISHED',str(finished)).replace('CARDS',''.join(cards))
s=PAGE.read_text()
if '<!-- PAIRED24:START -->' in s:s=re.sub(r'<!-- PAIRED24:START -->.*?<!-- PAIRED24:END -->',lambda m:section,s,flags=re.S)
else:s=s.replace('<!-- V291-PROGRESS:START -->',section+'\n<!-- V291-PROGRESS:START -->')
s=s.replace('href="#v291-progress">本次进展','href="#paired24">本次进展').replace('新物理实验目前为 <b>0 次</b>。','上述组件阶段没有运行新物理实验；本轮物理进度见上方。')
PAGE.write_text(s);print(f'Physical recordings: {finished}/24; checklist updated separately at milestones.')
