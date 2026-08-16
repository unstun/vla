---
origin: ai_only
reviewed: false
as_of: 2026-08-16
---

# 未应用到 `/Users/sun/vla` 的项目动作

当前执行环境没有挂载 `/Users/sun/vla`，因此以下动作没有执行：

- 未读取 `AGENTS.md`、状态简报、现有 literature index、terminology、upstream README；
- 未读取或创建 Trellis 活动任务；
- 未写入真实 `.pipeline/survey/...`；
- 未修改真实 `.pipeline/literature/index.md`；
- 未编辑只读 `machine-dog-nav`；
- 未导入候选仓库；
- 未运行上游安装、推理、仿真、训练或真机命令。

本 staging 包提供：

1. 按目标相对路径生成的主报告镜像；
2. `2026-08-16_surveyed_append.md`，用于在读取真实 index 后人工合并；
3. 24 篇可公开获取论文 PDF 与 SHA-256 清单；
4. 21 项仓库审计表、Top 5 统一字段证据表、来源登记表、检索日志；
5. 人工选择门。

应用顺序应为：先挂载项目 → 完整读取治理文件与 Trellis → 确认任务写入规则 → 审阅 staged 内容 → 合并而非覆盖 index → 保持 `surveyed` 状态。
