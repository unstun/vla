"""Generate the requested Chinese report from returned v288 evidence only."""
from pathlib import Path
import csv
import hashlib
import json

H = Path(__file__).resolve().parent
E = H.parents[2]
B = E / 'audits/2026-10-20_v287_local_cost_crash/ultra9'
load = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
yn = lambda value: '通过' if value else '未通过'
f = lambda x, n=3: '—' if x is None else f'{x:.{n}f}'

def main():
    s = load(H / 'physical_summary.json')
    g = load(H / 'offline/offline_gate.json')
    old = load(B / 'physical_summary.json')
    bill = load(H / 'physical_return/failure_terminal_bill.json')
    before = load(B / 'physical_return/failure_terminal_bill.json')
    startup = load(H / 'startup_return/summary.json')
    inventory = load(H / 'physical_return/return_inventory.json')
    decode = load(H / 'evidence/local_full_video_decode01.json')
    admission = load(H / 'evidence/physical_manifest01.json')['execution_admission']
    assert decode['passed'] and len(decode['files']) == 10
    assert s['formal_attempts'] == 10 and s['attempts_per_case'] == 1
    assert not g['passed'] and admission['timing_exception_authorized']
    assert admission['all_non_timing_gates_passed'] and not admission['timing_target_met']
    rows = s['cases']
    signal_crashes = sum(bool(r.get('native_faults')) for r in bill['cases'])
    old_signal_crashes = sum(bool(r.get('native_faults')) for r in before['cases'])
    order = load(H / 'evidence/input_order_audit01.json')
    parent_order = load(H / 'evidence/parent_input_order_audit01.json')
    affected = [r['case_id'] for r in order['cases'] if r['regressed_body_source_stamp_mentions']]
    unresponsive = [r['case_id'] for r in bill['cases'] if 'native_node_unresponsive' in json.dumps(r.get('finish', {}))]
    coupled = s['goal_pd_and_all_recorded_physical_envelope_clear']
    factory = sum(r['sampled_factory_envelope_clear'] for r in startup['cases'])
    physical_passed = coupled == factory == 10 and s['native_process_failures'] == 0 and s['scanner_deadline_failures'] == 0
    acceptance = dict(version='v288', offline_passed=g['passed'], timing_target_met=False,
        timing_exception_authorized=True, physical_passed=physical_passed,
        overall_passed=bool(g['passed'] and physical_passed),
        goal_and_pd=s['goal_and_pd_passed'], goal_pd_and_recorded_geometry=coupled,
        startup_envelopes=factory, native_signal_crashes=signal_crashes, native_process_failures=s['native_process_failures'],
        body_timestamp_regression_cases=affected, unresponsive_cases=unresponsive,
        scanner_deadline_miss=s['scanner_deadline_failures'])
    (H / 'acceptance.json').write_text(json.dumps(acceptance, indent=2) + '\n')
    counters = []
    for key in bill['cases'][0]['target_errors']:
        counters.append(dict(metric=key,
            v287=sum(r['target_errors'][key] for r in before['cases']),
            v288=sum(r['target_errors'][key] for r in bill['cases'])))
    with (H / 'error_comparison.csv').open('w') as stream:
        w = csv.DictWriter(stream, fieldnames=['metric', 'v287', 'v288'])
        w.writeheader(); w.writerows(counters)
    lines = ['# v288 完整验证报告', '',
        f"离线合法 **{g['positive_passed']}/50**、非法拒绝 **{g['illegal_correct_rejections']}/3**；全局中位耗时 **{g['global_median_s']:.6f} s，超过 1.5 s，未达标**。用户明确批准保留该结果并继续十条。",
        f"十条各单次物理实跑：**{s['goal_and_pd_passed']}/10 到达并完成 PD**；其中 **{coupled}/10 到达且整个后续传感器记录的几何检查通过**。原生信号崩溃 **{signal_crashes}** 次，原生进程/响应异常 **{s['native_process_failures']}** 次。完整验收 **{yn(acceptance['overall_passed'])}**。", '',
        '## 改动与约束', '',
        '基于冻结 v287 切出 v288，保留前版。329 份原生源码组成完整执行副本，15 个原生文件有变更。0.35 m 静态硬边界、0.1 s 扫描周期与截止时间不变，未加入路线、场景或坐标特判。最终源码冻结后未再修改导航，也未重跑已有正步数的路线。', '',
        '1. GridMap 共享一把 recursive_mutex，通过 lockMutex() 在地图注册回调入口与 FSM callbackBoundary 串行执行工作；允许同线程传感器刷新重入，时钟与私有快照查询组保持独立。',
        '2. 体素障碍依据真实非地面膨胀贡献源分类；空气或未命中贡献源交给一次完整支撑、层关联、净空与新鲜度判定。删除原始未穿过空气判 Unknown 后再豁免的分支，此处没有精确 StaticSolidField 网格查询。',
        '3. 地形端点先使用支撑面投影；失败后采用上游弦线/平面候选调整，删除 ring<=2 锁死及额外邻接预条件，仍经过占用、搜索边段与完整轨迹检查。',
        '4. 环境代价固定每 span 3 个积分样本；edge 非正区间代价饱和且梯度为零，原始负余量仍保留用于诊断；solid 穿透推离梯度保留。两阶段 L-BFGS 使用 past=3、delta=1e-4，返回后写回已回滚到最后接受步的 q；函数评估次数 iter_num_>1 的有限候选交给现有硬碰撞与动力学门禁。取消与非有限结果仍失败。负求解返回保留日志与计数。iter_num_ 实际计数函数评估，不等于已接受下降步数；本轮不能据此声称每次保留候选都已取得有效下降。',
        '5. 终点阶段同时做 XY 归中与 yaw 对齐，XY 比例速度上限 0.15 m/s，转入机体系并经同一 slew 限幅。跟踪器和外层 Controller 共用 0.02 m 居中停止条件，避免外层在 0.25 m 圈边提前切入 PD；外部任务验收容差未放宽。', '',
        '## 单元测试与上游依据', '',
        '最终原生测试 20 份 XML、178 次执行，失败 0；另有 8 项环境场、20 项修复探针、4 项地形方向、4 项轨迹时钟、1000 次双线程工作边界调用检查和 5 类信号栈捕获检查。完整 14 包从空构建目录重建，避免类布局混用；早期开发探针失败记录保留。',
        '双线程探针在父版观测最大并入 2，在候选观测 1，并验证递归进入与查询独立性。它验证显式串行不变量，不单独证明所安装 Foxy 的底层竞态窗口。',
        '主要依据仓库内归档的 [SCAN-Planner](https://github.com/wuyi2121/SCAN-Planner/tree/348e8a590a50a5a6bbab8d8c6dcfd171f009be26) 单线程 spin、膨胀占用、弦线调整及终点位置反馈；PCT 归档版本为 [35cd73f](https://github.com/byangw/PCT_planner/tree/35cd73fd82bcd51bc538429294af7646b2a09815)。逐文件绑定见任务 research/author_source_binding.json。',
        '核对 [GCOPTER LBFGS-Lite](https://github.com/ZJU-FAST-Lab/GCOPTER/blob/main/gcopter/include/gcopter/lbfgs.hpp) 后保留现有求解器，未替换库。past=3 有上游依据；delta=1e-4 是本轮指定设置，并非所查上游当前默认值。rclcpp #1708 是线程数配置 PR，#2012 是等待器问题 issue，不能将两者称为本次崩溃的已证实修复 PR。', '',
        '## 50 合法 + 3 非法完整离线门禁', '',
        '| 项目 | 结果 | 判定 |', '|---|---:|---|',
        f"| 合法通过 | {g['positive_passed']}/50 | {yn(g['positive_passed'] >= 48)} |",
        f"| 非法拒绝 | {g['illegal_correct_rejections']}/3 | {yn(g['illegal_correct_rejections'] == 3)} |",
        f"| 全局中位耗时 | {g['global_median_s']:.6f} s | 未通过（目标 <=1.5 s） |",
        f"| 全局 p95 / 最大耗时 | {g['global_p95_s']:.6f} / {g['global_max_s']:.6f} s | 如实保留 |",
        f"| 全局 / 已发布局部几何 | {yn(g['zero_admitted_negative_raw_margin'])} / {yn(g['zero_published_negative_raw_margin'])} | 0.35 m 未变 |",
        f"| 首次 GPMP | {g['first_gpmp_passed']}/{g['global_admitted']} | {100*g['first_gpmp_rate_admitted']:.2f}% |", '',
        '53 次原生计时全部结束后再进行独立几何审计；53 条审计均正常结束。初始化耗时单列，不混入全局调用计时。唯一未通过合法例为 CS01；十条实跑所选路线的离线检查全部通过。未根据结果重新抽样起终点。',
        '全部 50 个合法起点维持统一 >=0.10 m 静态额外安全余量规则，最小边缘约 0.150 m、最小固体约 0.144 m。具体值与原始零步输入绑定见 current_geometry01.json。',
        '严格 offline_gate.json 的 passed 始终为 false。用户原文“继续十条，耗时记未达标”及其源码绑定保存在 user_timing_decision01.json；执行层复用冻结门禁的全部非耗时检查，只对继续实跑作授权记录。', '',
        '## 十条单次实跑结果', '',
        '| 路线 | 到达+PD | 到达+全记录几何 | 时长 s | 实走 m | 支撑额外 cm | 源固体额外 cm | 点云额外 cm | 最长停顿 s |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        lines.append(f"| {r['case_id']} | {yn(r['goal_and_pd_passed'])} | {yn(r['goal_pd_and_all_recorded_physical_envelope_clear'])} | {f(r['simulation_duration_s'],2)} | {f(r['measured_path_m'],2)} | {f(100*r['all_recorded_support_gap_min_m'])} | {f(100*r['all_recorded_source_solid_min_m'])} | {f(100*r['all_recorded_raw_point_min_m'])} | {f(r['maximum_pause_after_first_translation_s'])} |")
    lines += ['',
        f"v287 对照：到达+PD {old['goal_and_pd_passed']}/10，全记录几何与到达双过 {old['goal_pd_and_all_recorded_physical_envelope_clear']}/10，原生信号崩溃 {old_signal_crashes}、原生进程/响应异常 {old['native_process_failures']}。本轮到达 {s['goal_and_pd_passed']}/10、双过 {coupled}/10、信号崩溃 {signal_crashes}、进程/响应异常 {s['native_process_failures']}。单次固定路线试验不等于统计可靠性。", '',
        f"扫描任务 {s['scanner_jobs']} 次；deadline_miss {s['scanner_deadline_failures']} 次。原全局参考几何保留 {s['cases_with_original_global_geometry']}/10。全部已记录的后续传感器轨迹几何均通过，但九条是失败前缀，不能算整条路线安全到达。", '',
        '## 日志计数与局部耗时', '',
        '| 暴露量 | v287 | v288 |', '|---|---:|---:|',
        f"| 记录仿真总时长 s | {sum(r['simulation_duration_s'] for r in old['cases']):.3f} | {sum(r['simulation_duration_s'] for r in rows):.3f} |",
        f"| 完成的局部规划轮次 | {sum(r['local_completed'] for r in old['cases'])} | {sum(r['local_completed'] for r in rows)} |", '',
        '| 相同原始日志计数 | v287 | v288 |', '|---|---:|---:|']
    for r in counters:
        lines.append(f"| {r['metric']} | {r['v287']} | {r['v288']} |")
    old_rounds=sum(r['local_completed'] for r in old['cases']);new_rounds=sum(r['local_completed'] for r in rows)
    old_lbfgs=sum(r['target_errors']['lbfgs_minus1008'] for r in before['cases']);new_lbfgs=sum(r['target_errors']['lbfgs_minus1008'] for r in bill['cases'])
    lines.append(f"| -1008 日志命中/100完成规划轮 | {100*old_lbfgs/old_rounds:.3f} | {100*new_lbfgs/new_rounds:.3f} |")
    lines.append(f"| regressed_body_source_stamp | {sum(r['regressed_body_source_stamp_mentions'] for r in parent_order['cases'])} | {sum(r['regressed_body_source_stamp_mentions'] for r in order['cases'])} |")
    lines += ['', f"实际出现躯干时间戳倒序锁死的路线：{', '.join(affected) if affected else '无'}；原生节点无响应结束的路线：{', '.join(unresponsive) if unresponsive else '无'}。见 evidence/input_order_audit01.json。",
        '零步确定性探针调用冻结的真实 BodyTimeBuffer：手动刷新先处理新消息、锁外已取出的旧消息随后进入，push 返回 [1,0,0]，后续更新消息也被永久拒绝。它证明入口锁不能保证消息获取顺序，并揭示永久错误锁存与手动 take 的冲突；实际传感器记录是否倒序与真实 DDS 取消息顺序仍须分开，未记录的线程顺序不能凭推测写成事实。',
        '计数为包括重试的日志命中次数，不等于独立失败次数。保留所有求解负返回；复用下降结果不会隐去 -1008。提前中止会减少优化调用与暴露时长；按同一解析器的完成规划轮归一化后，-1008 命中并未降低。每轮可含多次优化，以上不是独立求解失败概率；本轮不能宣称线搜索问题已收敛。去除调试器栈重复文本后的 application_log_target_errors 也逐条保留。', '',
        '| 路线 | 整轮 median / p95 / max ms | 优化器 median / p95 / max ms | >50 ms 优化器记录 |', '|---|---:|---:|---:|']
    for r in rows:
        t=r['local_solve_ms'];o=load(H/'physical_return'/r['case_id']/'results/local_stage_latency.json')['stages']['optimizer']
        lines.append(f"| {r['case_id']} | {f(t.get('median'))} / {f(t.get('p95'))} / {f(t.get('maximum'))} | {f(o['median_ms'])} / {f(o['p95_ms'])} / {f(o['maximum_ms'])} | {o['over_50ms']}/{o['reports']} |")
    lines += ['', '整轮还包含输入刷新、搜索、种子、精修和最终检查；优化器低中位数不代表整轮都满足 50 ms。真实资源并行占用保留在资源监控记录中。', '',
        '## 终点居中观测', '',
        '| 路线 | 最小 XY 误差 cm | 末帧 XY 误差 cm | <=2cm 样本 | <=25cm 样本 | 进度超时日志 |', '|---|---:|---:|---:|---:|---:|']
    for r in order['cases']:
        t=r['terminal_centering']
        lines.append(f"| {r['case_id']} | {100*t['minimum_recorded_xy_error_m']:.3f} | {100*t['final_recorded_xy_error_m']:.3f} | {t['samples_within_2cm']} | {t['samples_within_25cm']} | {r['failed_to_make_progress_mentions']} |")
    lines += ['', '这里只统计实际记录的 XY 距离，并非重建跟踪器内部状态。S04 的原生进度超时和终点邻域滞留说明本轮严格 2cm 停止条件与小速度比例控制尚未通过真实收敛验证；未到终点的 D07/CD12 不能拿安全前缀宣称终态擦碰已修复。', '',
        '## 几何、起立与进程证据边界', '',
        f"单独审计工厂起立原始帧 {startup['audited_factory_frames']} 个，几何通过 {factory}/10，最大采样 XY 漂移 {max(r['maximum_recorded_PD_xy_drift_m'] for r in startup['cases']):.6f} m。后续 all_recorded 是实际 10 Hz 躯干记录，包含终态和 PD 尾段，未把启动帧混入。", '',
        '额外余量以 0.35 m 硬边界为零点，正值通常饱和于 +0.15 m，负值完整保留；source solid、独立注册原始点云和支撑空隙均独立报告。WrongHeight 姿态标签不等于真实悬空；未将标签、支撑空隙和固体碰撞混为一谈。采样检查不等于连续时间或足端触地认证。', '',
        '每条原生信号退出、全线程栈、末端错误上下文及 reactive verdict 计数见 failure_terminal_bill.json 与各路线 results/native_signal_trace_audit.json。失败前缀即使余量为正，也不算完整路线通过。', '',
        '## 冻结身份与交付', '', '| 清单 | SHA-256 |', '|---|---|']
    for label,p in [('本地源码',E/'versions/v288/native_manifest.json'),('原生执行',H/'native_manifest01.json'),('物理执行',H/'evidence/physical_manifest01.json')]:
        lines.append(f'| {label} | `{sha(p)}` |')
    lines += ['', '本地 VLA 是唯一源码真源；ultra9 执行副本为 /home/ubuntu/sun/vla_v288_20261020。旧版本、早期开发失败和原始记录保留，未做数据清理。重型原始记录、构建与状态快照保留在远端；紧凑证据及十条实际 MP4 已返回本地。', '',
        '十条视频均为原始物理状态的完整回放，1280×720、30 fps，含工厂起立和导航，使用因果轨迹叠加；渲染没有重新步进物理。所有文件均为本地普通文件，SHA 与远端一致，并完成本地全片解码。', '',
        '| 路线 | 完整视频 | 字节数 |', '|---|---|---:|']
    for r in rows:
        name=Path(r['video_file']).name;record=inventory['videos'][name]
        assert sha(H/'delivered'/name)==record['sha256']
        lines.append(f"| {r['case_id']} | [{name}](delivered/{name}) | {record['bytes']} |")
    lines += ['', '详细表：physical_table.csv；53 条离线：offline/matrix_summary.json；全部日志指标：physical_return/failure_terminal_bill.json；最终验收：acceptance.json。时延未达标与实跑失败均按实际保留，本轮不因此自动升为通过版本。', '']
    (H/'RESULTS_zh.md').write_text('\n'.join(lines))
    (H/'delivered/README.md').write_text('# v288 十条完整单次视频\n\n'+ '\n'.join(f'- [{n}]({(H/"delivered"/n).resolve()})，{r["bytes"]} bytes，SHA-256 `{r["sha256"]}`' for n,r in inventory['videos'].items())+'\n')
    print(json.dumps(acceptance))

if __name__ == '__main__':
    main()
