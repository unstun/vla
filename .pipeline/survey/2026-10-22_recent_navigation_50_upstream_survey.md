---
origin: ai_only
reviewed: false
---

# 2026-10-22：新增 50 个近期开源仓库及 6 个补充参考

Dr Sun 要求至少新增 50 个最新开源仓库。已下载并核验 **50 个默认分支在 2026-04-22 之后有提交的新仓库**；另保留 **6 个较早更新的相关参考**。总计 56 个有效仓库身份，其中 50 个创建于 2025–2026 年，6 个为更早创建的项目。创建时间与最近源码提交日期分别记录，不混淆“新项目”和“旧项目的近期版本”。

完整交付：[中文分类目录与逐仓库阅读入口](../../references/upstream/2026-10-22_recent_navigation_50/comparison.md)、[固定版本清单](../../references/upstream/2026-10-22_recent_navigation_50/repository_manifest.yaml)、[核验结果](../../references/upstream/2026-10-22_recent_navigation_50/verification.json)。

## 覆盖与优先级

| 方向 | 近半年源码提交 | 含补充参考 |
|---|---:|---:|
| 导航、控制衔接与恢复 | 9 | 12 |
| 地形与运动能力 | 11 | 12 |
| 定位建图与三维感知 | 18 | 20 |
| 视觉语言导航 | 5 | 5 |
| 仿真评测与控制工具 | 7 | 7 |
| 合计 | 50 | 56 |

当前 v290 的终点转向/停站问题，优先参考 ros2_controllers、Quadruped-PyMPC、RoboGauge 和 MUSE；地形可执行性参考 ReTAP、JEPLO，以及补充区的 Feetend-Planner；路由和系统衔接参考 SWAGGER、DDDMR。源码、入口和适配边界见完整目录。

## 取得和核验范围

- GitHub 多组检索及逐仓库元数据核实；Exa 两个方向共请求 30 条候选结果。
- 检索和旧收藏覆盖不是同一个数量：以已有正式收藏及调研记录中的 361 个身份做保守去重，本次有效仓库与之交集为零。
- 固定默认分支提交、源码日期、代码许可证及许可证文件哈希。按本地 Git 对象核验检出文件，保留逐文件 SHA-256 清单；对 Git 属性规定的 CRLF 转换单独记录。
- 源码工作区跳过媒体、权重、数据及模型资产；子模块未展开。第三方文件、模型和数据的许可不能由根许可证推导。
- 两个缺少实际实现的仓库未计数；Ultra-Fusion 尚未公开核心源码，SA-MPPI 根许可证与 README 声明冲突，均保留记录并排除在达标数量外。

证据等级为 **imported**。本次做的是源码入库和初步映射，没有运行安装脚本、训练、仿真、导航或真机程序，也没有更换 v232/v233 基线或推进 v290 修复实验。尚无独立核查，frontmatter 的 reviewed 保持 false。

## 保存和恢复

源码与原始记录位于 `references/upstream/2026-10-22_recent_navigation_50/source/` 和 `raw_logs/`，沿用上级 `.gitignore`。版本清单、分类说明、候选/排除理由和恢复脚本入本地 Git。

`acquire.py --restore` 根据清单恢复固定提交；`--restore --verify-only` 重新核验现有检出。恢复脚本不执行上游程序。第一轮被中止的下载/校验记录保留在 raw_logs，原因和处理见完整目录。当前 `local/research-unpublished` 分支的发布保留要求继续有效。
