---
origin: ai_only
reviewed: false
as_of: 2026-08-16
---

# 检索与核验日志

## 执行边界

- 主时间窗：2023-01-01 至 2026-08-16。
- 最近 18 个月优先窗：2025-02-16 至 2026-08-16。
- 关键前序工作例外：LM-Nav、VLMaps 等早期基础工作。
- 本轮仅静态检索、代码树/README/许可证/模型卡/数据卡/issue 审计与公开 PDF 获取；没有 clone 或运行任何上游命令。
- 所有结论状态：`surveyed`。

## 渠道

arXiv、OpenReview、RSS Online Proceedings、PMLR、CVF Open Access、IEEE/ICRA 项目元数据、作者项目页、canonical GitHub repository、GitHub issue/release/commit、Hugging Face model/dataset cards。

## 核心查询词

- quadruped vision language action
- legged robot VLA
- robot dog vision language navigation
- language-conditioned quadruped navigation
- vision-language navigation legged robot
- VLM quadruped locomotion navigation
- semantic navigation quadruped open source
- outdoor embodied navigation vision language
- terrain-aware language navigation legged robot
- Unitree Go2 VLA navigation
- ANYmal language navigation
- Spot vision language navigation
- embodied VLA waypoint navigation open source

## 扩展查询

- navigation VLA trajectory waypoint velocity command pixel goal discrete action
- dual-system VLN foundation model Go2
- quadruped language locomotion contact plan
- open-vocabulary semantic map frontier waypoint Spot
- streaming VLN real-world deployment
- model card license dataset card license navigation VLA
- repository LICENSE checkpoint README command source entry

## 核验规则

1. 搜索结果只作线索，回到论文原文、项目页、canonical repository、模型卡或数据卡。
2. 许可证分别检查代码、模型权重、数据；README 自称 open source 不等于许可证成立。
3. README 命令必须能在固定 commit 的源码树中找到对应入口，才计为“有入口”。
4. 运行结果、时延、显存占用均未实测；官方未给出的资源数字写“未找到”或明确标为审计预算/工程估计。
5. 纯机械臂 VLA、纯 locomotion、纯视觉导航只作邻近对照，不计入四足导航 VLA shortlist。
