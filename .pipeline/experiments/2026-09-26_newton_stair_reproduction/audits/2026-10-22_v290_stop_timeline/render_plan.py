"""Render measured displacement plots and insert a findings panel in the plan."""
from datetime import datetime, timezone
import json
import re
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
PLAN = REPO / 'docs/research/plans/2026-10-22-convergence/index.html'
PREFIX = '../../../../' + HERE.relative_to(REPO).as_posix()
font = FontProperties(fname='/System/Library/Fonts/STHeiti Light.ttc')
plt.rcParams.update({'svg.fonttype': 'path', 'svg.hashsalt': 'v290-stop-analysis',
                    'font.size': 12, 'axes.edgecolor': '#dce1d7', 'axes.labelcolor': '#233b37',
                    'text.color': '#233b37', 'xtick.color': '#65756f', 'ytick.color': '#65756f'})


def chart(case, result):
    fig, ax = plt.subplots(figsize=(5.5, 3.0), layout='constrained')
    fig.patch.set_facecolor('#fffefa')
    ax.set_facecolor('#fffefa')
    zero = result['applied_zero']['time_s']
    end = result['stop_to_fixed_s'] + 1
    points = [p for p in result['plot_samples'] if zero <= p['time_s'] <= zero + end]
    ax.axvspan(0, result['stop_to_pd_s'], color='#f4e5d5')
    ax.axvspan(result['stop_to_pd_s'], result['stop_to_fixed_s'], color='#e1eddf')
    ax.plot([p['time_s'] - zero for p in points], [p['drift_cm'] for p in points], color='#23694c', lw=2.6)
    maximum = result['maximum_drift']
    x = maximum['time_s'] - zero
    y = maximum['displacement_from_applied_zero_cm']
    ax.scatter([x], [y], s=30, color='#a4522e', zorder=5)
    ax.annotate(f'最大 {y:.1f} cm', xy=(x, y), xytext=(0, 9), textcoords='offset points',
                ha='center', fontproperties=font, fontsize=13)
    ax.axvline(result['stop_to_pd_s'], color='#718b6d', ls='--', lw=1)
    ax.set_xlim(0, end)
    ax.set_ylim(0, 29)
    ax.set_xlabel('收到全零命令之后（秒）', fontproperties=font, fontsize=12)
    ax.set_ylabel('水平位移（厘米）', fontproperties=font, fontsize=12)
    ax.set_yticks([0, 10, 20])
    ax.grid(axis='y', alpha=.22)
    ax.spines[['top', 'right']].set_visible(False)
    output = HERE / f'{case}-stop-drift.svg'
    fig.savefig(output, metadata={'Date': '2026-10-22', 'Description': 'Measured closed v290 recording. No new physics.'})
    plt.close(fig)
    svg = output.read_text()
    for identifier in re.findall(r'id="([^"]+)"', svg):
        scoped = case + '-' + identifier
        svg = svg.replace('id="' + identifier + '"', 'id="' + scoped + '"')
        svg = svg.replace('href="#' + identifier + '"', 'href="#' + scoped + '"')
        svg = svg.replace('url(#' + identifier + ')', 'url(#' + scoped + ')')
    svg = '\n'.join(line.rstrip() for line in svg.splitlines()) + '\n'
    output.write_text(svg)
    svg = svg[svg.index('<svg'):]
    return svg.replace('<svg ', '<svg class="stop-chart" role="img" aria-label="' +
                       case + ' 收到全零命令后的实测水平位移。主要移动发生在等待 PD 接管的浅橙色区间。" ', 1)


def main():
    data = json.loads((HERE / 'summary.json').read_text())
    cards = []
    for case, r in data['cases'].items():
        title = '转身先越界，SCAN 随后急停' if case == 'D07' else '朝向刚达标，外层停止位置调整'
        caption = ('急停时朝向还差约 65.6°，没有满足“到达终点”的条件。' if case == 'D07' else
                   '朝向误差刚小于 7.16°，但身体仍偏离中心约 6.9 厘米。')
        svg = chart(case, r)
        cards.append(f'''<article class="panel stop-card"><div class="panel-inner"><div class="panel-heading"><span class="pill">{case}</span><h3>{title}</h3></div><p class="small muted">{caption}</p>
<div class="stop-metric"><b>{r['maximum_drift']['displacement_from_applied_zero_cm']:.1f}<span> 厘米</span></b><span>收到全零命令后<br>机身最大水平位移</span></div>
<div class="stop-events"><div><b>{r['published_xy_zero']['time_s']:.3f} s</b><span>发布停止平移命令</span></div><div><b>{r['applied_zero']['time_s']:.3f} s</b><span>全零命令实际生效</span></div><div><b>{r['pd_transition']['time_s']:.3f} s</b><span>PD 才开始接管</span></div></div>
{svg}<p class="small"><span class="legend-dot waiting"></span>等待 PD，仍由 RL 控制 <span class="legend-dot transfer"></span>PD 逐步接管</p>
<p class="stop-bottom">接管前等了 <b>{r['stop_to_pd_s']:.2f} 秒</b>，已净移动 <b>{r['pre_pd_displacement_cm']:.1f} 厘米</b>；接管开始到固定站立，仅再净移动 <b>{r['pd_transition_displacement_cm']:.2f} 厘米</b>。</p></div></article>''')
    findings = '''<!-- STOP-ANALYSIS:START -->
<style>.stop-chart{display:block;width:100%;height:auto;margin:16px 0 8px}.stop-metric{display:flex;gap:22px;align-items:center;margin:19px 0 23px}.stop-metric>b{font-size:43px;line-height:1.2;font-weight:600;color:#23694c}.stop-metric>b>span{font-size:17px;font-weight:400}.stop-metric>span{font-size:13px;color:#65756f}.stop-events{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;padding:14px 0;border-top:1px solid #dce1d7;border-bottom:1px solid #dce1d7}.stop-events b{display:block;font-size:16px}.stop-events span{font-size:12px;color:#65756f}.stop-bottom{margin-top:16px;font-size:14px;line-height:1.8}.legend-dot{display:inline-block;width:10px;height:10px;margin:0 4px 0 7px;border-radius:3px}.waiting{background:#e6c29e}.transfer{background:#a4c59e}.finding-correction{border-left:3px solid #a4522e;padding:12px 17px;margin:18px 0;background:#f5ede0;font-size:14px}.analysis-links{display:flex;gap:18px;flex-wrap:wrap;font-size:13px;margin-top:16px}@media(max-width:650px){.stop-metric>b{font-size:37px}.stop-events{gap:7px}.stop-events b{font-size:14px}.stop-events span{font-size:11px}.stop-card .panel-inner{padding:19px 17px}}</style>
<section class="section" id="stop-analysis"><div class="section-head"><div><div class="section-label">已完成第一项 / 旧记录实测分析</div><h2>喊停以后，机身仍移动了约 20 多厘米。</h2><p>大幅移动主要发生在站立保持（PD）接管之前。命令虽然已是零，走路策略（RL）仍在控制关节。</p></div><span class="pill good">分析完成 · 未修改控制器</span></div>
<div class="explain-grid">''' + ''.join(cards) + f'''</div>
<div class="finding-correction"><b>修正之前的判断：</b>D07 不是终点控制器“误判到达”，而是碰撞急停；CD12 确有外层提前结束位置调整的路径。两条路线第一次越界都发生在完全喊停之前，因此下一步还要覆盖转向过程和等待站稳时的偏移。</div>
<p class="note">“位移”从全零命令实际生效时的机身位置起算，取后续最大水平距离；不是累计路程，也不是越界深度。指标按原始约 50 Hz 遥测计算，图形抽样显示。浅橙色阶段仍由 RL 控制；主要等待条件是四只脚的受力。</p>
<div class="analysis-links"><a href="{PREFIX}/REPORT.md">查看完整时间线与归因</a><a href="{PREFIX}/summary.json">查看数值和原始行号</a><a href="#task-unify">下一步：统一终点控制 ↗</a></div></section>
<!-- STOP-ANALYSIS:END -->'''
    text = PLAN.read_text()
    if 'href="#stop-analysis">分析结果' not in text:
        text = text.replace('<a href="#understand">', '<a href="#stop-analysis">分析结果</a><a href="#understand">', 1)
    if '<!-- STOP-ANALYSIS:START -->' in text:
        text = re.sub(r'<!-- STOP-ANALYSIS:START -->[\s\S]*?<!-- STOP-ANALYSIS:END -->', lambda _: findings, text)
    else:
        text = text.replace('<section class="section" id="understand">', findings + '\n<section class="section" id="understand">', 1)
    pattern = r'(<script id="plan-state" type="application/json">)([\s\S]*?)(</script>)'
    match = re.search(pattern, text)
    state = json.loads(match.group(2))
    state['checks']['trace'] = True
    state['notes']['trace'] = ('2026-10-22 已完成：14 项旧录制源哈希匹配。D07 为 SCAN 碰撞急停，收到全零命令后最大位移 23.87 cm，等 12.573 s 才由 PD 接管；CD12 外层朝向进入 0.125 rad 后停止 XY，后续最大位移 21.26 cm，等 4.557 s 才接管。大部分位移发生在接管前的 RL settling。证据：' +
                             HERE.relative_to(REPO).as_posix() + '/REPORT.md')
    state['handoff'] = ('第一项停止分析已完成，未修改控制器、未跑新仿真。下一步统一 Controller/tracker 终点控制；D07 是碰撞急停，需同时考虑终点转向空间；CD12 是外层提前停止位置调整。两者主要漂移发生在 PD 接管前，先处理接近/过渡，不盲调 PD 增益。')
    state['updatedAt'] = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    text = re.sub(pattern, lambda m: m.group(1) + json.dumps(state, ensure_ascii=False).replace('<', '\\u003c') + m.group(3), text)
    PLAN.write_text(text)
    print('Updated first checklist item and measured findings panel:', PLAN)


if __name__ == '__main__':
    main()
