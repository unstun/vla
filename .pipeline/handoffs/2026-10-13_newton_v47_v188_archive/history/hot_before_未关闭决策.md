# 未关闭决策

更新：2026-10-02；实验与分析。

- [ ] 10-02 Local30Hz and tail elimination remain open. v47/v48/v50/v52 are implemented; v49 timeout mechanics are rejected. v52 idle replay and physical attempt02 are complete: 10.67% paired gain, but10.19 Hz successful plans and711.404 ms maximum. Next diagnose corner continuation and cold retry work in v53; preserve goal/yaw/PVA/support and stop rules. Component speedup is not full-system acceptance.
- [ ] 09-30 v45目检反馈与global_refresh_failed:pct_no_route诊断；完整Building到达、目标XYZ/yaw与最终PD保持仍未验收。
- [ ] 09-28 hold常量控制点仍位置纠偏，零控制语义需独立处理；不得跳过安全检查。
- [ ] 09-28 “腿可碰、机身不可碰”碰撞模型：13 cm凸起跨越须V12能力证据；步高上限、高箱/薄墙拒绝及动态行人处理仍待设计。
- [ ] 09-29 gpu5070ti机器人私有控制器快照/arm64镜像按用户决定保留供v34；v34后是否删除仍待决定，本轮未清理。
- [ ] 09-29 cloudflared隧道令牌片段曾进入试运行文件与复审记录；原文件已脱敏，是否轮换由Dr Sun决定。
- [ ] 历史归因未关闭：旧53次inside-obstacle中48次推测扫描超时、入口拐角5次未定；v33无>0.25秒位姿间隙，不能证明对停顿的容忍度。
- [ ] HarnessVLN并行主线与其既有准入/评测闸门保留，本archive不替代其决定。
- [ ] [⚠ 长期未决] Isaac A4、Pi/Cortex、OmniVLA、Issue Tracker暂缓。

已落实：明确局部/控制30 Hz、全局1 Hz；目标XY0.25 m/yaw0.25 rad及初始路线末段朝向；采用逐位合格的CPU图，CUDA图未采用；不建Trellis任务。
入口：[本次归档](../../.pipeline/handoffs/2026-10-01_newton_v36_v46_archive/SESSION_SUMMARY.md)；[v29–v35旧热区](../../.pipeline/handoffs/2026-10-01_newton_v36_v46_archive/history/)。
