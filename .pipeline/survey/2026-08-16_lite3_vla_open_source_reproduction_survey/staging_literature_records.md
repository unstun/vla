---
origin: ai_only
reviewed: false
as_of: 2026-08-16
---

# 2026-08-16 Lite3 VLA 开源复现调研：`surveyed` 索引追加块

> 注意：执行环境未挂载 `/Users/sun/vla`，原 `.pipeline/literature/index.md` 未读取，因此本文件是待人工合并的追加块，不是对原索引的替代。合并前必须先按 `AGENTS.md` 与 Trellis 规则审阅。

所有条目证据状态统一为 `surveyed`；本轮没有运行上游代码，不得改写为 `reproduced`。

## Chen2025VLMPC

- title: Commonsense Reasoning for Legged Robot Adaptation with Vision-Language Models
- authors: Annie S. Chen; Alec M. Lessing; Andy Tang; Govind Chada; Laura Smith; Sergey Levine; Chelsea Finn
- first_public: 2024-07-02
- venue: ICRA 2025（论文首次公开为 arXiv 2024）
- route: 1/4：四足 VLM 高层技能规划
- paper: https://arxiv.org/abs/2407.02666
- canonical_repository: https://github.com/stanford-iris-lab/vlm-pc
- pinned_commit: 4a616a93ebd8036bc2c43fbe45071ef939daca48
- local_pdf: `docs/research/papers/Chen2025VLMPC.pdf`
- evidence_status: surveyed
- note: 高层技能规划；代码许可缺失/外部 VLM 依赖，未进 shortlist

## Cheng2025NaVILA

- title: NaVILA: Legged Robot Vision-Language-Action Model for Navigation
- authors: An-Chieh Cheng; Yandong Ji; Zhaojing Yang; Zaitian Gongye; Xueyan Zou; Jan Kautz; Erdem Bıyık; Hongxu Yin; Sifei Liu; Xiaolong Wang
- first_public: 2024-12-05
- venue: RSS 2025
- route: 1/4：直接腿式 VLA → 中层动作 → RL locomotion
- paper: https://arxiv.org/abs/2412.04453
- canonical_repository: https://github.com/AnjieCheng/NaVILA
- pinned_commit: 76b98f233dd0fff05dfcd69435eec6740febff9d
- local_pdf: `docs/research/papers/Cheng2025NaVILA.pdf`
- evidence_status: surveyed
- note: 技术最贴近，但模型/数据许可证不闭合

## Ding2024QUARVLA

- title: QUAR-VLA: Vision-Language-Action Model for Quadruped Robots
- authors: Pengxiang Ding; Han Zhao; Wenjie Zhang; Wenxuan Song; Min Zhang; Siteng Huang; Ningxi Yang; Donglin Wang
- first_public: 2023-12-22
- venue: ECCV 2024
- route: 1：直接四足 VLA
- paper: https://arxiv.org/abs/2312.14457
- canonical_repository: 未找到 canonical 运行仓
- pinned_commit: —
- local_pdf: `docs/research/papers/Ding2024QUARVLA.pdf`
- evidence_status: surveyed
- note: 官方代码仍未公开，不能复现

## Frey2023WVN

- title: Fast Traversability Estimation for Wild Visual Navigation
- authors: Jonas Frey; Matias Mattamala; Nived Chebrolu; Cesar Cadena; Maurice Fallon; Marco Hutter
- first_public: 2023-07
- venue: RSS 2023
- route: 2/4：四足户外可通行性支撑
- paper: https://roboticsproceedings.org/rss19/p054.html
- canonical_repository: https://github.com/leggedrobotics/wild_visual_navigation
- pinned_commit: 未在本轮 shortlist 审计
- local_pdf: `docs/research/papers/Frey2023WVN.pdf`
- evidence_status: surveyed
- note: 纯视觉可通行性，不是 VLA

## Goetting2024VLMnav

- title: End-to-End Navigation with Vision Language Models: Transforming Spatial Reasoning into Question-Answering
- authors: Dylan Goetting; Himanshu Gaurav Singh; Antonio Loquercio
- first_public: 2024-11-08
- venue: NeSy 2025 / arXiv
- route: 3：通用 VLM 离散导航
- paper: https://arxiv.org/abs/2411.05755
- canonical_repository: https://github.com/Jirl-upenn/VLMnav
- pinned_commit: 82d59684c15a6694ea73b969e76a57157c8740b8
- local_pdf: `docs/research/papers/Goetting2024VLMnav.pdf`
- evidence_status: surveyed
- note: 零样本思路强，但代码许可/云模型依赖不合门槛

## Hirose2025LeLaN

- title: LeLaN: Learning A Language-Conditioned Navigation Policy from In-the-Wild Video
- authors: Noriaki Hirose; Catherine Glossop; Ajay Sridhar; Oier Mees; Sergey Levine
- first_public: 2024-10-04
- venue: CoRL 2024，PMLR 270（2025）
- route: 2/3/4：语言条件对象导航 → waypoint/velocity
- paper: https://proceedings.mlr.press/v270/hirose25b.html
- canonical_repository: https://github.com/NHirose/learning-language-navigation
- pinned_commit: a41d478cb966eabce78af2b79e6cbfef3aebd589
- local_pdf: `docs/research/papers/Hirose2025LeLaN.pdf`
- evidence_status: surveyed
- note: 接口很适合 Lite3，但权重/聚合数据许可未闭合且依赖老化

## Hirose2026OmniVLA

- title: OmniVLA: An Omni-Modal Vision-Language-Action Model for Robot Navigation
- authors: Noriaki Hirose; Catherine Glossop; Dhruv Shah; Sergey Levine
- first_public: 2025-09-23
- venue: ICRA 2026
- route: 3/4：通用导航 VLA → 连续轨迹
- paper: https://arxiv.org/abs/2509.19480
- canonical_repository: https://github.com/NHirose/OmniVLA
- pinned_commit: 5182600cb4a9ee07684e17cdd2a6cbafc56b8a68
- local_pdf: `docs/research/papers/Hirose2026OmniVLA.pdf`
- evidence_status: surveyed
- note: 本轮首选

## Huang2023VLMaps

- title: Visual Language Maps for Robot Navigation
- authors: Chenguang Huang; Oier Mees; Andy Zeng; Wolfram Burgard
- first_public: 2022-10-11
- venue: ICRA 2023
- route: 2/4：开放词汇语义地图
- paper: https://arxiv.org/abs/2210.05714
- canonical_repository: https://github.com/vlmaps/vlmaps
- pinned_commit: 58060f97239074338ab419a2090d43fa752d724d
- local_pdf: `docs/research/papers/Huang2023VLMaps.pdf`
- evidence_status: surveyed
- note: 关键前序；支撑模块而非 VLA

## Liu2025CityWalker

- title: CityWalker: Learning Embodied Urban Navigation from Web-Scale Videos
- authors: Xinhao Liu et al.
- first_public: 2024-11-26
- venue: CVPR 2025
- route: 3/4：户外视觉导航 foundation model
- paper: https://arxiv.org/abs/2411.17820
- canonical_repository: https://github.com/ai4ce/CityWalker
- pinned_commit: ab0ef60b17dc4d1d16c7d95dd143e6dac91abed1
- local_pdf: `docs/research/papers/Liu2025CityWalker.pdf`
- evidence_status: surveyed
- note: 无语言条件；作为邻近轨迹模型

## Long2024InstructNav

- title: InstructNav: Zero-shot System for Generic Instruction Navigation in Unexplored Environment
- authors: Yuxing Long et al.
- first_public: 2024-06-07
- venue: arXiv 2024
- route: 3/4：LLM/VLM 分层语义导航
- paper: https://arxiv.org/abs/2406.04882
- canonical_repository: https://github.com/LYX0501/InstructNav
- pinned_commit: e58a5aac51cdb1c1ea4794ded0138e78f24de70f
- local_pdf: `docs/research/papers/Long2024InstructNav.pdf`
- evidence_status: surveyed
- note: 无许可证/外部 API

## NavDP2025

- title: NavDP: Learning Sim-to-Real Navigation Diffusion Policy with Privileged Information Guidance
- authors: Wenzhe Cai; Jiaqi Peng; Yuqiang Yang; Yujian Zhang; Meng Wei; Hanqing Wang; Yilun Chen; Tai Wang; Jiangmiao Pang
- first_public: 2025-05-13
- venue: arXiv 2025（项目后续更新至 2026）
- route: 3/4：连续扩散轨迹 System 1
- paper: https://arxiv.org/abs/2505.08712
- canonical_repository: https://github.com/InternRobotics/NavDP
- pinned_commit: 878740a2011856d0e3782dd6ccd880fd2eccd70f
- local_pdf: `docs/research/papers/NavDP2025.pdf`
- evidence_status: surveyed
- note: 适合作为 InternVLA 轨迹执行组件，不是独立语言 baseline

## Roth2024ViPlanner

- title: ViPlanner: Visual Semantic Imperative Learning for Local Navigation
- authors: Pascal Roth et al.
- first_public: 2023-10-02
- venue: ICRA 2024
- route: 2/4：腿式视觉语义局部规划
- paper: https://arxiv.org/abs/2310.00982
- canonical_repository: https://github.com/leggedrobotics/viplanner
- pinned_commit: 6fcf3c60f6fa3b28b3a11af054d6033825923789
- local_pdf: `docs/research/papers/Roth2024ViPlanner.pdf`
- evidence_status: surveyed
- note: 纯规划，不是 VLA

## Shah2023LMNav

- title: LM-Nav: Robotic Navigation with Large Pre-Trained Models of Language, Vision, and Action
- authors: Dhruv Shah; Błażej Osiński; Brian Ichter; Sergey Levine
- first_public: 2022-07-11
- venue: CoRL 2022，PMLR 205（2023）
- route: 3/4：关键前序分层语言导航
- paper: https://proceedings.mlr.press/v205/shah23a.html
- canonical_repository: https://github.com/blazejosinski/lm_nav
- pinned_commit: 未进入本轮 Top 5
- local_pdf: `docs/research/papers/Shah2023LMNav.pdf`
- evidence_status: surveyed
- note: 关键前序，时间范围例外

## StreamVLN2025

- title: StreamVLN: Streaming Vision-and-Language Navigation via SlowFast Context Modeling
- authors: Meng Wei; Chenyang Wan; Xiqian Yu; Tai Wang; Yuqiang Yang; Xiaohan Mao; Chenming Zhu; Wenzhe Cai; Hanqing Wang; Yilun Chen; Xihui Liu; Jiangmiao Pang
- first_public: 2025-07-07
- venue: arXiv 2025
- route: 3：流式 VLN
- paper: https://arxiv.org/abs/2507.05240
- canonical_repository: https://github.com/InternRobotics/StreamVLN
- pinned_commit: e48f6ff7e9201d93aae003e8f64b04c00cec13bc
- local_pdf: `docs/research/papers/StreamVLN2025.pdf`
- evidence_status: surveyed
- note: 作为 InternNav 组件更合适

## Tang2023SayTap

- title: SayTap: Language to Quadrupedal Locomotion
- authors: Yujin Tang et al.
- first_public: 2023-06-12
- venue: CoRL 2023，PMLR 229
- route: 1/4：语言 → 足端接触/运动技能
- paper: https://arxiv.org/abs/2306.07580
- canonical_repository: https://github.com/google-deepmind/saytap
- pinned_commit: 未进入 shortlist 审计
- local_pdf: `docs/research/papers/Tang2023SayTap.pdf`
- evidence_status: surveyed
- note: 语言条件 locomotion，非导航 VLA；重要邻近技术

## Tong2025QUARTOnline

- title: QUART-Online: Latency-Free Multimodal Large Language Model for Quadruped Robot Learning
- authors: Xinyang Tong; Pengxiang Ding; Yiguo Fan; Donglin Wang; Wenjie Zhang; Can Cui; Mingyang Sun; Han Zhao; Hongyin Zhang; Yonghao Dang; Siteng Huang; Shangke Lyu
- first_public: 2024-12-20
- venue: arXiv 2024/2025
- route: 1：直接四足流式 VLA
- paper: https://arxiv.org/abs/2412.15576
- canonical_repository: 未找到满足硬门槛的 canonical 完整仓
- pinned_commit: —
- local_pdf: `docs/research/papers/Tong2025QUARTOnline.pdf`
- evidence_status: surveyed
- note: 高度相关但开源不足

## Yin2025UniGoal

- title: UniGoal: Towards Universal Zero-shot Goal-oriented Navigation
- authors: Hang Yin; Xiuwei Xu; Linqing Zhao; Ziwei Wang; Jie Zhou; Jiwen Lu
- first_public: 2025-03-13
- venue: CVPR 2025
- route: 3：多目标类型零样本导航
- paper: https://arxiv.org/abs/2503.10630
- canonical_repository: 项目代码线索；未入 Top 5
- pinned_commit: 未核验
- local_pdf: `docs/research/papers/Yin2025UniGoal.pdf`
- evidence_status: surveyed
- note: 目标统一化参考；不是四足直接基线

## Yokoyama2024VLFM

- title: VLFM: Vision-Language Frontier Maps for Zero-Shot Semantic Navigation
- authors: Naoki Yokoyama; Sehoon Ha; Dhruv Batra; Jiuguang Wang; Bernadette Bucher
- first_public: 2023-12-06
- venue: ICRA 2024
- route: 2/4：语言价值 frontier waypoint → PointNav
- paper: https://arxiv.org/abs/2312.03275
- canonical_repository: https://github.com/rai-opensource/vlfm
- pinned_commit: 584ed56008754fde7997d904983607def8328322
- local_pdf: `docs/research/papers/Yokoyama2024VLFM.pdf`
- evidence_status: surveyed
- note: shortlist 第三名；合规分层基线但不是端到端 VLA

## Zhang2025UniNaVid

- title: Uni-NaVid: A Video-based Vision-Language-Action Model for Unifying Embodied Navigation Tasks
- authors: Jiahao Zhang et al.
- first_public: 2024-12-09
- venue: RSS 2025
- route: 3：通用视频 VLN/VLA
- paper: https://arxiv.org/abs/2412.06224
- canonical_repository: https://github.com/jzhzhang/Uni-NaVid
- pinned_commit: 79ef5ea3fea14c205342d1ab070563d84c7a966a
- local_pdf: `docs/research/papers/Zhang2025UniNaVid.pdf`
- evidence_status: surveyed
- note: 模型权重许可未闭合

## Zheng2024NaviLLM

- title: Towards Learning a Generalist Model for Embodied Navigation
- authors: Duo Zheng; Shijia Huang; Lin Zhao; Yiwu Zhong; Liwei Wang
- first_public: 2023-12-04
- venue: CVPR 2024
- route: 3：通用 embodied navigation
- paper: https://arxiv.org/abs/2312.02010
- canonical_repository: https://github.com/zd11024/NaviLLM
- pinned_commit: a221f42ad52893e861779921df336d63c0b4f3a6
- local_pdf: `docs/research/papers/Zheng2024NaviLLM.pdf`
- evidence_status: surveyed
- note: benchmark 型；代码许可未找到

## Song2024GeRM

- title: GeRM: A Generalist Robotic Model with Mixture-of-experts for Quadruped Robot
- authors: Wenxuan Song; Han Zhao; Pengxiang Ding; Can Cui; Shangke Lyu; Yaning Fan; Donglin Wang
- first_public: 2024-03-20
- venue: IROS 2024
- route: 1：直接四足 VLA / 多任务控制
- paper: https://arxiv.org/abs/2403.13358
- canonical_repository: https://github.com/Songwxuan/GeRM
- pinned_commit: fadc5b2de494c1084e88865279341799a74417fc
- local_pdf: `docs/research/papers/Song2024GeRM.pdf`
- evidence_status: surveyed
- note: 论文高度相关；仓库无明确许可证且发布包不足，不能作为复现基线

## Huang2025MobileVLAR1

- title: MobileVLA-R1: Reinforcing Vision-Language-Action for Mobile Robots
- authors: Ting Huang; Dongjian Li; Rui Yang; Zeyu Zhang; Zida Yang; Hao Tang
- first_public: 2025-11-22
- venue: arXiv 2025
- route: 1/3/4：四足语言导航与连续控制
- paper: https://arxiv.org/abs/2511.17889
- canonical_repository: https://github.com/AIGeeksGroup/MobileVLA-R1
- pinned_commit: ff9062c143d6b50c05d913e6be15d36634a7a460
- local_pdf: `docs/research/papers/Huang2025MobileVLAR1.pdf`
- evidence_status: surveyed
- note: 直接 Go2/四足相关，但核心数据 URL 仍为占位符且无官方预训练 smoke 入口

## Wei2026InternVLA

- title: Ground Slow, Move Fast: A Dual-System Foundation Model for Generalizable Vision-and-Language Navigation
- authors: Meng Wei; Chenyang Wan; Jiaqi Peng; Xiqian Yu; Yuqiang Yang; Delin Feng; Wenzhe Cai; Chenming Zhu; Tai Wang; Jiangmiao Pang; Xihui Liu
- first_public: 2025-12-09
- venue: ICLR 2026 Poster
- route: 3/4：双系统 VLN → pixel goal + 连续轨迹
- paper: https://arxiv.org/abs/2512.08186
- canonical_repository: https://github.com/InternRobotics/InternNav
- pinned_commit: 7a5c62400ac45b313d9b709c740b64191556a242
- local_pdf: `docs/research/papers/Wei2026InternVLA.pdf`
- evidence_status: surveyed
- note: 本轮备选；代码/模型/数据较完整，但模型数据非商业许可、依赖与资源成本较高

## Zhang2026QwenRobotNav

- title: Qwen-RobotNav Technical Report: A Scalable Navigation Model Designed for an Agentic Navigation System
- authors: Jiazhao Zhang et al.
- first_public: 2026-06-16
- venue: arXiv technical report 2026
- route: 1/3/4：可配置多任务导航模型；Go2 零样本部署
- paper: https://arxiv.org/abs/2606.18112
- canonical_repository: https://github.com/QwenLM/Qwen-RobotNav
- pinned_commit: f74cf1f6079300aee6e40e03858da2f98b1b7261
- local_pdf: `docs/research/papers/Zhang2026QwenRobotNav.pdf`
- evidence_status: surveyed
- note: 截至固定 commit 只有报告/媒体与说明，未发布可运行代码、权重和许可证

# Canonical repository records

> 以下仓库记录与论文记录并列写入，状态仍为 `surveyed`。硬门槛失败不等于论文无价值，只表示不能作为本轮首选复现基线。

## Repository: OmniVLA

- canonical_repository: https://github.com/NHirose/OmniVLA
- default_branch: main
- pinned_commit: 5182600cb4a9ee07684e17cdd2a6cbafc56b8a68
- checked_on: 2026-08-16
- code_license: MIT（LICENSE 文件；GitHub API 元数据曾显示 NOASSERTION）
- model_license: MIT（NHirose/omnivla-original 等模型卡）
- data_license: 混合：各原始数据集分别适用；BDD 原始图像受 BDD 条款约束，项目标注/代码部分 MIT；离线 smoke 不需训练数据
- action_interface: 8×4 归一化轨迹 [x,y,hx,hy]；源码提供 PD 到 (v,ω)
- upstream_entry: python inference/run_omnivla.py；python inference/run_omnivla_edge.py
- maintenance: 中上：2026 年有实质更新；有活跃 issue
- gate: PASS
- decision: 首选
- evidence_status: surveyed

## Repository: InternVLA-N1 / InternNav

- canonical_repository: https://github.com/InternRobotics/InternNav
- default_branch: main
- pinned_commit: 7a5c62400ac45b313d9b709c740b64191556a242
- checked_on: 2026-08-16
- code_license: MIT
- model_license: CC BY-NC-SA 4.0
- data_license: InternData-N1 gated；协议正文 CC BY-NC-SA 4.0（HF 顶部标签与正文存在 BY-SA/NC-SA 不一致，按更严格正文处理）
- action_interface: System 2 像素目标/离散高层动作；System 1 离散动作或连续轨迹（配置相关）
- upstream_entry: python scripts/eval/start_server.py --port 8087；官方 notebook/client
- maintenance: 高：2026 年持续更新和发版；但最新固定提交有已知 diffusers 兼容 issue
- gate: PASS-WITH-RESTRICTION
- decision: 备选
- evidence_status: surveyed

## Repository: VLFM

- canonical_repository: https://github.com/rai-opensource/vlfm
- default_branch: main
- pinned_commit: 584ed56008754fde7997d904983607def8328322
- checked_on: 2026-08-16
- code_license: MIT
- model_license: 第三方组件混合且可核验：MobileSAM/GroundingDINO 等按各自许可证；YOLOv7 为 GPL-3.0，重新分发须单独审查
- data_license: HM3D/MP3D/Gibson 按各数据条款；HM3D/MP3D 需账户/协议，不能随项目任意再分发
- action_interface: 语言价值图 + frontier waypoint → PointNav 控制器
- upstream_entry: ./scripts/launch_vlm_servers.sh；python -m vlfm.run
- maintenance: 中低：代码完整但停止积极维护，PyTorch/CUDA 栈老
- gate: PASS-FOR-USE-UNDER-UPSTREAM-TERMS
- decision: shortlist 第三名；不是完整端到端 VLA
- evidence_status: surveyed

## Repository: NaVILA

- canonical_repository: https://github.com/AnjieCheng/NaVILA
- default_branch: main
- pinned_commit: 76b98f233dd0fff05dfcd69435eec6740febff9d
- checked_on: 2026-08-16
- code_license: Apache-2.0
- model_license: 未找到：官方 8B checkpoint 页面无 model card/许可证
- data_license: 未找到：NaVILA-Dataset 页面无独立许可证/数据卡
- action_interface: 自然语言中层空间动作，例如前进距离/转向；下层 RL 输出 12 关节位置
- upstream_entry: bash scripts/eval/r2r.sh ...；训练 scripts/train/sft_8frames.sh
- maintenance: 中：功能性更新停在 2025；多项复现/Go2 问题未闭合
- gate: FAIL
- decision: 技术条件候选；不得作为本轮首选
- evidence_status: surveyed

## Repository: NaVILA-Bench

- canonical_repository: https://github.com/yang-zj1026/NaVILA-Bench
- default_branch: main
- pinned_commit: e9d2db12ce5788c0f987d734c0094100b6bc0d3a
- checked_on: 2026-08-16
- code_license: MIT（LICENSE 文件；API 识别异常）
- model_license: 依赖 NaVILA 主 checkpoint；其许可证未闭合
- data_license: VLN-CE-Isaac 数据页为 MIT
- action_interface: VLM server 文本动作 + Go2 低层策略
- upstream_entry: python vlm_server.py ...；python scripts/navila_eval.py ...
- maintenance: 中
- gate: FAIL-DEPENDENCY
- decision: 可作后续基准组件，不能单独解除 NaVILA 许可证缺口
- evidence_status: surveyed

## Repository: LeLaN

- canonical_repository: https://github.com/NHirose/learning-language-navigation
- default_branch: main
- pinned_commit: a41d478cb966eabce78af2b79e6cbfef3aebd589
- checked_on: 2026-08-16
- code_license: MIT
- model_license: 未找到独立权重许可证
- data_license: 聚合数据/Google Drive 发布未在 README 中给出独立统一许可证；底层视频来源混合
- action_interface: /waypoint、/vel_lelan，经 PD 发布 /cmd_vel
- upstream_entry: python lelan_policy_col.py ...；python pd_controller_lelan.py
- maintenance: 低到中：接口清楚但长期无实质提交，ROS1/Python 3.7/CUDA10 老化
- gate: FAIL
- decision: 接口参考，不作为首选
- evidence_status: surveyed

## Repository: MobileVLA-R1

- canonical_repository: https://github.com/AIGeeksGroup/MobileVLA-R1
- default_branch: main
- pinned_commit: ff9062c143d6b50c05d913e6be15d36634a7a460
- checked_on: 2026-08-16
- code_license: Apache-2.0
- model_license: 未找到可直接 smoke 的官方导航 checkpoint 许可闭环
- data_license: README 核心 Nav_CoT_FINAL_38K.jsonl 下载仍是 your-storage 占位符
- action_interface: 导航 CoT / 移动动作（论文相关）
- upstream_entry: 未找到预训练推理/最小 smoke 入口
- maintenance: 新但发布不完整
- gate: FAIL
- decision: 淘汰：材料不完整
- evidence_status: surveyed

## Repository: Uni-NaVid

- canonical_repository: https://github.com/jzhzhang/Uni-NaVid
- default_branch: main
- pinned_commit: 79ef5ea3fea14c205342d1ab070563d84c7a966a
- checked_on: 2026-08-16
- code_license: MIT
- model_license: 未找到官方 16.2 GB 权重页的明确许可证
- data_license: 依赖多套 VLN 数据，各自条款
- action_interface: 连续/离散导航动作（任务配置相关）
- upstream_entry: python offline_eval_uninavid.py test_cases/vln_1 Ourpur_dir
- maintenance: 中
- gate: FAIL
- decision: 淘汰：模型许可未闭合、四足接口弱
- evidence_status: surveyed

## Repository: NaviLLM

- canonical_repository: https://github.com/zd11024/NaviLLM
- default_branch: main
- pinned_commit: a221f42ad52893e861779921df336d63c0b4f3a6
- checked_on: 2026-08-16
- code_license: 未找到仓库根目录明确许可证
- model_license: 需逐模型核验
- data_license: 依赖多 benchmark 条款
- action_interface: 多任务导航动作/回答
- upstream_entry: 有训练评测脚本，但面向 benchmark
- maintenance: 低：长期无实质更新
- gate: FAIL
- decision: 淘汰：代码许可证缺失、实机桥接成本高
- evidence_status: surveyed

## Repository: InstructNav

- canonical_repository: https://github.com/LYX0501/InstructNav
- default_branch: main
- pinned_commit: e58a5aac51cdb1c1ea4794ded0138e78f24de70f
- checked_on: 2026-08-16
- code_license: 未找到
- model_license: 依赖外部 VLM/LLM；部分云 API
- data_license: Habitat/场景条款
- action_interface: 语义目标/地图规划/离散动作
- upstream_entry: 有 Habitat 运行说明
- maintenance: 中低
- gate: FAIL
- decision: 淘汰：无许可证且可能依赖闭源 API
- evidence_status: surveyed

## Repository: VLMnav

- canonical_repository: https://github.com/Jirl-upenn/VLMnav
- default_branch: main
- pinned_commit: 82d59684c15a6694ea73b969e76a57157c8740b8
- checked_on: 2026-08-16
- code_license: 未找到
- model_license: 依赖外部 VLM/API
- data_license: benchmark 条款
- action_interface: 离散导航动作
- upstream_entry: 有评测代码
- maintenance: 中低
- gate: FAIL
- decision: 淘汰：无许可证/云模型依赖
- evidence_status: surveyed

## Repository: VLM-PC

- canonical_repository: https://github.com/stanford-iris-lab/vlm-pc
- default_branch: main
- pinned_commit: 4a616a93ebd8036bc2c43fbe45071ef939daca48
- checked_on: 2026-08-16
- code_license: 未找到
- model_license: 依赖外部 VLM 服务/模型
- data_license: 无独立训练数据需求；实验资产许可未形成复现包
- action_interface: 技能序列/高层行为选择
- upstream_entry: 有实现，但非低成本完全离线基线
- maintenance: 中
- gate: FAIL
- decision: 淘汰：代码许可与闭源服务依赖
- evidence_status: surveyed

## Repository: StreamVLN

- canonical_repository: https://github.com/InternRobotics/StreamVLN
- default_branch: main
- pinned_commit: e48f6ff7e9201d93aae003e8f64b04c00cec13bc
- checked_on: 2026-08-16
- code_license: 独立仓库根目录未找到明确许可证；已被 InternNav 集成
- model_license: 需按模型卡
- data_license: 依赖 InternData/VLN 数据条款
- action_interface: 流式离散动作
- upstream_entry: http_realworld_server.py / eval
- maintenance: 中
- gate: FAIL-STANDALONE
- decision: 作为 InternNav 组件审查，不单独 shortlist
- evidence_status: surveyed

## Repository: NavDP

- canonical_repository: https://github.com/InternRobotics/NavDP
- default_branch: master
- pinned_commit: 878740a2011856d0e3782dd6ccd880fd2eccd70f
- checked_on: 2026-08-16
- code_license: 独立仓库根目录未找到明确许可证；InternNav 内部集成受 MIT 主仓治理
- model_license: checkpoint 需逐卡核验
- data_license: 依赖相关导航数据
- action_interface: 连续轨迹/扩散策略
- upstream_entry: 有评测与部署文档
- maintenance: 高
- gate: FAIL-STANDALONE
- decision: 适合作为 InternVLA System 1/轨迹组件，不单独作为语言基线
- evidence_status: surveyed

## Repository: Qwen-RobotNav

- canonical_repository: https://github.com/QwenLM/Qwen-RobotNav
- default_branch: main
- pinned_commit: f74cf1f6079300aee6e40e03858da2f98b1b7261
- checked_on: 2026-08-16
- code_license: 未找到
- model_license: 截至检查日未发布可核验权重
- data_license: 未发布
- action_interface: 报告描述语言条件导航/agentic tool actions
- upstream_entry: 未找到代码入口；仓库主要是 README 与媒体资产
- maintenance: 展示活跃但实现未发布
- gate: FAIL
- decision: 淘汰：不是可复现代码仓
- evidence_status: surveyed

## Repository: GeRM

- canonical_repository: https://github.com/Songwxuan/GeRM
- default_branch: main
- pinned_commit: fadc5b2de494c1084e88865279341799a74417fc
- checked_on: 2026-08-16
- code_license: 未找到
- model_license: 未找到
- data_license: 未找到
- action_interface: 仓库声称 VLA/MoE；未见足够运行实现
- upstream_entry: 未找到完整原作者运行入口
- maintenance: 低
- gate: FAIL
- decision: 淘汰：宣传页级，不满足真实实现门槛
- evidence_status: surveyed

## Repository: VLMaps

- canonical_repository: https://github.com/vlmaps/vlmaps
- default_branch: master
- pinned_commit: 58060f97239074338ab419a2090d43fa752d724d
- checked_on: 2026-08-16
- code_license: MIT
- model_license: CLIP/LLM 等按上游许可证；语言分解常用 GPT API
- data_license: Habitat/真实数据各自条款
- action_interface: 语言查询语义地图 → 地图目标/规划
- upstream_entry: 有建图和导航 demo
- maintenance: 低到中
- gate: PASS-COMPONENT-NOT-VLA
- decision: 支撑模块，不冒充 VLA baseline
- evidence_status: surveyed

## Repository: ViPlanner

- canonical_repository: https://github.com/leggedrobotics/viplanner
- default_branch: main
- pinned_commit: 6fcf3c60f6fa3b28b3a11af054d6033825923789
- checked_on: 2026-08-16
- code_license: 自定义/Other；需阅读仓库 LICENSE，不按宽松开源默认处理
- model_license: 公开模型有单独条件
- data_license: Matterport/Omniverse 场景条款
- action_interface: 视觉语义局部轨迹
- upstream_entry: Isaac/Omniverse demo
- maintenance: 中低
- gate: FAIL-AS-VLA
- decision: 纯规划组件，不是语言/VLA
- evidence_status: surveyed

## Repository: CityWalker

- canonical_repository: https://github.com/ai4ce/CityWalker
- default_branch: main
- pinned_commit: ab0ef60b17dc4d1d16c7d95dd143e6dac91abed1
- checked_on: 2026-08-16
- code_license: Apache-2.0（仓库元数据/许可证）
- model_license: 需按权重卡核验
- data_license: web-scale/训练数据条款需逐项核验
- action_interface: 视觉目标/未来轨迹
- upstream_entry: python test.py --config config/finetune.yaml --checkpoint ...
- maintenance: 中
- gate: PASS-COMPONENT-NOT-LANGUAGE
- decision: 邻近视觉导航对照，不是 VLA
- evidence_status: surveyed

## Repository: QUAR-VLA official release

- canonical_repository: 未找到 canonical 可运行仓库；官方项目页仍显示 Code Coming Soon
- default_branch: —
- pinned_commit: —
- checked_on: 2026-08-16
- code_license: —
- model_license: —
- data_license: —
- action_interface: QUART 动作 token/四足任务
- upstream_entry: 无
- maintenance: 论文强相关但开源缺失
- gate: FAIL
- decision: 淘汰：无 canonical 实现
- evidence_status: surveyed

## Repository: VoroNav

- canonical_repository: 官方项目页标注 Code Coming Soon
- default_branch: —
- pinned_commit: —
- checked_on: 2026-08-16
- code_license: —
- model_license: —
- data_license: —
- action_interface: 拓扑/Voronoi exploration waypoint
- upstream_entry: 无
- maintenance: 无代码
- gate: FAIL
- decision: 淘汰：无实现
- evidence_status: surveyed
