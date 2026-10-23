"""Render the completed, independently audited comparison into the original plan."""
from pathlib import Path
import datetime,html,json,re
HERE=Path(__file__).resolve().parent
PAGE=HERE.parents[4]/'docs/research/plans/2026-10-22-convergence/index.html'
data=json.loads((HERE/'results/summary.json').read_text());comparison=json.loads((HERE/'results/comparison.json').read_text())
assert data['full_geometry'] and len(data['runs'])==24
rows=data['runs'];groups=comparison['case_groups'];passed=comparison['first_review_passed']
evidence='../../../../.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-22_v291_paired24/'
fmt=lambda x:'—' if x is None else f'{x:.1f}'
esc=html.escape
def why(r):
 if r['scanner_deadline_failures']:return '雷达超时中断'
 if not r['arrival_and_pd']:return '到达 / 最后站稳未通过'
 if not r['geometry']['passed']:return '到达，但全程几何未通过'
 return '完整通过'
def first_label(r):
 first=r['stop'].get('first')
 return '—' if first is None else fmt(first['max_displacement_cm'])+(' *' if first['pd_entry_censored'] else '')
table=[];details=[]
for case in ('D07','CD12','S04','A04'):
 old,new=groups[case]['v290'],groups[case]['v291']
 table.append(f'<tr><th>{case}</th><td>{old["successes"]} / 3</td><td>{new["successes"]} / 3</td><td>{fmt(old["worst_episode_median_cm"])} <small>({old["first_stop_observed_n"]}次)</small> → {fmt(new["worst_episode_median_cm"])} <small>({new["first_stop_observed_n"]}次)</small></td></tr>')
 lines=[]
 for repeat in (1,2,3):
  for version in ('v290','v291'):
   r=next(x for x in rows if x['case_id']==case and x['repeat']==repeat and x['variant']==version);first=r['stop'].get('first')
   wait='—' if first is None or first['pd_delay_s'] is None else f'{first["pd_delay_s"]:.2f} s'
   lines.append(f'<tr><td>{"旧" if version=="v290" else "新"} · {repeat}</td><td>{first_label(r)}</td><td>{wait}</td><td>{r["stop"].get("restart_count",0)}</td><td>{why(r)}</td></tr>')
 svg=(HERE/'figures'/f'{case}_stop_comparison.svg').read_text();svg=svg[svg.index('<svg'):]
 # Matplotlib clip-path IDs repeat across files; prefix every ID and reference.
 ids=re.findall(r'\bid="([^"]+)"',svg)
 for key in sorted(set(ids),key=len,reverse=True):
  svg=svg.replace(f'id="{key}"',f'id="pair24-{case}-{key}"').replace(f'#{key}"',f'#pair24-{case}-{key}"').replace(f'#{key})',f'#pair24-{case}-{key})')
 svg=svg.replace('<svg ',f'<svg role="img" aria-label="{case} 三次新旧实测停步位移：左侧第一次停步，右侧所有停步中最差一次。斜线表示本次停步未开始 PD 接管。" ',1)
 details.append(f'''<details class="pair-detail"><summary>{case} · 查看三次原始对照与每次失败原因</summary>
 <p>左：第一次喊停后移动多少。右：这一趟所有停步中，最差的一次。蓝色为旧版，绿色为新版；四张图使用相同刻度。</p>
 <div class="pair-figure">{svg}</div><div class="pair-table-wrap"><table class="pair-table"><thead><tr><th>版本 · 次数</th><th>首次位移 cm</th><th>开始接管前等待</th><th>再次启动</th><th>完整结果</th></tr></thead><tbody>{''.join(lines)}</tbody></table></div>
 <p class="note">* 这次停步结束前没有开始 PD 接管，所列是已经发生的位移；— 表示没有观测到终点停步。开始接管也不代表站稳，右侧完整结果还要求最终站稳和全程几何合格。</p></details>''')
totals=comparison['totals'];scan_counts={v:sum(r['scanner_deadline_failures']>0 for r in rows if r['variant']==v) for v in ('v290','v291')}
handoff_svg=(HERE/'figures/handoff_first_repeat.svg').read_text();handoff_svg=handoff_svg[handoff_svg.index('<svg'):]
for key in sorted(set(re.findall(r'\bid="([^"]+)"',handoff_svg)),key=len,reverse=True):
 handoff_svg=handoff_svg.replace(f'id="{key}"',f'id="pair24-handoff-{key}"').replace(f'#{key}"',f'#pair24-handoff-{key}"').replace(f'#{key})',f'#pair24-handoff-{key})')
handoff_svg=handoff_svg.replace('<svg ','<svg role="img" aria-label="S04 和 A04 的第一次新旧对照：位移随时间变化，底部显示等待、PD 交接、退回走路控制及固定站立阶段。" ',1)
headline='首轮达到数值决策线，下一步先核对停止流程。' if passed else 'v291 这轮不升级，先停下扩展。'
decision='数值门槛通过；停止流程仍需结合逐次记录判断。' if passed else '本轮没有达到事先定好的标准。后续 10 + 16 次暂缓，保留全部失败记录。'
section=f'''<!-- PAIRED-RESULTS:START -->
<style>.pair-score-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:22px 0}}.pair-score{{background:#edf1e6;border-radius:14px;padding:18px}}.pair-score b{{display:block;font-size:32px;line-height:1.4}}.pair-score small{{font-size:12px;color:#65756f}}.pair-result-note{{border-left:4px solid #aa6932;background:#f7eee0;padding:16px 20px;border-radius:0 12px 12px 0;margin:20px 0}}.pair-table-wrap{{overflow-x:auto}}.pair-table{{border-collapse:collapse;width:100%;font-size:13px;margin:14px 0}}.pair-table th,.pair-table td{{border-bottom:1px solid #dfe4d8;padding:12px 9px;text-align:left}}.pair-table th{{font-weight:600}}.pair-detail{{border:1px solid #dfe4d8;border-radius:14px;padding:16px 20px;margin:14px 0}}.pair-detail summary{{font-weight:600;cursor:pointer}}.pair-detail p{{font-size:13px;line-height:1.7}}.pair-figure svg{{display:block;width:100%;height:auto}}@media(max-width:650px){{.pair-score-grid{{grid-template-columns:1fr 1fr}}.pair-score-grid>div:last-child{{grid-column:1/-1}}.pair-detail{{padding:13px}}.pair-table{{font-size:11px}}.pair-table th,.pair-table td{{padding:9px 5px}}}}</style>
<section class="section" id="paired-results"><div class="section-head"><div><div class="section-label">24 次新物理仿真 / 完整复核已完成</div><h2>{headline}</h2><p>{decision}</p></div></div>
<div class="pair-score-grid"><div class="pair-score">旧版 v290<b>{totals['v290']} / 12</b><small>完整成功</small></div><div class="pair-score">新版 v291<b>{totals['v291']} / 12</b><small>完整成功 · 事先目标至少 10/12</small></div><div class="pair-score">完成录制<b>24 / 24</b><small>全部保留；没有替换失败重跑</small></div></div>
<div id="paired-interpretation" class="pair-result-note"><strong>没有稳定减少漂移。</strong>CD12 仅有一次新版停步记录明显变小；D07、S04、A04 的已观测最差停步中位数都变大。A04 从旧版约 <b>1.5 cm</b> 变成新版约 <b>8.1 cm</b>。<br>下一步先拆开“统一终点控制”和“接地腿停步辅助”，查清小速度停滞与 PD 交接回退；本轮不继续改参数补考。</div>
<div class="pair-table-wrap"><table class="pair-table"><thead><tr><th>路线</th><th>旧版成功</th><th>新版成功</th><th>最差停步位移中位数 · cm<br><small>旧 → 新</small></th></tr></thead><tbody>{''.join(table)}</tbody></table></div>
<p class="note">位移从每次全零命令生效的位置起算。上表“最差”取每趟所有停步中的最大值，再取可观测重复的中位数；包含被重新启动或中断截断的记录。主要指标“第一次停步”逐次列在下方，不用最后一次成功停步代替。</p>
{''.join(details)}
<details class="pair-detail"><summary>为什么“开始接管”还不算站稳？看第一轮 S04 / A04</summary><p>这两组是明确标注的故障示例；全部 24 次数据仍在上方。虚线是第一次开始 PD 接管，底部色条显示之后有没有退回走路控制。</p><div class="pair-figure">{handoff_svg}</div><p class="note">第一轮新版 S04 开始 PD 约 0.06 秒后，因机身速度过大退出交接；A04 也出现一次同类退出。图中展示实际记录，不能单凭这两组确定是哪一项改动造成。</p></details>
<div class="pair-result-note"><strong>同机负载确实影响了实验。</strong>固定 100 ms 雷达期限触发中断：旧版 {scan_counts['v290']} 次，新版 {scan_counts['v291']} 次。全部计为失败，并单列原因；这些中断不直接归因于终点控制。正常录完的路线仍可用于观察实际停步行为。</div>
<p class="note">A04 耗时比较使用成功完成时的真实墙钟时间，旧版 {groups['A04']['v290']['completion_wall_n']} 次、新版 {groups['A04']['v291']['completion_wall_n']} 次可用；中断不算“跑得更快”。几何审计覆盖原始采样轨迹与独立起身过程，沿用 v290 的支撑、实体和原始点云标准。</p>
<div class="analysis-links"><a href="{evidence}REPORT.md">完整结论与下一步</a><a href="{evidence}results/comparison.json">可复核的对照数值</a><a href="{evidence}results/preservation_receipt.json">原始记录保存凭据</a><a href="#checklist">查看已划掉的任务 ↗</a></div></section>
<!-- PAIRED-RESULTS:END -->'''
s=PAGE.read_text()
if '<!-- PAIRED-RESULTS:START -->' in s:s=re.sub(r'<!-- PAIRED-RESULTS:START -->.*?<!-- PAIRED-RESULTS:END -->',lambda _:section,s,flags=re.S)
else:s=s.replace('<!-- PAIRED24:START -->',section+'\n<!-- PAIRED24:START -->')
for r in rows:
 pattern=r'(<span class="trial-cell)[^"]*(" title="'+re.escape(r['run'])+r'">第 '+str(r['repeat'])+r' 次<br><b>)[^<]*(</b></span>)'
 s=re.sub(pattern,lambda m:m[1]+(' recorded' if r['success'] else ' running')+m[2]+why(r)+m[3],s)
s=s.replace('已完成物理录制','已完成录制与结果复核').replace('“已录制”不等于成功。','上方逐次结果已完成复核。')
s=s.replace('href="#paired24">本次进展','href="#paired-results">本次进展')
s=s.replace('控制已经接顺，实际少滑多少还要测。','回看组件阶段：逻辑通过，物理表现见上方。')
s=s.replace('这两个改动值得进入物理对比，但现在还不能把“少滑了多少”填成成绩。','这是物理对照前的判断；本轮实际成绩与结论已列在上方。')
state_match=re.search(r'(<script id="plan-state" type="application/json">)(.*?)(</script>)',s,re.S);assert state_match
state=json.loads(state_match[2]);state['checks']['paired']=True;state['checks']['first-review']=True
if not passed:
 state['checks']['decision']=True
 state['notes']['decision']='2026-10-22：本轮 v291 不升级，保留原版本和全部失败记录。完整成功 3/12 对 3/12；A04 新版两次完整记录均约 8 cm 漂移。后续 26 次暂缓。下一步先拆开统一控制与接地腿辅助，定位小速度停滞及 PD 交接回退；后续物理验证先解决 CPU 争用。'
 for key in ('regression','unseen','final-review'):
  state['notes'][key]='首轮未达到冻结决策线，本项暂缓，未运行、未计为完成。'
state['notes']['paired']='2026-10-22：ultra9 上 24/24 个冻结槽位都有正物理步数，原始失败全部保留，没有补跑替换。代码、原生安装与控制条件哈希复核不变。证据：audits/2026-10-22_v291_paired24/results/preservation_receipt.json。'
state['notes']['first-review']=f'2026-10-22：原始到达、全程采样几何和最终 PD 复核完成。旧版 {totals["v290"]}/12，新版 {totals["v291"]}/12；A04 新版 {groups["A04"]["v291"]["successes"]}/3。'+decision+'证据：audits/2026-10-22_v291_paired24/REPORT.md。'
state['scores'].update(firstOld=totals['v290'],firstNew=totals['v291'],firstA04=groups['A04']['v291']['successes'],firstSlow=None if comparison['a04_slowdown_fraction'] is None else round(comparison['a04_slowdown_fraction']*100,1))
state['handoff']=state['notes']['first-review']+'四条后续路线 CU04/CD09/CM04/CE04 已固定，本轮未运行。'+(state['notes'].get('decision','') if not passed else '')
state['notes']['environment']+=' 后续实测确认共享 CPU 争用：7 次雷达超时。配置一致检查已完成，但没有获得干净的独占资源比较，不能把所有中断归因于控制器。' if '7 次雷达超时' not in state['notes']['environment'] else ''
state['notes']['component']=state['notes']['component'].replace('新物理仿真 0 次。','该组件阶段新物理仿真 0 次；后续 24 次对照见本页最新结果。')
if '本轮物理评估' not in state['notes']['handoff']:
 state['notes']['handoff']+=' 本轮物理评估已完成，发现交接回退和漂移，候选未采用；见 paired24/REPORT.md。'
state['updatedAt']=datetime.datetime.now(datetime.timezone.utc).isoformat()
s=s[:state_match.start(2)]+json.dumps(state,ensure_ascii=False,indent=2)+s[state_match.end(2):]
s=s.replace('研究任务尚未完成','本轮评估完成 · 未通过' if not passed else '本轮评估完成')
PAGE.write_text(s);print(json.dumps({'checked':sum(state['checks'].values()),'scores':state['scores'],'first_review_passed':passed}))
