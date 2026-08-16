---
name: project-sync
description: |-
  Lite3 VLA 项目状态同步 SOP。触发：Dr Sun 说“同步状态/刷新热区/sync/文档没更新/补台账”。
argument-hint: "[可选：需要同步的遗漏进展]"
user-invocable: true
context: inline
---

# Lite3 VLA 状态同步

读取以下状态源：

```
bigmemory/热区/状态简报.md
bigmemory/热区/未关闭决策.md
bigmemory/热区/近期改动.md
.pipeline/literature/index.md
.pipeline/experiments/
.pipeline/survey/
.pipeline/terminology/terminology.md
.trellis/tasks/
references/upstream/
```

同步内容：

1. 刷新热区三个文件，保持容量预算。
2. 检查新复现或集成运行是否有 `.pipeline/experiments/` 记录。
3. 检查新论文和上游仓库是否进入 `.pipeline/literature/index.md`。
4. 检查上游仓库是否记录 URL、许可证和固定 commit。
5. 检查新术语是否进入 `.pipeline/terminology/terminology.md`。
6. AI 编辑 `reviewed: true` 文档时重置为 `reviewed: false`。

同步后运行本项目的 harness 检查；没有检查脚本时明确列出手工检查项。
