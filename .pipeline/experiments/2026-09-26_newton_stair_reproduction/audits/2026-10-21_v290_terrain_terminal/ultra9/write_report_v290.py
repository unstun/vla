"""Write Chinese results from returned evidence, including every failed attempt."""
from pathlib import Path
import json
H=Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_text())

def main():
    s=load(H/'physical_summary.json');g=load(H/'offline/offline_gate.json')
    unit=load(H/'component_return01/summary.json')
    startup=load(H/'startup_return/summary.json');boot={r['case_id']:r for r in startup['cases']}
    bill=load(H/'physical_return/failure_terminal_bill.json');errors={r['case_id']:r for r in bill['cases']}
    order=load(H/'evidence/input_order_audit01.json')
    causes=load(H/'case_diagnoses.json')
    parent=load(H.parents[1]/'2026-10-20_v289_ordered_input_terminal/ultra9/physical_summary.json')
    combined=sum(r['goal_pd_and_all_recorded_physical_envelope_clear'] and boot[r['case_id']]['sampled_factory_envelope_clear'] for r in s['cases'])
    signals=sum(bool(errors[r['case_id']]['native_faults']) for r in s['cases'])
    regressed=sum(r['regressed_body_source_stamp_mentions'] for r in order['cases'])
    acceptance=dict(version='v290',offline_passed=g['passed'],timing_exception_authorized=False,
        XML_testcases=unit['testcases'],functional_testcases=256,static_check_testcases=14,functional_failures=unit['failures']+unit['errors'],
        goal_and_pd=s['goal_and_pd_passed'],goal_pd_and_sampled_factory_and_recording_geometry=combined,
        native_signal_crash_routes=signals,native_process_failure_routes=s['native_process_failures'],
        scanner_deadline_misses=s['scanner_deadline_failures'],regressed_body_source_stamp_mentions=regressed,
        original_global_geometry_routes=s['cases_with_original_global_geometry'],
        physical_passed=combined==10 and signals==0 and s['scanner_deadline_failures']==0)
    acceptance['overall_passed']=bool(acceptance['offline_passed'] and acceptance['functional_failures']==0 and acceptance['physical_passed'])
    (H/'acceptance.json').write_text(json.dumps(acceptance,indent=2)+'\n')
    status='通过' if acceptance['overall_passed'] else '未通过'
    lines=['# v290 楼梯高度、膨胀障碍与终点减速实测报告','',
        f"**总验收{status}。** 离线 {g['positive_passed']}/50、非法 {g['illegal_correct_rejections']}/3、全局中位 {g['global_median_s']:.3f} s 均达标。十条各一次，{s['goal_and_pd_passed']}/10 到达并完成实测 PD 保持，{combined}/10 同时通过工厂起立及后续全记录的采样几何审计。原生信号崩溃 {signals}；扫描 deadline_miss {s['scanner_deadline_failures']}。",'',
        '## 1. 修改范围与实际根因','',
        '父版本为冻结 v289。v290 仅修改七个原生/测试文件。未改 0.35 m 硬安全半径、前后双圆柱偏移、0.1 s 扫描与 deadline、0.35 s 点云新鲜度、原躯干新鲜度、全局参考保持机制、ENV225、工厂 v216 策略/PD 或 53 个输入。没有路线、坐标或场景分支。','',
        '- **端点精度与中途高度被错误绑定。** v289 的 `!exact_endpoint` 同时决定地形搜索是否启用，精确目标请求的中间节点因而沿起终点斜平面走。v290 由真实地形可用性决定中间节点高度，精确起点 XYZ、精确终点连接边与原始准入保持。错误端点高度和无支撑负对照仍拒绝。',
        '- **CM02 遇障退点触发隐式模式切换。** v289 地形端点投影失败后直接 `terrain_search_=false`，整个搜索退回斜平面。v290 移除此切换，后退仅改 XY，每个候选重新关联台阶高度并执行原占用检查；失败仍失败，不伪造支撑。无地形时的原平面算法保留。',
        '- **踏面立面与楼板下方回波污染膨胀层。** 原立面分类只从高踏面识别；现在用相邻已选踏面的同一高度区间从两侧识别。另仅排除整个源体素均在查询关联支撑面下方的贡献，原始占用、非地面历史、地面上障碍及支撑/新鲜度检查保留。未添加精确网格慢查询或新缓存。',
        '- **CD12 终态擦墙不能只归咎于最后的零速。** v289 首次越界时实际仍在 RL 行进，所施加线速度约 0.407 m/s；最坏 -4.62 cm 出现在随后的 STAND_TRANSITION。v290 在原捕获圈之前复用位置比例增益限制接近速度，且仅此额外限速生效时同步减慢轨迹相位。原捕获圈、最终朝向控制、slew 与 PD 交接门槛不变。新实跑是否修复由下表决定。','',
        '## 2. 单元、录制输入与离线门禁','',
        f"14 包原生构建和功能套件通过，返回 XML 共 {unit['testcases']} 项（256 项功能测试、14 项 cppcheck/lint_cmake 检查）、失败 {unit['failures']}、错误 {unit['errors']}、跳过 {unit['skipped']}。沿用父版本明确排除的三个 Nav2 cpplint/uncrustify/xmllint 检查，不能把功能测试通过写成全部风格检查通过。",'',
        '原生精确楼梯双向测试：父版本 0/2，候选 2/2；相同八个历史失败请求：父版本及仅修高度的中间候选 0/8，最终候选 8/8，返回端点精度检查均通过。录制回放使用完整已测前缀、同步地图、精确实测起点及原日志四舍五入目标，不等于重现异步回调状态，也不是新物理到达。CD12 控制器回放共 4,977 tick、零异常，证明减速命令改变，不能代替实跑几何。','',
        '| 离线指标 | v290 | 门槛 |','|---|---:|---:|',
        f"| 合法通过 | {g['positive_passed']}/50 | ≥48/50 |",f"| 非法拒绝 | {g['illegal_correct_rejections']}/3 | 3/3 |",f"| 全局中位 | {g['global_median_s']:.6f} s | ≤1.5 s |",f"| 全局 P95 / 最大 | {g['global_p95_s']:.3f} / {g['global_max_s']:.3f} s | 单独报告 |",'',
        '53 次原生计时和独立几何审计全部完成。全部 50 个合法起点统一复核，最小额外支撑/固体余量分别 0.1500 / 0.1442 m；合法 CS01 沿用原始无路结论。原 2 CPU 配额，在用户批准的共享 CARLA/ROS 负载下计时，不宣称空闲主机，也没有启用耗时例外。','',
        '## 3. 十条单次物理实跑','',
        '“到达”要求原始 FINISHED、精确原目标/朝向审查和连续末尾 ≥2 s 实测 FIXED_STAND；几何由原始实测姿态独立计算。下表余量均为 0.35 m 外额外余量，包含起立及已录后续过程；负数就是越界。失败路线不计未录到的后续段。','',
        '| 路线 | 到达+PD | 支撑最小 cm | 源固体最小 cm | 原始点最小 cm | 扫描超时 | 结论 |','|---|---|---:|---:|---:|---:|---|']
    for r in s['cases']:
        cid=r['case_id'];b=boot[cid]
        vals=[min(r['all_recorded_support_gap_min_m'],b['minimum_support_gap_extra_margin_m']),min(r['all_recorded_source_solid_min_m'],b['minimum_source_solid_margin_m']),min(r['all_recorded_raw_point_min_m'],b['minimum_raw_point_margin_m'])]
        lines.append(f"| {cid} | {'是' if r['goal_and_pd_passed'] else '否'} | {vals[0]*100:+.2f} | {vals[1]*100:+.2f} | {vals[2]*100:+.2f} | {r['scanner_deadline_failures']} | {causes[cid]} |")
    lines+=['',f"若把原生静态姿态verdict也要求全部为Free，则到达联合通过为{s['goal_pd_and_measured_geometry_clear']}/10；物理支撑与源/原始点固体采样联合通过为{combined}/10，CM07动态WrongHeight记录仍逐项保留，不把它当作真实悬空。",'',f"v289 到达+PD 为 {parent['goal_and_pd_passed']}/10；v290 为 {s['goal_and_pd_passed']}/10。每版本每路线仅一次，个别路线变化须按下述证据解释，不能当作统计可靠性提升。",'',
        '## 4. 失败、边界与运行开销','']
    for r in s['cases']:lines.append(f"- **{r['case_id']}**：{causes[r['case_id']]}")
    keys=['pool_exhaustion','endpoint_adjustment_failed','astar_optimization_failed','inside_obstacle','lbfgs_minus1008','no_executable_trajectory']
    totals={k:sum(e['target_errors'][k] for e in bill['cases']) for k in keys}
    sweep=load(H/'terminal_geometry01/summary.json')
    lines+=['','**终点尚未解决的直接代码原因：** 外层 `Controller::computeVelocityCommands()` 在25cm位置容差和朝向内进入 `goal_braking_`，直接返回 `LocalMotion::brakeCommand()`；后者调用 `tracker_->publishStop()`。这条更外层的终点门槛绕开持续归中，使仅修改 tracker 接近速度不足以解决实际PD交接滑移。tracker 自己也会在朝向合格时停止XY，不要求到中心。这是应统一收敛的重复终点控制，不能继续只调早刹车。','',
        '追加静态诊断：在每个原目标精确中心、名义身体高度下，保持0.35m半径，对32个朝向做几何查询。它不是新实跑，也不表示实际必须原地转一圈；仅证明“最终姿态合法”不能自动推出“任意转头过程合法”。CD12 本次首次/最坏越界时仍是负yaw，准确居中在邻近已查负yaw样本下仍有正余量，因此全角扫掠本身不能单独归因为这次擦墙；实测偏心和PD滑移证据单独保留。','',
        '| 原目标 | 指定朝向余量cm | 全角采样最小cm | 负值朝向数/32 |','|---|---:|---:|---:|']
    for item in sweep['cases']:
        lines.append(f"| {item['case_id']} | {item['requested']['source_solid_margin_m']*100:+.2f} | {item['minimum_yaw_sweep_source_margin_m']*100:+.2f} | {item['negative_yaw_samples']} |")
    lines+=['','| 日志项 | 本轮次数 |','|---|---:|']+[f'| `{k}` | {v} |' for k,v in totals.items()]
    lines+=['','| 路线 | 完整轮次成功/总数 | 中位ms | P95ms | 最大ms |','|---|---:|---:|---:|---:|']
    for r in s['cases']:
        metrics=load(H/'physical_return'/r['case_id']/'results/metrics.json')['planning']
        latency=metrics['solve_ms']
        lines.append(f"| {r['case_id']} | {metrics['successful']}/{metrics['completed']} | {latency['median']:.2f} | {latency['p95']:.2f} | {latency['maximum']:.2f} |")
    lines+=['','完整轮次按原始收敛主机时钟映射及实际录制区间统计；它和goal-request至终止的窗口成功数有独立边界，两个分母不混用。中位小于50ms不等于尾部也满足50ms。','',
        '这是完整实际日志中的错误行次数，包含重试；不是独立碰撞次数。`-1008` 使用严格数字匹配，排除 `---1008` 重规划计数器，原始子串次数另外保留。','',
        'G05 与 CS03 均因固定100ms扫描时限中断。CS03扫描324总耗时102.851ms，CPU35.265ms、可运行等待64.311ms；它此前已有局部规划急停/拒绝，不能仅凭最终扫描超时宣称算法过程完全正常。G05 原录制器在 scan 326 的固定周期门禁终止：扫描总耗时 122.908 ms，线程 CPU 39.502 ms，可运行等待 76.357 ms；主机调度干扰有直接计时证据。已有至少 43,780 步真实物理及约 43.8 s 状态，因此计作本轮一次失败，未重跑。原批次因缺少 result.json 误标 startup_failure，原记录未改；continuation02 单独纠正计数，只启动此前未开跑的八条。`native_node_unresponsive` 是录制器停钟后观察到的节点状态，不等同 GDB 证实的信号崩溃。没有伪造缺失的 result.json、完成状态或驾驶器结果。','',
        f"全局原始几何或已走前缀裁剪保持 {s['cases_with_original_global_geometry']}/10；躯干时间戳回退错误 {regressed}。每条局部完整轮次耗时、种子/优化/精修/复核分项见 `physical_summary.json` 与 `local_stage_latency.json`，不能把某个子项耗时写成整轮耗时。",'',
        '## 5. 视频与可追溯性','',
        '[十条离线 HTML 播放器](delivered/index.html)；每条普通 MP4 可单独打开。视频从实际零时刻起立开始，保留全部已录导航、等待、失败与最终状态；显示重放使用原关节/位姿、实测时钟和原曲线，无新增物理步。中断路线展示完整已录前缀，不补造后半段。','',
        f"十条 MP4 共 {s['video_bytes']:,} bytes，均同步到本地、核对 SHA-256、逐文件完整解码，并抽取 20 帧实际画面目检。原始大文件及不裁剪归档留在 ultra9。",'',
        f"- 原生冻结 manifest：`{s['native_manifest_sha256']}`（351 文件，332 原生文件）。",f"- 物理执行 manifest：`{s['execution_manifest_sha256']}`（8,262 文件）。",'- 本地主仓唯一真源；ultra9 为执行副本。冻结后导航、输入及物理关键启动文件不再修改。新分析适配器单独归档，未重跑物理。',
        '- `physical_return/failure_terminal_bill.json`、`boundary_witnesses.json`、`mechanism_witnesses.json`：错误计数、首次/最坏越界实际命令与日志行号。',
        '- `component_return01`、`offline`、`startup_return`、`physical_return`、`evidence`：测试、53 次门禁、起立/全程审计、录制及交付证明。',
        '- 零步组装失败及旧 lsof 保留失败均保留。使用经逐成员验证的不裁剪 capture_snapshot；没有删除原记录。',
        '- 自动浏览器预览因file://协议被工具策略拒绝，未绕过。HTML数据绑定、文件链接及JavaScript语法静态检查通过；全部视频的实际完整解码和20帧目检另有证据，不把静态检查写成浏览器播放通过。',
        '- 本轮未晋升 v232/v233 已接受基线，未暂存或提交 Git；验收失败项目明确保留。','']
    (H/'RESULTS_zh.md').write_text('\n'.join(lines))
    (H/'delivered/README.md').write_text('# v290 实跑全片\n\n'+ '\n'.join(f"- [{r['case_id']}](v290_{r['case_id']}_full_attempt01.mp4)：{causes[r['case_id']]}" for r in s['cases'])+'\n\n[完整中文报告](../RESULTS_zh.md)\n')
    print(json.dumps(acceptance,ensure_ascii=False))
if __name__=='__main__':main()
