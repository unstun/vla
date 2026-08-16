---
origin: ai_only
reviewed: false
as_of: 2026-08-16
---

# Lite3 VLA 调研 staging 包

本包是目标项目 `/Users/sun/vla` 的**隔离镜像交付**。当前执行环境没有挂载该路径，因此没有读取真实 `AGENTS.md`、状态简报、terminology、现有 literature index、upstream README 或 Trellis 任务，也没有向真实项目写入任何文件。

## 裁决

- 首选复现对象：`OmniVLA`。
- 备选：`InternVLA-N1 / InternNav`。
- 第三候选：`VLFM`，仅作为分层语义导航基线，不是完整端到端 VLA。
- 技术条件候选：`NaVILA`；模型/数据许可证与实机发布链闭合后再重评。
- 所有证据状态：`surveyed`；没有运行任何上游安装、推理、仿真、训练或真机命令。

## 主要文件

- 主报告：`Users/sun/vla/.pipeline/survey/2026-08-16_lite3_vla_open_source_reproduction_survey.md`
- literature 待合并块：`Users/sun/vla/.pipeline/literature/2026-08-16_surveyed_append.md`
- 论文 PDF：`Users/sun/vla/docs/research/papers/`（24 篇）
- PDF 来源/页数/SHA-256：`audit/paper_pdf_manifest.tsv`
- 21 项仓库审计：`audit/repository_audit.tsv`
- Top 5 代码级统一字段：`audit/top5_code_evidence.tsv`
- 原始来源登记：`audit/source_register.tsv`
- 检索日志：`audit/search_log.md`
- 内部一致性验证：`audit/validation_report.md`
- 可重复的本地验证脚本：`audit/validate_staging.py`
- 未应用动作：`UNAPPLIED_PROJECT_ACTIONS.md`
- 全包校验：`MANIFEST.sha256`

## 应用规则

1. 先在真实项目中完整读取治理文件与当前 Trellis 任务。
2. 将主报告按目标路径审阅写入。
3. literature 文件只能作为**追加/合并块**，不得覆盖现有 `index.md`。
4. PDF 可按 manifest 校验后复制。
5. 在 Dr Sun 明确选择前，不 clone 候选仓库、不启动 smoke、不创建集成分支。
6. 后续只有固定上游 commit/revision、官方命令成功并保存日志/输出后，才能按项目规则从 `surveyed` 升级。
