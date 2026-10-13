"""Build a Chinese stop ledger from the returned, verified audit evidence."""
import collections
import csv
import hashlib
import html
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
LABELS={'age':'地图数据过期','geometry':'新鲜数据下曲线被拒绝','progress':'接不上下一段，进展超时',
        'missing':'停车位置不合法，首条曲线超时','goal':'正常到终点停车'}
GEO={(1,1):'机身当前位置可通行；曲线前方3.113秒处的后侧安全轮廓进入未观测格。原生回放复现第1561个采样点被拒绝。',
     (3,5):'机身当前位置可通行；曲线前方2.709秒处的后侧安全轮廓进入无支撑禁行边缘。原生回放复现第1360个采样点被拒绝。',
     (5,1):'之前已低速纠偏数秒；当前曲线尾部及实际机身前侧找不到合格支撑层。原生回放第1个点即被拒绝；数据年龄190毫秒，未过期。'}


def main():
    for directory in ['results','windows','windows02','native_replays','native_replays02']:
        m=json.loads((HERE/directory/'manifest.json').read_text())
        for n,v in m['files'].items():
            assert hashlib.sha256((HERE/directory/n).read_bytes()).hexdigest()==v['sha256'],(directory,n)
    stops=[];pauses=[];summary=[]
    for a in range(1,6):
        r=json.loads((HERE/f'results/attempt{a:02d}.json').read_text())
        w=json.loads((HERE/f'windows02/windows{a:02d}.json').read_text())
        proofs=json.loads((BASE/f'versions/v177/results/repeats/v177_full_candidate_attempt{a:02d}/recovery_proofs.json').read_text())['entries']
        proof_by={x['old_generation']:x for x in proofs}
        for o,s in zip(r['owners'],w['stops']):
            g=o['generation'];reason=o['cancel']['data']['reason'];p=s['proof']
            if reason=='requested_goal_reached':kind='goal';detail='到达目标位置与朝向，随后进行最终站立确认；单独列出，不计入途中故障。'
            elif reason=='nav2_server_stop':kind='progress';detail='局部曲线已到头，新的曲线反复无法通过起点/搜索/几何检查；身体几乎原地纠偏，10秒进展检查最终要求重试。'
            elif reason=='scan_trajectory_missing':kind='missing';detail='同一长停期间重新分配任务段，但2秒内没有可执行的首条曲线。记录姿态的原生检查表明安全轮廓已进入静态无支撑边缘。'
            elif (a,g) in GEO:kind='geometry';detail=GEO[a,g]
            else:
                assert p and p['cloud_age_s']>.25,(a,g,s)
                kind='age';detail=f'安全检查所用数据已旧{p["cloud_age_s"]*1000:.1f}毫秒，超过250毫秒门槛；旁路观察器已收到的新帧仅旧{s["latest_received_cloud"]["age_at_stop_s"]*1000:.1f}毫秒。更新后的安全地图没有及时供本次检查使用。'
            proof=proof_by.get(g)
            stops.append({'id':f'R{a}-{g:02d}','run':a,'generation':g,'time_s':o['cancel']['sim_s'],
                          'kind':kind,'label':LABELS[kind],'detail':detail,'native_reason':reason,
                          'age_ms':p['cloud_age_s']*1000 if p else None,
                          'cancel_to_still_proof_s':proof['cancel_to_proof_wall_s'] if proof else None,
                          'still_proof_to_new_route_s':proof['proof_to_new_route_wall_s'] if proof else None,
                          'nav2_log_line':o['revocation_log_line'],'observation_line':o['cancel_source_line'],
                          'source':f'windows02/windows{a:02d}.json'})
        for p,q in zip(r['pauses'],w['pauses']):
            final=p['index']==len(r['pauses'])
            if final:detail='到终点前后的最终对齐/站立确认。'
            elif a==1 and p['index'] in (3,4,5):detail='旧曲线已到头，反复接不上新曲线；微小纠偏不足以形成前进，最终触发进展超时。'
            elif a==1 and p['index'] in (6,7,8):detail='连续重试期间机身漂到禁行边缘；重规划不能从当前姿态生成合法曲线。'
            elif a==3 and p['index'] in (1,2):detail='同一条已结束的短曲线长期占用控制器，后续搜索反复失败；最后由进展超时重试。'
            elif a==5 and p['index']==1:detail='局部曲线已到尾部，后续优化频繁把起始段判为障碍；继续微小纠偏后，支撑检查拒绝当前曲线。'
            else:
                near=[x for x in stops if x['run']==a and x['generation'] in p['revocations_near']]
                detail='；'.join(dict.fromkeys(x['label'] for x in near))+'，随后等待站稳证据并重新接管。' if near else '恢复过程中的低速段；不是独立的一次新规划失败。'
            pauses.append({'id':f'R{a}-P{p["index"]:02d}','run':a,'start_s':p['start_sim_s'],'end_s':p['end_sim_s'],
                           'duration_s':p['duration_sim_s'],'final_hold':final,'detail':detail,
                           'raw_zero':p['zero_raw_commands'],'raw_total':p['raw_commands'],
                           'displacement_m':q['displacement_m'],'failure_counts':q['log_counts']})
        summary.append({'run':a,'retries':len(r['owners'])-1,'low_speed_intervals':len(r['pauses']),
                        'causes':dict(collections.Counter(x['kind'] for x in stops if x['run']==a and x['kind']!='goal'))})
    counts=dict(collections.Counter(x['kind'] for x in stops))
    assert counts=={'geometry':3,'age':20,'progress':3,'missing':4,'goal':5},counts
    assert len(stops)==35 and len(pauses)==33 and sum(not p['final_hold'] for p in pauses)==28
    payload={'summary':summary,'counts':counts,'stops':stops,'pauses':pauses,
             'low_speed_definition':'原有指标：平面实测速度低于0.05 m/s持续至少1秒。它包含微小纠偏及最终站立，不等同于所有控制撤销。'}
    (HERE/'stop_ledger.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    with (HERE/'stop_ledger.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(stops[0]));writer.writeheader();writer.writerows(stops)
    lines=['# 五次运行逐次停车原因','',
        '核对范围：v177在5070Ti完成的五次原起点全路线。阶段：实验与分析。本次没有修改导航，也没有新跑完整路线。','',
        '**共核对30次途中取消重试、5次正常终点停车，以及33段超过1秒的低速区间（其中5段为终点确认）。三者不能混成同一个停车次数。**','',
        '最重要的问题出现在第一轮：79.69秒机身安全轮廓已进入无支撑边缘；80.19秒进展超时取消任务段。随后约15.86秒里，上层661条命令均为零速；排除最初0.2秒后，底层783条遥测中的有效命令也全部为零，但机身仍漂移约0.957米。整个区间保持在STAND_SETTLING，没有进入定点站立。主要受四脚接触条件阻挡，也出现速度、倾斜与支撑分配条件不满足。**这说明到达终点的5/5结果不能证明停车恢复已修好。**','',
        '## 直接触发条件','',
        '| 条件 | 次数 | 解释 |','|---|---:|---|',
        '| 地图数据过期 | 20 | 安全检查数据年龄252～275毫秒；旁路已收到较新帧，但更新后的安全地图没有及时供检查使用。 |',
        '| 新鲜数据下的几何/支撑拒绝 | 3 | 分别为曲线远端未知格、曲线远端无支撑边缘、当前曲线/机身前侧无合格支撑。原生回放复现。 |',
        '| 长期接不上下一段，进展超时 | 3 | 小曲线走完后原地纠偏、重复失败，10秒后升级重试。 |',
        '| 停车姿态位于禁行边缘，首条曲线超时 | 4 | 全在第一轮连续重试段；没有合法起点，2秒后再次重试。 |',
        '| 正常终点停车 | 5 | 每轮各一次，单独统计。 |','',
        '地图过期是20次事件的充分触发条件，不排除同时存在几何问题。原日志没有分开记录输入消费、地图计算、发布锁等待，所以不能把这些延迟全部归因于CPU或某把锁。','',
        '## 每一次控制撤销','',
        '时间均为原始仿真时间。等待列为取消后取得实测站稳证据的时间；这些证据不等于整个等待期间位置一直固定。','',
        '| 编号 | 时间/秒 | 直接原因 | 等待站稳证据/秒 | 具体解释 |','|---|---:|---|---:|---|']
    for s in stops:
        wait='—' if s['cancel_to_still_proof_s'] is None else f'{s["cancel_to_still_proof_s"]:.2f}'
        lines.append(f'| {s["id"]} | {s["time_s"]:.3f} | {s["label"]} | {wait} | {s["detail"]} |')
    lines+=['','## 视频里的每一段明显低速','',payload['low_speed_definition'],
            '同一段长停可能经历多个任务段；部分取消重试不足1秒，因而没有单独出现在这张表。','',
            '| 编号 | 起止时间/秒 | 持续/秒 | 解释 |','|---|---|---:|---|']
    for p in pauses:lines.append(f'| {p["id"]} | {p["start_s"]:.2f}–{p["end_s"]:.2f} | {p["duration_s"]:.2f} | {p["detail"]} |')
    lines+=['','## 开源对照后的判断','',
        '本次检查13个仓库：Nav2（Foxy和较新版本）、move_base、TEB、SCAN、EGO、Fast-Planner、FASTER、CMU Go2导航、ART、field_local_planner，以及官方Lite3 sdk_deploy、Unitree RL Gym、legged_gym。导航实现、站立状态机和训练目标分开比较。详见[固定提交与源码对照](../../../../survey/2026-10-12_v177_stop_recovery_upstream_survey.md)。','',
        '下一步优先修“发零速后仍漂移”，并用停车位置保持验证；然后处理地图时效与短暂失效的分级重试；最后修复反复从同一不可行起点/朝向生成曲线的问题。每项分别改、分别测。不能通过放宽碰撞、支撑或数据时效门槛来减少停车。','',
        '开源实现并没有证明“它们从不失败”。值得借鉴的是：区分失败原因；允许有界重试；保留仍安全的执行段；卡住后改变局部路径或朝向策略；把RL零速命令和站立保持作为不同控制职责。','',
        '## 核验与限制','',
        '- 五轮原始取消事件和原生日志逐个对应，35/35一致；结果文件与远端哈希核对。',
        '- 三个新鲜数据拒绝点的原生回放，首次拒绝相位/采样数与原记录对应；另核验三个长停尾部和四个失败恢复起点。',
        '- 原生回放采用已记录传感器的有序重建；没有重现原异步调度，也不是新跑全路线。',
        '- 初版诊断工具矩阵方向错误以及过旧定时消息的选择错误均已保留、修正，未混入最终结论。见[诊断边界](DIAGNOSTIC_LIMITS.md)。',
        '- 20次地图时效事件的具体内部等待归因仍需要增加时间标记；此处没有推断GPU、SSH或训练导致这些历史停车。',
        '- 本轮交付是原因调查，未声称已经修复。',
        '', '[全部机器可读记录](stop_ledger.json) · [CSV](stop_ledger.csv) · [漂移实测](v177_stop_drift_detailed.json) · [禁行边缘时间段](gap_intervals.json)','']
    (HERE/'REPORT.zh.md').write_text('\n'.join(lines))
    data=json.dumps(payload,ensure_ascii=False).replace('</','<\\/')
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>五轮停车原因核查</title>
<style>body{font:16px/1.65 system-ui,-apple-system,sans-serif;color:#23303b;background:#f6f7f8;margin:0}main{max-width:1180px;margin:40px auto;padding:0 24px}h1{font-size:29px;margin-bottom:10px}h2{font-size:22px;margin-top:36px}.lead{max-width:970px}.alert{background:#fff2e9;border-left:4px solid #ba5425;padding:18px 22px;margin:24px 0}.numbers{display:flex;gap:16px;flex-wrap:wrap}.numbers div{background:white;padding:16px 22px;border:1px solid #dde1e5;border-radius:8px;flex:1;min-width:130px}.numbers b{display:block;font-size:28px;color:#1f5369}.controls{margin:24px 0;display:flex;gap:12px;align-items:center;flex-wrap:wrap}select{padding:9px;border:1px solid #bfc8ce;border-radius:5px;background:white;font-size:15px}.scroll{overflow:auto;background:white;border:1px solid #dde1e5}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:12px 14px;border-bottom:1px solid #e4e7e9;text-align:left;vertical-align:top}th{background:#eaf0f3;white-space:nowrap}td:nth-child(1),td:nth-child(2){white-space:nowrap}a{color:#075a80}details summary{cursor:pointer;font-weight:600}small,.muted{color:#61707c}footer{margin:32px 0;font-size:14px}</style>
<main><h1>五轮停车，逐次核查</h1><p class="muted">v177 · 同地图、原起点 · 原始仿真时间 · 原因调查，尚未实施修复</p>
<p class="lead">这些停车有不同原因。大部分事件涉及地图数据没有及时更新；另一些是曲线或当前车身姿态过不了安全检查。长时间停顿还暴露了底层站立保持问题。</p>
<div class="alert"><b>最需要先修：零速命令生效，机身仍漂移。</b><br>第一轮 80.19～96.05 秒间，上层持续要求零速；排除最初 0.2 秒后，底层记录也全部是零速，但机身仍移动约 <b>96 厘米</b>，一直没进入定点站立。车身在 79.69 秒已经越入地图的无支撑边缘，随后连续四次恢复起不来。五次到终点不能证明这个问题已解决。</div>
<div class="numbers"><div><b>20</b>地图时效事件</div><div><b>3</b>新鲜数据下的曲线拒绝</div><div><b>7</b>进展或首条曲线超时</div><div><b>13</b>对照开源仓库</div></div>
<h2>每次取消与重试</h2><p>30 次途中重试，另有 5 次正常终点停车。点击证据可查看对应原生日志行号与输入时间。短暂重试不一定形成超过 1 秒的可见低速段。</p>
<div class="controls"><label>运行 <select id="run"><option value="0">全部五轮</option><option value="1">第1轮</option><option value="2">第2轮</option><option value="3">第3轮</option><option value="4">第4轮</option><option value="5">第5轮</option></select></label><label><input type="checkbox" id="goals">显示正常终点停车</label><span id="count"></span></div>
<div class="scroll"><table><thead><tr><th>编号</th><th>时间 / 秒</th><th>触发原因</th><th>为什么停</th><th>等待站稳证据</th></tr></thead><tbody id="stops"></tbody></table></div>
<h2>视频中超过1秒的低速段</h2><p class="muted">沿用原有口径：实测平面速度低于 5 厘米/秒。可能仍有微小纠偏或转向，不能全部叫“计算失败”。</p><div class="scroll"><table><thead><tr><th>编号</th><th>起止 / 秒</th><th>持续 / 秒</th><th>解释</th></tr></thead><tbody id="pauses"></tbody></table></div>
<h2>别人怎么处理</h2><p>Nav2、move_base、TEB 的共同启示是区分短暂失败和任务失败，采用有界重试，并在卡住后改变局部路径或朝向策略。SCAN / EGO 会区分近处危险与更远处的重规划问题。官方 Lite3 与 Unitree 的部署代码也把姿态控制和 RL 策略控制分开；零速输入本身并不等于位置锁定。</p>
<p><a href="../../../../survey/2026-10-12_v177_stop_recovery_upstream_survey.md">13个仓库的固定提交、源码行号和适用边界</a></p>
<details><summary>证据能说明到哪一步</summary><p>已逐个核对全部控制撤销；三个新鲜数据拒绝点在原生回放中复现对应检查点。回放采用有序传感器重建，没有重现原异步调度。20次时效事件仍需进一步区分输入消费、计算、发布等待各占多少时间。初版诊断工具的失败被单独保留，没有算成导航失败。</p><p><a href="DIAGNOSTIC_LIMITS.md">完整诊断边界</a></p></details>
<footer><a href="REPORT.zh.md">完整中文报告</a> · <a href="stop_ledger.csv">下载逐次表 CSV</a> · <a href="stop_ledger.json">全部数据</a> · <a href="../../versions/v178/delivered/v177_full_route_attempt01.mp4">第一轮完整视频</a></footer></main>
<script>const data=DATA;function esc(s){return String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;')}function draw(){let r=+document.querySelector('#run').value,g=document.querySelector('#goals').checked;let rows=data.stops.filter(x=>(!r||x.run===r)&&(g||x.kind!=='goal'));document.querySelector('#count').textContent=rows.length+' 条记录';document.querySelector('#stops').innerHTML=rows.map(x=>`<tr><td>${x.id}</td><td>${x.time_s.toFixed(3)}</td><td>${esc(x.label)}</td><td>${esc(x.detail)} <a href="${x.source}">证据</a><br><small>nav2.log 第 ${x.nav2_log_line} 行</small></td><td>${x.cancel_to_still_proof_s===null?'正常结束':x.cancel_to_still_proof_s.toFixed(2)+' 秒'}</td></tr>`).join('');document.querySelector('#pauses').innerHTML=data.pauses.filter(x=>(!r||x.run===r)&&(g||!x.final_hold)).map(x=>`<tr><td>${x.id}</td><td>${x.start_s.toFixed(2)}～${x.end_s.toFixed(2)}</td><td>${x.duration_s.toFixed(2)}</td><td>${esc(x.detail)}</td></tr>`).join('')}document.querySelector('#run').onchange=draw;document.querySelector('#goals').onchange=draw;draw();</script></html>'''.replace('DATA',data)
    mobile='''@media(max-width:700px){main{margin:24px auto;padding:0 18px}h1{font-size:25px}.alert{padding:15px}.numbers{gap:8px}.numbers div{min-width:110px;padding:12px}.scroll{border:0;background:transparent}table,tbody,tr,td{display:block;width:auto}thead{display:none}tr{background:white;border:1px solid #dde1e5;border-radius:6px;margin:10px 0;padding:12px}td{padding:4px 0;border:0;font-size:14px}td:nth-child(1),td:nth-child(2){display:inline-block;white-space:normal}td:nth-child(1){font-weight:700;margin-right:16px}td:nth-child(2)::before{content:"时间：";color:#61707c}#stops td:nth-child(3){font-weight:600;color:#1f5369}#stops td:nth-child(5)::before{content:"站稳确认：";color:#61707c}#pauses td:nth-child(3)::before{content:"持续：";color:#61707c}#pauses td:nth-child(3)::after{content:" 秒"}}'''
    page=page.replace('</style>',mobile+'</style>')
    (HERE/'stops.html').write_text(page)
    print(json.dumps({'stops':len(stops),'pauses':len(pauses),'counts':counts},ensure_ascii=False))

if __name__=='__main__':main()
