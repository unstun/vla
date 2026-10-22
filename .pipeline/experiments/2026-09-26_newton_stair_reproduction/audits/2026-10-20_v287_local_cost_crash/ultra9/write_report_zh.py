"""Chinese delivery report assembled from verified v287 result artifacts."""
from pathlib import Path
import json,csv,hashlib
H=Path(__file__).resolve().parent;E=H.parents[2]
load=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 s=load(H/'physical_summary.json');g=load(H/'offline/offline_gate.json');bill=load(H/'physical_return/failure_terminal_bill.json');old=load(E/'audits/2026-10-19_v286_supported_air_refinement/migration_ultra9/physical_return/failure_terminal_bill.json');startup=load(H/'startup_return/summary.json')
 b={r['case_id']:r for r in bill['cases']};media=load(H/'evidence/local_media_verification01.json');inventory=load(H/'physical_return/return_inventory.json')
 lines=['# v287 完整执行报告','',f"**完整修复未通过验收。** 离线合法 {g['positive_passed']}/50（98%）、非法拒绝 {g['illegal_correct_rejections']}/3，全局中位数 **{g['global_median_s']:.3f} s**；十条单次实跑 **6/10 到达并完成 PD，4/10 同时通过完整记录几何检查**。",'',
 '## 本轮实际修改','',
 '在独立 v287 中修改九个生产文件，完整重建十四个原生包。v286 和先前版本均保留。0.35 m 硬阈值、0.1 s 雷达周期/耗时门禁、原有点云新鲜度与饥饿时限、工厂 PD/策略、全局参考路径保持机制均未放宽；没有场景、路线编号或坐标特判。',
 '',
 '1. 删除局部第一阶段的 `hasReboundEnvironmentalField` / `reboundEnvironmentalCostGradient` 精确网格查询，仅保留预计算 ENV225 场；第二阶段继续不加环境项。',
 '2. 两处环境代价都改为无上限的单侧二次铰链，并在余量为零或负数时保留梯度。相同原生数值微分测试：v286 8 项中失败 4 项，v287 8/8 通过。',
 '3. 删除未知空气分支中的精确固体碰撞查询及 `supported_air_source_cache_`，恢复原始“先判断 raw Unknown，再判断膨胀/贡献者”的顺序。只有地图内、未膨胀、完整支撑/层关联/边缘/新鲜度判断通过的未知空气才归一化为空闲；真实障碍和缺失证据仍拒绝。',
 '4. 补充相关 Eigen 堆对象的对齐声明、A* 访问前的索引检查，安全初始化空 A* 对象；配置保留信号退出状态的 GDB 全线程调用栈。**这些改动没有消除真实内存崩溃，不能把补宏等同于根因已修复。**',
 '',
 '原生验证包括 174 次继承测试、18 项局部修复检查、8 项环境值/梯度检查、4 条地形搜索方向、4 组跟踪时钟检查，以及五种致命信号的零物理步调用栈测试。开发期夹具格式/日志目录错误和首个预检的元数据错误均保留，不计为物理实跑。',
 '', '## 完整 50+3 离线门禁','',
 f"53 次规划和 53 条独立几何审计全部结束。合法通过 49/50；唯一未通过合法条目为 CS01。三条非法对照全部拒绝。已接纳路线中位数 {g['global_median_s']:.6f} s，p95 {g['global_p95_s']:.6f} s，最大 {g['global_max_s']:.6f} s；<=1.5 s 中位数门禁通过，初始化耗时单独记录。",
 '全部 50 个合法起点重新核验通过，最小额外边缘余量约 0.1500 m、固体余量约 0.1442 m；53 组请求、起终点、几何和零步雷达夹具与 v286 ultra9 批次逐字节一致，本轮每次规划均为新运行。门禁完成后才执行十条路线。',
 '', '## 十条单次实跑','',
 '表中的几何检查覆盖完整后续传感器记录，包括终点及收尾；起立阶段另有原始状态审计。失败路线的安全前缀不算几何双过。余量正值上限为 +15 cm。', '',
 '| 路线 | 到达+PD | 到达且完整几何通过 | 最小支撑额外余量 cm | 最小固体余量 cm | 终止结果 |',
 '|---|---:|---:|---:|---:|---|']
 for r in s['cases']:
  finish=b[r['case_id']]['finish'];status=finish.get('note','')
  if r['goal_and_pd_passed']:status='到达并完成实测 PD 保持'
  elif 'exit_code=-11' in status:status='controller_server SIGSEGV (-11)'
  elif 'exit_code=-6' in status:status='controller_server SIGABRT (-6)，堆损坏'
  else:status='Nav2 失败'
  lines.append(f"| {r['case_id']} | {'是' if r['goal_and_pd_passed'] else '否'} | {'是' if r['goal_pd_and_all_recorded_physical_envelope_clear'] else '否'} | {100*r['all_recorded_support_gap_min_m']:.3f} | {100*r['all_recorded_source_solid_min_m']:.3f} | {status} |")
 lines += ['', '几何双过路线是 **S04、CM07、CS03、CE03**。D07 和 CD12 到达，但固体边界仍分别越界 1.6354 cm、4.2260 cm；独立原始点几何也同时为负，不能判成浮点噪声。全部十条保留同一全局路径几何；没有通过重跑选择成功结果。',
 '', '## 耗时与错误计数','',
 '优化阶段多数路线中位数约 2.4–4.8 ms，常见耗时已明显下降；但仍存在数百毫秒长尾，不能宣称所有局部优化均低于 50 ms。以下是原生日志 `V50_PROFILE` 的阶段总耗时，包含其内部修补工作；完整局部轮次还包含搜索、输入、种子和复核，详见英文报告与原始 JSON。', '',
 '| 路线 | 优化阶段中位数 ms | p95 ms | 最大 ms | 完整局部轮次最大 ms |', '|---|---:|---:|---:|---:|']
 for r in s['cases']:
  t=load(H/'physical_return'/r['case_id']/'results/local_stage_latency.json')['stages']['optimizer'];whole=r['local_solve_ms']
  lines.append(f"| {r['case_id']} | {t['median_ms']:.3f} | {t['p95_ms']:.3f} | {t['maximum_ms']:.3f} | {whole['maximum']:.3f} |")
 names=dict(pool_exhaustion='Ran out of pool',endpoint_adjustment_failed='端点调整失败',astar_optimization_failed='A-star failed',inside_obstacle='The robot is inside an obstacle',lbfgs_minus1008='L-BFGS -1008',no_executable_trajectory='Native SCAN has no executable trajectory')
 lines += ['', '| 相同逐行计数器 | v286 | v287 |','|---|---:|---:|']
 for k,label in names.items():lines.append(f"| {label} | {sum(r['target_errors'][k] for r in old['cases'])} | {sum(r['target_errors'][k] for r in bill['cases'])} |")
 lines += ['', '这些是包含重试的日志提及次数，不是独立故障次数。另存的去除调试器输出计数与上述结果一致。**断流和 inside-obstacle 大幅下降，但端点调整、A* 与 -1008 相比 v286 回升，相关目标未全部达成。**',
 f"全程 {s['scanner_jobs']} 次雷达扫描，0 次 0.1 s 耗时门禁失败。实际导航 RTF 为 {min(r['actual_rtf'] for r in s['cases']):.6f}–{max(r['actual_rtf'] for r in s['cases']):.6f}，目标仍为 1.0；调试器启动/故障停住会影响墙钟时间。未丢弃物理步或通过重定时伪造实时表现。",
 '', '## 真实剩余问题','',
 '**原生堆内存故障仍在。** A04 的故障指令位于 `terrainCellLayers` 缓存查询，CU06 位于 `rawContributorOccupancy` 缓存查询；CM02 报出 `double free or corruption (out)`，故障线程在 A* 队列向量扩容/释放中。三个故障的全线程栈和寄存器已返回。它们定位了崩溃位置，但尚不能区分更早的非法写入/释放、生命周期错误或并发损坏；不能断言 Eigen 或池索引就是根因。下一次修复需要先找到首次非法访问，不能仅删除一个报错容器。',
 '',
 '**两次固体越界首先发生在终点纯转向。** D07 首次负余量时实际命令为 `[0,0,1.0]`，距请求终点约 0.1251 m；CD12 首次负余量时命令为 `[0,0,0.5019]`，距终点约 0.1068 m。CD12 随后在 `STAND_TRANSITION` 的零命令阶段达到最负余量。因此不能把这两次新越界简单归因于负余量梯度仍为零。',
 '',
 '最严重 D07 样本附近，最新曲线仅发布约 40 ms，最近曲线点距机身约 1.78 cm，以曲线切向评估固体余量为 +7.67 cm，但实测机身朝向与该切向相差约 128.35°，实测余量为负。CD12 最近点相差约 3.96 cm、朝向相差约 23.50°；当时最后曲线已约 1.40 s。这是已发布几何与实测姿态的对照，不能用它倒推出缩放后的内部轨迹相位。',
 '',
 '现有 `tracking_node.hpp:310–323` 在 XY/Z 捕获范围内直接切到零线速度的最终朝向对齐。原本允许的终点纯转向仍可能突破真实包络；优化器在参考曲线上的软排斥不能自动保证这个执行阶段安全。本轮保持冻结，未加急刹门禁、场景分支或事后成功重跑。',
 '', '## 起立、交付和证据边界','',
 f"另外审计 {startup['audited_factory_frames']} 个原始工厂起立帧，十条起立包络均通过，最大采样 PD XY 漂移约 {100*max(v['maximum_recorded_PD_xy_drift_m'] for v in startup['cases']):.2f} cm。起立时名义高度 WrongHeight 与真实 SupportGap/固体余量分别记录，未混为一谈。",
 f"十条完整常规 MP4 已返回本地，总计 {inventory['videos'] and s['video_bytes']:,} 字节，1280×720、30 fps；逐文件 SHA 与远端全量解码/因果曲线检查结果一致，另外目检了 20 个时间样本。视频包含原始起立和导航状态，渲染新增物理步数为零。",
 '物理几何使用记录中的实测机身姿态，后续传感器为 10 Hz 采样，起立单独审计；这不是连续时间或足端接触认证。原始日志/录像状态、归档和构建仍保留在 ultra9，本地保留源码、完整紧凑报告、哈希清单和十条实体视频。',
 '', '## 文件入口','',
 '- [英文技术报告](RESULTS.md)', '- [逐路线完整指标](physical_table.csv)', '- [错误对比](error_comparison.csv)', '- [完整失败账单](physical_return/failure_terminal_bill.json)', '- [视频清单及 SHA](delivered/README.md)', '- [离线逐条结果](offline/matrix_summary.json)',
 '', '源码/执行身份：', '',
 f"- v287 本地源码清单：`{sha(E/'versions/v287/native_manifest.json')}`",
 f"- 原生二进制/输入/评估器清单：`{sha(H/'evidence/native_manifest01.json')}`",
 f"- 十条物理执行清单：`{sha(H/'evidence/physical_manifest01.json')}`",
 '', '结论：离线门禁通过，十条单次实跑、完整报告和视频交付完成；**v287 的全面修复目标未达标，不提升为通过验收的版本。**','']
 (H/'RESULTS_zh.md').write_text('\n'.join(lines))
 print('Chinese complete report written')
if __name__=='__main__':main()
