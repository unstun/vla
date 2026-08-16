---
origin: ai_only
reviewed: false
as_of: 2026-08-16
---

# 来源会话记录：VLA 四足机器人调研

## 来源

- 会话标题：`VLA四足机器人调研`
- 会话 ID：`6a817fcc-aad0-83e8-97c2-c299b1f2df8f`
- 会话链接：`chatgpt-conversation://6a817fcc-aad0-83e8-97c2-c299b1f2df8f`
- 当前读取日期：2026-08-16
- 信任边界：这是 AI 生成的外部调研结果，只能作为待核验线索。

## 已读取到的核心结论

- 首选建议：OmniVLA。
- 备选建议：InternVLA-N1 / InternNav。
- 条件候选：NaVILA；技术匹配度高，但先前会话认为模型与数据许可材料未闭合。
- 分层语义导航对照：VLFM；先前会话认为代码和 Habitat 入口明确，但不是统一导航 VLA，且维护和依赖栈偏旧。
- 最大不确定性：OmniVLA 到 Lite3 的相机视角、尺度、速度范围和语言分布迁移。
- 先前会话明确声明所有结果仅为 `surveyed`，未执行安装、推理、仿真、训练或真机动作。

## 已声明的附件

- 主调研报告。
- 完整 staging 包，约 202 MB，称包含 24 篇论文 PDF。
- 轻量 staging 包，约 61 KB，不含 PDF。
- literature index 待合并追加块。
- Top 5 代码证据表、全部候选仓库审计表、PDF 清单、来源登记表、检索日志、内部验证报告、文件校验清单和未应用动作清单。

## 会话声明的包哈希

- 完整包：`bbc468a3ad00e802f655e55af06d475ed4d64f47f826a2f8fdc12628a86631b5`
- 轻量包：`963e76a9e395aa1c83b840ac48c5d2a031962e18a26e1e9f4f6ef12be200a31f`

这些数值原本只是待核验预期；下节记录本轮真实下载结果。

## 本轮真实附件清单

- 下载页面：`https://chatgpt.com/c/6a817fcc-aad0-83e8-97c2-c299b1f2df8f`。
- 页面中实际取得两个独立下载按钮；其余主报告和支持文件作为 ZIP 内条目取得，
  没有伪称为单独附件。
- `2026-08-16_lite3_vla_survey_staging_full.zip`：211,553,810 字节，
  本地 SHA-256 为
  `bbc468a3ad00e802f655e55af06d475ed4d64f47f826a2f8fdc12628a86631b5`，
  与会话声明一致；47 个 ZIP 条目，含 24 篇 PDF。
- `2026-08-16_lite3_vla_survey_staging_core.zip`：61,598 字节，
  本地 SHA-256 为
  `963e76a9e395aa1c83b840ac48c5d2a031962e18a26e1e9f4f6ef12be200a31f`，
  与会话声明一致；24 个 ZIP 条目，不含 PDF。
- 两个原始文件保存在
  `.pipeline/survey/local-artifacts/2026-08-16_lite3_vla_survey/`，具体大小、
  哈希和恢复方式见 `artifact_manifest.tsv`。

## 导入后的项目边界

- 先前会话没有挂载 `/Users/sun/vla`；本轮只把调研证据和本地二进制归档进
  项目，没有导入候选代码。
- literature index 已合并 24 篇论文和 21 个仓库的 `surveyed` 记录。
- 尚未选定或导入 VLA 架构、动作接口、`machine-dog-nav` 基线或候选仓库。
- 本任务只负责归档、完整性核验和可追溯的 `surveyed` 级审计。
