# 新增开源参考仓库：2026-10-22

已实际下载并核验 **50 个近半年有默认分支提交的新仓库**，另保留 **6 个补充参考**，共 56 个有效仓库身份。

“近期”按 2026-04-22 至本次取得的默认分支提交判断，使用 Git commit 日期，不使用网页 updated_at 或最近 push 时间。较老项目的当前维护版本明确列出创建年份。

本次以已有正式收藏和调研记录中的 361 个仓库身份做保守去重；同仓库分支、子模块和内嵌依赖不另计。独立仓库数量不代表原创算法数量：SRU 等衍生部署实现会标明来源关系。

证据等级：**imported（源码已导入）**。检查了源码存在、许可证、Git 提交与本地文件一致性；没有运行上游安装、训练、仿真或真机程序。源码工作区按 sparse 模式跳过媒体、权重、数据和模型资产，子模块没有展开。

按 Dr Sun 随后的要求，本批及既有参考源码已迁至 `/Volumes/ModelArchive/vla-references/`；项目中的 `source` 是外接盘链接，原阅读路径保持可用。见 [迁移核验与路径恢复](../storage/2026-10-22_external/README.md)。

## 当前项目优先阅读

优先看 ros2_controllers 的停止/控制切换、Quadruped-PyMPC 的模型失配与接触控制、ReTAP 的地形轨迹、RoboGauge 的执行能力评测、MUSE 的实测速度、JEPLO 的 LiDAR 感知控制。SWAGGER 与 DDDMR 可补全路由和完整系统对照。Feetend-Planner 放在补充区，适合研究足端地形与身体轨迹。

保留现有 v232/v233 基线与 v290 修复计划；收集参考不代表采用新架构。

## 方向分布

| 方向 | 近半年提交 | 含补充参考 |
|---|---:|---:|
| 导航与恢复 | 9 | 12 |
| 地形与运动能力 | 11 | 12 |
| 定位建图与三维感知 | 18 | 20 |
| 视觉语言导航 | 5 | 5 |
| 仿真评测与控制工具 | 7 | 7 |

## 50 个近期仓库

| # | 仓库与本地源码 | 创建 | 固定提交日期 | 代码许可证 | 当前用途 |
|---:|---|---|---|---|---|
| 1 | [botbotrobotics/BotBrain](https://github.com/botbotrobotics/BotBrain) · [本地](source/botbotrobotics__BotBrain) | 2026 | [2026-05-18](https://github.com/botbotrobotics/BotBrain/commit/b646f5ee2a2d9bc43ddc006c67a12ad366900f98) | MIT | 四足导航、地图、遥操作和状态监测的完整系统接口 |
| 2 | [dfl-rlab/dddmr_navigation](https://github.com/dfl-rlab/dddmr_navigation) · [本地](source/dfl-rlab__dddmr_navigation) | 2025 | [2026-10-15](https://github.com/dfl-rlab/dddmr_navigation/commit/43d48ee593f073d116b5656484a120cd5f0b75b1) | BSD-3-Clause | 三维地图到控制器的完整地面导航实现 |
| 3 | [iit-DLSLab/muse](https://github.com/iit-DLSLab/muse) · [本地](source/iit-DLSLab__muse) | 2024 | [2026-10-15](https://github.com/iit-DLSLab/muse/commit/f5acb87e9764a574c78fa406218fcc261e1464b6) | BSD-3-Clause | 融合 IMU 与关节状态估计四足实测运动，辅助判断真正停稳 |
| 4 | [ManifoldTechLtd/Odin-Nav-Stack](https://github.com/ManifoldTechLtd/Odin-Nav-Stack) · [本地](source/ManifoldTechLtd__Odin-Nav-Stack) | 2025 | [2026-08-21](https://github.com/ManifoldTechLtd/Odin-Nav-Stack/commit/e6a28acef044bad8aa5daaef3a8f4b07904ca85b) | Apache-2.0 | LiDAR 定位、地图和自主导航的整套接口 |
| 5 | [ros-controls/ros2_controllers](https://github.com/ros-controls/ros2_controllers) · [本地](source/ros-controls__ros2_controllers) | 2017 | [2026-10-19](https://github.com/ros-controls/ros2_controllers/commit/e70c3573807076e93583a022620348d1a9244a3e) | Apache-2.0 | 查看轨迹跟踪、指令超时、停止和控制器状态切换的成熟实现 |
| 6 | [engineai-robotics/engineai_navigation](https://github.com/engineai-robotics/engineai_navigation) · [本地](source/engineai-robotics__engineai_navigation) | 2026 | [2026-09-10](https://github.com/engineai-robotics/engineai_navigation/commit/7ee29a3ede5ecd7d884a1a53b258cd5a0147bd81) | Apache-2.0 | LiDAR 距离图驱动导航与底层步态分层接口 |
| 7 | [ManifoldTechLtd/SRU-Odin](https://github.com/ManifoldTechLtd/SRU-Odin) · [本地](source/ManifoldTechLtd__SRU-Odin) | 2026 | [2026-07-22](https://github.com/ManifoldTechLtd/SRU-Odin/commit/6a81ba77f46d4ab010d3d3354d54ec25ef730955) | MIT | 感知导航策略在实际传感器上的部署适配 |
| 8 | [suchetanrs/roadmap-explorer](https://github.com/suchetanrs/roadmap-explorer) · [本地](source/suchetanrs__roadmap-explorer) | 2025 | [2026-07-06](https://github.com/suchetanrs/roadmap-explorer/commit/203ff2602e1a1e41eec7ef663eacc21266e270c6) | Apache-2.0 | 探索航点、路线图更新与目标选择 |
| 9 | [tudelft/Bee-Nav](https://github.com/tudelft/Bee-Nav) · [本地](source/tudelft__Bee-Nav) | 2026 | [2026-10-21](https://github.com/tudelft/Bee-Nav/commit/408f03155a639afd8e28ae77529d7b938062d62e) | MIT | 轻量视觉导航与学习飞行启发的记忆机制 |
| 10 | [ASIG-X/JEPLO](https://github.com/ASIG-X/JEPLO) · [本地](source/ASIG-X__JEPLO) | 2026 | [2026-09-17](https://github.com/ASIG-X/JEPLO/commit/460e2272907af053d6e66b57fec71fdbe6ca1774) | GPL-3.0 | 无显式地图的 LiDAR 感知步态表示，比较地形输入与运动能力 |
| 11 | [HITSZ-NRSL/ReTAP-Planner](https://github.com/HITSZ-NRSL/ReTAP-Planner) · [本地](source/HITSZ-NRSL__ReTAP-Planner) | 2025 | [2026-09-08](https://github.com/HITSZ-NRSL/ReTAP-Planner/commit/dc908c076ab9608c83442f3fc4268d9db6fe7698) | Apache-2.0 | 不平地形上的可行轨迹和地形约束组织 |
| 12 | [iit-DLSLab/basic-locomotion-isaaclab](https://github.com/iit-DLSLab/basic-locomotion-isaaclab) · [本地](source/iit-DLSLab__basic-locomotion-isaaclab) | 2025 | [2026-10-22](https://github.com/iit-DLSLab/basic-locomotion-isaaclab/commit/92687729f3b85ca4c88f87d075f64c1ff99a0777) | BSD-3-Clause | 多四足平台的指令、观测、训练和部署边界 |
| 13 | [iit-DLSLab/Quadruped-PyMPC](https://github.com/iit-DLSLab/Quadruped-PyMPC) · [本地](source/iit-DLSLab__Quadruped-PyMPC) | 2024 | [2026-10-15](https://github.com/iit-DLSLab/Quadruped-PyMPC/commit/c46cb9a3960554cffc467a71c6674b65c0f4a2c8) | BSD-3-Clause | 四足 MPC、落脚优化、接触力平滑及模型失配处理 |
| 14 | [nvidia-isaac/SWAGGER](https://github.com/nvidia-isaac/SWAGGER) · [本地](source/nvidia-isaac__SWAGGER) | 2025 | [2026-09-28](https://github.com/nvidia-isaac/SWAGGER/commit/6e7884b6e2df1ca3173704a059ae8af16728799c) | Apache-2.0 | 从占用地图生成稀疏航点图及 Nav2 路由接口 |
| 15 | [amazon-far/RPL](https://github.com/amazon-far/RPL) · [本地](source/amazon-far__RPL) | 2026 | [2026-10-20](https://github.com/amazon-far/RPL/commit/1ca0250ba3745381cfbfb2b72ebcf55e995076da) | Apache-2.0 | 复杂地形上的感知运动控制与鲁棒性训练 |
| 16 | [GalaxyGeneralRobotics/Click-and-Traverse](https://github.com/GalaxyGeneralRobotics/Click-and-Traverse) · [本地](source/GalaxyGeneralRobotics__Click-and-Traverse) | 2026 | [2026-07-07](https://github.com/GalaxyGeneralRobotics/Click-and-Traverse/commit/866ba392f1c1e84b92ad75fa66550f26e8af8e48) | Apache-2.0 | 视觉目标到跨越动作的分层控制和地形行为衔接 |
| 17 | [iit-DLSLab/fault-locomotion-isaaclab](https://github.com/iit-DLSLab/fault-locomotion-isaaclab) · [本地](source/iit-DLSLab__fault-locomotion-isaaclab) | 2026 | [2026-10-12](https://github.com/iit-DLSLab/fault-locomotion-isaaclab/commit/ce2c85ef5920ab284bb6d9167bfdf51b369b5241) | BSD-3-Clause | 执行能力退化时的运动鲁棒性与失败恢复评测 |
| 18 | [iit-DLSLab/get-up-isaaclab](https://github.com/iit-DLSLab/get-up-isaaclab) · [本地](source/iit-DLSLab__get-up-isaaclab) | 2026 | [2026-09-30](https://github.com/iit-DLSLab/get-up-isaaclab/commit/8b84bc8cdc18d45a839faca9a0ca78ad06e7ea2d) | BSD-3-Clause | 四足起立和恢复动作的状态组织与仿真评测 |
| 19 | [junhengl/mpc-rl](https://github.com/junhengl/mpc-rl) · [本地](source/junhengl__mpc-rl) | 2026 | [2026-06-10](https://github.com/junhengl/mpc-rl/commit/97e37648d19b635f9b233c7146c28e68a8d672eb) | MIT | 训练时以 MPC 引导策略，研究模型误差与执行能力 |
| 20 | [linchangyi1/LocoTouch](https://github.com/linchangyi1/LocoTouch) · [本地](source/linchangyi1__LocoTouch) | 2025 | [2026-05-15](https://github.com/linchangyi1/LocoTouch/commit/31eeaf70cd42be7c24aab7093cf7a1c4f6a1effa) | MIT | 触觉和本体感觉如何进入四足控制与训练 |
| 21 | [PRBonn/rko_lio](https://github.com/PRBonn/rko_lio) · [本地](source/PRBonn__rko_lio) | 2025 | [2026-10-18](https://github.com/PRBonn/rko_lio/commit/04566e598f700bc7d5efcfcf3a83327ce842f4f7) | MIT | 减少传感器特定假设的 LiDAR-IMU 里程计 |
| 22 | [PRBonn/spatio-temporal-mapping](https://github.com/PRBonn/spatio-temporal-mapping) · [本地](source/PRBonn__spatio-temporal-mapping) | 2024 | [2026-04-24](https://github.com/PRBonn/spatio-temporal-mapping/commit/3778de520128aaceb3ecd5b75894de1c9b88fd50) | MIT | 动态环境中时空一致地图构建，研究旧占用如何更新 |
| 23 | [amap-cvlab/ABot-Recon](https://github.com/amap-cvlab/ABot-Recon) · [本地](source/amap-cvlab__ABot-Recon) | 2026 | [2026-10-15](https://github.com/amap-cvlab/ABot-Recon/commit/6e3b2e1257464a74dfceff22eb33190bd228276e) | Apache-2.0 | 长视频流式几何重建与局部上下文管理 |
| 24 | [clegenti/2fast2lamaa](https://github.com/clegenti/2fast2lamaa) · [本地](source/clegenti__2fast2lamaa) | 2024 | [2026-10-09](https://github.com/clegenti/2fast2lamaa/commit/fbeb70b3d658e955400f36272253ac403cf50652) | MIT | 实时 LiDAR-IMU 里程计与大范围地图维护 |
| 25 | [cvg/VIGS-SLAM](https://github.com/cvg/VIGS-SLAM) · [本地](source/cvg__VIGS-SLAM) | 2026 | [2026-07-07](https://github.com/cvg/VIGS-SLAM/commit/22ffe24c6df81d0bf63bd20057565c00c51d2996) | Apache-2.0 | 视觉惯性约束与高斯地图的联合优化 |
| 26 | [hku-mars/UMI-3D](https://github.com/hku-mars/UMI-3D) · [本地](source/hku-mars__UMI-3D) | 2026 | [2026-07-21](https://github.com/hku-mars/UMI-3D/commit/0c54c1e1ac71249d04db64a60b8a8858d9146691) | GPL-2.0 | 多传感器 SLAM 与三维轨迹数据处理 |
| 27 | [kornia/kornia-slam](https://github.com/kornia/kornia-slam) · [本地](source/kornia__kornia-slam) | 2025 | [2026-10-17](https://github.com/kornia/kornia-slam/commit/05ea01ce9f40382917024a7db3987c36c01c76ec) | Apache-2.0 | Rust 实时视觉惯性估计的模块和时间戳接口 |
| 28 | [KTH-RPL/OneMap](https://github.com/KTH-RPL/OneMap) · [本地](source/KTH-RPL__OneMap) | 2025 | [2026-07-29](https://github.com/KTH-RPL/OneMap/commit/897abb4ded745de2c23fe82a606e1ac0d5157089) | MIT | 开放词汇目标与几何地图的统一表达 |
| 29 | [Lab-of-AI-and-Robotics/LEGO-SLAM](https://github.com/Lab-of-AI-and-Robotics/LEGO-SLAM) · [本地](source/Lab-of-AI-and-Robotics__LEGO-SLAM) | 2025 | [2026-08-04](https://github.com/Lab-of-AI-and-Robotics/LEGO-SLAM/commit/84cfbfe9d6920630b3eef37ac12648cd8e9bb17b) | MIT | 语言特征与三维重建融合，用于未来语义导航 |
| 30 | [MIT-SPARK/VGGT-SLAM](https://github.com/MIT-SPARK/VGGT-SLAM) · [本地](source/MIT-SPARK__VGGT-SLAM) | 2025 | [2026-06-29](https://github.com/MIT-SPARK/VGGT-SLAM/commit/35327ac28b7d193df9ccc39ba6346052bb6f1207) | BSD-2-Clause | 视觉基础模型与 SLAM 一致性优化 |
| 31 | [ori-drs/ScaRF-SLAM](https://github.com/ori-drs/ScaRF-SLAM) · [本地](source/ori-drs__ScaRF-SLAM) | 2026 | [2026-09-23](https://github.com/ori-drs/ScaRF-SLAM/commit/e0a34267d575d8b21d548ea8ed3cf5782192bac3) | GPL-3.0 | 前馈视觉模型与传统 SLAM 的尺度一致性 |
| 32 | [ouguangjun/kilo-map](https://github.com/ouguangjun/kilo-map) · [本地](source/ouguangjun__kilo-map) | 2026 | [2026-07-01](https://github.com/ouguangjun/kilo-map/commit/7445a6a2c8ddb133c506f34b5d23e7aacfa550e3) | MIT | LiDAR 里程计、地图维护和鲁棒性实现 |
| 33 | [PRBonn/2DGS-SLAM](https://github.com/PRBonn/2DGS-SLAM) · [本地](source/PRBonn__2DGS-SLAM) | 2025 | [2026-05-13](https://github.com/PRBonn/2DGS-SLAM/commit/b46da105aa6d3899816e05cbf118be96819b8c6c) | MIT | RGB-D 建图与全局一致性 |
| 34 | [PRBonn/rko_slam](https://github.com/PRBonn/rko_slam) · [本地](source/PRBonn__rko_slam) | 2026 | [2026-10-15](https://github.com/PRBonn/rko_slam/commit/4a85cdaf761a3a0f99cb477edc346392a8d7d87b) | MIT | ROS 2 LiDAR-IMU SLAM 和多次运行地图对齐 |
| 35 | [sjtuyinjie/Ground-Fusion2](https://github.com/sjtuyinjie/Ground-Fusion2) · [本地](source/sjtuyinjie__Ground-Fusion2) | 2025 | [2026-08-08](https://github.com/sjtuyinjie/Ground-Fusion2/commit/aa1c8dc80b05df7a536f5759d2f7725ad12015a6) | MIT | 地面机器人多传感器融合及传感器退化处理 |
| 36 | [Tsinghua-MARS-Lab/SLAM-Former](https://github.com/Tsinghua-MARS-Lab/SLAM-Former) · [本地](source/Tsinghua-MARS-Lab__SLAM-Former) | 2025 | [2026-08-10](https://github.com/Tsinghua-MARS-Lab/SLAM-Former/commit/0071ca9e6c53aec55572a5557c5fcf3a23cdba5d) | BSD-3-Clause | Transformer 联合定位建图的研究对照 |
| 37 | [wentingw/AWSM](https://github.com/wentingw/AWSM) · [本地](source/wentingw__AWSM) | 2026 | [2026-10-03](https://github.com/wentingw/AWSM/commit/0dc038a1233b43478d223be4dbfa60b8742b0a72) | Apache-2.0 | 从视觉观测建立可编辑、可仿真的三维环境 |
| 38 | [Yancey2023/small_point_lio](https://github.com/Yancey2023/small_point_lio) · [本地](source/Yancey2023__small_point_lio) | 2025 | [2026-08-31](https://github.com/Yancey2023/small_point_lio/commit/688d75cfa780049ae532e5100ca64f46ad8b1a93) | MIT | 紧凑 Point-LIO 实现，查看状态估计与部署取舍 |
| 39 | [Fantasy-AMAP/fantasy-vln](https://github.com/Fantasy-AMAP/fantasy-vln) · [本地](source/Fantasy-AMAP__fantasy-vln) | 2026 | [2026-08-18](https://github.com/Fantasy-AMAP/fantasy-vln/commit/01be27681184b1b878d79ac9fd434f032051427a) | Apache-2.0 | 多模态推理与视觉语言导航的接口 |
| 40 | [Ganvin-Li/AlldayWalker](https://github.com/Ganvin-Li/AlldayWalker) · [本地](source/Ganvin-Li__AlldayWalker) | 2026 | [2026-06-29](https://github.com/Ganvin-Li/AlldayWalker/commit/a7ab7b4c948ce53e4f5187b00ec50b1ae52514ab) | Apache-2.0 | 跨时段、多场景导航适应与长期评测 |
| 41 | [GWxuan/AwareVLN](https://github.com/GWxuan/AwareVLN) · [本地](source/GWxuan__AwareVLN) | 2026 | [2026-05-24](https://github.com/GWxuan/AwareVLN/commit/8f14eb8450cdd14ff4e3ba1ea04824255121e6be) | Apache-2.0 | 导航推理的自我状态意识和决策校准 |
| 42 | [NJU-R-L-Group-Embodied-Lab/lavira-code](https://github.com/NJU-R-L-Group-Embodied-Lab/lavira-code) · [本地](source/NJU-R-L-Group-Embodied-Lab__lavira-code) | 2026 | [2026-06-17](https://github.com/NJU-R-L-Group-Embodied-Lab/lavira-code/commit/4b87bed3b70e4d6e3e28d59466baa37b6647c1f4) | Apache-2.0 | 语言与视觉到机器人动作的转换 |
| 43 | [TeleHuman/GN0](https://github.com/TeleHuman/GN0) · [本地](source/TeleHuman__GN0) | 2026 | [2026-09-01](https://github.com/TeleHuman/GN0/commit/c92778118542bf1dd7d437855d06e0d822e8361d) | Apache-2.0 | 导航生成、评测和策略学习的一体化实验组织 |
| 44 | [iit-DLSLab/state_estimation_benchmark](https://github.com/iit-DLSLab/state_estimation_benchmark) · [本地](source/iit-DLSLab__state_estimation_benchmark) | 2026 | [2026-09-07](https://github.com/iit-DLSLab/state_estimation_benchmark/commit/8e87a77bf47e667c0366c447b02fd5e198a1d752) | BSD-3-Clause | 比较四足本体状态估计，检查停站时实测速度和足端运动是否可信 |
| 45 | [mit-acl/mighty](https://github.com/mit-acl/mighty) · [本地](source/mit-acl__mighty) | 2025 | [2026-10-16](https://github.com/mit-acl/mighty/commit/a21dcd5dd9367a8db32171857ae68f16b2baf521) | BSD-3-Clause | 实时轨迹生成、速度连续性和动态重规划的实现对照 |
| 46 | [wty-yy/RoboGauge](https://github.com/wty-yy/RoboGauge) · [本地](source/wty-yy__RoboGauge) | 2025 | [2026-10-05](https://github.com/wty-yy/RoboGauge/commit/add2c7ee0185ea8fd93d242f86e1c8cac6e9913b) | MIT | 对现有 RL 步态做速度跟踪、稳定性和鲁棒性评测 |
| 47 | [allenai/vla-evaluation-harness](https://github.com/allenai/vla-evaluation-harness) · [本地](source/allenai__vla-evaluation-harness) | 2026 | [2026-10-01](https://github.com/allenai/vla-evaluation-harness/commit/41bd8a44dbe5ba0f7902adb5b7c121c1c174dc84) | Apache-2.0 | 模型与环境解耦的评测接口、逐回合记录和异步推理测量 |
| 48 | [isaac-sim2real/sage](https://github.com/isaac-sim2real/sage) · [本地](source/isaac-sim2real__sage) | 2025 | [2026-04-27](https://github.com/isaac-sim2real/sage/commit/5b31cfa35416d1300b5099557049bd8e9cb4507d) | Apache-2.0 | 量化命令到关节实际运动的仿真与真机差距 |
| 49 | [Renforce-Dynamics/genesislab](https://github.com/Renforce-Dynamics/genesislab) · [本地](source/Renforce-Dynamics__genesislab) | 2026 | [2026-04-24](https://github.com/Renforce-Dynamics/genesislab/commit/0f2e4d96df9b24bcce66f8bdf7a1884a1363a5bb) | BSD-3-Clause | 轻量仿真任务组织和不同步态策略的评测接口 |
| 50 | [zsibot/matrix](https://github.com/zsibot/matrix) · [本地](source/zsibot__matrix) | 2025 | [2026-09-23](https://github.com/zsibot/matrix/commit/55ad3fec77deaf1b589d27fa6cc4bfca4553754e) | BSD-3-Clause | 传感器、物理仿真与可视化分离的系统组织 |

## 补充参考：不计入近期 50 个

| 仓库与本地源码 | 固定提交日期 | 用途 |
|---|---|---|
| [ivaROS/quad_gap](https://github.com/ivaROS/quad_gap) · [本地](source/ivaROS__quad_gap) | 2026-02-25 | 基于可通行间隙的四足局部规划，作为简洁控制组 |
| [leggedrobotics/ocs2](https://github.com/leggedrobotics/ocs2) · [本地](source/leggedrobotics__ocs2) | 2025-12-16 | 切换系统最优控制、足式接触约束与感知 MPC 的参考实现 |
| [hucebot/g1pilot](https://github.com/hucebot/g1pilot) · [本地](source/hucebot__g1pilot) | 2026-03-03 | ROS 2 机器人状态和控制桥接的工程组织 |
| [lab-sun/Feetend-Planner](https://github.com/lab-sun/Feetend-Planner) · [本地](source/lab-sun__Feetend-Planner) | 2026-03-05 | 以足端地形特征生成身体轨迹，补充仅查身体中心的规划视角 |
| [PRBonn/kiss-slam](https://github.com/PRBonn/kiss-slam) · [本地](source/PRBonn__kiss-slam) | 2025-12-05 | 简洁 LiDAR SLAM 作为定位建图工程对照 |
| [arclab-hku/P2M](https://github.com/arclab-hku/P2M) · [本地](source/arclab-hku__P2M) | 2026-04-07 | LiDAR 输入下的动态环境端到端导航与控制接口 |

## 源码复核后未计数

- **SimonSchwaiger/resireg-traversability**：No implementation source found 本地记录保留。
- **sjtuyinjie/Ultra-Fusion**：README 明确说明当前仅发布可执行文件和演示，核心源码待论文接收后公开；工具脚本不作为完整算法开源计数。 本地记录保留。
- **FINS-Fines/FineNav**：No implementation source found 本地记录保留。
- **Robot-Nav/SA-MPPI**：根 LICENSE 为 Apache-2.0，但 README 第 13 节声明 GPLv3-or-later；源码保留，许可冲突单列，不计入本次达标数量。 本地记录保留。

另有候选因许可证尚未完成核验、与当前任务关联较弱或已有引用而未入选；见 [候选表](candidates.json) 和 [GitHub 元数据](metadata.json)。NOASSERTION 或空字段表示本次没有确认可采用的许可证，不直接断言项目一定没有许可证。

## 使用与恢复

- [固定版本、许可证哈希、入口和原始命令摘录](repository_manifest.yaml)
- [校验摘要](verification.json)
- [源码取得与恢复脚本](acquire.py)
- [原始抓取和逐文件 SHA-256](raw_logs/)

恢复命令（在项目根目录）：

```bash
python3 references/upstream/2026-10-22_recent_navigation_50/acquire.py --restore --workers 8
python3 references/upstream/2026-10-22_recent_navigation_50/acquire.py --restore --verify-only --workers 8
```

恢复使用固定提交；不会运行上游代码。对同一次入库生成的逐文件清单，工作区 SHA-256 与 Git blob 校验分别记录；少数 CRLF 文件按仓库 .gitattributes 规范化后匹配原 Git 对象。根许可证不自动覆盖第三方依赖、模型权重或数据集。

## 过程记录

Exa 两个方向各请求 15 条结果，并结合 GitHub 多组检索及逐仓库元数据核实。检索结果只是候选，最终以本地默认分支源码和许可证复核为准。

初次校验误用了会读取遗漏 blob 大小的 git ls-tree --long，触发部分大对象按需下载并超时。已停止本次下载进程树、保留第一次记录，改为仅读取树对象后完成核验；本地 Git 缓存可能因此含工作区排除的对象。没有删除旧参考或失败记录。

源码和原始日志沿用 references/upstream/.gitignore，不加入项目提交；清单、报告和脚本可以本地提交。当前研究分支继续遵守 docs/agents/git-workflow.md 的未发布研究保留要求。

## 逐仓库阅读入口

### botbotrobotics/BotBrain

**优先** · 近半年默认分支提交 · `b646f5ee2a2d9bc43ddc006c67a12ad366900f98`

四足导航、地图、遥操作和状态监测的完整系统接口。系统集成项目，不能把其上游组件重复当独立算法贡献。

主要源码：[botbrain_ws/src/bot_navigation/launch/nav2.launch.py](source/botbotrobotics__BotBrain/botbrain_ws/src/bot_navigation/launch/nav2.launch.py)；[botbrain_ws/src/bot_navigation/scripts/nav2_utils.py](source/botbotrobotics__BotBrain/botbrain_ws/src/bot_navigation/scripts/nav2_utils.py)；[botbrain_ws/src/g1_pkg/scripts/g1_controller_commands.py](source/botbotrobotics__BotBrain/botbrain_ws/src/g1_pkg/scripts/g1_controller_commands.py)；[botbrain_ws/src/bot_navigation/bot_navigation/__init__.py](source/botbotrobotics__BotBrain/botbrain_ws/src/bot_navigation/bot_navigation/__init__.py)；[botbrain_ws/src/bot_navigation/launch/nav_utils.launch.py](source/botbotrobotics__BotBrain/botbrain_ws/src/bot_navigation/launch/nav_utils.launch.py)

原项目说明：[固定版 README](https://github.com/botbotrobotics/BotBrain/blob/b646f5ee2a2d9bc43ddc006c67a12ad366900f98/README.md)。 运行环境提及：Humble、ROS 2、ROS2、cuda、ros2。

### dfl-rlab/dddmr_navigation

**优先** · 近半年默认分支提交 · `43d48ee593f073d116b5656484a120cd5f0b75b1`

三维地图到控制器的完整地面导航实现。需要匹配机器人几何、ROS 版本与速度接口。

主要源码：[src/dddmr_explore_and_search/src/main.cpp](source/dfl-rlab__dddmr_navigation/src/dddmr_explore_and_search/src/main.cpp)；[src/dddmr_global_planner/src/a_star_on_pc.cpp](source/dfl-rlab__dddmr_navigation/src/dddmr_global_planner/src/a_star_on_pc.cpp)；[src/dddmr_global_planner/src/global_planner.cpp](source/dfl-rlab__dddmr_navigation/src/dddmr_global_planner/src/global_planner.cpp)；[src/dddmr_global_planner/script/example_client.py](source/dfl-rlab__dddmr_navigation/src/dddmr_global_planner/script/example_client.py)；[src/dddmr_global_planner/utils/occupancy2ground.cpp](source/dfl-rlab__dddmr_navigation/src/dddmr_global_planner/utils/occupancy2ground.cpp)

原项目说明：[固定版 README](https://github.com/dfl-rlab/dddmr_navigation/blob/43d48ee593f073d116b5656484a120cd5f0b75b1/README.md)。 运行环境提及：README 未提取到标准环境标签。

### iit-DLSLab/muse

**优先** · 近半年默认分支提交 · `f5acb87e9764a574c78fa406218fcc261e1464b6`

融合 IMU 与关节状态估计四足实测运动，辅助判断真正停稳。默认 unitree_sdk 分支；Lite3 需运动学与消息适配。

主要源码：[muse_ws/src/iit_commons/src/planning.cpp](source/iit-DLSLab__muse/muse_ws/src/iit_commons/src/planning.cpp)；[muse_ws/src/iit_commons/src/hydraulics.cpp](source/iit-DLSLab__muse/muse_ws/src/iit_commons/src/hydraulics.cpp)；[muse_ws/src/iit_commons/src/algebra_test.cpp](source/iit-DLSLab__muse/muse_ws/src/iit_commons/src/algebra_test.cpp)；[muse_ws/src/iit_commons/src/test-filters.cpp](source/iit-DLSLab__muse/muse_ws/src/iit_commons/src/test-filters.cpp)；[muse_ws/src/iit_commons/src/planning_test.cpp](source/iit-DLSLab__muse/muse_ws/src/iit_commons/src/planning_test.cpp)

原项目说明：[固定版 README](https://github.com/iit-DLSLab/muse/blob/f5acb87e9764a574c78fa406218fcc261e1464b6/README.md)。 运行环境提及：Humble、ROS 2、ROS2、isaaclab、ros2。

### ManifoldTechLtd/Odin-Nav-Stack

**优先** · 近半年默认分支提交 · `e6a28acef044bad8aa5daaef3a8f4b07904ca85b`

LiDAR 定位、地图和自主导航的整套接口。依赖 Odin 传感器/运行环境，需逐项适配。

主要源码：[ros_ws/src/map_planner/src/map_planner.cpp](source/ManifoldTechLtd__Odin-Nav-Stack/ros_ws/src/map_planner/src/map_planner.cpp)；[ros_ws/src/map_planner/include/map_planner.h](source/ManifoldTechLtd__Odin-Nav-Stack/ros_ws/src/map_planner/include/map_planner.h)；[ros_ws/src/map_planner/src/goal_state_machine.cpp](source/ManifoldTechLtd__Odin-Nav-Stack/ros_ws/src/map_planner/src/goal_state_machine.cpp)；[ros_ws/src/map_planner/include/goal_state_machine.h](source/ManifoldTechLtd__Odin-Nav-Stack/ros_ws/src/map_planner/include/goal_state_machine.h)；[ros_ws/src/unitree_control/src/unitree_vel_controller.cpp](source/ManifoldTechLtd__Odin-Nav-Stack/ros_ws/src/unitree_control/src/unitree_vel_controller.cpp)

原项目说明：[固定版 README](https://github.com/ManifoldTechLtd/Odin-Nav-Stack/blob/e6a28acef044bad8aa5daaef3a8f4b07904ca85b/README.md)。 运行环境提及：CUDA、Noetic、ROS1、ROS2、cuda、noetic、ros1。

### ros-controls/ros2_controllers

**优先** · 近半年默认分支提交 · `e70c3573807076e93583a022620348d1a9244a3e`

查看轨迹跟踪、指令超时、停止和控制器状态切换的成熟实现。通用 ROS 2 控制器；不将轮式约束直接套给 Lite3。

主要源码：[joint_trajectory_controller/src/joint_trajectory_controller.cpp](source/ros-controls__ros2_controllers/joint_trajectory_controller/src/joint_trajectory_controller.cpp)；[ros2_controllers_test_nodes/setup.py](source/ros-controls__ros2_controllers/ros2_controllers_test_nodes/setup.py)；[rqt_joint_trajectory_controller/setup.py](source/ros-controls__ros2_controllers/rqt_joint_trajectory_controller/setup.py)；[ros2_controllers/doc/conf.py](source/ros-controls__ros2_controllers/ros2_controllers/doc/conf.py)；[tricycle_controller/src/odometry.cpp](source/ros-controls__ros2_controllers/tricycle_controller/src/odometry.cpp)

原项目说明：[固定版 README](https://github.com/ros-controls/ros2_controllers/blob/e70c3573807076e93583a022620348d1a9244a3e/README.md)。 运行环境提及：Humble、Jazzy、ROS2、humble、jazzy、ros2。

### engineai-robotics/engineai_navigation

**后续** · 近半年默认分支提交 · `7ee29a3ede5ecd7d884a1a53b258cd5a0147bd81`

LiDAR 距离图驱动导航与底层步态分层接口。PM01 人形且基于 SRU；不当成独立全新算法。

主要源码：[training/sru-navigation-learning/setup.py](source/engineai-robotics__engineai_navigation/training/sru-navigation-learning/setup.py)；[training/scripts/nav/play.py](source/engineai-robotics__engineai_navigation/training/scripts/nav/play.py)；[training/scripts/nav/train.py](source/engineai-robotics__engineai_navigation/training/scripts/nav/train.py)；[training/source/engineai_rl_lab/setup.py](source/engineai-robotics__engineai_navigation/training/source/engineai_rl_lab/setup.py)；[training/scripts/nav/convert_checkpoint.py](source/engineai-robotics__engineai_navigation/training/scripts/nav/convert_checkpoint.py)

原项目说明：[固定版 README](https://github.com/engineai-robotics/engineai_navigation/blob/7ee29a3ede5ecd7d884a1a53b258cd5a0147bd81/README.en.md)。 运行环境提及：Humble、Isaac Lab、ROS 2、humble、isaaclab、ros2。

### ManifoldTechLtd/SRU-Odin

**后续** · 近半年默认分支提交 · `6a81ba77f46d4ab010d3d3354d54ec25ef730955`

感知导航策略在实际传感器上的部署适配。SRU 的部署衍生实现，不当作新的基础算法。

主要源码：[Train/scripts/probe_pt.py](source/ManifoldTechLtd__SRU-Odin/Train/scripts/probe_pt.py)；[Train/scripts/export_onnx.py](source/ManifoldTechLtd__SRU-Odin/Train/scripts/export_onnx.py)；[Train/scripts/inspect_run.py](source/ManifoldTechLtd__SRU-Odin/Train/scripts/inspect_run.py)；[Train/scripts/check_go2_registration.py](source/ManifoldTechLtd__SRU-Odin/Train/scripts/check_go2_registration.py)；[Train/scripts/validate_go2_locomotion.py](source/ManifoldTechLtd__SRU-Odin/Train/scripts/validate_go2_locomotion.py)

原项目说明：[固定版 README](https://github.com/ManifoldTechLtd/SRU-Odin/blob/6a81ba77f46d4ab010d3d3354d54ec25ef730955/README.md)。 运行环境提及：IsaacLab、Noetic、ROS1、isaaclab、noetic、ros1、ros2。

### suchetanrs/roadmap-explorer

**后续** · 近半年默认分支提交 · `203ff2602e1a1e41eec7ef663eacc21266e270c6`

探索航点、路线图更新与目标选择。探索模块，不直接解决局部停站。

主要源码：[roadmap_explorer/src/main.cpp](source/suchetanrs__roadmap-explorer/roadmap_explorer/src/main.cpp)；[roadmap_explorer/src/planners/Astar.cpp](source/suchetanrs__roadmap-explorer/roadmap_explorer/src/planners/Astar.cpp)；[roadmap_explorer/src/planners/NavFn.cpp](source/suchetanrs__roadmap-explorer/roadmap_explorer/src/planners/NavFn.cpp)；[roadmap_explorer/src/planners/ThetaStar.cpp](source/suchetanrs__roadmap-explorer/roadmap_explorer/src/planners/ThetaStar.cpp)；[roadmap_explorer/src/planners/NavFnPlugin.cpp](source/suchetanrs__roadmap-explorer/roadmap_explorer/src/planners/NavFnPlugin.cpp)

原项目说明：[固定版 README](https://github.com/suchetanrs/roadmap-explorer/blob/203ff2602e1a1e41eec7ef663eacc21266e270c6/README.md)。 运行环境提及：Humble、Jazzy、ROS 2、humble、jazzy、ros2。

### tudelft/Bee-Nav

**后续** · 近半年默认分支提交 · `408f03155a639afd8e28ae77529d7b938062d62e`

轻量视觉导航与学习飞行启发的记忆机制。平台/传感器与足式三维约束不同。

主要源码：[code_theoretical_simulation_analysis/insect_navigation.py](source/tudelft__Bee-Nav/code_theoretical_simulation_analysis/insect_navigation.py)；[robot_network_training/home-learning_rpi/test.py](source/tudelft__Bee-Nav/robot_network_training/home-learning_rpi/test.py)；[robot_network_training/home-learning_rpi/train.py](source/tudelft__Bee-Nav/robot_network_training/home-learning_rpi/train.py)；[robot_network_training/home-learning_laptop/test.py](source/tudelft__Bee-Nav/robot_network_training/home-learning_laptop/test.py)；[robot_network_training/home-learning_rpi/dataset.py](source/tudelft__Bee-Nav/robot_network_training/home-learning_rpi/dataset.py)

原项目说明：[固定版 README](https://github.com/tudelft/Bee-Nav/blob/408f03155a639afd8e28ae77529d7b938062d62e/README.md)。 运行环境提及：ROS 2。

### ASIG-X/JEPLO

**优先** · 近半年默认分支提交 · `460e2272907af053d6e66b57fec71fdbe6ca1774`

无显式地图的 LiDAR 感知步态表示，比较地形输入与运动能力。属于步态学习路线，本轮只读源码。

主要源码：[training/lejepa/setup.py](source/ASIG-X__JEPLO/training/lejepa/setup.py)；[training/rsl_rl/setup.py](source/ASIG-X__JEPLO/training/rsl_rl/setup.py)；[training/scripts/play.py](source/ASIG-X__JEPLO/training/scripts/play.py)；[training/scripts/train.py](source/ASIG-X__JEPLO/training/scripts/train.py)；[training/scripts/cli_args.py](source/ASIG-X__JEPLO/training/scripts/cli_args.py)

原项目说明：[固定版 README](https://github.com/ASIG-X/JEPLO/blob/460e2272907af053d6e66b57fec71fdbe6ca1774/README.md)。 运行环境提及：CUDA、Humble、IsaacLab、MuJoCo、Mujoco、ROS2、cuda、humble、isaaclab、mujoco、ros2。

### HITSZ-NRSL/ReTAP-Planner

**优先** · 近半年默认分支提交 · `dc908c076ab9608c83442f3fc4268d9db6fe7698`

不平地形上的可行轨迹和地形约束组织。地面移动机器人方法，需适配多层楼梯和四足支撑。

主要源码：[src/path_planning/include/local_planning/local_planning.h](source/HITSZ-NRSL__ReTAP-Planner/src/path_planning/include/local_planning/local_planning.h)；[src/path_planning/include/local_planning/trajectory_generator.h](source/HITSZ-NRSL__ReTAP-Planner/src/path_planning/include/local_planning/trajectory_generator.h)；[src/mapping_module/src/apps/ghpr_test.cpp](source/HITSZ-NRSL__ReTAP-Planner/src/mapping_module/src/apps/ghpr_test.cpp)；[src/mapping_module/src/apps/pcd_smooth_mls.cpp](source/HITSZ-NRSL__ReTAP-Planner/src/mapping_module/src/apps/pcd_smooth_mls.cpp)；[src/path_planning/src/hybrid_astar/planner.cpp](source/HITSZ-NRSL__ReTAP-Planner/src/path_planning/src/hybrid_astar/planner.cpp)

原项目说明：[固定版 README](https://github.com/HITSZ-NRSL/ReTAP-Planner/blob/dc908c076ab9608c83442f3fc4268d9db6fe7698/README.md)。 运行环境提及：Noetic。

### iit-DLSLab/basic-locomotion-isaaclab

**优先** · 近半年默认分支提交 · `92687729f3b85ca4c88f87d075f64c1ff99a0777`

多四足平台的指令、观测、训练和部署边界。保存源码，模型资产与实机启动均未执行。

主要源码：[deploy/run_controller_ros2.py](source/iit-DLSLab__basic-locomotion-isaaclab/deploy/run_controller_ros2.py)；[scripts/rsl_rl/train.py](source/iit-DLSLab__basic-locomotion-isaaclab/scripts/rsl_rl/train.py)；[scripts/amp_rl/train_amp.py](source/iit-DLSLab__basic-locomotion-isaaclab/scripts/amp_rl/train_amp.py)；[scripts/dagger/train_dagger.py](source/iit-DLSLab__basic-locomotion-isaaclab/scripts/dagger/train_dagger.py)；[scripts/morphosymm_rl/train_symm.py](source/iit-DLSLab__basic-locomotion-isaaclab/scripts/morphosymm_rl/train_symm.py)

原项目说明：[固定版 README](https://github.com/iit-DLSLab/basic-locomotion-isaaclab/blob/92687729f3b85ca4c88f87d075f64c1ff99a0777/README.md)。 运行环境提及：IsaacLab、Mujoco、ROS2、humble、isaaclab、mujoco、ros2。

### iit-DLSLab/Quadruped-PyMPC

**优先** · 近半年默认分支提交 · `c46cb9a3960554cffc467a71c6674b65c0f4a2c8`

四足 MPC、落脚优化、接触力平滑及模型失配处理。用作控制能力对照，不直接替换当前 RL。

主要源码：[ros2/run_controller.py](source/iit-DLSLab__Quadruped-PyMPC/ros2/run_controller.py)；[quadruped_pympc/controllers/__init__.py](source/iit-DLSLab__Quadruped-PyMPC/quadruped_pympc/controllers/__init__.py)；[quadruped_pympc/helpers/swing_trajectory_controller.py](source/iit-DLSLab__Quadruped-PyMPC/quadruped_pympc/helpers/swing_trajectory_controller.py)；[quadruped_pympc/interfaces/srbd_controller_interface.py](source/iit-DLSLab__Quadruped-PyMPC/quadruped_pympc/interfaces/srbd_controller_interface.py)；[quadruped_pympc/interfaces/srbd_batched_controller_interface.py](source/iit-DLSLab__Quadruped-PyMPC/quadruped_pympc/interfaces/srbd_batched_controller_interface.py)

原项目说明：[固定版 README](https://github.com/iit-DLSLab/Quadruped-PyMPC/blob/c46cb9a3960554cffc467a71c6674b65c0f4a2c8/README.md)。 运行环境提及：Mujoco、ROS 2、ROS2、cuda、humble、mujoco、ros2。

### nvidia-isaac/SWAGGER

**优先** · 近半年默认分支提交 · `6e7884b6e2df1ca3173704a059ae8af16728799c`

从占用地图生成稀疏航点图及 Nav2 路由接口。二维占用图方法，不能直接表达跨层楼梯。

主要源码：[scripts/evaluate_graph.py](source/nvidia-isaac__SWAGGER/scripts/evaluate_graph.py)；[swagger/graph_evaluator.py](source/nvidia-isaac__SWAGGER/swagger/graph_evaluator.py)；[swagger/performance_evaluator.py](source/nvidia-isaac__SWAGGER/swagger/performance_evaluator.py)；[integration/nav2/swagger_planner/setup.py](source/nvidia-isaac__SWAGGER/integration/nav2/swagger_planner/setup.py)；[integration/nav2/swagger_planner/launch/planner.launch.py](source/nvidia-isaac__SWAGGER/integration/nav2/swagger_planner/launch/planner.launch.py)

原项目说明：[固定版 README](https://github.com/nvidia-isaac/SWAGGER/blob/6e7884b6e2df1ca3173704a059ae8af16728799c/README.md)。 运行环境提及：CUDA、cuda。

### amazon-far/RPL

**后续** · 近半年默认分支提交 · `1ca0250ba3745381cfbfb2b72ebcf55e995076da`

复杂地形上的感知运动控制与鲁棒性训练。人形平台参考，不能直接移植其策略到 Lite3。

主要源码：[rpl_training/paths.py](source/amazon-far__RPL/rpl_training/paths.py)；[rpl_training/__init__.py](source/amazon-far__RPL/rpl_training/__init__.py)；[rpl_training/train_agent.py](source/amazon-far__RPL/rpl_training/train_agent.py)；[rpl_training/terms/reward.py](source/amazon-far__RPL/rpl_training/terms/reward.py)；[rpl_training/envs/__init__.py](source/amazon-far__RPL/rpl_training/envs/__init__.py)

原项目说明：[固定版 README](https://github.com/amazon-far/RPL/blob/1ca0250ba3745381cfbfb2b72ebcf55e995076da/README.md)。 运行环境提及：IsaacGym、MuJoCo、mujoco。

### GalaxyGeneralRobotics/Click-and-Traverse

**后续** · 近半年默认分支提交 · `866ba392f1c1e84b92ad75fa66550f26e8af8e48`

视觉目标到跨越动作的分层控制和地形行为衔接。需核对 G1 等平台差异，不能当现成四足控制器。

主要源码：[train_ppo.py](source/GalaxyGeneralRobotics__Click-and-Traverse/train_ppo.py)；[train_batch.py](source/GalaxyGeneralRobotics__Click-and-Traverse/train_batch.py)；[train_ppo_dagger.py](source/GalaxyGeneralRobotics__Click-and-Traverse/train_ppo_dagger.py)；[train_dagger_batch.py](source/GalaxyGeneralRobotics__Click-and-Traverse/train_dagger_batch.py)；[procedural_obstacle_generation/main.py](source/GalaxyGeneralRobotics__Click-and-Traverse/procedural_obstacle_generation/main.py)

原项目说明：[固定版 README](https://github.com/GalaxyGeneralRobotics/Click-and-Traverse/blob/866ba392f1c1e84b92ad75fa66550f26e8af8e48/README.md)。 运行环境提及：CUDA、MuJoCo、cuda、mujoco。

### iit-DLSLab/fault-locomotion-isaaclab

**后续** · 近半年默认分支提交 · `ce2c85ef5920ab284bb6d9167bfdf51b369b5241`

执行能力退化时的运动鲁棒性与失败恢复评测。电机故障场景不同于当前终点漂移。

主要源码：[deploy/run_controller_ros2.py](source/iit-DLSLab__fault-locomotion-isaaclab/deploy/run_controller_ros2.py)；[scripts/rsl_rl/train.py](source/iit-DLSLab__fault-locomotion-isaaclab/scripts/rsl_rl/train.py)；[scripts/moe_rsl_rl/train_moe.py](source/iit-DLSLab__fault-locomotion-isaaclab/scripts/moe_rsl_rl/train_moe.py)；[scripts/morphosymm_rl/eval_symm.py](source/iit-DLSLab__fault-locomotion-isaaclab/scripts/morphosymm_rl/eval_symm.py)；[scripts/morphosymm_rl/train_symm.py](source/iit-DLSLab__fault-locomotion-isaaclab/scripts/morphosymm_rl/train_symm.py)

原项目说明：[固定版 README](https://github.com/iit-DLSLab/fault-locomotion-isaaclab/blob/ce2c85ef5920ab284bb6d9167bfdf51b369b5241/README.md)。 运行环境提及：IsaacLab、Mujoco、ROS2、humble、isaaclab、mujoco、ros2。

### iit-DLSLab/get-up-isaaclab

**后续** · 近半年默认分支提交 · `8b84bc8cdc18d45a839faca9a0ca78ad06e7ea2d`

四足起立和恢复动作的状态组织与仿真评测。起立恢复不是精确终点站立控制。

主要源码：[deploy/run_controller_ros2.py](source/iit-DLSLab__get-up-isaaclab/deploy/run_controller_ros2.py)；[scripts/rsl_rl/train.py](source/iit-DLSLab__get-up-isaaclab/scripts/rsl_rl/train.py)；[scripts/morphosymm_rl/train_symm.py](source/iit-DLSLab__get-up-isaaclab/scripts/morphosymm_rl/train_symm.py)；[deploy/config.py](source/iit-DLSLab__get-up-isaaclab/deploy/config.py)；[deploy/console.py](source/iit-DLSLab__get-up-isaaclab/deploy/console.py)

原项目说明：[固定版 README](https://github.com/iit-DLSLab/get-up-isaaclab/blob/8b84bc8cdc18d45a839faca9a0ca78ad06e7ea2d/README.md)。 运行环境提及：IsaacLab、Mujoco、ROS2、humble、isaaclab、mujoco、ros2。

### junhengl/mpc-rl

**后续** · 近半年默认分支提交 · `97e37648d19b635f9b233c7146c28e68a8d672eb`

训练时以 MPC 引导策略，研究模型误差与执行能力。人形运动/操作任务，属于方法参考。

主要源码：[src/themis_training/rl_cfg.py](source/junhengl__mpc-rl/src/themis_training/rl_cfg.py)；[src/themis_training/__init__.py](source/junhengl__mpc-rl/src/themis_training/__init__.py)；[src/themis_training/env_cfgs.py](source/junhengl__mpc-rl/src/themis_training/env_cfgs.py)；[src/themis_training/finetune.py](source/junhengl__mpc-rl/src/themis_training/finetune.py)；[src/themis_training/phase_mdp.py](source/junhengl__mpc-rl/src/themis_training/phase_mdp.py)

原项目说明：[固定版 README](https://github.com/junhengl/mpc-rl/blob/97e37648d19b635f9b233c7146c28e68a8d672eb/README.md)。 运行环境提及：CUDA、MuJoCo、cuda、mujoco。

### linchangyi1/LocoTouch

**后续** · 近半年默认分支提交 · `31eeaf70cd42be7c24aab7093cf7a1c4f6a1effa`

触觉和本体感觉如何进入四足控制与训练。原任务是运输，主要借鉴接触感知与控制接口。

主要源码：[locotouch/scripts/train.py](source/linchangyi1__LocoTouch/locotouch/scripts/train.py)；[setup.py](source/linchangyi1__LocoTouch/setup.py)；[loco_rl/setup.py](source/linchangyi1__LocoTouch/loco_rl/setup.py)；[locotouch/__init__.py](source/linchangyi1__LocoTouch/locotouch/__init__.py)；[locotouch/assets/go1.py](source/linchangyi1__LocoTouch/locotouch/assets/go1.py)

原项目说明：[固定版 README](https://github.com/linchangyi1/LocoTouch/blob/31eeaf70cd42be7c24aab7093cf7a1c4f6a1effa/README.md)。 运行环境提及：CUDA、Isaac Lab、IsaacLab、isaaclab。

### PRBonn/rko_lio

**优先** · 近半年默认分支提交 · `04566e598f700bc7d5efcfcf3a83327ce842f4f7`

减少传感器特定假设的 LiDAR-IMU 里程计。校准、时间同步与鲁棒性需在 Lite3 验证。

主要源码：[tests/python/test_lio_pipeline.py](source/PRBonn__rko_lio/tests/python/test_lio_pipeline.py)；[rko_lio/python/rko_lio/lio_pipeline.py](source/PRBonn__rko_lio/rko_lio/python/rko_lio/lio_pipeline.py)；[.cmake-format.py](source/PRBonn__rko_lio/.cmake-format.py)；[docs/conf.py](source/PRBonn__rko_lio/docs/conf.py)；[launch/autodetect.py](source/PRBonn__rko_lio/launch/autodetect.py)

原项目说明：[固定版 README](https://github.com/PRBonn/rko_lio/blob/04566e598f700bc7d5efcfcf3a83327ce842f4f7/README.md)。 运行环境提及：Humble、Jazzy、ROS1、ROS2、humble、jazzy、ros1、ros2。

### PRBonn/spatio-temporal-mapping

**优先** · 近半年默认分支提交 · `3778de520128aaceb3ecd5b75894de1c9b88fd50`

动态环境中时空一致地图构建，研究旧占用如何更新。动态对象处理不能直接等同当前地图历史规则。

主要源码：[python/st_mapping/__init__.py](source/PRBonn__spatio-temporal-mapping/python/st_mapping/__init__.py)；[python/st_mapping/odometry.py](source/PRBonn__spatio-temporal-mapping/python/st_mapping/odometry.py)；[python/st_mapping/mapping_pipeline.py](source/PRBonn__spatio-temporal-mapping/python/st_mapping/mapping_pipeline.py)；[python/st_mapping/deform_ref_pipeline.py](source/PRBonn__spatio-temporal-mapping/python/st_mapping/deform_ref_pipeline.py)；[python/st_mapping/mapping_onref_pipeline.py](source/PRBonn__spatio-temporal-mapping/python/st_mapping/mapping_onref_pipeline.py)

原项目说明：[固定版 README](https://github.com/PRBonn/spatio-temporal-mapping/blob/3778de520128aaceb3ecd5b75894de1c9b88fd50/README.md)。 运行环境提及：ros2。

### amap-cvlab/ABot-Recon

**后续** · 近半年默认分支提交 · `6e3b2e1257464a74dfceff22eb33190bd228276e`

长视频流式几何重建与局部上下文管理。视觉重建，不等于实时 Lite3 导航。

主要源码：[abot_recon/sparse_loop/retrieval.py](source/amap-cvlab__ABot-Recon/abot_recon/sparse_loop/retrieval.py)；[demo.py](source/amap-cvlab__ABot-Recon/demo.py)；[abot_recon/api.py](source/amap-cvlab__ABot-Recon/abot_recon/api.py)；[abot_recon/cli.py](source/amap-cvlab__ABot-Recon/abot_recon/cli.py)；[tests/test_api.py](source/amap-cvlab__ABot-Recon/tests/test_api.py)

原项目说明：[固定版 README](https://github.com/amap-cvlab/ABot-Recon/blob/6e3b2e1257464a74dfceff22eb33190bd228276e/README.md)。 运行环境提及：CUDA、cuda。

### clegenti/2fast2lamaa

**后续** · 近半年默认分支提交 · `fbeb70b3d658e955400f36272253ac403cf50652`

实时 LiDAR-IMU 里程计与大范围地图维护。需要传感器标定和实际时序适配。

主要源码：[include/preint/Eigen/src/Core/CoreEvaluators.h](source/clegenti__2fast2lamaa/include/preint/Eigen/src/Core/CoreEvaluators.h)；[include/preint/Eigen/src/Core/AssignEvaluator.h](source/clegenti__2fast2lamaa/include/preint/Eigen/src/Core/AssignEvaluator.h)；[include/preint/Eigen/src/Core/CommaInitializer.h](source/clegenti__2fast2lamaa/include/preint/Eigen/src/Core/CommaInitializer.h)；[include/preint/Eigen/src/Core/ProductEvaluators.h](source/clegenti__2fast2lamaa/include/preint/Eigen/src/Core/ProductEvaluators.h)；[include/preint/Eigen/unsupported/src/IterativeSolvers/ConstrainedConjGrad.h](source/clegenti__2fast2lamaa/include/preint/Eigen/unsupported/src/IterativeSolvers/ConstrainedConjGrad.h)

原项目说明：[固定版 README](https://github.com/clegenti/2fast2lamaa/blob/fbeb70b3d658e955400f36272253ac403cf50652/README.md)。 运行环境提及：Jazzy、ROS 2、ROS2、jazzy、ros2、rust。

### cvg/VIGS-SLAM

**后续** · 近半年默认分支提交 · `22ffe24c6df81d0bf63bd20057565c00c51d2996`

视觉惯性约束与高斯地图的联合优化。算力及地图更新延迟需要单独测量。

主要源码：[eval_rpng_mono.py](source/cvg__VIGS-SLAM/eval_rpng_mono.py)；[eval_utmm_mono.py](source/cvg__VIGS-SLAM/eval_utmm_mono.py)；[eval_vigs_mono.py](source/cvg__VIGS-SLAM/eval_vigs_mono.py)；[eval_euroc_mono.py](source/cvg__VIGS-SLAM/eval_euroc_mono.py)；[eval_fastlivo_mono.py](source/cvg__VIGS-SLAM/eval_fastlivo_mono.py)

原项目说明：[固定版 README](https://github.com/cvg/VIGS-SLAM/blob/22ffe24c6df81d0bf63bd20057565c00c51d2996/README.md)。 运行环境提及：CUDA。

### hku-mars/UMI-3D

**后续** · 近半年默认分支提交 · `0c54c1e1ac71249d04db64a60b8a8858d9146691`

多传感器 SLAM 与三维轨迹数据处理。原采集装置不同于 Lite3。

主要源码：[run_dataset_pipeline.py](source/hku-mars__UMI-3D/run_dataset_pipeline.py)；[scripts/eval_real_robot.py](source/hku-mars__UMI-3D/scripts/eval_real_robot.py)；[scripts_slam_pipeline/00_detect_aruco.py](source/hku-mars__UMI-3D/scripts_slam_pipeline/00_detect_aruco.py)；[scripts_slam_pipeline/01_run_calibrations.py](source/hku-mars__UMI-3D/scripts_slam_pipeline/01_run_calibrations.py)；[scripts_slam_pipeline/auto_bag_to_mp4_aligned.py](source/hku-mars__UMI-3D/scripts_slam_pipeline/auto_bag_to_mp4_aligned.py)

原项目说明：[固定版 README](https://github.com/hku-mars/UMI-3D/blob/0c54c1e1ac71249d04db64a60b8a8858d9146691/README.md)。 运行环境提及：Noetic。

### kornia/kornia-slam

**后续** · 近半年默认分支提交 · `05ea01ce9f40382917024a7db3987c36c01c76ec`

Rust 实时视觉惯性估计的模块和时间戳接口。Rust 工具链与传感器格式需适配。

主要源码：[apps/kornia-slam-app/src/main.rs](source/kornia__kornia-slam/apps/kornia-slam-app/src/main.rs)；[apps/kornia-slam-app/src/evaluation.rs](source/kornia__kornia-slam/apps/kornia-slam-app/src/evaluation.rs)；[crates/kornia-slam/src/mapping/mod.rs](source/kornia__kornia-slam/crates/kornia-slam/src/mapping/mod.rs)；[crates/kornia-slam/src/mapping/growth.rs](source/kornia__kornia-slam/crates/kornia-slam/src/mapping/growth.rs)；[crates/kornia-slam/src/mapping/robust.rs](source/kornia__kornia-slam/crates/kornia-slam/src/mapping/robust.rs)

原项目说明：[固定版 README](https://github.com/kornia/kornia-slam/blob/05ea01ce9f40382917024a7db3987c36c01c76ec/README.md)。 运行环境提及：ROS 2、Rust、ros2、rust。

### KTH-RPL/OneMap

**后续** · 近半年默认分支提交 · `897abb4ded745de2c23fe82a606e1ac0d5157089`

开放词汇目标与几何地图的统一表达。留给后续 VLA，当前不接入语义模块。

主要源码：[eval_habitat.py](source/KTH-RPL__OneMap/eval_habitat.py)；[eval_habitat_multi.py](source/KTH-RPL__OneMap/eval_habitat_multi.py)；[eval/actor.py](source/KTH-RPL__OneMap/eval/actor.py)；[eval/__init__.py](source/KTH-RPL__OneMap/eval/__init__.py)；[config/eval_conf.py](source/KTH-RPL__OneMap/config/eval_conf.py)

原项目说明：[固定版 README](https://github.com/KTH-RPL/OneMap/blob/897abb4ded745de2c23fe82a606e1ac0d5157089/README.md)。 运行环境提及：CUDA、cuda、habitat。

### Lab-of-AI-and-Robotics/LEGO-SLAM

**后续** · 近半年默认分支提交 · `84cfbfe9d6920630b3eef37ac12648cd8e9bb17b`

语言特征与三维重建融合，用于未来语义导航。高斯地图不是现有占用/支撑地图的直接替代。

主要源码：[utils/undistort_remaining.py](source/Lab-of-AI-and-Robotics__LEGO-SLAM/utils/undistort_remaining.py)；[submodules/fast_gicp/src/python/main.cpp](source/Lab-of-AI-and-Robotics__LEGO-SLAM/submodules/fast_gicp/src/python/main.cpp)；[clip_sed/language/sed/open_clip/src/training/data.py](source/Lab-of-AI-and-Robotics__LEGO-SLAM/clip_sed/language/sed/open_clip/src/training/data.py)；[clip_sed/language/sed/open_clip/src/training/main.py](source/Lab-of-AI-and-Robotics__LEGO-SLAM/clip_sed/language/sed/open_clip/src/training/main.py)；[clip_sed/language/sed/open_clip/src/training/train.py](source/Lab-of-AI-and-Robotics__LEGO-SLAM/clip_sed/language/sed/open_clip/src/training/train.py)

原项目说明：[固定版 README](https://github.com/Lab-of-AI-and-Robotics/LEGO-SLAM/blob/84cfbfe9d6920630b3eef37ac12648cd8e9bb17b/README.md)。 运行环境提及：CUDA、cuda。

### MIT-SPARK/VGGT-SLAM

**后续** · 近半年默认分支提交 · `35327ac28b7d193df9ccc39ba6346052bb6f1207`

视觉基础模型与 SLAM 一致性优化。依赖模型和算力，未下载权重。

主要源码：[main.py](source/MIT-SPARK__VGGT-SLAM/main.py)；[main_realtime.py](source/MIT-SPARK__VGGT-SLAM/main_realtime.py)；[evals/__init__.py](source/MIT-SPARK__VGGT-SLAM/evals/__init__.py)；[evals/process_logs_tum.py](source/MIT-SPARK__VGGT-SLAM/evals/process_logs_tum.py)；[setup.py](source/MIT-SPARK__VGGT-SLAM/setup.py)

原项目说明：[固定版 README](https://github.com/MIT-SPARK/VGGT-SLAM/blob/35327ac28b7d193df9ccc39ba6346052bb6f1207/README.md)。 运行环境提及：rust。

### ori-drs/ScaRF-SLAM

**后续** · 近半年默认分支提交 · `e0a34267d575d8b21d548ea8ed3cf5782192bac3`

前馈视觉模型与传统 SLAM 的尺度一致性。视觉尺度与 Lite3 LiDAR 几何仍需对齐。

主要源码：[run_mapping.py](source/ori-drs__ScaRF-SLAM/run_mapping.py)；[scarf_slam/mapping_app.py](source/ori-drs__ScaRF-SLAM/scarf_slam/mapping_app.py)；[scarf_slam/mapping/fusion.py](source/ori-drs__ScaRF-SLAM/scarf_slam/mapping/fusion.py)；[scarf_slam/mapping/__init__.py](source/ori-drs__ScaRF-SLAM/scarf_slam/mapping/__init__.py)；[scarf_slam/mapping/graph_io.py](source/ori-drs__ScaRF-SLAM/scarf_slam/mapping/graph_io.py)

原项目说明：[固定版 README](https://github.com/ori-drs/ScaRF-SLAM/blob/e0a34267d575d8b21d548ea8ed3cf5782192bac3/README.md)。 运行环境提及：README 未提取到标准环境标签。

### ouguangjun/kilo-map

**后续** · 近半年默认分支提交 · `7445a6a2c8ddb133c506f34b5d23e7aacfa550e3`

LiDAR 里程计、地图维护和鲁棒性实现。不是规划器或步态控制器。

主要源码：[legkilo/launch_ros2/debug.launch.py](source/ouguangjun__kilo-map/legkilo/launch_ros2/debug.launch.py)；[legkilo/launch_ros2/legkilo_go1_velodyne.py](source/ouguangjun__kilo-map/legkilo/launch_ros2/legkilo_go1_velodyne.py)；[legkilo/src/common/kernel.hpp](source/ouguangjun__kilo-map/legkilo/src/common/kernel.hpp)；[legkilo/src/common/file_io.hpp](source/ouguangjun__kilo-map/legkilo/src/common/file_io.hpp)；[legkilo/src/common/pcl_types.h](source/ouguangjun__kilo-map/legkilo/src/common/pcl_types.h)

原项目说明：[固定版 README](https://github.com/ouguangjun/kilo-map/blob/7445a6a2c8ddb133c506f34b5d23e7aacfa550e3/README.md)。 运行环境提及：Humble、Jazzy、ROS 1、ROS 2、ROS1、ROS2、noetic、ros1、ros2。

### PRBonn/2DGS-SLAM

**后续** · 近半年默认分支提交 · `b46da105aa6d3899816e05cbf118be96819b8c6c`

RGB-D 建图与全局一致性。需检查实时性与深度相机误差。

主要源码：[utils/eval_utils.py](source/PRBonn__2DGS-SLAM/utils/eval_utils.py)；[submodules/dust3r/croco/pretrain.py](source/PRBonn__2DGS-SLAM/submodules/dust3r/croco/pretrain.py)；[submodules/dust3r/dust3r/training.py](source/PRBonn__2DGS-SLAM/submodules/dust3r/dust3r/training.py)；[submodules/dust3r/croco/stereoflow/train.py](source/PRBonn__2DGS-SLAM/submodules/dust3r/croco/stereoflow/train.py)；[submodules/dust3r/mast3r/retrieval/graph.py](source/PRBonn__2DGS-SLAM/submodules/dust3r/mast3r/retrieval/graph.py)

原项目说明：[固定版 README](https://github.com/PRBonn/2DGS-SLAM/blob/b46da105aa6d3899816e05cbf118be96819b8c6c/README.md)。 运行环境提及：CUDA。

### PRBonn/rko_slam

**后续** · 近半年默认分支提交 · `4a85cdaf761a3a0f99cb477edc346392a8d7d87b`

ROS 2 LiDAR-IMU SLAM 和多次运行地图对齐。用于跨次实验定位一致性。

主要源码：[.cmake-format.py](source/PRBonn__rko_slam/.cmake-format.py)；[docs/conf.py](source/PRBonn__rko_slam/docs/conf.py)；[launch/common.py](source/PRBonn__rko_slam/launch/common.py)；[launch/slam.launch.py](source/PRBonn__rko_slam/launch/slam.launch.py)；[launch/align.launch.py](source/PRBonn__rko_slam/launch/align.launch.py)

原项目说明：[固定版 README](https://github.com/PRBonn/rko_slam/blob/4a85cdaf761a3a0f99cb477edc346392a8d7d87b/README.md)。 运行环境提及：Jazzy、ROS2、jazzy、ros2。

### sjtuyinjie/Ground-Fusion2

**后续** · 近半年默认分支提交 · `aa1c8dc80b05df7a536f5759d2f7725ad12015a6`

地面机器人多传感器融合及传感器退化处理。与当前传感器配置需逐项匹配。

主要源码：[Ground-Fusion++/mesh/src/voxel_mapping.cpp](source/sjtuyinjie__Ground-Fusion2/Ground-Fusion++/mesh/src/voxel_mapping.cpp)；[Ground-Fusion++/mesh/src/voxel_mapping.hpp](source/sjtuyinjie__Ground-Fusion2/Ground-Fusion++/mesh/src/voxel_mapping.hpp)；[Ground-Fusion++/mesh/src/voxel_mapping_common.cpp](source/sjtuyinjie__Ground-Fusion2/Ground-Fusion++/mesh/src/voxel_mapping_common.cpp)；[Ground-Fusion++/support_files/grid_mapping/Pose2d.h](source/sjtuyinjie__Ground-Fusion2/Ground-Fusion++/support_files/grid_mapping/Pose2d.h)；[Ground-Fusion++/support_files/grid_mapping/main.cpp](source/sjtuyinjie__Ground-Fusion2/Ground-Fusion++/support_files/grid_mapping/main.cpp)

原项目说明：[固定版 README](https://github.com/sjtuyinjie/Ground-Fusion2/blob/aa1c8dc80b05df7a536f5759d2f7725ad12015a6/README.md)。 运行环境提及：Noetic、ROS 2、ROS2、noetic。

### Tsinghua-MARS-Lab/SLAM-Former

**后续** · 近半年默认分支提交 · `0071ca9e6c53aec55572a5557c5fcf3a23cdba5d`

Transformer 联合定位建图的研究对照。不是当前终点控制修复的优先依赖。

主要源码：[src/croco/pretrain.py](source/Tsinghua-MARS-Lab__SLAM-Former/src/croco/pretrain.py)；[src/croco/stereoflow/train.py](source/Tsinghua-MARS-Lab__SLAM-Former/src/croco/stereoflow/train.py)；[setup.py](source/Tsinghua-MARS-Lab__SLAM-Former/setup.py)；[slam/demo.py](source/Tsinghua-MARS-Lab__SLAM-Former/slam/demo.py)；[slam/utils.py](source/Tsinghua-MARS-Lab__SLAM-Former/slam/utils.py)

原项目说明：[固定版 README](https://github.com/Tsinghua-MARS-Lab/SLAM-Former/blob/0071ca9e6c53aec55572a5557c5fcf3a23cdba5d/README.md)。 运行环境提及：README 未提取到标准环境标签。

### wentingw/AWSM

**后续** · 近半年默认分支提交 · `0dc038a1233b43478d223be4dbfa60b8742b0a72`

从视觉观测建立可编辑、可仿真的三维环境。用于后续场景生成，非实时局部规划器。

主要源码：[scripts/evaluate_pose.py](source/wentingw__AWSM/scripts/evaluate_pose.py)；[scripts/evaluate_depth.py](source/wentingw__AWSM/scripts/evaluate_depth.py)；[scripts/evaluate_geometry.py](source/wentingw__AWSM/scripts/evaluate_geometry.py)；[scripts/evaluate_frozen_model.py](source/wentingw__AWSM/scripts/evaluate_frozen_model.py)；[scripts/evaluate_packet_depth.py](source/wentingw__AWSM/scripts/evaluate_packet_depth.py)

原项目说明：[固定版 README](https://github.com/wentingw/AWSM/blob/0dc038a1233b43478d223be4dbfa60b8742b0a72/README.md)。 运行环境提及：README 未提取到标准环境标签。

### Yancey2023/small_point_lio

**后续** · 近半年默认分支提交 · `688d75cfa780049ae532e5100ca64f46ad8b1a93`

紧凑 Point-LIO 实现，查看状态估计与部署取舍。属于现有算法的衍生实现，单列来源关系。

主要源码：[src/util/pointcloud_mapping.h](source/Yancey2023__small_point_lio/src/util/pointcloud_mapping.h)；[src/util/pointcloud_mapping.cpp](source/Yancey2023__small_point_lio/src/util/pointcloud_mapping.cpp)；[include/pch.h](source/Yancey2023__small_point_lio/include/pch.h)；[src/small_point_lio_node.cpp](source/Yancey2023__small_point_lio/src/small_point_lio_node.cpp)；[src/small_point_lio_node.hpp](source/Yancey2023__small_point_lio/src/small_point_lio_node.hpp)

原项目说明：[固定版 README](https://github.com/Yancey2023/small_point_lio/blob/688d75cfa780049ae532e5100ca64f46ad8b1a93/README.md)。 运行环境提及：ROS2、ros2。

### Fantasy-AMAP/fantasy-vln

**后续** · 近半年默认分支提交 · `01be27681184b1b878d79ac9fd434f032051427a`

多模态推理与视觉语言导航的接口。待基础导航稳定后再接入。

主要源码：[train.py](source/Fantasy-AMAP__fantasy-vln/train.py)；[trainer.py](source/Fantasy-AMAP__fantasy-vln/trainer.py)；[lhvln/nav_gen/main.py](source/Fantasy-AMAP__fantasy-vln/lhvln/nav_gen/main.py)；[lhvln/nav_gen/recognize_anything/pretrain.py](source/Fantasy-AMAP__fantasy-vln/lhvln/nav_gen/recognize_anything/pretrain.py)；[lhvln/NavModel/LLMModel/EVA/EVA_CLIP/rei/training/adan.py](source/Fantasy-AMAP__fantasy-vln/lhvln/NavModel/LLMModel/EVA/EVA_CLIP/rei/training/adan.py)

原项目说明：[固定版 README](https://github.com/Fantasy-AMAP/fantasy-vln/blob/01be27681184b1b878d79ac9fd434f032051427a/README.md)。 运行环境提及：Habitat、habitat。

### Ganvin-Li/AlldayWalker

**后续** · 近半年默认分支提交 · `a7ab7b4c948ce53e4f5187b00ec50b1ae52514ab`

跨时段、多场景导航适应与长期评测。模型适应不等于楼梯运动能力。

主要源码：[alldaywalker/alldaywalker_eval.py](source/Ganvin-Li__AlldayWalker/alldaywalker/alldaywalker_eval.py)；[alldaywalker/alldaywalker_train.py](source/Ganvin-Li__AlldayWalker/alldaywalker/alldaywalker_train.py)；[llava/train/train.py](source/Ganvin-Li__AlldayWalker/llava/train/train.py)；[llava/eval/model_vqa.py](source/Ganvin-Li__AlldayWalker/llava/eval/model_vqa.py)；[llava/train/train_dpo.py](source/Ganvin-Li__AlldayWalker/llava/train/train_dpo.py)

原项目说明：[固定版 README](https://github.com/Ganvin-Li/AlldayWalker/blob/a7ab7b4c948ce53e4f5187b00ec50b1ae52514ab/README.md)。 运行环境提及：CUDA、Habitat、habitat。

### GWxuan/AwareVLN

**后续** · 近半年默认分支提交 · `8f14eb8450cdd14ff4e3ba1ea04824255121e6be`

导航推理的自我状态意识和决策校准。先核对连续动作接口与真实反馈。

主要源码：[evaluation/run.py](source/GWxuan__AwareVLN/evaluation/run.py)；[llava/cli/eval.py](source/GWxuan__AwareVLN/llava/cli/eval.py)；[llava/eval/rtl.py](source/GWxuan__AwareVLN/llava/eval/rtl.py)；[llava/train/args.py](source/GWxuan__AwareVLN/llava/train/args.py)；[llava/train/train.py](source/GWxuan__AwareVLN/llava/train/train.py)

原项目说明：[固定版 README](https://github.com/GWxuan/AwareVLN/blob/8f14eb8450cdd14ff4e3ba1ea04824255121e6be/README.md)。 运行环境提及：Habitat、habitat。

### NJU-R-L-Group-Embodied-Lab/lavira-code

**后续** · 近半年默认分支提交 · `4b87bed3b70e4d6e3e28d59466baa37b6647c1f4`

语言与视觉到机器人动作的转换。需要对齐当前导航执行接口。

主要源码：[vlnce_baselines/lavira_main.py](source/NJU-R-L-Group-Embodied-Lab__lavira-code/vlnce_baselines/lavira_main.py)；[vlnce_baselines/map/mapping.py](source/NJU-R-L-Group-Embodied-Lab__lavira-code/vlnce_baselines/map/mapping.py)；[real_world_code/cobot_magic/main.py](source/NJU-R-L-Group-Embodied-Lab__lavira-code/real_world_code/cobot_magic/main.py)；[real_world_code/unitree_go1/main.py](source/NJU-R-L-Group-Embodied-Lab__lavira-code/real_world_code/unitree_go1/main.py)；[vlnce_baselines/models/fmm_planner.py](source/NJU-R-L-Group-Embodied-Lab__lavira-code/vlnce_baselines/models/fmm_planner.py)

原项目说明：[固定版 README](https://github.com/NJU-R-L-Group-Embodied-Lab/lavira-code/blob/4b87bed3b70e4d6e3e28d59466baa37b6647c1f4/README.md)。 运行环境提及：CUDA、Habitat、habitat。

### TeleHuman/GN0

**后续** · 近半年默认分支提交 · `c92778118542bf1dd7d437855d06e0d822e8361d`

导航生成、评测和策略学习的一体化实验组织。后续 VLA 研究参考，本轮未运行模型。

主要源码：[gn0/evaluation/local.py](source/TeleHuman__GN0/gn0/evaluation/local.py)；[gn0/evaluation/common.py](source/TeleHuman__GN0/gn0/evaluation/common.py)；[gn0/evaluation/remote.py](source/TeleHuman__GN0/gn0/evaluation/remote.py)；[gn0/evaluation/__init__.py](source/TeleHuman__GN0/gn0/evaluation/__init__.py)；[gn0/media.py](source/TeleHuman__GN0/gn0/media.py)

原项目说明：[固定版 README](https://github.com/TeleHuman/GN0/blob/c92778118542bf1dd7d437855d06e0d822e8361d/README.md)。 运行环境提及：CUDA、Habitat、habitat。

### iit-DLSLab/state_estimation_benchmark

**优先** · 近半年默认分支提交 · `8e87a77bf47e667c0366c447b02fd5e198a1d752`

比较四足本体状态估计，检查停站时实测速度和足端运动是否可信。需要匹配机器人运动学和传感器格式。

主要源码：[iekf/apps/main_iekf.cpp](source/iit-DLSLab__state_estimation_benchmark/iekf/apps/main_iekf.cpp)；[muse/apps/main_muse.cpp](source/iit-DLSLab__state_estimation_benchmark/muse/apps/main_muse.cpp)；[invariant_smoother/apps/main_invariant_smoother.cpp](source/iit-DLSLab__state_estimation_benchmark/invariant_smoother/apps/main_invariant_smoother.cpp)；[muse/include/Csv.hpp](source/iit-DLSLab__state_estimation_benchmark/muse/include/Csv.hpp)；[muse/include/lib.hpp](source/iit-DLSLab__state_estimation_benchmark/muse/include/lib.hpp)

原项目说明：[固定版 README](https://github.com/iit-DLSLab/state_estimation_benchmark/blob/8e87a77bf47e667c0366c447b02fd5e198a1d752/README.md)。 运行环境提及：README 未提取到标准环境标签。

### mit-acl/mighty

**优先** · 近半年默认分支提交 · `a21dcd5dd9367a8db32171857ae68f16b2baf521`

实时轨迹生成、速度连续性和动态重规划的实现对照。同时面向无人机和地面机器人，不包含 Lite3 步态。

主要源码：[src/hgp/hgp_planner.cpp](source/mit-acl__mighty/src/hgp/hgp_planner.cpp)；[include/hgp/hgp_planner.hpp](source/mit-acl__mighty/include/hgp/hgp_planner.hpp)；[include/timer.hpp](source/mit-acl__mighty/include/timer.hpp)；[mighty/__init__.py](source/mit-acl__mighty/mighty/__init__.py)；[scripts/run_sim.py](source/mit-acl__mighty/scripts/run_sim.py)

原项目说明：[固定版 README](https://github.com/mit-acl/mighty/blob/a21dcd5dd9367a8db32171857ae68f16b2baf521/README.md)。 运行环境提及：Humble、ROS 2、ROS2、ros2。

### wty-yy/RoboGauge

**优先** · 近半年默认分支提交 · `add2c7ee0185ea8fd93d242f86e1c8cac6e9913b`

对现有 RL 步态做速度跟踪、稳定性和鲁棒性评测。先评测原策略，不把下载当成重新训练授权。

主要源码：[robogauge/scripts/run.py](source/wty-yy__RoboGauge/robogauge/scripts/run.py)；[scripts/eval_jit_models_to_tensorboard.py](source/wty-yy__RoboGauge/scripts/eval_jit_models_to_tensorboard.py)；[robogauge/tasks/pipeline/__init__.py](source/wty-yy__RoboGauge/robogauge/tasks/pipeline/__init__.py)；[robogauge/tasks/pipeline/base_pipeline.py](source/wty-yy__RoboGauge/robogauge/tasks/pipeline/base_pipeline.py)；[robogauge/tasks/pipeline/level_pipeline.py](source/wty-yy__RoboGauge/robogauge/tasks/pipeline/level_pipeline.py)

原项目说明：[固定版 README](https://github.com/wty-yy/RoboGauge/blob/add2c7ee0185ea8fd93d242f86e1c8cac6e9913b/README.md)。 运行环境提及：IsaacGym、MUJOCO、MuJoCo、Mujoco、mujoco。

### allenai/vla-evaluation-harness

**后续** · 近半年默认分支提交 · `41bd8a44dbe5ba0f7902adb5b7c121c1c174dc84`

模型与环境解耦的评测接口、逐回合记录和异步推理测量。通用 VLA 评测工具，不是楼梯导航算法。

主要源码：[src/vla_eval/api.py](source/allenai__vla-evaluation-harness/src/vla_eval/api.py)；[src/vla_eval/dirs.py](source/allenai__vla-evaluation-harness/src/vla_eval/dirs.py)；[src/vla_eval/specs.py](source/allenai__vla-evaluation-harness/src/vla_eval/specs.py)；[src/vla_eval/types.py](source/allenai__vla-evaluation-harness/src/vla_eval/types.py)；[src/vla_eval/config.py](source/allenai__vla-evaluation-harness/src/vla_eval/config.py)

原项目说明：[固定版 README](https://github.com/allenai/vla-evaluation-harness/blob/41bd8a44dbe5ba0f7902adb5b7c121c1c174dc84/README.md)。 运行环境提及：cuda。

### isaac-sim2real/sage

**后续** · 近半年默认分支提交 · `5b31cfa35416d1300b5099557049bd8e9cb4507d`

量化命令到关节实际运动的仿真与真机差距。以人形关节实验为主，方法需适配 Lite3。

主要源码：[sage/assets.py](source/isaac-sim2real__sage/sage/assets.py)；[sage/__init__.py](source/isaac-sim2real__sage/sage/__init__.py)；[sage/analysis.py](source/isaac-sim2real__sage/sage/analysis.py)；[sage/simulation.py](source/isaac-sim2real__sage/sage/simulation.py)；[scripts/run_real.py](source/isaac-sim2real__sage/scripts/run_real.py)

原项目说明：[固定版 README](https://github.com/isaac-sim2real/sage/blob/5b31cfa35416d1300b5099557049bd8e9cb4507d/README.md)。 运行环境提及：Isaac Lab、IsaacLab、ROS2。

### Renforce-Dynamics/genesislab

**后续** · 近半年默认分支提交 · `0f2e4d96df9b24bcce66f8bdf7a1884a1363a5bb`

轻量仿真任务组织和不同步态策略的评测接口。新增仿真框架只作参考，本轮不迁移现有实验。

主要源码：[scripts/reinforcement_learning/sb3/train.py](source/Renforce-Dynamics__genesislab/scripts/reinforcement_learning/sb3/train.py)；[scripts/reinforcement_learning/skrl/train.py](source/Renforce-Dynamics__genesislab/scripts/reinforcement_learning/skrl/train.py)；[scripts/reinforcement_learning/rsl_rl/eval.py](source/Renforce-Dynamics__genesislab/scripts/reinforcement_learning/rsl_rl/eval.py)；[scripts/reinforcement_learning/rsl_rl/train.py](source/Renforce-Dynamics__genesislab/scripts/reinforcement_learning/rsl_rl/train.py)；[scripts/reinforcement_learning/rl_games/train.py](source/Renforce-Dynamics__genesislab/scripts/reinforcement_learning/rl_games/train.py)

原项目说明：[固定版 README](https://github.com/Renforce-Dynamics/genesislab/blob/0f2e4d96df9b24bcce66f8bdf7a1884a1363a5bb/README.md)。 运行环境提及：Genesis、genesis。

### zsibot/matrix

**后续** · 近半年默认分支提交 · `55ad3fec77deaf1b589d27fa6cc4bfca4553754e`

传感器、物理仿真与可视化分离的系统组织。完整运行另需引擎与资产。

主要源码：[Tools/bbox_motion.py](source/zsibot__matrix/Tools/bbox_motion.py)；[Tools/gimbal_udp_ui.py](source/zsibot__matrix/Tools/gimbal_udp_ui.py)；[Tools/send_spawn_udp.py](source/zsibot__matrix/Tools/send_spawn_udp.py)；[Tools/send_udp_voice.py](source/zsibot__matrix/Tools/send_udp_voice.py)；[Tools/zenoh_recording.py](source/zsibot__matrix/Tools/zenoh_recording.py)

原项目说明：[固定版 README](https://github.com/zsibot/matrix/blob/55ad3fec77deaf1b589d27fa6cc4bfca4553754e/README.md)。 运行环境提及：MuJoCo、ROS 2、mujoco。

### ivaROS/quad_gap

**优先** · 补充参考；不计入近期50个 · `a37e22b58b8a2cdebe81aa9c5968ab5ff51afbdd`

基于可通行间隙的四足局部规划，作为简洁控制组。提交早于近半年窗口；需另做楼梯与停站验证。

主要源码：[src/planner.cpp](source/ivaROS__quad_gap/src/planner.cpp)；[src/trajectory_controller.cpp](source/ivaROS__quad_gap/src/trajectory_controller.cpp)；[include/quad_gap/planner.h](source/ivaROS__quad_gap/include/quad_gap/planner.h)；[include/quad_gap/trajectory_controller.h](source/ivaROS__quad_gap/include/quad_gap/trajectory_controller.h)；[src/quad_gap.cpp](source/ivaROS__quad_gap/src/quad_gap.cpp)

原项目说明：[固定版 README](https://github.com/ivaROS/quad_gap/blob/a37e22b58b8a2cdebe81aa9c5968ab5ff51afbdd/readme.md)。 运行环境提及：README 未提取到标准环境标签。

### leggedrobotics/ocs2

**优先** · 补充参考；不计入近期50个 · `26386754b8bf31ab78b503971d0cbf4fdbcd7cb4`

切换系统最优控制、足式接触约束与感知 MPC 的参考实现。成熟项目的当前版本，依赖及各子模块许可需分别保留。

主要源码：[ocs2_mpc/src/MPC_BASE.cpp](source/leggedrobotics__ocs2/ocs2_mpc/src/MPC_BASE.cpp)；[ocs2_mpc/include/ocs2_mpc/MPC_MRT_Interface.h](source/leggedrobotics__ocs2/ocs2_mpc/include/ocs2_mpc/MPC_MRT_Interface.h)；[ocs2_core/src/control/LinearController.cpp](source/leggedrobotics__ocs2/ocs2_core/src/control/LinearController.cpp)；[ocs2_core/src/control/FeedforwardController.cpp](source/leggedrobotics__ocs2/ocs2_core/src/control/FeedforwardController.cpp)；[ocs2_core/src/constraint/StateConstraintCppAd.cpp](source/leggedrobotics__ocs2/ocs2_core/src/constraint/StateConstraintCppAd.cpp)

原项目说明：[固定版 README](https://github.com/leggedrobotics/ocs2/blob/26386754b8bf31ab78b503971d0cbf4fdbcd7cb4/README.md)。 运行环境提及：ROS 1、ROS 2、ros2。

### hucebot/g1pilot

**后续** · 补充参考；不计入近期50个 · `5346e52191e97d3ec07312f23c87bb58a849fdf7`

ROS 2 机器人状态和控制桥接的工程组织。G1 人形平台，仅作为系统接口参考。

主要源码：[launch/navigation_launcher.launch.py](source/hucebot__g1pilot/launch/navigation_launcher.launch.py)；[g1pilot/navigation/__init__.py](source/hucebot__g1pilot/g1pilot/navigation/__init__.py)；[g1pilot/navigation/nav2point.py](source/hucebot__g1pilot/g1pilot/navigation/nav2point.py)；[g1pilot/navigation/create_map.py](source/hucebot__g1pilot/g1pilot/navigation/create_map.py)；[g1pilot/navigation/loco_client.py](source/hucebot__g1pilot/g1pilot/navigation/loco_client.py)

原项目说明：[固定版 README](https://github.com/hucebot/g1pilot/blob/5346e52191e97d3ec07312f23c87bb58a849fdf7/README.md)。 运行环境提及：Humble、Jazzy、ROS2、ROS 2、jazzy、ros2。

### lab-sun/Feetend-Planner

**优先** · 补充参考；不计入近期50个 · `49f993dec38e66081e98a6b20d4ccf8498111e6d`

以足端地形特征生成身体轨迹，补充仅查身体中心的规划视角。2026 年论文，当前提交早于近半年窗口；依赖 OCS2 感知控制。

主要源码：[compute_body_traj.py](source/lab-sun__Feetend-Planner/compute_body_traj.py)

原项目说明：[固定版 README](https://github.com/lab-sun/Feetend-Planner/blob/49f993dec38e66081e98a6b20d4ccf8498111e6d/README.md)。 运行环境提及：README 未提取到标准环境标签。

### PRBonn/kiss-slam

**优先** · 补充参考；不计入近期50个 · `3d4d1fabf5e301742ccc5f55753bf171a51953e2`

简洁 LiDAR SLAM 作为定位建图工程对照。需要 LiDAR 数据与基准轨迹验证。

主要源码：[kiss_slam/pipeline.py](source/PRBonn__kiss-slam/kiss_slam/pipeline.py)；[kiss_slam/slam.py](source/PRBonn__kiss-slam/kiss_slam/slam.py)；[kiss_slam/__init__.py](source/PRBonn__kiss-slam/kiss_slam/__init__.py)；[kiss_slam/voxel_map.py](source/PRBonn__kiss-slam/kiss_slam/voxel_map.py)；[kiss_slam/loop_closer.py](source/PRBonn__kiss-slam/kiss_slam/loop_closer.py)

原项目说明：[固定版 README](https://github.com/PRBonn/kiss-slam/blob/3d4d1fabf5e301742ccc5f55753bf171a51953e2/README.md)。 运行环境提及：ROS2。

### arclab-hku/P2M

**后续** · 补充参考；不计入近期50个 · `6aa1f7cf464a158b1464fad314a77ad23ff2bcf5`

LiDAR 输入下的动态环境端到端导航与控制接口。须核对平台和动作空间；提交早于近半年窗口。

主要源码：[scripts/train.py](source/arclab-hku__P2M/scripts/train.py)；[resources/controllers/__init__.py](source/arclab-hku__P2M/resources/controllers/__init__.py)；[resources/controllers/controller.py](source/arclab-hku__P2M/resources/controllers/controller.py)；[resources/controllers/lee_acc_controller.py](source/arclab-hku__P2M/resources/controllers/lee_acc_controller.py)；[resources/NeuFlow_v2/data_utils/evaluate.py](source/arclab-hku__P2M/resources/NeuFlow_v2/data_utils/evaluate.py)

原项目说明：[固定版 README](https://github.com/arclab-hku/P2M/blob/6aa1f7cf464a158b1464fad314a77ad23ff2bcf5/README.md)。 运行环境提及：Isaac Lab、isaac lab。
