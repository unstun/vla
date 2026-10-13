# 项目状态简报

更新：2026-10-02；阶段：实验与分析。

活跃工作：
- Newton local30Hz remains unvalidated. v48 is the reference; v49 is a frozen failed timeout attempt; v50 directly inherits v48. v52 inherits v50 and caches scoped terrain lookups: 35 native/64 cache checks and18 paired rounds pass; idle replay max473.514→422.981 ms. Live attempt02: 10.19 Hz successful plans, max711.404 ms, path23.19 m and late pause46.57 s; controller30 Hz. Cold recovery, continuity and30Hz still fail; 795 bulk members are archived remotely. See versions/v52/RESULTS.md.
- v45全局刷新以pct_no_route失败，未到达；global实测1.0000 Hz、原始controller29.9648 Hz。等待57秒wall视频目检与下一设计决定。
- HarnessVLN导航主线保留；本轮未改其任务或结果。

关键上下文：
- Local VLA is the source of truth; gpu5070ti is the execution copy. current remains v48; development is frozen v52; storage/rendering is v51. Heavy data/builds stay remote, compact provenance/plots and review videos return locally; inherited source snapshots are referenced by hash.
- v36 Nav2目标/身份/停止契约通过34项native、15项backend及独立只读审查；目标XY0.25 m、yaw0.25 rad，默认初始路线末段朝向；局部/控制30 Hz、全局1 Hz为用户要求。
- v40 CPU solver graph连续4.1秒、200行轨迹逐位同原CPU，physics-only RTF1.5845；原1 ms PD/物理、20 ms策略与逐步安全检查保留。CUDA图误差超预定门槛，未采用。
- v44组件完整旧几何同原，11.76/12.76 ms；v45完整链路导航RTF0.9400（53.835 native/57.271 wall秒），661原始文件回传SHA一致；不得用组件速度证明完整系统。
- v3仍仅一次12 m空地accepted；v34/v35完整Building失败证据保留，完整楼层、动态避障和Isaac A4未验收。

未解警告：
- v46为真实wall时间线播放，30 FPS不是局部规划Hz，也不证明仿真1:1；额外STOP消息不计为controller定时器Hz。
- 原SCAN论文不报固定重规划Hz；作者代码FSM100、安全20、controller100 Hz，新轨迹按事件/位移触发。
- hold仍会位置纠偏；私有控制器/镜像清理、令牌轮换和旧未归因停止证据未关闭。

入口：[会话归档](../../.pipeline/handoffs/2026-10-01_newton_v36_v46_archive/SESSION_SUMMARY.md)。视频：output/2026-09-30_lite3_realtime/v45_actual_wall_57s.mp4。
