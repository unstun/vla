# v242–v290 本地提交与实验交付收尾

日期：2026-10-22。阶段：实验与分析的资料归档；本次没有新训练、物理步或远程运行。
授权：Dr Sun 要求先本地提交源码和结果，再更新状态、收尾任务，保留所有实验和失败记录，**不推 GitHub**。

## 决定与入口

- 采用基线仍为源码 **v232 / 执行显示 v233**；`versions/current.json` 保持原字节。
- 最新已评估候选为 **v290**，整体物理验收失败，没有晋升基线。
- 源码、紧凑结果、原任务记录及六份相关规范已保存在本地提交 `77d4ca08e09d23f8193d9e7b9ca81de773669f34`。
- 分支仍为 `local/research-unpublished`；原未公开研究历史继续保留。本次没有 push、merge 或历史重写。
- [完整版本索引](../../../.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/README.md)保存 v242–v281 的逐轮离线、准备、中止与物理失败记录。49 个目录不等于 49 个完成验收的版本；v243/v258/v263 等准备记录仍按原状态保存。

## 最近各轮实测结果

| 版本 | 到达并完成 PD | 同时通过该轮采样几何 | 整体修复验收 |
|---|---:|---:|---|
| [v280/v281/v282](../../../.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-19_v280_source_generalization/RESULTS.md) | 4/10 | 2/10 | 未通过 |
| [v283](../../../.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-19_v283_navigation_geometry/RESULTS.md) | 5/10 | 2/10 | 未通过 |
| [v284](../../../.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-19_v284_static_continuity/RESULTS.md) | 3/10 | 1/10 | 未通过 |
| [v285](../../../.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-19_v285_local_search_tracking/RESULTS.md) | 6/10 | 5/10 | 未通过 |
| [v286（ultra9）](../../../.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-19_v286_supported_air_refinement/migration_ultra9/RESULTS.md) | 0/10 | 0/10 | 未通过 |
| [v287](../../../.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-20_v287_local_cost_crash/ultra9/RESULTS_zh.md) | 6/10 | 4/10 | 未通过 |
| [v288](../../../.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-20_v288_reentrant_work_terminal/ultra9/RESULTS_zh.md) | 1/10 | 1/10 | 未通过 |
| [v289](../../../.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-20_v289_ordered_input_terminal/ultra9/RESULTS_zh.md) | 6/10 | 5/10 | 未通过 |
| [v290](../../../.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-21_v290_terrain_terminal/ultra9/RESULTS_zh.md) | 6/10 | 4/10 | 未通过 |

每轮每条路线只有一次正式尝试。表格复述各原报告；主机、实现及部分审计口径变化，不作为受控性能排名。到达、几何、持续实时性、重复可靠性和真机验证分开记录。

## v290 留下的明确问题

- 完整离线 53 项：合法 49/50，非法拒绝 3/3，中位 1.361381101 s；原生 256 项功能测试和 14 项静态检查通过。这是已有记录，本次未重跑。
- 十条实测：6 条到达并完成 PD，4 条同时通过采样几何；原生信号崩溃 0，扫描 deadline_miss 2。
- 外层 Controller 的 `goal_braking_` 会提前转入 `brakeCommand()/publishStop()`，绕过归中；tracker 也存在朝向达标就停止 XY 的路径。下一步优先统一这两处终点控制。
- D07/CD12 终点转向与 PD 交接仍越界；最坏源固体余量分别 -27.60/-13.77 cm。终点位置、实际转向和 PD 漂移应合并检查。
- G05/CS03 的 100 ms 扫描超时保留为失败；CS03 在超时前已越界，不能全部归因于 CPU 负载。
- 原生搜索/求解失败、持续 30 Hz、重复可靠性、反馈绕行、逐脚接触、真机与 VLA 闭环仍未闭合。旧决策见保留快照。

## 任务收尾

v242–v282 总任务以及 v283–v289 七个任务，共 **8 个**归档到 `.trellis/tasks/archive/2026-10/`。
`completed` 表示本轮交付行政收尾；每个任务都另记 `acceptance_passed=false`，保留失败结论、原记录和后续入口。
[v290 待审查任务](../../../.trellis/tasks/10-21-v290-terrain-terminal/CLOSEOUT.md)保留为 `review`，集中承接余下问题。没有因目录归档启动新实验；范围外旧任务不变。

## 保留与核对

[保留清单与复核命令](../../../.pipeline/experiments/2026-09-26_newton_stair_reproduction/artifact_retention/2026-10-22_v242-v290_local/README.md)覆盖全部原文件：源码和紧凑结果进入 Git，6,152 个本地原始数据/媒体文件原位保留并记录大小和 SHA-256，174 个缓存也未删除。
42 份冻结清单的 2,494 项声明源已匹配。视频、完整日志和大数据没有加入新提交；没有搬移或删除实验目录。
Git 提交不等于原始数据的异地备份；本次未访问或验证远程存储。原有主机路径按历史证据保留。

[刷新前热区原文](../改动记录/2026-10-22_pre-v290-hot-zone/MANIFEST.json)完整保存。最终维护检查见 [verification.json](../../../.pipeline/experiments/2026-09-26_newton_stair_reproduction/artifact_retention/2026-10-22_v242-v290_local/verification.json)。
