---
origin: ai_only
reviewed: false
as_of: 2026-08-16
---

# Lite3 VLA 调研包本地导入审计

## 结论

会话 `6a817fcc-aad0-83e8-97c2-c299b1f2df8f` 中的两份调研包已完整下载到
本地，文件哈希与会话给出的值一致。报告、24 篇论文 PDF、仓库审计表和来源
登记表已归档进 `/Users/sun/tongbu/study/phdproject/vla`。当前最强证据标签是 `surveyed`；本次工作没有
导入候选仓库、模型或数据，没有安装依赖，也没有执行推理、仿真、训练或真机
控制。

`OmniVLA` 仍是该 AI 调研报告给出的第一复现建议，但它尚未成为 Dr Sun 已选择
的项目基线。`InternVLA-N1 / InternNav` 仍是技术备选；其模型卡顶部徽章声明
CC BY-NC-SA 4.0，但 Hugging Face API 的 `cardData` 为空，模型仓文件树也没有
独立许可证文件，因此使用或下载前应由人工保存并确认当时的完整条款。

## 本轮实际完成的检查

- 完整包：211,553,810 字节，SHA-256
  `bbc468a3ad00e802f655e55af06d475ed4d64f47f826a2f8fdc12628a86631b5`。
- 精简包：61,598 字节，SHA-256
  `963e76a9e395aa1c83b840ac48c5d2a031962e18a26e1e9f4f6ef12be200a31f`。
- 两个 ZIP 的完整性测试通过；完整包 47 个条目，精简包 24 个条目；所有路径
  都是相对路径，未发现目录穿越、绝对路径、设备文件或符号链接。
- 完整包自带的 `MANIFEST.sha256` 对 35 个文件全部通过；其只读校验脚本在本地
  复跑得到 `PASS: 294 internal checks`。
- `source_register.tsv` 中 46 个官方来源 URL 均能访问；19 个仓库固定 commit
  页面均能访问。
- 24 份 PDF 的文件签名、字节数、SHA-256 和论文身份已复核；其中
  `Zhang2025UniNaVid.pdf` 无文本层，改用渲染后的首页做视觉身份确认。
- 对 OmniVLA、InternVLA-N1 / InternNav、NaVILA、LeLaN 和 VLFM 重新检查了
  官方仓库、许可证、入口、动作接口、模型/数据页面和关键公开问题。

## 导入时发现并修正的差异

1. 原始 `paper_pdf_manifest.tsv` 中 LeLaN 的 PMLR PDF 路径已返回 404。PMLR
   proceedings 页面当前链接到
   `https://raw.githubusercontent.com/mlresearch/v270/main/assets/hirose25b/hirose25b.pdf`；
   新地址文件长度和本地文件完全一致，当前项目清单已改用该地址。原始 ZIP
   保持不变。
2. InternVLA 模型卡确实显示 CC BY-NC-SA 4.0 徽章，但没有标准 YAML
   许可证元数据或独立许可证文件。项目内报告和两张审计表已改为
   `PASS-WITH-RESTRICTION-AND-METADATA-GAP`，避免把徽章声明写成完整的
   许可证闭环。InternData-N1 的 gated、非商业限制继续按更严格正文处理。
3. 原报告第 0 节的“未挂载 `/Users/sun/vla`”只描述调研包生成环境。当前本地
   导入已完成，但这不改变任何候选项目的运行证据等级。

## Top 5 当前证据边界

| 候选 | 当前核验结论 | 仍未证明 |
|---|---|---|
| OmniVLA | 固定 commit、MIT 代码、MIT 官方模型卡、离线入口和 8×4 连续轨迹接口可核验 | 未下载模型，未安装或运行；Lite3 相机、尺度与 prompt sensitivity 未验证 |
| InternVLA-N1 / InternNav | MIT 代码、官方 server/client、模型卡 NC 徽章、gated 数据协议和 Go2 路线可核验 | 模型许可元数据不完整；依赖兼容性、资源预算和 Lite3 bridge 未运行 |
| NaVILA | Apache-2.0 代码和四足中层动作链可核验 | 主模型与主数据许可仍未闭合；完整 Go2/locomotion 发布链未证明 |
| LeLaN | MIT 代码及 `/waypoint`、`/vel_lelan`、`/cmd_vel` 接口可核验 | 权重与聚合数据许可未闭合；ROS1 老依赖未运行 |
| VLFM | MIT 主代码、RGB-D frontier waypoint 分层和官方入口可核验 | 第三方许可证矩阵、gated 场景与老软件栈未运行；它不是端到端 VLA |

## 本地存储与恢复

- 两份原始 ZIP 位于
  `.pipeline/survey/local-artifacts/2026-08-16_lite3_vla_survey/`。
- 24 篇 PDF 位于 `docs/research/papers/`。
- 上述二进制只按精确路径忽略；来源、大小、SHA-256 和恢复方法记录在
  [`artifact_manifest.tsv`](artifact_manifest.tsv)。
- 报告和支持表保留 `origin: ai_only` / `reviewed: false` 的人工复核门槛。

## 尚待 Dr Sun 决定

1. 是否接受报告的 OmniVLA 第一 smoke 候选建议；接受前不导入代码或模型。
2. InternVLA 的模型卡许可证元数据缺口是否足以阻止下载和内部研究评估。
3. 第一条 VLA contract、导入的 `machine-dog-nav` 干净提交和停止条件。
