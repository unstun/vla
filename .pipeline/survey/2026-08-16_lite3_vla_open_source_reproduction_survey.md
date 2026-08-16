---
origin: ai_only
reviewed: false
as_of: 2026-08-16
---

> **本地导入说明（2026-08-16）：** 本文主体来自会话
> `6a817fcc-aad0-83e8-97c2-c299b1f2df8f` 生成的隔离 staging 包，原文的
> “项目未挂载”描述仅指生成时环境。现已在 `/Users/sun/vla` 完成压缩包哈希、
> 归档安全、294 项内部检查、24 篇 PDF 身份、46 个来源 URL 和 19 个固定 commit
> 的本地复核。复核修正与证据边界见
> [`import_audit.zh.md`](2026-08-16_lite3_vla_open_source_reproduction_survey/import_audit.zh.md)。
> 当前最强证据标签仍是 `surveyed`；尚未选定、导入或运行任何候选代码。

# Lite3 VLA、视觉语言导航与语言条件导航开源复现调研

## 先说人话

**本轮最推荐先复现 `OmniVLA`。** 它不是“论文标题里最像机器狗”的项目，但它是当前严格过完代码、模型权重、运行入口和导航动作接口门槛后，最适合作为 Lite3 第一条低成本 VLA 复现链的项目：官方代码与主要 checkpoint 均为 MIT；已有 GO1 实验；输入支持自然语言、目标图像和二维目标位姿；输出是明确的连续局部轨迹，源码还给出轨迹到 `(v, ω)` 的控制转换。对 Lite3 来说，可以先保留现有 RL locomotion，只替换导航上层，不必让 VLA 直接输出 12 关节动作。

**备选是 `InternVLA-N1 / InternNav`。** 它更新、更活跃，也有真实 Go2 部署与较完整的平台化代码，但第一条复现链更重：双系统、server/client、RGB-D/像素目标/离散或轨迹多种动作路径并存；模型卡徽章与数据协议声明 CC BY-NC-SA 4.0，但模型卡缺少结构化许可证元数据和独立许可证文件；最新固定提交还存在公开的 `diffusers` 兼容报错。它更适合第二阶段做“强基线”，不是最低风险的第一个 smoke test。

**第三名 `VLFM` 也不应先做。** 它的许可证和 waypoint 分层链更透明，但本质是 VLM 语义 frontier + PointNav 的模块化语义导航，不是统一的导航 VLA；同时仓库已明确不再积极维护，PyTorch/CUDA/Habitat 依赖明显老化。它适合做可解释对照和接口验证，不适合承担 Lite3 第一条 VLA 主基线。

**不是 NaVILA 的核心原因不是技术不匹配，而是开源证据没有闭合。** NaVILA 是四足导航 VLA 中技术结构最贴 Lite3 的项目，但官方 8B 权重页面没有 model card/许可证，官方训练数据页面也没有独立许可证；真实 Go2 部署与低层策略发布仍有公开问题单。按本轮硬门槛，不能把它写成首选的“真正开源复现基线”。它应保留为条件候选：作者补齐模型/数据许可和部署包后可立即重评。

**当前最大不确定性是 OmniVLA 在 Lite3 相机视角、机身尺度和语言分布上的迁移。** 公开 issue 已报告文本提示可能不生效、轨迹归一化尺度/速度敏感，以及源码速度限幅可能改变曲率。第一阶段必须先做离线 prompt-sensitivity 与尺度审计，不能直接上真机。

本报告状态是 **`surveyed`，不是 `reproduced`**。本轮没有运行任何候选项目的安装、推理、仿真、训练或真机命令。

## 0. 执行边界与项目写入状态

当前执行环境没有挂载 `/Users/sun/vla`，甚至没有可读取的 `/Users/sun/vla/AGENTS.md`。因此，以下前置治理动作没有完成，也不能伪称完成：

- 未读取 `AGENTS.md`、`bigmemory/热区/状态简报.md`、现有 literature index、terminology、upstream README；
- 未读取、创建或更新 Trellis 活动任务；
- 未写入真实 `/Users/sun/vla/.pipeline/survey/...`；
- 未合并真实 `/Users/sun/vla/.pipeline/literature/index.md`；
- 未编辑只读 `machine-dog-nav`；
- 未导入任何候选代码。

本次交付采用隔离 staging 镜像。目标报告相对路径保持为：

`Users/sun/vla/.pipeline/survey/2026-08-16_lite3_vla_open_source_reproduction_survey.md`

文献索引提供的是待合并块：

`Users/sun/vla/.pipeline/literature/2026-08-16_surveyed_append.md`

在真实项目挂载前，**不得**把该追加块直接覆盖为 `index.md`。必须先按真实 `AGENTS.md` 和 Trellis 规则审阅与合并。

### 覆盖量

- 原始论文：24 篇已核验并保存公开 PDF；其中补充了 2025-12 的 InternVLA-N1、2025-11 的 MobileVLA-R1 和 2026-06 的 Qwen-RobotNav。
- canonical repository：21 个项目/伴随仓库进入对比表，其中 19 个有可固定 commit 的 GitHub 仓库，2 个只有“Code Coming Soon”或无实现。
- 代码级深审：OmniVLA、InternVLA-N1/InternNav、NaVILA、LeLaN、VLFM 共 5 个。
- shortlist：3 个。没有用纯视觉导航项目冒充端到端 VLA；VLFM 被明确标为“合规的分层语义导航基线”。
- 证据状态：全部为 `surveyed`。

## 1. 检索方法

### 1.1 时间范围

主检索范围为 2023-01-01 至 2026-08-16；最近 18 个月按 2025-02-16 至 2026-08-16 处理。LM-Nav、VLMaps 等关键前序工作不受主时间窗限制，但不会用其“经典性”替代当前维护与开源材料审计。

### 1.2 四条路线

1. 四足机器人直接 VLA：QUAR-VLA、NaVILA、QUART-Online、VLM-PC、SayTap、GeRM、Qwen-RobotNav 等。
2. 四足/腿式视觉语言导航、语言条件导航与语义导航：LeLaN、VLFM、VLMaps、ViPlanner、WVN 等。
3. 可迁移到四足的移动机器人或 embodied navigation VLA/VLN：OmniVLA、InternVLA-N1、Uni-NaVid、NaviLLM、VLMnav、InstructNav、StreamVLN、UniGoal 等。
4. 分层路线：`VLA/VLM high-level planner → waypoint/velocity/trajectory/pixel goal/discrete action → safety/local planner → RL locomotion`。

### 1.3 渠道与查询

检索渠道包括 arXiv、OpenReview、RSS、PMLR、CVF Open Access、作者项目页、canonical GitHub repository、GitHub commit/release/issue、Hugging Face 模型卡与数据卡。查询覆盖用户给定的全部关键词，并扩展至 `trajectory`、`pixel goal`、`frontier waypoint`、`diffusion navigation policy`、`model card license`、`dataset card license`、`Go2 real-world deployment` 等组合。

完整查询与核验规则见 staging 包 `audit/search_log.md`。

### 1.4 证据优先级

论文原文/正式 proceedings > 官方项目页 > canonical repository 固定 commit > 官方模型卡/数据卡 > 官方 issue/release。聚合页、搜索摘要、视频和二手博客只用于发现线索，不用于决定许可证、命令、权重或复现状态。

### 1.5 开源硬门槛的执行方式

进入 shortlist 必须同时满足：canonical 仓库可固定 commit；代码许可证明确；有真实实现和原作者入口；checkpoint、配置、数据或可行训练方法可获取；动作能映射到导航接口；不依赖不可替换的专有硬件/封闭服务；能设计低成本 smoke test。代码、模型、数据分别核验。

“公开可下载”不等于“有许可证”；“论文声称开源”不等于仓库当前已发布；“演示了 Go2”不等于发布了 Go2 接口和低层 policy。

## 2. 文献路线图

### 2.1 结论性技术地图

直接四足 VLA 的论文数量已经不少，但满足完整开源链的项目仍很稀缺。NaVILA、QUAR-VLA、QUART-Online 的技术相关性很高，开源许可或实现发布却未闭合。当前更实际的第一基线是从通用导航 VLA 获取连续轨迹，再接入四足已有 locomotion。

语言条件导航路线比直接四足 VLA 更成熟。LeLaN 的 waypoint/velocity 接口最清楚；VLFM 的语义 frontier 与 PointNav 分层最透明；OmniVLA 则把语言、图像和 pose goal 统一到连续轨迹，是“研究新颖性、复现成本、Lite3 接口清晰度”之间最平衡的点。

移动/embodied VLN 在 2025—2026 年快速转向双系统和流式控制。InternVLA-N1、StreamVLN、NavDP 组合代表“慢推理规划 + 快动作控制”；这一方向适合后续强基线，但软件栈和数据体量明显高于第一 smoke test。

纯视觉可通行性与局部规划仍是 Lite3 必需的安全支撑。WVN、ViPlanner、CityWalker 可以成为 VLA 下游安全/轨迹组件，但不能在论文中称为 VLA。

| CitationKey | 首次公开 | venue | 路线 | 论文 | 动作/接口 | 本轮结论 | 本地 PDF |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Chen2025VLMPC | 2024-07-02 | ICRA 2025（论文首次公开为 arXiv 2024） | 1/4：四足 VLM 高层技能规划 | [Commonsense Reasoning for Legged Robot Adaptation with Vision-Language Models](https://arxiv.org/abs/2407.02666) | 高层技能序列/行为选择 | 高层技能规划；代码许可缺失/外部 VLM 依赖，未进 shortlist | [`Chen2025VLMPC.pdf`](../../docs/research/papers/Chen2025VLMPC.pdf) |
| Cheng2025NaVILA | 2024-12-05 | RSS 2025 | 1/4：直接腿式 VLA → 中层动作 → RL locomotion | [NaVILA: Legged Robot Vision-Language-Action Model for Navigation](https://arxiv.org/abs/2412.04453) | 自然语言中层位移/转向 → RL 关节策略 | 技术最贴近，但模型/数据许可证不闭合 | [`Cheng2025NaVILA.pdf`](../../docs/research/papers/Cheng2025NaVILA.pdf) |
| Ding2024QUARVLA | 2023-12-22 | ECCV 2024 | 1：直接四足 VLA | [QUAR-VLA: Vision-Language-Action Model for Quadruped Robots](https://arxiv.org/abs/2312.14457) | QUART 动作 token / 四足多任务动作 | 官方代码仍未公开，不能复现 | [`Ding2024QUARVLA.pdf`](../../docs/research/papers/Ding2024QUARVLA.pdf) |
| Frey2023WVN | 2023-07 | RSS 2023 | 2/4：四足户外可通行性支撑 | [Fast Traversability Estimation for Wild Visual Navigation](https://roboticsproceedings.org/rss19/p054.html) | 视觉可通行性图 | 纯视觉可通行性，不是 VLA | [`Frey2023WVN.pdf`](../../docs/research/papers/Frey2023WVN.pdf) |
| Goetting2024VLMnav | 2024-11-08 | NeSy 2025 / arXiv | 3：通用 VLM 离散导航 | [End-to-End Navigation with Vision Language Models: Transforming Spatial Reasoning into Question-Answering](https://arxiv.org/abs/2411.05755) | 离散导航动作 | 零样本思路强，但代码许可/云模型依赖不合门槛 | [`Goetting2024VLMnav.pdf`](../../docs/research/papers/Goetting2024VLMnav.pdf) |
| Hirose2025LeLaN | 2024-10-04 | CoRL 2024，PMLR 270（2025） | 2/3/4：语言条件对象导航 → waypoint/velocity | [LeLaN: Learning A Language-Conditioned Navigation Policy from In-the-Wild Video](https://proceedings.mlr.press/v270/hirose25b.html) | waypoint、velocity、ROS /cmd_vel | 接口很适合 Lite3，但权重/聚合数据许可未闭合且依赖老化 | [`Hirose2025LeLaN.pdf`](../../docs/research/papers/Hirose2025LeLaN.pdf) |
| Hirose2026OmniVLA | 2025-09-23 | ICRA 2026 | 3/4：通用导航 VLA → 连续轨迹 | [OmniVLA: An Omni-Modal Vision-Language-Action Model for Robot Navigation](https://arxiv.org/abs/2509.19480) | 8 点连续轨迹；可转 (v,ω) | 本轮首选 | [`Hirose2026OmniVLA.pdf`](../../docs/research/papers/Hirose2026OmniVLA.pdf) |
| Huang2023VLMaps | 2022-10-11 | ICRA 2023 | 2/4：开放词汇语义地图 | [Visual Language Maps for Robot Navigation](https://arxiv.org/abs/2210.05714) | 开放词汇地图目标/waypoint | 关键前序；支撑模块而非 VLA | [`Huang2023VLMaps.pdf`](../../docs/research/papers/Huang2023VLMaps.pdf) |
| Liu2025CityWalker | 2024-11-26 | CVPR 2025 | 3/4：户外视觉导航 foundation model | [CityWalker: Learning Embodied Urban Navigation from Web-Scale Videos](https://arxiv.org/abs/2411.17820) | 视觉未来轨迹 | 无语言条件；作为邻近轨迹模型 | [`Liu2025CityWalker.pdf`](../../docs/research/papers/Liu2025CityWalker.pdf) |
| Long2024InstructNav | 2024-06-07 | arXiv 2024 | 3/4：LLM/VLM 分层语义导航 | [InstructNav: Zero-shot System for Generic Instruction Navigation in Unexplored Environment](https://arxiv.org/abs/2406.04882) | 语义目标/地图规划/离散动作 | 无许可证/外部 API | [`Long2024InstructNav.pdf`](../../docs/research/papers/Long2024InstructNav.pdf) |
| NavDP2025 | 2025-05-13 | arXiv 2025（项目后续更新至 2026） | 3/4：连续扩散轨迹 System 1 | [NavDP: Learning Sim-to-Real Navigation Diffusion Policy with Privileged Information Guidance](https://arxiv.org/abs/2505.08712) | 连续扩散轨迹 | 适合作为 InternVLA 轨迹执行组件，不是独立语言 baseline | [`NavDP2025.pdf`](../../docs/research/papers/NavDP2025.pdf) |
| Roth2024ViPlanner | 2023-10-02 | ICRA 2024 | 2/4：腿式视觉语义局部规划 | [ViPlanner: Visual Semantic Imperative Learning for Local Navigation](https://arxiv.org/abs/2310.00982) | 局部连续轨迹 | 纯规划，不是 VLA | [`Roth2024ViPlanner.pdf`](../../docs/research/papers/Roth2024ViPlanner.pdf) |
| Shah2023LMNav | 2022-07-11 | CoRL 2022，PMLR 205（2023） | 3/4：关键前序分层语言导航 | [LM-Nav: Robotic Navigation with Large Pre-Trained Models of Language, Vision, and Action](https://proceedings.mlr.press/v205/shah23a.html) | 语言 landmark → 视觉导航子目标 | 关键前序，时间范围例外 | [`Shah2023LMNav.pdf`](../../docs/research/papers/Shah2023LMNav.pdf) |
| StreamVLN2025 | 2025-07-07 | arXiv 2025 | 3：流式 VLN | [StreamVLN: Streaming Vision-and-Language Navigation via SlowFast Context Modeling](https://arxiv.org/abs/2507.05240) | 流式离散动作 | 作为 InternNav 组件更合适 | [`StreamVLN2025.pdf`](../../docs/research/papers/StreamVLN2025.pdf) |
| Tang2023SayTap | 2023-06-12 | CoRL 2023，PMLR 229 | 1/4：语言 → 足端接触/运动技能 | [SayTap: Language to Quadrupedal Locomotion](https://arxiv.org/abs/2306.07580) | 语言 → 足端接触序列/运动技能 | 语言条件 locomotion，非导航 VLA；重要邻近技术 | [`Tang2023SayTap.pdf`](../../docs/research/papers/Tang2023SayTap.pdf) |
| Tong2025QUARTOnline | 2024-12-20 | arXiv 2024/2025 | 1：直接四足流式 VLA | [QUART-Online: Latency-Free Multimodal Large Language Model for Quadruped Robot Learning](https://arxiv.org/abs/2412.15576) | 流式多模态动作序列 | 高度相关但开源不足 | [`Tong2025QUARTOnline.pdf`](../../docs/research/papers/Tong2025QUARTOnline.pdf) |
| Yin2025UniGoal | 2025-03-13 | CVPR 2025 | 3：多目标类型零样本导航 | [UniGoal: Towards Universal Zero-shot Goal-oriented Navigation](https://arxiv.org/abs/2503.10630) | 统一目标图/语义探索动作 | 目标统一化参考；不是四足直接基线 | [`Yin2025UniGoal.pdf`](../../docs/research/papers/Yin2025UniGoal.pdf) |
| Yokoyama2024VLFM | 2023-12-06 | ICRA 2024 | 2/4：语言价值 frontier waypoint → PointNav | [VLFM: Vision-Language Frontier Maps for Zero-Shot Semantic Navigation](https://arxiv.org/abs/2312.03275) | frontier waypoint → PointNav | shortlist 第三名；合规分层基线但不是端到端 VLA | [`Yokoyama2024VLFM.pdf`](../../docs/research/papers/Yokoyama2024VLFM.pdf) |
| Zhang2025UniNaVid | 2024-12-09 | RSS 2025 | 3：通用视频 VLN/VLA | [Uni-NaVid: A Video-based Vision-Language-Action Model for Unifying Embodied Navigation Tasks](https://arxiv.org/abs/2412.06224) | 统一 VLN 动作 | 模型权重许可未闭合 | [`Zhang2025UniNaVid.pdf`](../../docs/research/papers/Zhang2025UniNaVid.pdf) |
| Zheng2024NaviLLM | 2023-12-04 | CVPR 2024 | 3：通用 embodied navigation | [Towards Learning a Generalist Model for Embodied Navigation](https://arxiv.org/abs/2312.02010) | 多任务导航动作/回答 | benchmark 型；代码许可未找到 | [`Zheng2024NaviLLM.pdf`](../../docs/research/papers/Zheng2024NaviLLM.pdf) |
| Song2024GeRM | 2024-03-20 | IROS 2024 | 1：直接四足 VLA / 多任务控制 | [GeRM: A Generalist Robotic Model with Mixture-of-experts for Quadruped Robot](https://arxiv.org/abs/2403.13358) | 离散动作 token → 速度/步态/足端/姿态命令 | 论文高度相关；仓库无明确许可证且发布包不足，不能作为复现基线 | [`Song2024GeRM.pdf`](../../docs/research/papers/Song2024GeRM.pdf) |
| Huang2025MobileVLAR1 | 2025-11-22 | arXiv 2025 | 1/3/4：四足语言导航与连续控制 | [MobileVLA-R1: Reinforcing Vision-Language-Action for Mobile Robots](https://arxiv.org/abs/2511.17889) | [Vx,Vy,ωyaw,离散行为] 连续/离散混合控制 | 直接 Go2/四足相关，但核心数据 URL 仍为占位符且无官方预训练 smoke 入口 | [`Huang2025MobileVLAR1.pdf`](../../docs/research/papers/Huang2025MobileVLAR1.pdf) |
| Wei2026InternVLA | 2025-12-09 | ICLR 2026 Poster | 3/4：双系统 VLN → pixel goal + 连续轨迹 | [Ground Slow, Move Fast: A Dual-System Foundation Model for Generalizable Vision-and-Language Navigation](https://arxiv.org/abs/2512.08186) | pixel goal + 32 点连续轨迹 | 本轮备选；代码/模型/数据较完整，但模型数据非商业许可、依赖与资源成本较高 | [`Wei2026InternVLA.pdf`](../../docs/research/papers/Wei2026InternVLA.pdf) |
| Zhang2026QwenRobotNav | 2026-06-16 | arXiv technical report 2026 | 1/3/4：可配置多任务导航模型；Go2 零样本部署 | [Qwen-RobotNav Technical Report: A Scalable Navigation Model Designed for an Agentic Navigation System](https://arxiv.org/abs/2606.18112) | 8 点 [x,y,heading] waypoint trajectory | 截至固定 commit 只有报告/媒体与说明，未发布可运行代码、权重和许可证 | [`Zhang2026QwenRobotNav.pdf`](../../docs/research/papers/Zhang2026QwenRobotNav.pdf) |

### 2.2 最近 18 个月的增量判断

最近增量并未自动取代首选。**InternVLA-N1** 是材料与维护最强的新项目之一，但 7B 双系统、server/client、218 GB mini 数据和非商业许可使其更适合第二阶段。**MobileVLA-R1** 直接面向四足并输出 `[Vx,Vy,ω_yaw,离散行为]`，但固定仓库的核心数据下载仍是占位符，缺少可固定的官方预训练 smoke 入口。**Qwen-RobotNav** 在 2026 年报告了统一 8 点 waypoint trajectory 和 Go2 部署，但截至固定 commit，canonical repository 尚未发布可运行代码、权重与许可证，因此只能列为高优先级跟踪项，不能进入本轮 shortlist。

## 3. 全部候选仓库对比

下表中的 commit 均按 2026-08-16 检查日固定；`PASS-COMPONENT-NOT-VLA` 只表示该组件自身材料可用，不表示它能替代 VLA baseline。

| 项目 | 路线 | 分支 | pinned commit | 代码许可 | 模型许可 | 数据许可 | 动作接口 | 硬门槛 | 处理 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OmniVLA | 3/4（通用移动机器人 VLA；已含 Go1 实验） | main | `5182600cb4a9ee07684e17cdd2a6cbafc56b8a68` | MIT（LICENSE 文件；GitHub API 元数据曾显示 NOASSERTION） | MIT（NHirose/omnivla-original 等模型卡） | 混合：各原始数据集分别适用；BDD 原始图像受 BDD 条款约束，项目标注/代码部分 MIT；离线 smoke 不需训练数据 | 8×4 归一化轨迹 [x,y,hx,hy]；源码提供 PD 到 (v,ω) | PASS | 首选 |
| InternVLA-N1 / InternNav | 3/4（导航 foundation model；真实 Go2） | main | `7a5c62400ac45b313d9b709c740b64191556a242` | MIT | 模型卡徽章声明 CC BY-NC-SA 4.0；HF `cardData=null` 且无独立许可证文件，需人工确认 | InternData-N1 gated；协议正文 CC BY-NC-SA 4.0（HF 顶部标签与正文存在 BY-SA/NC-SA 不一致，按更严格正文处理） | System 2 像素目标/离散高层动作；System 1 离散动作或连续轨迹（配置相关） | PASS-WITH-RESTRICTION-AND-METADATA-GAP | 技术备选；模型许可元数据需人工确认 |
| VLFM | 2/4（视觉语言语义导航；Spot；waypoint 分层） | main | `584ed56008754fde7997d904983607def8328322` | MIT | 第三方组件混合且可核验：MobileSAM/GroundingDINO 等按各自许可证；YOLOv7 为 GPL-3.0，重新分发须单独审查 | HM3D/MP3D/Gibson 按各数据条款；HM3D/MP3D 需账户/协议，不能随项目任意再分发 | 语言价值图 + frontier waypoint → PointNav 控制器 | PASS-FOR-USE-UNDER-UPSTREAM-TERMS | shortlist 第三名；不是完整端到端 VLA |
| NaVILA | 1/4（直接腿式 VLA + RL locomotion） | main | `76b98f233dd0fff05dfcd69435eec6740febff9d` | Apache-2.0 | 未找到：官方 8B checkpoint 页面无 model card/许可证 | 未找到：NaVILA-Dataset 页面无独立许可证/数据卡 | 自然语言中层空间动作，例如前进距离/转向；下层 RL 输出 12 关节位置 | FAIL | 技术条件候选；不得作为本轮首选 |
| NaVILA-Bench | 1/4 支撑基准（Isaac Sim/Isaac Lab） | main | `e9d2db12ce5788c0f987d734c0094100b6bc0d3a` | MIT（LICENSE 文件；API 识别异常） | 依赖 NaVILA 主 checkpoint；其许可证未闭合 | VLN-CE-Isaac 数据页为 MIT | VLM server 文本动作 + Go2 低层策略 | FAIL-DEPENDENCY | 可作后续基准组件，不能单独解除 NaVILA 许可证缺口 |
| LeLaN | 2/3/4（语言条件目标导航 → waypoint/cmd_vel） | main | `a41d478cb966eabce78af2b79e6cbfef3aebd589` | MIT | 未找到独立权重许可证 | 聚合数据/Google Drive 发布未在 README 中给出独立统一许可证；底层视频来源混合 | /waypoint、/vel_lelan，经 PD 发布 /cmd_vel | FAIL | 接口参考，不作为首选 |
| MobileVLA-R1 | 3/4（移动机器人导航 VLA） | main | `ff9062c143d6b50c05d913e6be15d36634a7a460` | Apache-2.0 | 未找到可直接 smoke 的官方导航 checkpoint 许可闭环 | README 核心 Nav_CoT_FINAL_38K.jsonl 下载仍是 your-storage 占位符 | 导航 CoT / 移动动作（论文相关） | FAIL | 淘汰：材料不完整 |
| Uni-NaVid | 3（通用连续 VLN） | main | `79ef5ea3fea14c205342d1ab070563d84c7a966a` | MIT | 未找到官方 16.2 GB 权重页的明确许可证 | 依赖多套 VLN 数据，各自条款 | 连续/离散导航动作（任务配置相关） | FAIL | 淘汰：模型许可未闭合、四足接口弱 |
| NaviLLM | 3（通用 embodied navigation） | main | `a221f42ad52893e861779921df336d63c0b4f3a6` | 未找到仓库根目录明确许可证 | 需逐模型核验 | 依赖多 benchmark 条款 | 多任务导航动作/回答 | FAIL | 淘汰：代码许可证缺失、实机桥接成本高 |
| InstructNav | 3/4（LLM/VLM 分层语义导航） | main | `e58a5aac51cdb1c1ea4794ded0138e78f24de70f` | 未找到 | 依赖外部 VLM/LLM；部分云 API | Habitat/场景条款 | 语义目标/地图规划/离散动作 | FAIL | 淘汰：无许可证且可能依赖闭源 API |
| VLMnav | 3（零样本 VLM 端到端离散导航） | main | `82d59684c15a6694ea73b969e76a57157c8740b8` | 未找到 | 依赖外部 VLM/API | benchmark 条款 | 离散导航动作 | FAIL | 淘汰：无许可证/云模型依赖 |
| VLM-PC | 1/4（四足 VLM 高层技能规划） | main | `4a616a93ebd8036bc2c43fbe45071ef939daca48` | 未找到 | 依赖外部 VLM 服务/模型 | 无独立训练数据需求；实验资产许可未形成复现包 | 技能序列/高层行为选择 | FAIL | 淘汰：代码许可与闭源服务依赖 |
| StreamVLN | 3（流式 VLN） | main | `e48f6ff7e9201d93aae003e8f64b04c00cec13bc` | 独立仓库根目录未找到明确许可证；已被 InternNav 集成 | 需按模型卡 | 依赖 InternData/VLN 数据条款 | 流式离散动作 | FAIL-STANDALONE | 作为 InternNav 组件审查，不单独 shortlist |
| NavDP | 3/4（扩散轨迹策略） | master | `878740a2011856d0e3782dd6ccd880fd2eccd70f` | 独立仓库根目录未找到明确许可证；InternNav 内部集成受 MIT 主仓治理 | checkpoint 需逐卡核验 | 依赖相关导航数据 | 连续轨迹/扩散策略 | FAIL-STANDALONE | 适合作为 InternVLA System 1/轨迹组件，不单独作为语言基线 |
| Qwen-RobotNav | 1/3/4（Go2 语言导航技术报告） | main | `f74cf1f6079300aee6e40e03858da2f98b1b7261` | 未找到 | 截至检查日未发布可核验权重 | 未发布 | 报告描述语言条件导航/agentic tool actions | FAIL | 淘汰：不是可复现代码仓 |
| GeRM | 1（四足 generalist/VLA 声称） | main | `fadc5b2de494c1084e88865279341799a74417fc` | 未找到 | 未找到 | 未找到 | 仓库声称 VLA/MoE；未见足够运行实现 | FAIL | 淘汰：宣传页级，不满足真实实现门槛 |
| VLMaps | 2/4（开放词汇语义地图 → 目标/waypoint） | master | `58060f97239074338ab419a2090d43fa752d724d` | MIT | CLIP/LLM 等按上游许可证；语言分解常用 GPT API | Habitat/真实数据各自条款 | 语言查询语义地图 → 地图目标/规划 | PASS-COMPONENT-NOT-VLA | 支撑模块，不冒充 VLA baseline |
| ViPlanner | 2/4（腿式语义局部规划） | main | `6fcf3c60f6fa3b28b3a11af054d6033825923789` | 自定义/Other；需阅读仓库 LICENSE，不按宽松开源默认处理 | 公开模型有单独条件 | Matterport/Omniverse 场景条款 | 视觉语义局部轨迹 | FAIL-AS-VLA | 纯规划组件，不是语言/VLA |
| CityWalker | 3/4（户外视觉轨迹 foundation model） | main | `ab0ef60b17dc4d1d16c7d95dd143e6dac91abed1` | Apache-2.0（仓库元数据/许可证） | 需按权重卡核验 | web-scale/训练数据条款需逐项核验 | 视觉目标/未来轨迹 | PASS-COMPONENT-NOT-LANGUAGE | 邻近视觉导航对照，不是 VLA |
| QUAR-VLA official release | 1（直接四足 VLA） | — | — | — | — | — | QUART 动作 token/四足任务 | FAIL | 淘汰：无 canonical 实现 |
| VoroNav | 3/4（VLM 高层探索） | — | — | — | — | — | 拓扑/Voronoi exploration waypoint | FAIL | 淘汰：无实现 |

完整字段、维护日期、release、入口和权重情况另见 `audit/repository_audit.tsv`。

## 4. Top 5 代码级证据卡

下列卡片保留决策所需的主要证据；39 个统一审计字段（机器人、传感器、模拟器、ROS/OS/CUDA、资源、模型/数据许可、入口、issue、Lite3 适配）另见 staging 根目录 `audit/top5_code_evidence.tsv`。

### 4.1 OmniVLA — 首选

**论文与时间。** Noriaki Hirose、Catherine Glossop、Dhruv Shah、Sergey Levine，*OmniVLA: An Omni-Modal Vision-Language-Action Model for Robot Navigation*；首次公开 2025-09-23；作者项目页和 Princeton PRISM 元数据显示为 ICRA 2026。

- 论文：<https://arxiv.org/abs/2509.19480>
- 项目页：<https://omnivla-nav.github.io/>
- canonical repository：<https://github.com/NHirose/OmniVLA>
- default branch：`main`
- pinned commit：`5182600cb4a9ee07684e17cdd2a6cbafc56b8a68`
- 检查日期：2026-08-16
- 最近实质提交：`092f478cdc5aa669571945bcb31fc132ba925292`，2026-02-18，加入 edge 推理；当前固定 head 的 2026-03-25 变更主要是 README。
- release：未找到 GitHub Release。
- 状态：`surveyed`。

**许可证。** 代码仓 LICENSE 为 MIT。官方 `NHirose/omnivla-original`、`omnivla-original-balance`、`omnivla-finetuned-cast`、`omnivla-edge` 模型页标记 MIT。训练数据不是一个单一许可证：GNM、LeLaN、FrodoBots、BDD、CAST 等各自适用上游条款；尤其 BDD 原始图像不能因为项目标注代码是 MIT 就被视为 MIT 数据。首轮官方预训练离线推理不需要下载训练数据，因此可以先把数据许可风险与 smoke test 解耦。

**机器人、传感器与软件。** 项目展示 GO1、Vizbot、FrodoBots 等移动平台。核心输入是前视 RGB 与目标条件；目标可为自然语言、二维 pose、目标图像或其组合。仓库没有要求 ROS 才能做静态推理；真实部署控制代码需要按平台自行接入。README/SETUP 给出 Python 3.10、PyTorch 2.2.0、CUDA 对应 wheel、FlashAttention；官方建议 RTX 4090 或至少约 20 GB GPU 显存。操作系统没有形成严格矩阵，但依赖明显以 Linux/CUDA 为目标。

**动作表示。** `inference/run_omnivla.py` 的模型输出为 8 个 waypoint，每点为 `[x, y, hx, hy]`；源码用 `metric_waypoint_spacing=0.1` 将归一化轨迹恢复为米制，并取中间 waypoint，经 PD 控制器生成线速度和角速度。坐标约定在源码中为 X 向前、Y 向左。该接口与 Lite3 的上层导航—下层 locomotion 分离最契合。

**checkpoint、环境和入口。** 官方原始模型约 8B、BF16，模型页为 safetensors；总模型文件约 16 GB 量级。edge 模型明显更小，但 `.pth`/pickle 类权重应只从固定官方 revision 在隔离环境加载。

原作者 SETUP 命令为：

```bash
conda create -n omnivla python=3.10 -y
conda activate omnivla
pip3 install numpy==1.26.4 torch==2.2.0 torchvision==0.17.0 torchaudio==2.2.0

git clone https://github.com/NHirose/OmniVLA.git
cd OmniVLA
pip install -e .
pip install packaging ninja
pip install "flash-attn==2.5.5" --no-build-isolation
```

官方 original checkpoint 与推理入口：

```bash
git clone https://huggingface.co/NHirose/omnivla-original
python inference/run_omnivla.py
```

官方 edge 入口：

```bash
git clone https://huggingface.co/NHirose/omnivla-edge
python inference/run_omnivla_edge.py
```

README 命令可以在固定 commit 中找到对应 `inference/run_omnivla.py` 和 `inference/run_omnivla_edge.py`，不是空壳命令。

**预期可观察输出。** 原作者脚本应生成示例轨迹可视化，例如 `1_ex.jpg`；edge 脚本应生成 `1_ex_omnivla_edge.jpg`。还应能在 Python 层检查得到有限数值、形状正确的 `8×4` 轨迹，以及有限的 `(v,ω)`。这些是预期，不是本轮已观察结果。

**已知风险。** issue #28 报告语言 prompt 可能不生效、机器人持续直行；#27 质疑单一 waypoint spacing 对速度/时间尺度的敏感性；#26 指出先逐分量 clip 再做比例限幅可能改变 `v/ω`；#13 指出 CAST 训练数据转换所需的若干 preprocessing 文件/脚本未完全公开；#22 询问完整评测/SR benchmark 是否开放。由此，OmniVLA 适合“预训练离线推理基线”，暂不适合把官方完整训练重现写成低风险任务。

**Lite3 具体适配。** 必须新增而不是假定已有：

1. `camera_adapter`：把 Lite3 前视相机时间戳、分辨率、颜色顺序和裁剪方式转换为 OmniVLA 输入；记录 `T_base_camera`。
2. `goal_adapter`：规范自然语言、目标图和相对 pose goal；禁止把世界系 GPS 直接塞进机器人局部 pose 字段。
3. `trajectory_sanitizer`：检查 `8×4`、NaN/Inf、最大长度、曲率、轨迹是否落在当前可通行区域。
4. `trajectory_to_body_command`：重写受控的轨迹跟踪器，不直接照搬有争议的双重 clip。
5. `lite3_command_bridge`：映射到真实 `machine-dog-nav`/Lite3 body velocity 或 waypoint 接口；当前接口未知，必须在项目挂载后读取，不得发明 ROS topic。
6. `safety_supervisor`：看门狗、跌倒/非站立态禁止、障碍 veto、速度/加速度限幅和急停。

不可直接复用的部分包括：GO1/Vizbot 的相机外参、轮式/差速 PD 参数、训练时 waypoint spacing、真实底盘速度上限和任何机器人 SDK 调用。

### 4.2 InternVLA-N1 / InternNav — 备选

**论文与时间。** Meng Wei、Chenyang Wan、Jiaqi Peng、Xiqian Yu、Yuqiang Yang、Delin Feng、Wenzhe Cai、Chenming Zhu、Tai Wang、Jiangmiao Pang、Xihui Liu，*Ground Slow, Move Fast: A Dual-System Foundation Model for Generalizable Vision-Language Navigation*；arXiv 2512.08186；OpenReview 显示 ICLR 2026 Poster，2026-01-26 公开会议版本。

- canonical repository：<https://github.com/InternRobotics/InternNav>
- default branch：`main`
- pinned commit：`7a5c62400ac45b313d9b709c740b64191556a242`
- 最近实质提交：`5544d95cbf7feb62e8fd11e9d3f0d6391cab0302`，2026-03-03。
- release：`v0.3.1`，2026-02-11。
- 状态：`surveyed`。

**许可证。** InternNav 代码是 MIT。`InternRobotics/InternVLA-N1-DualVLN` 模型卡顶部徽章声明 CC BY-NC-SA 4.0；但 2026-08-16 复核时 Hugging Face API 返回 `cardData=null`，文件树也没有独立许可证文件，因此只能确认“官方卡片有非商业许可声明”，不能把标准元数据和法律文本视为已闭合。`InternData-N1` 是 gated 数据；Hugging Face 顶部元数据曾显示 `cc-by-sa-4.0`，但数据卡和社区协议正文明确写 CC BY-NC-SA 4.0，本报告按更严格正文处理。上述限制不妨碍博士研究内部评估，但模型下载、衍生物分发和后续合作前仍需 Dr Sun 人工确认并保存当时条款。

**系统与接口。** InternVLA-N1 是双系统：System 2 做较慢的语言/像素目标或高层计划，System 1 以更高频率生成动作。固定 commit 的 `internnav/agent/internvla_n1_agent.py` 读取 RGB、深度、instruction 与 pose；不同配置可输出像素目标、离散动作、latent plan 或连续轨迹。项目展示 Go2、TurtleBot、G1 等实机；这比 OmniVLA 更接近完整 foundation model 平台，也意味着首复现的配置空间更大。

**环境和原作者入口。** 文档给出的基础环境是 Ubuntu 20.04/22.04、Python 3.10、CUDA 11.8、PyTorch 2.5.1；推理平台示例包括 RTX 4090/A100，训练为 A100 类资源。

```bash
git clone https://github.com/InternRobotics/InternNav.git --recursive
conda create -n internnav python=3.10 libxcb=1.14
conda activate internnav
pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu118
pip install -e .[model] --no-build-isolation
python scripts/eval/start_server.py --port 8087
```

预期 server 日志包括 `Starting Agent Server...` 与 Uvicorn 本地监听。官方 notebook/client 通过 `AgentCfg`、`AgentClient` 和示例 `rs_meta.json` 调用 `agent.step`；文档示例可见 `s2 infer finish!!`、`Output discretized traj: [2] 0`、HTTP 200、`Action taken: 2`。这些仍是文档预期，不是本轮执行结果。

**资源。** 8B BF16 模型本体约 16 GB 量级；环境、缓存和样例应预留至少 40–80 GB 磁盘。数据 mini 约 218 GB，full 页面当前标称 7.78 TB；smoke test 不应下载训练数据。官方未给出统一的单次推理耗时和 host RAM 最低值。本报告建议把首轮 server+一条样例的执行上限设为 3 小时、主机内存 64 GB、单卡 24 GB 显存；这是审计预算，不是已测性能。

**已知风险。** issue #321 在最新 pinned commit、官方 Docker v1.2/Ubuntu 22.04 环境中报告 `diffusers >=0.31` 调用 `_set_gradient_checkpointing(enable=...)` 导致 TypeError。#365 显示微调后过早 STOP 与 pixel-goal 距离/定义仍需作者澄清。首复现必须固定依赖版本或应用最小兼容补丁，并把补丁与上游 diff 分开记录。

**Lite3 适配。** 有两条可选桥：A）固定离散动作表，映射 `forward/left/right/stop` 到有限时长 body velocity；B）使用连续 NavDP 轨迹作为局部计划。A 成本低但丢失几何精度；B 更适合论文基线但要核验轨迹 frame、频率、深度相机和 action decoder。当前不能假定 Lite3 具备与 Go2 相同的 action table、相机高度或 SDK。

### 4.3 NaVILA — 技术最匹配但硬门槛失败

**论文与时间。** An-Chieh Cheng、Yandong Ji、Zhaojing Yang、Zaitian Gongye、Xueyan Zou、Jan Kautz、Erdem Bıyık、Hongxu Yin、Sifei Liu、Xiaolong Wang；首次公开 2024-12-05；RSS 2025，DOI `10.15607/RSS.2025.XXI.018`。

- repo：<https://github.com/AnjieCheng/NaVILA>
- branch：`main`
- pinned commit：`76b98f233dd0fff05dfcd69435eec6740febff9d`
- 代码许可证：Apache-2.0。
- 最近实质代码：`c59d8cb24b4b366033798f931f218711303a94fc`，2025-07-07；2025-08-20 为 README 更新。
- 状态：`surveyed`，硬门槛 `FAIL`。

**架构。** 这是最贴合 Lite3 现有思路的两层结构：VLA 不直接输出关节，先产生带空间量的中层语言动作，例如“向前移动 75 cm”，然后视觉 locomotion RL policy 执行，最终输出 12 关节位置。该结构证明“VLA 上层 + RL locomotion”本身是合理研究路线。

**实现与命令。** 仓库包含 Habitat/VLN-CE 评测和训练入口：

```bash
cd evaluation
bash scripts/eval/r2r.sh CKPT_PATH NUM_CHUNKS CHUNK_START_IDX "GPU_IDS"
```

训练入口包括 `scripts/train/sft_8frames.sh`。伴随 `NaVILA-Bench` 固定在 `e9d2db12ce5788c0f987d734c0094100b6bc0d3a`，提供 Isaac Sim 4.1 / Isaac Lab 1.1 的 Go2 基准脚本和 VLM server；`VLN-CE-Isaac` 数据约 5.03 GB 且模型卡标 MIT。

**为什么仍失败。** 官方 `a8cheng/navila-llama3-8b-8f` 页面无 model card 和许可证；`a8cheng/NaVILA-Dataset` 也没有独立许可证/数据卡。主权重与训练数据不满足本轮“代码、模型、数据分别检查”的硬门槛。伴随 benchmark 的 MIT 许可不能回溯性覆盖主模型和主数据。

**复现风险。** issue #10 报告 Habitat Lab/Sim 版本字段不兼容；#25/#51/#54 报告无输出、无视频或模型生成非导航文本；#53 询问 Go2 部署代码与 locomotion checkpoint；#57 报告真实 Go2 中“向右”持续被解释为“向左”。因此不能把论文演示直接等价为公开仓库的一键实机复现。

**Lite3 可借鉴与不可照搬。** 可借鉴两层接口、历史帧 VLA server 和中层动作审计；不可照搬 Unitree Go2 SDK、相机/雷达高度图、低层 policy、动作字符串解析器和速度持续时间。NaVILA 最值得作为论文结构对照，而不是当前第一执行对象。

### 4.4 LeLaN — 接口最干净的语言条件导航参考

**论文。** Noriaki Hirose、Catherine Glossop、Ajay Sridhar、Oier Mees、Sergey Levine；首次公开 2024-10-04；CoRL 2024，PMLR 270（2025）。

- repo：<https://github.com/NHirose/learning-language-navigation>
- branch：`main`
- pinned commit：`a41d478cb966eabce78af2b79e6cbfef3aebd589`
- code license：MIT。
- 最近实质提交：2024-09-27。
- 状态：`surveyed`，硬门槛 `FAIL`。

**接口证据。** README 与源码明确包含：

```bash
python train.py -c ./config/lelan_col_pretrain.yaml
python train.py -c ./config/lelan_col.yaml
python lelan_policy_col.py -p <prompt> -c <config> -m <checkpoint> -r <camera flag>
python pd_controller_lelan.py
python navigate_lelan.py -p <prompt> --model vint --dir <topomap_dir>
```

ROS 节点发布 `/waypoint`、`/vel_lelan`，PD controller 再发布 `/cmd_vel`。这正是 Lite3 导航层最容易适配的接口形态。

**为什么不首选。** 仓库长期无实质更新，环境是 Ubuntu 18.04/20.04、Python 3.7+、CUDA 10+、ROS1，并面向 Jetson Orin AGX。Google Drive 权重与聚合数据在 README 中没有独立统一许可证；底层包含机器人、YouTube、人行视频等混合来源。代码 MIT 不自动覆盖这些资产。它适合作为 adapter 设计参考，但不满足本轮“真正开源第一基线”的严格资产门槛。

### 4.5 VLFM — 合规的分层语义导航第三候选

**论文。** Naoki Yokoyama、Sehoon Ha、Dhruv Batra、Jiuguang Wang、Bernadette Bucher；首次公开 2023-12-06；ICRA 2024。

- canonical repo：<https://github.com/rai-opensource/vlfm>
- branch：`main`
- pinned commit：`584ed56008754fde7997d904983607def8328322`
- code license：MIT。
- README 明示项目按现状提供、没有积极维护。
- 状态：`surveyed`。

**架构。** RGB-D 构建 occupancy/frontier；预训练视觉语言模型形成语言价值图；选择最有希望的 frontier waypoint；PointNav policy 执行。真实机器人支持 Spot。它不是端到端 VLA，但输出 waypoint、模块边界清楚，适合验证“语言高层 → 安全局部导航 → 四足 locomotion”链路。

**原作者入口。** 典型安装栈为 Python 3.9、PyTorch 1.12.1+cu113、GroundingDINO、LAVIS；Habitat 模式或 Spot reality 模式分别安装：

```bash
conda create -n vlfm python=3.9 -y
conda activate vlfm
pip install torch==1.12.1+cu113 torchvision==0.13.1+cu113 -f https://download.pytorch.org/whl/torch_stable.html
pip install git+https://github.com/IDEA-Research/GroundingDINO.git@eeba084341aaa454ce13cb32fa7fd9282fc73a67 salesforce-lavis==1.0.2
pip install -e .[habitat]
./scripts/launch_vlm_servers.sh
python -m vlfm.run
```

README 命令在源码中有对应 module/script。模型组件来自 MobileSAM、GroundingDINO、YOLOv7、LAVIS/CLIP、PointNav；许可证是混合矩阵，其中 YOLOv7 的 GPL-3.0 可能影响重新分发。HM3D/MP3D 需要 Matterport 许可。它可以在上游条款下使用，但不能把整个依赖包笼统标成 MIT。

**Lite3 适配。** 替换 Spot SDK 与 PointNav 执行器，把 frontier waypoint 发布给 Lite3 局部规划/速度桥；保留 occupancy、语言价值图和 frontier 选择。不可直接复用 Spot 相机、深度标定、footprint、PointNav policy 运动学或安全控制。由于依赖老化，建议容器隔离，不建议污染主工程环境。

## 5. Top 3 排序、评分与置信度

### 5.1 硬门槛先行

| 项目 | 代码许可 | 模型许可 | 数据许可/可避开性 | 真实入口 | 导航动作 | 硬门槛结论 |
| --- | --- | --- | --- | --- | --- | --- |
| OmniVLA | MIT | MIT | smoke 不需训练数据；训练数据混合需逐项遵守 | 有 | 连续轨迹/(v,ω) | 通过 |
| InternVLA-N1 | MIT | 模型卡徽章声明 CC BY-NC-SA 4.0；结构化元数据与独立许可证文件缺失 | gated、NC；smoke 可不下载 full data | 有 | pixel/discrete/trajectory | 有条件通过；非商业限制与模型许可元数据缺口需人工确认 |
| VLFM | MIT | 第三方混合、可核验 | 数据需 Matterport 等条款 | 有 | frontier waypoint | 通过用于分层组件；不是完整 VLA |
| NaVILA | Apache-2.0 | 未找到 | 主数据未找到许可证 | 有但部署链不闭合 | 中层语言动作 | 失败 |
| LeLaN | MIT | 未找到独立许可 | 聚合数据许可未闭合 | 有 | waypoint/velocity | 失败 |

### 5.2 100 分评分

| 排名 | 项目 | Lite3/四足匹配 25 | 材料完整 25 | 健康度 15 | 科学证据 15 | 适配成本 10 | 新颖时效 10 | 总分 | 置信度 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | OmniVLA | 22 | 22 | 12 | 13 | 8 | 9 | **86** | 离线 smoke：中高；Lite3 迁移：中 |
| 2 | InternVLA-N1 / InternNav | 20 | 21 | 14 | 14 | 5 | 10 | **84** | 中；受依赖 bug、NC 许可和配置复杂度影响 |
| 3 | VLFM | 15 | 21 | 7 | 14 | 8 | 4 | **69** | 中；方法成熟但依赖老化且不是完整 VLA |

评分只在过硬门槛后排序。GitHub stars 未计入任何主分项，只在判断社区暴露面时作为弱信号。

### 5.3 为什么 OmniVLA 比另外两个更适合作为第一条

相对 InternVLA-N1，OmniVLA 的入口更短、动作更连续、模型资产许可更宽松，不要求先选定 System 1/System 2 配置，也不需要下载 218 GB mini 数据。相对 VLFM，OmniVLA 是真正的导航 VLA，可直接检验语言/图像/pose goal 到轨迹的统一能力；VLFM 更像稳健、透明的 semantic navigation 对照。

OmniVLA 的弱点不是被忽略，而是被转化为第一阶段明确试验：语言 prompt sensitivity、相机/机身尺度、轨迹 metric spacing、曲率保持和离线 collision audit。

## 6. 被排除项目与具体理由

**许可证不成立或资产许可不闭合：** NaVILA（主模型与主数据未找到许可）、LeLaN（权重与聚合数据许可未闭合）、Uni-NaVid（官方权重许可未找到）、NaviLLM/InstructNav/VLMnav/VLM-PC/StreamVLN/NavDP standalone/GeRM/Qwen-RobotNav（根仓许可、模型或发布包至少一项缺失）。

**只有论文/演示，没有可运行 release：** QUAR-VLA 官方页仍是 Code Coming Soon；Qwen-RobotNav 固定 commit 主要是 README/视频，未发布代码和权重；VoroNav 项目页显示 Code Coming Soon；GeRM 仓库不足以构成真实运行实现。

**数据或命令是占位：** MobileVLA-R1 的核心 `Nav_CoT_FINAL_38K.jsonl` 下载命令仍指向 `https://your-storage/...`，没有预训练最小推理入口。

**依赖不可替换的闭源 API：** VLM-PC、InstructNav、VLMnav 和部分 VLMaps 默认路径使用商业/闭源 VLM/LLM；即使可以替换，也不能把当前仓库写成完全离线开源基线。

**不是 VLA：** ViPlanner、WVN、CityWalker 是重要视觉规划/可通行性/轨迹组件；VLMaps 是开放词汇语义地图；它们可接在 VLA 下游或作为消融，但不能冒充语言条件 VLA。

**伴随仓不能解除主项目缺口：** NaVILA-Bench 自身有 MIT 代码和 MIT benchmark 数据，但仍依赖无许可证的 NaVILA 主权重与未完整发布的 locomotion/Go2 部署链。

## 7. 首选 OmniVLA 的最小复现方案

### 7.1 目标和非目标

目标是在获得 Dr Sun 批准后，只完成一个**离线、无机器人动作、可观察、可停止**的官方预训练推理 smoke test，确认固定 commit、固定 checkpoint 能产生有限且对输入有基本敏感性的轨迹。

本阶段不做：完整 benchmark、训练、CAST 数据重建、Isaac 仿真、`machine-dog-nav` 导入、Lite3 真机运动、长时间远端任务。

### 7.2 前置检查

1. 在真实 `/Users/sun/vla` 中读取 AGENTS/Trellis/terminology/upstream 规则并建立正式任务。
2. Dr Sun 明确选择 OmniVLA；未批准前不 clone。
3. 核验代码 MIT、模型 MIT；记录 Hugging Face revision 和每个下载文件 SHA-256。
4. 隔离 conda/container；不在现有 Lite3/Isaac Lab 环境中直接安装 PyTorch 2.2/FlashAttention。
5. GPU：官方要求至少约 20 GB，首选 RTX 4090 24 GB。无 20 GB 单卡时先用 edge 模型，不用 CPU 强行跑 8B。
6. 加载 `.pt/.pth` 前确认来源是固定官方 revision；在无凭据、无项目写权限的沙箱执行。

### 7.3 固定源码

审计 wrapper 应在原作者 clone 命令后增加固定 commit：

```bash
git clone https://github.com/NHirose/OmniVLA.git
cd OmniVLA
git checkout 5182600cb4a9ee07684e17cdd2a6cbafc56b8a68
git status --short
git rev-parse HEAD
```

成功标准：HEAD 精确等于上述 SHA，工作树在运行前为空。任何本地兼容补丁必须单独 commit/diff，不得改写成上游原貌。

### 7.4 环境

按原作者命令安装，不擅自升级 torch/transformers/flash-attn：

```bash
conda create -n omnivla python=3.10 -y
conda activate omnivla
pip3 install numpy==1.26.4 torch==2.2.0 torchvision==0.17.0 torchaudio==2.2.0
pip install -e .
pip install packaging ninja
pip install "flash-attn==2.5.5" --no-build-isolation
```

额外只做审计输出：`python --version`、`pip freeze`、`nvidia-smi`、CUDA/driver、GPU 名称和可用显存。不得把环境创建成功写成模型复现成功。

### 7.5 官方 checkpoint 与官方推理

original 路线：

```bash
git lfs install
git clone https://huggingface.co/NHirose/omnivla-original
python inference/run_omnivla.py
```

低显存备选：

```bash
git lfs install
git clone https://huggingface.co/NHirose/omnivla-edge
python inference/run_omnivla_edge.py
```

模型仓同样要固定 Hugging Face commit/revision；不能只写 `main`。固定 revision 需在正式运行时从模型页获取并登记，因为本轮没有 clone 模型仓。

### 7.6 预期日志、文件和检查

至少保存：

- stdout/stderr 完整日志；
- `pip freeze`、GPU/driver 信息；
- 源码和模型 revision；
- 所有模型文件 SHA-256；
- 原始脚本生成的 `1_ex.jpg` 或 `1_ex_omnivla_edge.jpg`；
- 原始 `8×4` trajectory 数组；
- metric scaling 后的轨迹；
- 由控制器得到的 `(v,ω)`，但不发布到任何机器人 topic；
- 峰值显存、host RAM、加载时间和单次前向时间。

轨迹通过条件：shape 正确、全部有限、首尾顺序合理、没有异常巨跳；控制输出有限且在配置限幅内。

### 7.7 最小输入敏感性测试

官方单样例成功后，在不改模型的情况下对同一图像使用至少三种语义明显不同的目标，例如“直行”“左转靠近目标”“停止/不要前进”，并在三组不同图像上重复。记录轨迹点差、末端方向差与 `v/ω` 差。

这不是论文 benchmark，只是排除“语言完全被忽略”这一公开 issue。若相反指令的轨迹几乎完全相同，首轮状态应写为 `smoke_failed_language_sensitivity`，不得继续接 Lite3。

### 7.8 资源预算

| 项目 | 官方证据 | 本轮执行预算/上限（非实测） |
| --- | --- | --- |
| GPU | RTX 4090；≥20 GB VRAM | 24 GB 单卡；edge 可作低显存降级 |
| host RAM | 官方未给出统一最低值 | 建议 64 GB；最低 32 GB 仅作尝试 |
| 磁盘 | 8B BF16 模型约 16 GB 量级 | 环境+模型+缓存+日志预留 40 GB；edge 另算 |
| 下载 | 取决于模型仓 | original 预留约 20 GB 网络传输 |
| wall-clock | 官方未给出 | 环境已就绪后 smoke 上限 2 小时；不含网络下载；超时停止 |
| 训练 | H100 级基础设施 | 不在本阶段执行 |

### 7.9 成功标准

只有同时满足以下条件，才能把后续任务从 `surveyed` 升为单独的 `reproduced_smoke` 或项目规定的等价状态：

1. 固定 commit 和固定模型 revision；
2. 官方脚本无本质改动运行结束，退出码 0；
3. 生成预期可视化与有限 `8×4` 轨迹；
4. 至少基本区分相反语言/目标输入；
5. 记录完整环境、校验和和资源；
6. 没有调用机器人控制接口。

### 7.10 停止条件

- checkpoint/model card 许可与本报告不一致；
- Hugging Face 文件不可访问、LFS 指针未下载完整或 hash 不稳定；
- 20/24 GB GPU OOM，且 edge 仍无法运行；
- 依赖冲突需要大规模改动上游；
- 输出 NaN/Inf、shape 错误或尺度明显异常；
- 相反语言输入无可辨识差异；
- 任何脚本试图连接真实机器人、发布速度或访问未授权服务；
- 超过 2 小时 smoke 上限仍未得到可解释结果。

## 8. 到 Lite3 导航—运动控制链路的接口映射

### 8.1 五种动作接口比较

| 接口 | 代表项目 | Lite3 接入方式 | 优点 | 主要缺口 | 本轮建议 |
| --- | --- | --- | --- | --- | --- |
| waypoint | LeLaN、VLFM、NaVILA 部分中层 | 发布机器人局部系 `(x,y)` 给局部跟踪器 | 边界清楚、可插入避障 | 单点会丢失曲率/未来形状；需 frame/尺度 | 可作备份接口 |
| velocity command | LeLaN、OmniVLA 源码 PD | 映射到 locomotion 的 body command `(v_x,v_y,ω_z)` | 最低接入成本 | VLA 误差直接变控制；需要 watchdog/限幅/障碍 veto | 只用于低速 dry-run，不能裸接 |
| trajectory | **OmniVLA**、NavDP | 保留 8 点/连续轨迹，由安全局部跟踪器生成 body command | 几何信息最多；便于 collision/curvature 审计 | 需尺度、相机外参、时间参数化 | **首选内部接口** |
| pixel goal | InternVLA System 2 | 深度/地面平面反投影为 3D/2D waypoint，再交局部规划 | 高层与低层解耦；适合双系统 | 必须有标定深度、遮挡处理和可见性检查 | 第二阶段研究接口 |
| 离散导航动作 | InternVLA、VLMnav、NaVILA | `forward/left/right/stop` → 有限时长速度 primitive | 实现简单、可解释 | 粗糙、累计误差、动作表依机器人 | 仅作 sanity baseline |

### 8.2 推荐的第一条内部链路

```text
language / image / relative-pose goal
                +
        timestamped front RGB
                ↓
          OmniVLA inference
                ↓
  normalized local trajectory (8×4)
                ↓
 scale + camera→base transform + validation
                ↓
 collision/traversability veto + curvature filter
                ↓
 trajectory tracker / guarded body command
                ↓
 Lite3 navigation-to-locomotion bridge
                ↓
 existing RL locomotion controller
                ↓
 joint targets / low-level actuator interface
```

关键原则：**VLA 输出保留为 trajectory；velocity 只是在下游受控生成的执行命令。** 这样可以比较轨迹质量、插入安全层，也能在未来替换 OmniVLA 而不改 locomotion。

### 8.3 建议的轨迹契约

OmniVLA 给出

\[
\hat\tau=\{(x_i,y_i,h^x_i,h^y_i)\}_{i=1}^{8}.
\]

源码默认用尺度 `s=0.1 m`；正式适配必须通过相机与实测轨迹校准，不能默认它对 Lite3 成立：

\[
p_i^C=s[x_i,y_i]^\top,
\qquad
p_i^B=T_{B\leftarrow C}\,p_i^C.
\]

选择满足最小 look-ahead 的点 `k`，可用一个独立、可审计的跟踪器：

\[
e_y=y_k^B,
\qquad
e_\psi=\operatorname{atan2}(h_k^y,h_k^x),
\]

\[
v_x=\operatorname{sat}(k_x x_k^B,0,v_{\max}),
\qquad
\omega_z=\operatorname{sat}(k_y e_y+k_\psi e_\psi,-\omega_{\max},\omega_{\max}).
\]

第一版可设 `v_y=0`，避免同时引入侧向运动；后续若 Lite3 locomotion 已验证全向 body command，再扩展横移。上述控制律是建议 adapter，不是 OmniVLA 论文结果。

### 8.4 初始安全参数建议

只用于仿真/架空 dry-run 的保守起点，不代表 Lite3 实机认证参数：

- `v_x_max = 0.15 m/s`；
- `|ω_z|max = 0.25 rad/s`；
- `|a_x|max = 0.20 m/s²`；
- `|α_z|max = 0.50 rad/s²`；
- command TTL `≤ 0.20 s`，超时立即发零速度；
- 机器人非站立、跌倒风险、通信丢失、轨迹无效、局部障碍 veto 时强制零速度。

实机前还需加入 foot/body collision margin、深度/雷达局部占据图、最小可通行宽度、地形坡度/台阶限制和人工急停。VLA 不能覆盖安全责任。

### 8.5 需要在真实项目中确认的接口

当前项目没有已选定的 VLA 架构、动作接口，也没有已导入 `machine-dog-nav` 基线。本轮没有读取真实代码，因此以下均写“未知”，不做假设：

- Lite3 RL policy 接收的是 ROS `Twist`、自定义 UDP/SDK body command，还是几何 waypoint；
- body command 频率、范围、坐标系、是否支持 `v_y`；
- 当前导航仓是否已有局部规划、障碍 veto、状态估计和安全 supervisor；
- 相机内参、外参、高度、FOV、时间同步；
- locomotion policy 的有效速度域和站立/跌倒状态接口。

真实适配前应先写一个最小 `NavigationCommandContract`，再决定 ROS2 message/topic 或 SDK call；不能先按 Go1/Go2 命名复制。

## 9. 需要 Dr Sun 决定的问题

1. 是否批准 **OmniVLA** 为第一复现对象；备选是否固定为 **InternVLA-N1/InternNav**。
2. 是否接受 InternVLA 模型卡徽章与数据协议声明的 CC BY-NC-SA 4.0 作为研究用途备选；是否要求作者或模型发布方补充标准元数据/独立许可证文本；未来是否有商业或联合项目限制。
3. 可用 GPU 是 24 GB 4090、48/80 GB 数据中心卡，还是只有较小显存；这决定 original 还是 edge smoke。
4. Lite3 第一接口是否同意采用“trajectory 为内部契约、guarded velocity 为执行桥”，而不是直接让 VLA 输出关节动作。
5. 是否批准第一阶段仅做离线官方预训练 smoke + prompt sensitivity，不做 Habitat/Isaac/真机。
6. 需要挂载或提供 `/Users/sun/vla`，以便读取治理文件、当前 Trellis 任务、真实 terminology/index，并把 staged 内容按规则合并。

## 10. 证据缺口与风险登记

- **项目治理缺口：** 本环境看不到 `/Users/sun/vla`，因此报告尚未通过项目术语、状态机和 Trellis 规则校验。
- **运行证据缺口：** 任何项目均未执行；资源、日志和输出均不能写成观察结果。
- **直接四足开源缺口：** 截至检查日，没有发现同时满足“直接四足导航 VLA + 明确代码/模型/数据许可 + 完整部署入口 + 可低成本 smoke”的项目。OmniVLA 是跨 embodiment 的最佳可执行替代；NaVILA 是最相关但许可未闭合的条件候选。
- **OmniVLA 迁移缺口：** 语言敏感性、尺度、相机外参和速度分布未在 Lite3 上验证。
- **完整训练缺口：** OmniVLA 的 CAST 转换链、混合数据资产治理不够完整，因此本轮只推荐预训练推理，不推荐先重训。
- **户外森林缺口：** 当前 VLA/VLN 多数在室内或城市/校园数据上训练。森林地形的可通行性、坡度、灌木/树根/倒木判断仍需 WVN/ViPlanner/自有感知作为独立安全层，不能指望语言模型补足。

## 11. 人工选择门

本轮在这里停止。当前裁决为：

- 首选：**OmniVLA**；
- 备选：**InternVLA-N1 / InternNav**；
- 第三候选：**VLFM**，仅作为合规、透明的分层语义导航基线；
- 条件候选：**NaVILA**，等待模型/数据许可与 Go2/locomotion 发布链闭合后重评；
- 当前状态：**`surveyed`**。

未经 Dr Sun 选择，不导入代码、不创建上游分支、不运行命令、不接入 Lite3。

## 附录 A：本次产物

- 主报告：`.pipeline/survey/2026-08-16_lite3_vla_open_source_reproduction_survey.md`
- 待合并 literature 块：`.pipeline/literature/2026-08-16_surveyed_append.md`
- 公开 PDF：`docs/research/papers/<CitationKey>.pdf`
- PDF 页数、来源与 SHA-256：staging 根目录 `audit/paper_pdf_manifest.tsv`
- 仓库审计表：`audit/repository_audit.tsv`
- Top 5 统一字段证据表：`audit/top5_code_evidence.tsv`
- 来源登记：`audit/source_register.tsv`
- 检索日志：`audit/search_log.md`
- 内部一致性验证：`audit/validation_report.md`
- 可重复的本地验证脚本：`audit/validate_staging.py`
- 未应用动作：staging 根目录 `UNAPPLIED_PROJECT_ACTIONS.md`

## 附录 B：审计口径

“最近一次实质提交”排除纯 stars、fork、自动格式化和只改 citation 的情况；若固定 head 只是 README，报告同时记录最近功能性 commit。资源数字优先采用官方文档；官方未给出时写“未找到”或标成“本轮执行预算/工程估计”。没有任何结果从演示视频反推为复现成功。
