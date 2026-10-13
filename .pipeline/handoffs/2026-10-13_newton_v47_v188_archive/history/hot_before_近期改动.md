# 近期改动

更新：2026-10-02；实验与分析。

2026-10-02：
- Cold-tail audit reproduces unchanged v50 corner failure at476–482ms; CPU samples identify repeated terrain-tree lookups. v52 adds one scoped lookup cache, passes builds/safety/parity, reduces idle paired max by10.67%. Live trial02 then measures10.19 Hz successful planning, max711.404 ms and46.57 s late pause; 17 compact returns verified, all795 bulk members archived remotely. Physical tail/continuity/30Hz acceptance fails. v48 remains the reference; remote heavy-data policy is one sentence in AGENTS.md.

2026-10-01：
- 汇总v36–v46组件、失败实跑、wall视频与原SCAN频率证据；刷新热区。无新实验、v47、正式训练或真机动作；旧冻结版本保留。

2026-09-30：
- v36目标/时钟/停止契约；v39/v44原始贡献缓存；v40 CPU图逐位合格并集成，CUDA图未通过误差门槛。组件几何一致不等于局部30 Hz。
- v42/v45实跑均未完成Building；v45局部16.8619、原始控制29.9648、global1.0000 Hz，导航RTF0.9400，末尾pct_no_route。原始回传与copyback核验。
- v46生成v45真实wall视频57.033秒/1711帧，全解码通过；只读优化审计发现647轮首搜索失败，单次19.7 ms仍21轮超时。优化未实施，原论文无固定局部Hz。

2026-09-29：
- v31–v33与墙钟链诊断完成；v33移植5070Ti、实跑走廊入口失败、视频与4597原始文件回传；私有字节保留/令牌轮换决定仍开放。

2026-09-28：
- v28修崩溃、v29点+雷达柱、v30支撑证据与停止诊断；v31保留单线程安全点取消息，完整路线未验收。

2026-09-27：
- v24短楼梯到达；v26修自动楼层；v27完整路线段错误。

入口：[会话归档](../../.pipeline/handoffs/2026-10-01_newton_v36_v46_archive/SESSION_SUMMARY.md)。
